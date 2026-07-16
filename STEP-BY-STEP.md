# Laboratorio: Login con Docker, Flask y MySQL

Guia paso a paso para replicar el laboratorio desde cero en cualquier maquina.

---

## Indice

1. [Requisitos previos](#1-requisitos-previos)
2. [Estructura del proyecto](#2-estructura-del-proyecto)
3. [Crear el archivo .env](#3-crear-el-archivo-env)
4. [Crear config.py](#4-crear-configpy)
5. [Crear api.py](#5-crear-apipy)
6. [Crear Dockerfile](#6-crear-dockerfile)
7. [Crear requirements.txt](#7-crear-requirementstxt)
8. [Crear docker-compose.yml](#8-crear-docker-composeyml)
9. [Crear el frontend: index.html](#9-crear-el-frontend-indexhtml)
10. [Crear el frontend: registro.html](#10-crear-el-frontend-registrohtml)
11. [Crear el frontend: dashboard.html](#11-crear-el-frontend-dashboardhtml)
12. [Crear el archivo script.js](#12-crear-el-archivo-scriptjs)
13. [Crear el archivo style.css](#13-crear-el-archivo-stylecss)
14. [Crear .gitignore](#14-crear-gitignore)
15. [Ejecutar el laboratorio](#15-ejecutar-el-laboratorio)
16. [Probar el flujo completo](#16-probar-el-flujo-completo)
17. [Solucion de problemas](#17-solucion-de-problemas)

---

## 1. Requisitos previos

Antes de empezar necesitas tener instalado:

### Docker y Docker Compose

```bash
# En Arch Linux
sudo pacman -S docker docker-compose

# En Ubuntu/Debian
sudo apt install docker.io docker-compose

# En Windows/Mac: instalar Docker Desktop desde https://www.docker.com/products/docker-desktop
```

Una vez instalado, verificar:

```bash
docker --version
docker compose version
```

### Habilitar el servicio Docker

```bash
# En Linux
sudo systemctl enable --now docker

# Verificar que este corriendo
sudo systemctl status docker
```

### Python (opcional, solo para desarrollo local)

```bash
# Solo si quieres probar la API fuera de Docker
python3 --version
```

### Un navegador web

Cualquier navegador moderno (Firefox, Chrome, Edge).

---

## 2. Estructura del proyecto

Crear la siguiente estructura de carpetas. Desde la terminal:

```bash
# Crear carpeta raiz del proyecto
mkdir docker_login
cd docker_login

# Crear subcarpeta docker (backend)
mkdir docker

# Crear subcarpetas del frontend
mkdir login
mkdir login/css
mkdir login/js
mkdir login/img
```

La estructura final debe verse asi:

```
docker_login/
├── docker/
│   ├── .env
│   ├── config.py
│   ├── api.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
└── login/
    ├── index.html
    ├── registro.html
    ├── dashboard.html
    ├── css/
    │   └── style.css
    ├── js/
    │   └── script.js
    └── img/
        └── (opcional: imagen de fondo)
```

---

## 3. Crear el archivo .env

Crear el archivo `docker/.env` con el siguiente contenido:

```bash
nano docker/.env
```

Pegar exactamente:

```
MYSQL_HOST=basedatos
MYSQL_ROOT_PASSWORD=una_clave_segura_root
MYSQL_DATABASE=practica_db
MYSQL_USER=api_usuario
MYSQL_PASSWORD=una_clave_segura_api
SECRET_KEY=0b855363bc44f16d8f73342325475f27d21bdef8263a24de8f468603d0466ef2
```

Guardar con Ctrl+O y salir con Ctrl+X.

**Que hace este archivo:**

- `MYSQL_HOST=basedatos` es el nombre del servicio MySQL dentro de Docker. Docker resuelve este nombre automaticamente a la direccion interna del contenedor de base de datos.
- `MYSQL_ROOT_PASSWORD` es la contrasena del usuario administrador de MySQL (root).
- `MYSQL_DATABASE` es el nombre de la base de datos que se crea automaticamente cuando el contenedor de MySQL arranca por primera vez.
- `MYSQL_USER` y `MYSQL_PASSWORD` son credenciales de un usuario normal, sin privilegios de administrador, que nuestra API usa para conectarse. Es mala practica usar el usuario root desde la aplicacion.
- `SECRET_KEY` es la clave secreta para firmar y verificar tokens JWT. Nunca debe subirse a Git.

---

## 4. Crear config.py

Crear el archivo `docker/config.py`:

```bash
nano docker/config.py
```

Pegar:

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "basedatos")
    MYSQL_USER = os.environ.get("MYSQL_USER")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")

    # Clave secreta para firmar tokens JWT.
    # Se lee desde .env, nunca esta hardcodeada aqui.
    SECRET_KEY = os.environ.get("SECRET_KEY")
```

**Que hace este archivo:**

- `load_dotenv()` carga las variables del archivo `.env` al entorno del sistema.
- La clase `Config` centraliza toda la configuracion en un solo lugar. En vez de leer `os.environ.get("MYSQL_USER")` en diez archivos diferentes, lo leemos una vez aqui y lo importamos con `Config.MYSQL_USER`.
- `os.environ.get("CLAVE", "valor_por_defecto")` lee una variable de entorno. Si no existe, usa el valor por defecto (solo `MYSQL_HOST` tiene uno).

---

## 5. Crear api.py

Crear el archivo `docker/api.py` con TODO el siguiente contenido:

```bash
nano docker/api.py
```

Pegar:

```python
# ============================================================
# Imports: traemos las librerias que necesitamos
# ============================================================

# Flask: framework web para crear la API
from flask import Flask
from flask import jsonify    # jsonify convierte diccionarios de Python en respuestas JSON
from flask import request    # request permite leer los datos que llegan en cada peticion HTTP

# flask-cors: permite que nuestro frontend (en otro puerto/dominio) se comunique con la API
from flask_cors import CORS

# werkzeug.security: funciones para hashear y verificar contrasenas de forma segura
# Nunca almacenamos contrasenas en texto plano, solo hashes
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

# jwt: libreria para crear (encode) y verificar (decode) tokens JWT
import jwt

# datetime: para calcular la fecha de expiracion del token
import datetime

# functools.wraps: se usa dentro de nuestro decorador personalizado
# para que Flask siga reconociendo correctamente el nombre de cada
# funcion protegida, en vez de confundirlas entre si
from functools import wraps

# mysql.connector: driver para conectarnos a MySQL desde Python
import mysql.connector

# Config: nuestra clase de configuracion centralizada
from config import Config


# ============================================================
# Crear la aplicacion Flask
# ============================================================

app = Flask(__name__)

# CORS restringido solo a http://localhost:8080, que es de donde
# se sirve el frontend (python -m http.server 8080).
# Esto impide que otros sitios web hagan peticiones Ajax no autorizadas.
# En produccion, cambiar al dominio real (ej: "https.midominio.com").
CORS(app, origins=["http://localhost:8080"])


# ============================================================
# Conexion a la base de datos
# ============================================================

def get_connection():
    """Crea y devuelve una conexion nueva a MySQL usando las credenciales de Config."""
    connection = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
    )
    return connection


# ============================================================
# Crear las tablas si no existen
# ============================================================

def create_table():
    """
    Crea las tablas 'usuarios' e 'intentos_login' si no existen.
    Se ejecuta cuando la API arranca (al final de este archivo).
    """
    connection = get_connection()
    cursor = connection.cursor()

    # Tabla de usuarios: almacena nombre, correo y contrasena hasheada
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            correo VARCHAR(150) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL
        )
    """
    )

    # Tabla de intentos de login: proteccion contra fuerza bruta.
    # Cada fila almacena: el correo, el numero de intentos fallidos
    # consecutivos, cuando ocurrio el primer intento, y hasta cuando
    # esta bloqueada la cuenta.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS intentos_login (
            id INT AUTO_INCREMENT PRIMARY KEY,
            correo VARCHAR(150) NOT NULL,
            intentos INT NOT NULL DEFAULT 1,
            primer_intento DATETIME NOT NULL,
            bloqueado_hasta DATETIME DEFAULT NULL,
            UNIQUE KEY idx_correo (correo)
        )
    """
    )

    connection.commit()
    cursor.close()
    connection.close()


# ============================================================
# Decorador: proteger rutas con JWT
# ============================================================

def token_required(original_function):
    """
    Decorador personalizado que verifica el token JWT antes de
    dejar pasar la peticion a la funcion protegida.

    Un decorador es una funcion que envuelve a otra funcion para
    agregarle comportamiento extra. En este caso, verifica el
    token antes de ejecutar la funcion original.
    """
    @wraps(original_function)
    def wrapper_function(*args, **kwargs):
        token = None

        # Se espera el token en el header HTTP "Authorization"
        # con el formato "Bearer <token>".
        # Verificamos si ese header existe en la peticion.
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            # Separamos la palabra "Bearer" del token real
            parts = auth_header.split(" ")
            if len(parts) == 2 and parts[0] == "Bearer":
                token = parts[1]

        if not token:
            return jsonify({"error": "Authentication token required"}), 401

        try:
            # jwt.decode verifica la firma del token usando la misma
            # clave secreta con la que fue creado. Si alguien modifico
            # el token, o si expiro, esta linea lanza una excepcion.
            token_data = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return (
                jsonify({"error": "Token has expired, please log in again"}),
                401,
            )
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        # Si todo salio bien, dejamos pasar la peticion a la
        # funcion original, pasando los datos verificados del usuario
        # como primer argumento.
        return original_function(token_data, *args, **kwargs)

    return wrapper_function


# ============================================================
# Rutas publicas (no requieren token)
# ============================================================

@app.route("/", methods=["GET"])
def index():
    """Ruta raiz: solo retorna un mensaje de bienvenida."""
    return jsonify({"message": "Welcome to my first Flask API"})


@app.route("/saludo", methods=["GET"])
def greeting():
    """Ruta de prueba: retorna un saludo."""
    return jsonify({"message": "Hello orami, this is another API route"})


# ============================================================
# CRUD de usuarios (todas requieren token)
# ============================================================

@app.route("/usuarios", methods=["GET"])
@token_required
def list_users(token_data):
    """
    Listar todos los usuarios (protegido con token).
    Solo un usuario autenticado deberia poder ver esta lista,
    porque revela informacion de todos los registros.
    """
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, nombre, correo FROM usuarios")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    user_list = []
    for row in rows:
        user_list.append({"id": row[0], "nombre": row[1], "correo": row[2]})

    return jsonify(user_list)


@app.route("/usuarios", methods=["POST"])
@token_required
def create_user(token_data):
    """
    Crear un usuario (protegido con token).
    La funcion recibe token_data como primer argumento,
    inyectado automaticamente por el decorador.
    """
    data = request.get_json()

    if (
        not data
        or "nombre" not in data
        or "correo" not in data
        or "password" not in data
    ):
        return (
            jsonify({"error": "Fields nombre, correo and password are required"}),
            400,
        )

    nombre = data["nombre"]
    correo = data["correo"]
    password_hash = generate_password_hash(data["password"])

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO usuarios (nombre, correo, password) VALUES (%s, %s, %s)",
        (nombre, correo, password_hash),
    )
    connection.commit()
    new_id = cursor.lastrowid
    cursor.close()
    connection.close()

    return jsonify({"id": new_id, "nombre": nombre, "correo": correo}), 201


@app.route("/usuarios/<int:user_id>", methods=["PUT"])
@token_required
def edit_user(token_data, user_id):
    """
    Editar un usuario (protegido con token).
    Aqui token_data viene primero, y user_id (de la URL) despues.
    El orden importa: el decorador siempre inyecta token_data
    como primer argumento posicional.
    """
    data = request.get_json()

    if not data or "nombre" not in data or "correo" not in data:
        return jsonify({"error": "Fields nombre and correo are required"}), 400

    nombre = data["nombre"]
    correo = data["correo"]

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE id = %s", (user_id,))
    if cursor.fetchone() is None:
        cursor.close()
        connection.close()
        return jsonify({"error": "User not found"}), 404

    cursor.execute(
        "UPDATE usuarios SET nombre = %s, correo = %s WHERE id = %s",
        (nombre, correo, user_id),
    )
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({"id": user_id, "nombre": nombre, "correo": correo}), 200


@app.route("/usuarios/<int:user_id>", methods=["DELETE"])
@token_required
def delete_user(token_data, user_id):
    """Eliminar un usuario (protegido con token)."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE id = %s", (user_id,))
    if cursor.fetchone() is None:
        cursor.close()
        connection.close()
        return jsonify({"error": "User not found"}), 404

    cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
    connection.commit()
    cursor.close()
    connection.close()

    return (
        jsonify({"message": "User deleted successfully", "id": user_id}),
        200,
    )


# ============================================================
# LOGIN - Autenticacion con JWT + proteccion fuerza bruta
# ============================================================

@app.route("/login", methods=["POST"])
def login():
    """
    Ruta de login: verifica credenciales y genera un token JWT.
    Incluye proteccion contra fuerza bruta.
    """
    data = request.get_json()

    if not data or "correo" not in data or "password" not in data:
        return jsonify({"error": "Fields correo and password are required"}), 400

    correo = data["correo"]
    password = data["password"]

    connection = get_connection()
    cursor = connection.cursor()

    # --- PROTECCION CONTRA FUERZA BRUTA ---
    # MAX_INTENTOS = intentos fallidos maximos permitidos antes de bloquear.
    # TIEMPO_BLOQUEO = minutos que la cuenta queda bloqueada despues de exceder el limite.
    MAX_INTENTOS = 5
    TIEMPO_BLOQUEO = 15

    cursor.execute(
        "SELECT intentos, bloqueado_hasta FROM intentos_login WHERE correo = %s",
        (correo,),
    )
    registro = cursor.fetchone()

    if registro:
        intentos, bloqueado_hasta = registro

        # Si la cuenta esta bloqueada y el tiempo de bloqueo no expiro,
        # rechazamos la peticion inmediatamente con 429 (Too Many Requests).
        if bloqueado_hasta and bloqueado_hasta > datetime.datetime.utcnow():
            remaining = bloqueado_hasta - datetime.datetime.utcnow()
            remaining_seconds = int(remaining.total_seconds())
            cursor.close()
            connection.close()
            return (
                jsonify(
                    {
                        "error": "Too many failed attempts, try again later",
                        "retry_after_seconds": remaining_seconds,
                    }
                ),
                429,
            )

    # --- VERIFICACION DE CREDENCIALES ---
    cursor.execute(
        "SELECT id, nombre, correo, password FROM usuarios WHERE correo = %s", (correo,)
    )
    user = cursor.fetchone()

    generic_error = jsonify({"error": "Incorrect email or password"}), 401

    if user is None:
        # Si el usuario no existe, igual registramos un intento fallido
        # para evitar que un atacante detecte emails validos verificando
        # si el contador se incrementa.
        _registrar_intento_fallido(cursor, correo, MAX_INTENTOS, TIEMPO_BLOQUEO)
        connection.commit()
        cursor.close()
        connection.close()
        return generic_error

    user_id, nombre, correo_bd, password_hash = user

    if not check_password_hash(password_hash, password):
        # Contrasena incorrecta: registramos el intento fallido y
        # bloqueamos si se alcanzo el limite.
        _registrar_intento_fallido(cursor, correo, MAX_INTENTOS, TIEMPO_BLOQUEO)
        connection.commit()
        cursor.close()
        connection.close()
        return generic_error

    # --- LOGIN EXITOSO ---
    # Si las credenciales son correctas, borramos cualquier registro
    # de intentos fallidos para este correo, reseteando el contador.
    cursor.execute("DELETE FROM intentos_login WHERE correo = %s", (correo,))
    connection.commit()
    cursor.close()
    connection.close()

    # Construimos el payload del token. "exp" es una clave especial
    # que jwt reconoce automaticamente como fecha de expiracion.
    # Aqui el token sera valido por 1 hora desde su creacion.
    payload = {
        "id": user_id,
        "nombre": nombre,
        "correo": correo_bd,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }

    # jwt.encode firma el payload con nuestra clave secreta usando
    # el algoritmo HS256, uno de los mas comunes para este proposito.
    token = jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")

    return (
        jsonify(
            {
                "message": "Login successful",
                "id": user_id,
                "nombre": nombre,
                "correo": correo_bd,
                "token": token,
            }
        ),
        200,
    )


def _registrar_intento_fallido(cursor, correo, max_intentos, tiempo_bloqueo):
    """
    Funcion auxiliar que maneja la logica de registrar un intento
    de login fallido. Se llama desde la ruta /login cuando las
    credenciales son invalidas.

    Parametros:
      cursor: el cursor activo de la base de datos
      correo: el correo que fallo al autenticar
      max_intentos: maximo de intentos permitidos
      tiempo_bloqueo: minutos de bloqueo despues de exceder el limite

    Si no existe registro para este correo, se crea uno con 1 intento.
    Si existe y el periodo de bloqueo expiro, el contador se resetea.
    Si existe y no esta bloqueado, el contador se incrementa.
    Si el contador alcanza max_intentos, la cuenta se bloquea.
    """
    now = datetime.datetime.utcnow()

    cursor.execute(
        "SELECT intentos, primer_intento FROM intentos_login WHERE correo = %s",
        (correo,),
    )
    registro = cursor.fetchone()

    if registro is None:
        # Primer intento fallido para este correo: crear un registro nuevo.
        cursor.execute(
            "INSERT INTO intentos_login (correo, intentos, primer_intento) "
            "VALUES (%s, 1, %s)",
            (correo, now),
        )
    else:
        intentos, primer_intento = registro

        # Si paso mas tiempo del permitido desde el primer intento,
        # reseteamos el contador.
        if (now - primer_intento).total_seconds() > tiempo_bloqueo * 60:
            cursor.execute(
                "UPDATE intentos_login SET intentos = 1, primer_intento = %s, "
                "bloqueado_hasta = NULL WHERE correo = %s",
                (now, correo),
            )
        else:
            # Incrementar el contador. Si alcanza el limite, bloquear.
            nuevos_intentos = intentos + 1
            if nuevos_intentos >= max_intentos:
                bloqueado_hasta = now + datetime.timedelta(minutes=tiempo_bloqueo)
                cursor.execute(
                    "UPDATE intentos_login SET intentos = %s, "
                    "bloqueado_hasta = %s WHERE correo = %s",
                    (nuevos_intentos, bloqueado_hasta, correo),
                )
            else:
                cursor.execute(
                    "UPDATE intentos_login SET intentos = %s WHERE correo = %s",
                    (nuevos_intentos, correo),
                )


# ============================================================
# REGISTRO - Ruta publica (no requiere token)
# ============================================================
# Diferencia con POST /usuarios:
# - POST /usuarios: requiere token (solo usuarios autenticados
#   pueden crear otros usuarios, como en un panel de administracion)
# - POST /registro: no requiere token (cualquiera puede registrarse,
#   como en un sitio web publico)
#
# Esta separacion es una practica comun en aplicaciones reales:
# hay rutas publicas (registro, login) y rutas protegidas (CRUD).

@app.route("/registro", methods=["POST"])
def register():
    """
    Ruta de registro: crea un usuario nuevo.
    NO requiere token porque es el punto de entrada para nuevos usuarios.
    """
    data = request.get_json()

    # Validamos que los tres campos requeridos esten presentes.
    # Si falta alguno, devolvemos un 400 (Bad Request).
    if (
        not data
        or "nombre" not in data
        or "correo" not in data
        or "password" not in data
    ):
        return (
            jsonify({"error": "Fields nombre, correo and password are required"}),
            400,
        )

    nombre = data["nombre"]
    correo = data["correo"]
    password = data["password"]

    # Validacion basica de seguridad: la contrasena debe tener
    # al menos 6 caracteres. Esto evita contrasenas como "123".
    if len(password) < 6:
        return (
            jsonify({"error": "Password must be at least 6 characters long"}),
            400,
        )

    # generate_password_hash convierte la contrasena en un hash seguro.
    # Nunca almacenamos la contrasena en texto plano. El hash incluye
    # automaticamente una "salt" (valor aleatorio) que hace que dos
    # contrasenas identicas produzcan hashes diferentes.
    password_hash = generate_password_hash(password)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO usuarios (nombre, correo, password) VALUES (%s, %s, %s)",
            (nombre, correo, password_hash),
        )
        connection.commit()
        new_id = cursor.lastrowid
    except mysql.connector.errors.IntegrityError:
        # Si el correo ya existe en la base de datos, MySQL lanza
        # un error de integridad (por la restriccion UNIQUE).
        # Capturamos ese error y devolvemos un mensaje amigable.
        cursor.close()
        connection.close()
        return (
            jsonify({"error": "An account with that email already exists"}),
            409,
        )
    finally:
        # finally siempre se ejecuta, haya ido bien o mal.
        # Aqui nos aseguramos de cerrar la conexion para no dejar
        # conexiones abiertas.
        cursor.close()
        connection.close()

    # Devolvemos 201 (Created), que es el codigo correcto cuando
    # se crea un nuevo recurso exitosamente.
    return jsonify({"id": new_id, "nombre": nombre, "correo": correo}), 201


# ============================================================
# VERIFICAR SESION - Protegida con token
# ============================================================

@app.route("/verificar-sesion", methods=["GET"])
@token_required
def verify_session(token_data):
    """
    Ruta protegida: solo responde si el token es valido.
    El decorador @token_required se encarga de toda la verificacion
    antes de que el codigo de esta funcion se ejecute.
    """
    return (
        jsonify(
            {
                "message": "Valid session",
                "nombre": token_data["nombre"],
                "correo": token_data["correo"],
            }
        ),
        200,
    )


# ============================================================
# Arranque: crear tablas al importar el modulo
# ============================================================
# Esto se ejecuta cuando Gunicorn importa api.py.
# create_table() esta FUERA del bloque if __name__ == "__main__"
# porque Gunicorn ejecuta el codigo directamente, no como "__main__".

create_table()


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
```

---

## 6. Crear Dockerfile

Crear el archivo `docker/Dockerfile`:

```bash
nano docker/Dockerfile
```

Pegar:

```dockerfile
# Imagen base: Python 3.12 en version slim (sin extras innecesarios)
FROM python:3.12-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar e instalar dependencias PRIMERO.
# Docker cachea esta capa: si requirements.txt no cambia,
# no reinstala las librerias cada vez que se reconstruye.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el codigo fuente despues de instalar dependencias
COPY config.py .
COPY api.py .

# Exponer el puerto que usara la API
EXPOSE 5000

# Comando de arranque: Gunicorn como servidor de produccion
# --bind 0.0.0.0:5000 = escuchar en todas las interfaces, puerto 5000
# --workers 4 = 4 procesos paralelos para manejar peticiones
# --access-logfile - = mostrar logs de accesos en consola
# api:app = importar el objeto "app" del archivo "api.py"
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--access-logfile", "-", "api:app"]
```

---

## 7. Crear requirements.txt

Crear el archivo `docker/requirements.txt`:

```bash
nano docker/requirements.txt
```

Pegar:

```
blinker==1.9.0
click==8.4.2
Flask==3.1.3
flask-cors==6.0.5
gunicorn==26.0.0
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
mysql-connector-python==9.7.0
packaging==26.2
PyJWT==2.13.0
python-dotenv==1.2.2
Werkzeug==3.1.8
```

**Que hace cada dependencia:**

| Paquete | Que hace |
|---|---|
| Flask | Framework web para crear la API REST |
| flask-cors | Permite peticiones entre origen cruzado (frontend y backend en puertos distintos) |
| gunicorn | Servidor HTTP de produccion (mucho mas rapido y seguro que el servidor de desarrollo de Flask) |
| mysql-connector-python | Driver para conectarse a MySQL desde Python |
| PyJWT | Crear y verificar tokens JWT |
| python-dotenv | Leer variables de entorno desde archivos .env |
| Werkzeug | Utilidades de seguridad (hashing de contrasenas) |

---

## 8. Crear docker-compose.yml

Crear el archivo `docker/docker-compose.yml`:

```bash
nano docker/docker-compose.yml
```

Pegar:

```yaml
services:
  basedatos:
    image: mysql:8.0
    env_file:
      - .env
    volumes:
      - datos_mysql:/var/lib/mysql
    ports:
      - "3306:3306"

    # healthcheck define una prueba que Docker ejecuta periodicamente
    # para verificar si el contenedor esta realmente listo, no solo iniciado.
    healthcheck:
      # test es el comando que Docker ejecuta dentro del contenedor.
      # mysqladmin ping es una utilidad incluida en la imagen de MySQL
      # que solo responde cuando el servidor acepta conexiones.
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      # interval: cada cuanto se repite la prueba
      interval: 5s
      # timeout: cuanto espera cada intento antes de marcar fallo
      timeout: 5s
      # retries: cuantas veces puede fallar la prueba antes de marcar
      # el contenedor como "unhealthy" (no saludable)
      retries: 10

  api:
    build: .
    env_file:
      - .env
    ports:
      - "5000:5000"

    # depends_on ahora usa un condition en vez del nombre del servicio.
    # condition: service_healthy le dice a Docker que espere hasta que
    # el healthcheck de basedatos responda correctamente antes de
    # iniciar el servicio api.
    depends_on:
      basedatos:
        condition: service_healthy

volumes:
  datos_mysql:
```

**Que hace cada servicio:**

- `basedatos`: Contenedor de MySQL 8.0. Se crea automaticamente la base de datos `practica_db` y el usuario `api_usuario` al iniciar por primera vez. Los datos se guardan en un volume para que no se pierdan al reiniciar.
- `api`: Contenedor de la API Flask. Se construye desde el Dockerfile. Espera a que MySQL este listo (healthcheck) antes de arrancar. Expone el puerto 5000 al host.

---

## 9. Crear el frontend: index.html

Crear el archivo `login/index.html`:

```bash
nano login/index.html
```

Pegar:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Log in</title>

    <!-- Bootstrap CSS desde CDN -->
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css"
      rel="stylesheet"
      integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB"
      crossorigin="anonymous"
    />

    <!-- Estilos personalizados -->
    <link rel="stylesheet" href="css/style.css" />
  </head>

  <body>
    <!-- container-fluid ocupa todo el ancho de la pantalla -->
    <!-- vh-100 lo hace ocupar todo el alto de la pantalla -->
    <!-- d-flex, align-items-center y justify-content-center centran -->
    <!-- el contenido vertical y horizontalmente -->
    <div
      class="container-fluid vh-100 d-flex align-items-center justify-content-center"
    >
      <!-- card es un componente de Bootstrap que crea una caja con sombra -->
      <!-- p-4 agrega espaciado interno (padding) nivel 4 -->
      <!-- shadow agrega una sombra suave alrededor de la caja -->
      <div class="card p-4 shadow" style="width: 100%; max-width: 400px">
        <h3 class="text-center mb-4">Log in</h3>

        <!-- id="formulario-login" es el identificador que script.js -->
        <!-- usa para capturar el envio del formulario -->
        <form id="formulario-login">
          <!-- mb-3 agrega espaciado debajo de cada grupo de campos -->
          <div class="mb-3">
            <label for="correo" class="form-label">Email</label>
            <!-- type="email" hace que el navegador valide automaticamente -->
            <!-- que el texto tenga formato de correo electronico -->
            <!-- required impide enviar el formulario si el campo esta vacio -->
            <input
              type="email"
              class="form-control"
              id="correo"
              placeholder="name@technova.com"
              required
            />
          </div>

          <div class="mb-3">
            <label for="password" class="form-label">Password</label>
            <!-- type="password" oculta el texto que escribe el usuario -->
            <input
              type="password"
              class="form-control"
              id="password"
              placeholder="Enter your password"
              required
            />
          </div>

          <!-- Aqui se mostraran mensajes de exito o error con JavaScript -->
          <!-- d-none lo oculta por defecto, hasta que script.js lo necesite -->
          <div id="mensaje-resultado" class="d-none mb-3"></div>

          <!-- type="submit" hace que este boton dispare el evento -->
          <!-- submit del formulario, que capturamos en script.js -->
          <button type="submit" class="btn btn-primary w-100">Log in</button>
        </form>

        <!-- Link a la pagina de registro (archivo separado) -->
        <p class="text-center mt-3">
          <span class="texto-ayuda">Don't have an account?</span>
          <a href="registro.html">Create account</a>
        </p>
      </div>
    </div>

    <!-- Scripts -->

    <script
      src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"
      integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI"
      crossorigin="anonymous"
    ></script>

    <!-- jQuery, necesario antes de script.js porque script.js -->
    <!-- usa la sintaxis de jQuery ($) para hacer peticiones Ajax -->
    <script
      src="https://code.jquery.com/jquery-3.7.1.min.js"
      integrity="sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo="
      crossorigin="anonymous"
    ></script>

    <!-- script.js -->
    <script src="js/script.js" type="text/javascript"></script>
  </body>
</html>
```

---

## 10. Crear el frontend: registro.html

Crear el archivo `login/registro.html`:

```bash
nano login/registro.html
```

Pegar:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Create account</title>

    <!-- Bootstrap CSS desde CDN -->
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css"
      rel="stylesheet"
      integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB"
      crossorigin="anonymous"
    />

    <!-- Estilos personalizados -->
    <link rel="stylesheet" href="css/style.css" />
  </head>

  <body>
    <div
      class="container-fluid vh-100 d-flex align-items-center justify-content-center"
    >
      <div class="card p-4 shadow" style="width: 100%; max-width: 400px">
        <h3 class="text-center mb-4">Create account</h3>

        <!-- id="formulario-registro" es el identificador que script.js -->
        <!-- usa para capturar el envio del formulario de registro -->
        <form id="formulario-registro">
          <div class="mb-3">
            <label for="registro-nombre" class="form-label">Name</label>
            <input
              type="text"
              class="form-control"
              id="registro-nombre"
              placeholder="Your name"
              required
            />
          </div>

          <div class="mb-3">
            <label for="registro-correo" class="form-label">Email</label>
            <input
              type="email"
              class="form-control"
              id="registro-correo"
              placeholder="name@technova.com"
              required
            />
          </div>

          <div class="mb-3">
            <label for="registro-password" class="form-label">Password</label>
            <!-- minlength="6" refuerza la validacion del backend -->
            <!-- que requiere al menos 6 caracteres -->
            <input
              type="password"
              class="form-control"
              id="registro-password"
              placeholder="Minimum 6 characters"
              minlength="6"
              required
            />
          </div>

          <div class="mb-3">
            <label for="registro-password2" class="form-label">Confirm password</label>
            <!-- Este campo se compara con el anterior -->
            <!-- en script.js para asegurar que escribio la misma contrasena -->
            <input
              type="password"
              class="form-control"
              id="registro-password2"
              placeholder="Repeat your password"
              minlength="6"
              required
            />
          </div>

          <!-- Mensaje de exito o error para el registro -->
          <div id="mensaje-registro" class="d-none mb-3"></div>

          <button type="submit" class="btn btn-primary w-100">Register</button>
        </form>

        <!-- Link para volver al login (archivo separado) -->
        <p class="text-center mt-3">
          <span class="texto-ayuda">Already have an account?</span>
          <a href="index.html">Log in</a>
        </p>
      </div>
    </div>

    <!-- Scripts -->

    <script
      src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"
      integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI"
      crossorigin="anonymous"
    ></script>

    <script
      src="https://code.jquery.com/jquery-3.7.1.min.js"
      integrity="sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo="
      crossorigin="anonymous"
    ></script>

    <script src="js/script.js" type="text/javascript"></script>
  </body>
</html>
```

---

## 11. Crear el frontend: dashboard.html

Crear el archivo `login/dashboard.html`:

```bash
nano login/dashboard.html
```

Pegar:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Project Summary</title>

    <!-- Bootstrap CSS desde CDN -->
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css"
      rel="stylesheet"
      integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB"
      crossorigin="anonymous"
    />

    <!-- Estilos personalizados -->
    <link rel="stylesheet" href="css/style.css" />

    <!-- jQuery se carga aqui, en el head, porque el script de -->
    <!-- verificacion de sesion se ejecuta al inicio del body -->
    <!-- y necesita $.ajax disponible en ese momento. -->
    <script
      src="https://code.jquery.com/jquery-3.7.1.min.js"
      integrity="sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo="
      crossorigin="anonymous"
    ></script>
  </head>

  <body>
    <!-- ============================================================
         BLOQUE 1: Verificacion de sesion al cargar la pagina
         ============================================================
         Este script se ejecuta INMEDIATAMENTE cuando se abre
         dashboard.html. Su trabajo es verificar si el usuario
         esta autenticado antes de mostrar cualquier contenido.

         El flujo es:
         1. Leer el token de sessionStorage
         2. Si no hay token -> redirigir al login
         3. Si hay token -> enviarlo al servidor para verificar
         4. Si el servidor lo acepta -> mostrar la pagina
         5. Si el servidor lo rechaza -> limpiar todo y volver al login

         Por que va en el body (y no en script.js):
         Tiene que ejecutarse ANTES de que el navegador renderice
         el HTML de abajo. Si el token es invalido, el usuario
         nunca deberia ver lo que hay en esta pagina.
    -->
    <script>
      // API_URL: misma variable que en script.js, define la direccion
      // base del servidor backend. Si el frontend y backend estan
      // en el mismo servidor, puede ser un string vacio "".
      var API_URL = "http://127.0.0.1:5000";

      // sessionStorage.getItem() lee un valor del almacenamiento
      // temporal del navegador. El argumento "tokenSesion" es la clave
      // que configuramos en script.js cuando el usuario se logueo.
      // Si el usuario nunca se logueo, o cerro la pestana, esto
      // devuelve null.
      var token = sessionStorage.getItem("tokenSesion");

      if (!token) {
        // Si token es null o un string vacio, no hay sesion activa.
        // Usamos location.replace() en vez de location.href porque
        // replace() no deja la pagina actual en el historial del navegador,
        // asi que el usuario no puede volver con el boton "Atras".
        window.location.replace("index.html");
      } else {
        // Si hay un token, lo enviamos al servidor para verificacion.
        // El servidor es la unica autoridad que puede decir si un token
        // es valido: firma tokens con su SECRET_KEY, y solo alguien
        // con esa clave puede confirmar que no fueron manipulados.

        // $.ajax con modo sincrono (async: false).
        // "Sincrono" significa que el navegador CONGELA toda la pagina
        // (no responde a clics, no puede hacer scroll, el cursor se
        // convierte en estado de espera) hasta que termine esta peticion.
        //
        // En produccion NUNCA se hace esto porque destruye la experiencia
        // del usuario. Se usa aqui solo para que el flujo de aprendizaje
        // sea lineal y facil de seguir: primero verificar, despues mostrar.
        //
        // El enfoque profesional seria async: true (que es el valor por
        // defecto) y mostrando un indicador de "cargando..." mientras se
        // espera la respuesta.
        $.ajax({
          url: API_URL + "/verificar-sesion",
          method: "GET",
          async: false,

          // beforeSend es un callback que jQuery ejecuta JUSTO ANTES
          // de enviar la peticion HTTP al servidor. El parametro "xhr"
          // es el objeto XMLHttpRequest, que representa la conexion
          // al servidor. Con setRequestHeader() agregamos el header
          // "Authorization" a la peticion.
          //
          // El formato "Bearer <token>" es un estandar (RFC 6750) que
          // los servidores esperan encontrar. El decorador token_required
          // en api.py busca exactamente este header y este formato.
          beforeSend: function (xhr) {
            xhr.setRequestHeader("Authorization", "Bearer " + token);
          },

          // success se ejecuta si el servidor respondio con 200 OK.
          // En este caso no necesitamos hacer nada, porque el contenido
          // HTML de la pagina ya esta en el codigo y se mostrara
          // automaticamente una vez que termine este script.
          success: function () {
            // Intencionalmente no hacemos nada aqui. Si llegamos a este
            // punto, significa que el token es valido y la pagina puede
            // mostrarse de forma segura.
          },

          // error se ejecuta si el servidor respondio con cualquier
          // codigo 4xx (401, 403, etc.) o 5xx (500, etc.).
          error: function () {
            // Si el token no es valido (expirado, corrupto, o no existe
            // en la base de datos), borramos todo lo relacionado con la
            // sesion en sessionStorage y redirigimos al login.
            sessionStorage.removeItem("tokenSesion");
            sessionStorage.removeItem("nombreUsuario");

            // replace() en vez de href para no dejar esta pagina
            // en el historial de navegacion.
            window.location.replace("index.html");
          },
        });
      }
    </script>

    <!-- ============================================================
         BLOQUE 2: Encabezado con boton de cerrar sesion real
         ============================================================ -->
    <header class="encabezado">
      <div class="contenedor navegacion">
        <span class="marca" id="texto-bienvenida"
          >Docker + Flask Project Summary</span
        >
        <!--
          El boton de logout ahora tiene:
          - id="boton-logout": para poder seleccionarlo con jQuery si se necesita
          - onclick="cerrarSesion()": llama a la funcion JavaScript que borra la sesion
          - class="boton boton-secundario": mantiene el mismo estilo visual
        -->
        <a href="#" id="boton-logout" onclick="cerrarSesion()" class="boton boton-secundario">Log out</a>
      </div>
    </header>

    <!-- Contenido principal: resumen del proyecto paso a paso -->
    <section class="seccion">
      <div class="contenedor">
        <h1 class="text-center">From zero to a complete CRUD with Docker</h1>
        <p class="text-center">
          This summary documents every step taken in this project, from
          installing Docker to this very login page working. Includes
          brute force protection and CORS restriction.
        </p>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>1. Verify and install Docker</h3>
          <p>
            Docker was confirmed to be already installed on Arch Linux, but the
            service was disabled and inactive. It was permanently enabled with
            <code>sudo systemctl enable --now docker</code>.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>2. Security decision: keep sudo</h3>
          <p>
            Running Docker without <code>sudo</code> failed due to permissions,
            since the user did not belong to the <code>docker</code> group.
            It was decided to keep requiring <code>sudo</code> for every
            command, because belonging to that group is equivalent to root.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>3. First container: hello world in Python</h3>
          <p>
            A basic <code>Dockerfile</code> was created with FROM, WORKDIR,
            COPY and CMD, fixing an incomplete COPY and an invalid image name.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>4. First API with Flask</h3>
          <p>
            A virtual environment was created, Flask was installed, and an API
            was written with routes <code>/</code> and <code>/saludo</code>,
            returning JSON with <code>jsonify</code>.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>5. Fix insecure Flask configuration</h3>
          <p>
            <code>debug=True</code> with <code>host="0.0.0.0"</code> exposes a
            dangerous interactive debugger. Changed to <code>debug=False</code>.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>6. Dockerize the API</h3>
          <p>
            <code>requirements.txt</code> was generated and a Dockerfile was
            written that installs dependencies before copying the code.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>7. Database review</h3>
          <p>
            Table, row, column and primary key concepts reviewed, along with
            the four CRUD operations in SQL.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>8. Separate passwords with .env</h3>
          <p>
            A <code>.env</code> file was created with MySQL credentials,
            protected with <code>.gitignore</code>.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>9. MySQL and API together with docker-compose</h3>
          <p>
            Two services defined in <code>docker-compose.yml</code>: MySQL
            and Flask API, using env_file, volumes and depends_on.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>10. Centralize configuration in config.py</h3>
          <p>
            Configuration logic separated into its own file with a Config
            class that reads environment variables once.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>11. Diagnose startup error with healthcheck</h3>
          <p>
            A healthcheck was added with <code>mysqladmin ping</code> and
            <code>condition: service_healthy</code>.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>12. Complete CRUD</h3>
          <p>
            Four routes implemented: POST, GET, PUT and DELETE for /usuarios,
            all using parameterized queries to prevent SQL injection.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>13. Gunicorn as production server</h3>
          <p>
            Flask's dev server was replaced with Gunicorn, moving
            <code>create_table()</code> outside the <code>if __name__</code> block.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>14. Login with hashed passwords</h3>
          <p>
            A password column was added using <code>generate_password_hash</code>,
            and a <code>POST /login</code> route that compares with
            <code>check_password_hash</code>.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>15. Frontend with Bootstrap and jQuery</h3>
          <p>
            A login form was built connected to the API via Ajax with jQuery,
            enabling CORS on the backend with <code>flask-cors</code>.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>16. Diagnosis: Gunicorn logs</h3>
          <p>
            <code>--access-logfile -</code> was added to Gunicorn to see each
            request in real time.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>17. Real authentication with JWT</h3>
          <p>
            The simple sessionStorage flag was replaced with a JWT token signed
            by the server with PyJWT and a SECRET_KEY stored in .env.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>18. Real logout</h3>
          <p>
            The "Back to login" link was replaced with a button that calls
            <code>sessionStorage.clear()</code> before redirecting.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>19. Protect user listing with token</h3>
          <p>
            GET /usuarios was protected with <code>@token_required</code>,
            making all CRUD routes require authentication.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>20. Configurable API URL</h3>
          <p>
            The server URL was extracted to a global <code>API_URL</code>
            variable at the start of each JavaScript file.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>21. Clean up dead code</h3>
          <p>
            <code>app.py</code> was removed and <code>.gitignore</code> was
            fixed to exclude <code>.venv/</code>.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>22. Brute force protection</h3>
          <p>
            An <code>intentos_login</code> table was added. After 5 failures,
            the account is blocked for 15 minutes with HTTP 429.
          </p>
        </div>

        <div class="tarjeta" style="margin-bottom: 24px">
          <h3>23. CORS restriction</h3>
          <p>
            CORS was changed from open to only accept requests from
            <code>http://localhost:8080</code>.
          </p>
        </div>

        <div class="lista-datos" style="margin-top: 32px">
          <p>
            <strong>Note:</strong> the token is stored in
            <code>sessionStorage</code>, which is still vulnerable to
            XSS attacks. The more secure alternative, httpOnly cookies,
            requires more advanced configuration.
          </p>
        </div>
      </div>
    </section>

    <footer class="pie">
      <div class="contenedor text-center">
        <p>
          Practice project: Docker, Flask, MySQL and frontend with Bootstrap.
        </p>
      </div>
    </footer>

    <!-- Scripts -->

    <script
      src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"
      integrity="sha384-FKyoEForCGlyvwx9Hj09JcYn3nv7wiPVlz7YYwJrWVcXK/BmnVDxM+D2scQbITxI"
      crossorigin="anonymous"
    ></script>

    <script src="js/script.js" type="text/javascript"></script>

    <!-- ============================================================
         BLOQUE 3: Mostrar nombre del usuario y funcion de logout
         ============================================================
         Este script se ejecuta DESPUES de que todo el HTML ya cargo
         (porque esta al final del body). Su trabajo es:
         1. Leer el nombre de sessionStorage y mostrarlo en el encabezado
         2. Definir la funcion cerrarSesion() que el boton llama
    -->
    <script>
      // --- Mostrar el nombre del usuario en el encabezado ---

      // sessionStorage.getItem() lee el nombre que se guardo durante
      // el login (en script.js, linea sessionStorage.setItem("nombreUsuario", ...)).
      var nombreGuardado = sessionStorage.getItem("nombreUsuario");

      // Si hay un nombre guardado, lo mostramos en el encabezado.
      // getElementById() encuentra un elemento HTML por su atributo id.
      // .textContent reemplaza el texto interno del elemento.
      if (nombreGuardado) {
        document.getElementById("texto-bienvenida").textContent =
          "Welcome, " + nombreGuardado;
      }

      // --- Funcion real de logout ---

      // Esta funcion se ejecuta cuando el usuario hace clic en "Log out".
      // Su trabajo es simple pero critico:
      // 1. Borrar TODA la informacion de sesion del navegador
      // 2. Redirigir al login
      //
      // sessionStorage.clear() borra TODAS las claves en sessionStorage
      // para esta pestana. Es mas seguro que llamar removeItem() una
      // por una, porque garantiza que nada quede. Si manana se agrega
      // una tercera clave (por ejemplo, "userRole"), clear() la borra
      // automaticamente sin tener que modificar esta funcion.
      //
      // window.location.replace() redirige SIN dejar esta pagina en
      // el historial del navegador.
      function cerrarSesion() {
        sessionStorage.clear();
        window.location.replace("index.html");
      }
    </script>
  </body>
</html>
```

---

## 12. Crear el archivo script.js

Crear el archivo `login/js/script.js`:

```bash
nano login/js/script.js
```

Pegar:

```javascript
// ============================================================
// script.js - Manejo de formularios de login y registro
//
// Este archivo se comparte entre index.html (login) y
// registro.html (registro). Cada pagina solo tiene un formulario,
// asi que los handlers solo se ejecutan cuando el elemento existe.
//
// jQuery internamente verifica si el elemento seleccionado existe
// antes de asociar el evento. Si el elemento no esta en la pagina
// (por ejemplo, #formulario-registro no existe en index.html),
// simplemente no hace nada. No causa errores.
//
// Este archivo maneja:
// 1. Capturar el envio del formulario de login
// 2. Capturar el envio del formulario de registro
// 3. Enviar datos al servidor via Ajax (jQuery)
// 4. Almacenar el token JWT y el nombre en sessionStorage
// 5. Redirigir al dashboard en login exitoso
// 6. Redirigir al login en registro exitoso
// ============================================================

// API_URL define la direccion base de la API.
// Si el frontend y backend corren en el mismo origen (mismo host y puerto),
// puede ser un string vacio "". Si estan en servidores diferentes,
// pon la direccion completa del backend aqui.
// Ejemplo: "http://127.0.0.1:5000" o "https.midominio.com/api"
var API_URL = "http://127.0.0.1:5000";

// $(document).ready() es un evento de jQuery que se dispara cuando
// todo el contenido HTML ha terminado de cargar. Sin esto, nuestro
// script podria intentar encontrar elementos que aun no existen en la pagina.
$(document).ready(function () {

    // ============================================================
    // FORMULARIO DE LOGIN
    // ============================================================
    // Capturamos el evento "submit" del formulario con
    // id="formulario-login". Este evento se dispara cada vez que
    // el usuario presiona el boton "Log in" o presiona Enter
    // mientras esta dentro de un campo del formulario.
    // El parametro "evento" es el objeto del evento, que contiene
    // informacion sobre lo que acaba de ocurrir.
    $("#formulario-login").on("submit", function (evento) {

        // preventDefault() detiene el comportamiento por defecto del
        // formulario, que recargaria toda la pagina. Queremos enviar
        // los datos via Ajax y manejar la respuesta sin recargar.
        evento.preventDefault();

        // .val() obtiene el texto que el usuario escribio en cada campo.
        // #correo y #password son los ids de los inputs en index.html.
        var correo = $("#correo").val();
        var password = $("#password").val();

        // Antes de enviar una nueva peticion, borramos cualquier mensaje
        // anterior que pueda estar visible en el div #mensaje-resultado.
        // d-none oculta el div, y removemos las clases de color de estilo.
        $("#mensaje-resultado")
            .addClass("d-none")
            .removeClass("alerta-exito alerta-error")
            .text("");

        // $.ajax() es la funcion de jQuery para hacer peticiones HTTP.
        // Es similar a fetch() nativo de JavaScript, pero con sintaxis
        // diferente y mejor compatibilidad con navegadores antiguos.
        $.ajax({
            // url: a donde enviar la peticion. Usamos API_URL + "/login"
            // para que si la direccion del servidor cambia, solo necesitemos
            // cambiar una linea en vez de buscar en todo el archivo.
            url: API_URL + "/login",

            // method: el verbo HTTP. POST se usa para enviar datos al
            // servidor, en este caso las credenciales del usuario.
            method: "POST",

            // contentType: le dice al servidor en que formato estan los datos.
            // "application/json" significa que el cuerpo de la peticion es JSON.
            contentType: "application/json",

            // data: los datos que enviamos. JSON.stringify() convierte un
            // objeto normal de JavaScript en un string de texto JSON,
            // que es lo que el servidor espera recibir.
            data: JSON.stringify({
                correo: correo,
                password: password
            }),

            // success solo se ejecuta si el servidor respondio con un
            // codigo 2xx (200, 201, etc.), lo que significa que todo
            // salio bien.
            success: function (respuesta) {

                // Mostramos un mensaje de exito al usuario.
                // Removemos d-none para mostrar el div, y agregamos
                // alerta-exito para que se vea en verde.
                $("#mensaje-resultado")
                    .removeClass("d-none alerta-error")
                    .addClass("alerta-exito")
                    .text("Welcome, " + respuesta.nombre);

                // Almacenamos el token JWT y el nombre del usuario en
                // sessionStorage. sessionStorage es un almacenamiento
                // del navegador que guarda datos mientras la pestana
                // este abierta. Si el usuario cierra la pestana, los
                // datos se borran automaticamente.
                // Esto es diferente de localStorage, que guarda datos
                // incluso despues de cerrar el navegador.
                sessionStorage.setItem("tokenSesion", respuesta.token);
                sessionStorage.setItem("nombreUsuario", respuesta.nombre);

                // Redirigimos al dashboard despues de 1.2 segundos
                // (1200 milisegundos). setTimeout crea un delay antes
                // de ejecutar la redireccion. Dejamos un tiempo para que
                // el usuario pueda ver el mensaje de exito antes de
                // ser redirigido.
                setTimeout(function () {
                    window.location.href = "dashboard.html";
                }, 1200);
            },

            // error se ejecuta si el servidor respondio con un codigo
            // 4xx o 5xx, lo que significa que hubo un problema
            // (credenciales incorrectas, error del servidor, etc.).
            error: function (peticion) {

                // Empezamos con un mensaje de error generico por si la
                // respuesta del servidor no tiene un campo "error" especifico.
                var mensajeError = "An error occurred while logging in";

                // Status 429 = Too Many Requests. Esto significa que la
                // cuenta esta temporalmente bloqueada por demasiados
                // intentos fallidos de login. Mostramos un mensaje
                // especifico con el tiempo restante de bloqueo.
                if (peticion.status === 429) {
                    var retrySeconds = peticion.responseJSON.retry_after_seconds;
                    var minutes = Math.floor(retrySeconds / 60);
                    var seconds = retrySeconds % 60;
                    mensajeError = "Account temporarily locked. Try again in " +
                        minutes + "m " + seconds + "s";
                }

                // peticion.responseJSON contiene la respuesta del servidor
                // ya parseada como objeto JavaScript. Si existe y tiene
                // un campo "error", usamos ese mensaje en vez del generico.
                // Esto permite que el backend envie mensajes como
                // "Incorrect email or password" directamente.
                else if (peticion.responseJSON && peticion.responseJSON.error) {
                    mensajeError = peticion.responseJSON.error;
                }

                // Mostramos el mensaje de error al usuario en rojo.
                $("#mensaje-resultado")
                    .removeClass("d-none alerta-exito")
                    .addClass("alerta-error")
                    .text(mensajeError);
            }
        });
    });

    // ============================================================
    // FORMULARIO DE REGISTRO
    // ============================================================
    // Este bloque maneja el envio del formulario de creacion de cuenta.
    // Es similar al login, pero con dos diferencias clave:
    // 1. Envia 3 campos (nombre, correo, password) en vez de 2
    // 2. Valida que ambas contrasenas coincidan ANTES de enviar
    // 3. Envia a /registro (ruta publica) en vez de /login

    $("#formulario-registro").on("submit", function (evento) {
        // Evitamos que el formulario recargue la pagina
        evento.preventDefault();

        // Leemos los valores de los 4 campos del formulario de registro.
        // Cada id corresponde a un input en registro.html.
        var nombre = $("#registro-nombre").val();
        var correo = $("#registro-correo").val();
        var password = $("#registro-password").val();
        var password2 = $("#registro-password2").val();

        // Borramos mensajes anteriores del area de registro.
        // Nota: usamos #mensaje-registro en vez de #mensaje-resultado,
        // porque cada pagina tiene su propio div de mensajes.
        $("#mensaje-registro")
            .addClass("d-none")
            .removeClass("alerta-exito alerta-error")
            .text("");

        // Validacion del lado del cliente: las contrasenas deben coincidir.
        // Esto evita enviar una peticion al servidor que sabemos que fallara.
        // El servidor tambien valida, pero esta verificacion rapida le da
        // retroalimentacion inmediata al usuario.
        if (password !== password2) {
            $("#mensaje-registro")
                .removeClass("d-none")
                .addClass("alerta-error")
                .text("Passwords do not receive match");
            return;
        }

        // Validacion adicional: la contrasena debe tener al menos
        // 6 caracteres. Aunque el input ya tiene minlength="6" en HTML,
        // algunos navegadores no lo enforcement, asi que es mejor
        // tambien verificarlo en JavaScript.
        if (password.length < 6) {
            $("#mensaje-registro")
                .removeClass("d-none")
                .addClass("alerta-error")
                .text("Password must be at least 6 characters long");
            return;
        }

        // Enviamos los datos al servidor via Ajax.
        // El endpoint es /registro, que es una ruta PUBLICA (no requiere
        // token). El servidor creara el usuario y devolvera un 201
        // (Created) si todo sale bien.
        $.ajax({
            url: API_URL + "/registro",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
                nombre: nombre,
                correo: correo,
                password: password
            }),

            // Si el servidor responde con 201 (Created), el usuario
            // se creo exitosamente.
            success: function (respuesta) {
                // Mostramos un mensaje de exito al usuario
                $("#mensaje-registro")
                    .removeClass("d-none alerta-error")
                    .addClass("alerta-exito")
                    .text("Account created successfully. You can now log in.");

                // Limpiamos los campos del formulario para que el usuario
                // no tenga que borrar lo que escribio.
                $("#formulario-registro")[0].reset();

                // Despues de 2 segundos, redirigimos a la pagina de login
                // para que el usuario pueda iniciar sesion con su nueva cuenta.
                setTimeout(function () {
                    window.location.href = "index.html";
                }, 2000);
            },

            // Si el servidor responde con un error (400, 409, etc.)
            error: function (peticion) {
                var mensajeError = "An error occurred while creating the account";

                // Si el servidor envio un mensaje de error especifico,
                // lo mostramos en vez del generico.
                if (peticion.responseJSON && peticion.responseJSON.error) {
                    mensajeError = peticion.responseJSON.error;
                }

                $("#mensaje-registro")
                    .removeClass("d-none alerta-exito")
                    .addClass("alerta-error")
                    .text(mensajeError);
            }
        });
    });
});
```

---

## 13. Crear el archivo style.css

Crear el archivo `login/css/style.css`:

```bash
nano login/css/style.css
```

Pegar:

```css
/* ============================================================
   style.css - M_R Web Design
   Version: 3.0
   Descripcion: Reset general, variables CSS, parallax global
   y estilos responsivos. Paleta inspirada en TryHackMe.
   ============================================================ */

:root {
    --color-fondo: #1c2333;
    --color-texto: #ffffff;
    --color-primario: #1db954;
    --color-secundario: #212c3d;
    --color-terciario: #2a3647;
    --color-borde: #3d4f66;
    --color-claro: #ffffff;
    --color-suave: #a9b5c8;
    --color-blanco-suave: #dce4ee;

    --fuente-principal: Arial, Helvetica, sans-serif;
    --tamano-base: 16px;
    --altura-linea: 1.6;

    --espaciado-chico: 8px;
    --espaciado-medio: 16px;
    --espaciado-grande: 32px;

    --radio-borde: 4px;
    --sombra-caja: 0 2px 6px rgba(0, 0, 0, 0.12);
    --transicion-rapida: 0.2s ease;
}

/* --- RESET --- */
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    font-size: var(--tamano-base);
    scroll-behavior: smooth;
}

/* --- PARALLAX GLOBAL Y BODY --- */
body {
    font-family: var(--fuente-principal);
    font-size: 1rem;
    line-height: var(--altura-linea);
    color: var(--color-texto);
    /* Si no tienes la imagen de fondo, comenta estas lineas: */
    /* background-image: url('../img/infosec_orami_.png'); */
    background-attachment: fixed;
    background-position: center;
    background-repeat: no-repeat;
    background-size: cover;

    padding-top: env(safe-area-inset-top, 0px);
    padding-right: env(safe-area-inset-right, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
    padding-left: env(safe-area-inset-left, 0px);
    overflow-x: hidden;
    -webkit-font-smoothing: antialiased;
}

body::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-color: rgba(28, 35, 51, 0.85);
    z-index: -1;
}

.contenedor {
    width: 100%;
    max-width: 1200px;
    margin-left: auto;
    margin-right: auto;
    padding-left: var(--espaciado-medio);
    padding-right: var(--espaciado-medio);
}

/* --- TIPOGRAFIA --- */
h1, h2, h3, h4, h5, h6 {
    font-weight: bold;
    line-height: 1.3;
    margin-bottom: var(--espaciado-medio);
    color: var(--color-texto);
}
h1 { font-size: 2rem; }
h2 { font-size: 1.75rem; }
h3 { font-size: 1.5rem; }

p { margin-bottom: var(--espaciado-medio); }

a {
    color: var(--color-blanco-suave);
    text-decoration: underline;
    transition: color var(--transicion-rapida);
}
a:hover { color: var(--color-claro); text-decoration: none; }
img { max-width: 100%; height: auto; display: block; }
ul, ol { list-style: none; }

/* --- FORMULARIOS BASE --- */
input, textarea, select {
    width: 100%;
    font-family: var(--fuente-principal);
    font-size: 1rem;
    padding: var(--espaciado-chico) var(--espaciado-medio);
    border: 1px solid var(--color-borde);
    border-radius: var(--radio-borde);
    background-color: rgba(33, 44, 61, 0.9);
    color: var(--color-texto);
    transition: border-color var(--transicion-rapida);
}
input:focus, textarea:focus, select:focus {
    outline: none;
    border-color: var(--color-primario);
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.30);
}
input::placeholder, textarea::placeholder { color: var(--color-suave); }

button {
    font-family: var(--fuente-principal);
    font-size: 1rem;
    padding: var(--espaciado-chico) var(--espaciado-grande);
    background-color: var(--color-primario);
    color: var(--color-claro);
    border: none;
    border-radius: var(--radio-borde);
    cursor: pointer;
    transition: background-color var(--transicion-rapida);
}
button:hover { background-color: var(--color-terciario); }

/* --- HEADER Y NAV --- */
.encabezado {
    background-color: rgba(33, 44, 61, 0.95);
    border-bottom: 1px solid var(--color-borde);
    position: sticky;
    top: 0;
    z-index: 100;
}
@supports (backdrop-filter: blur(5px)) {
    .encabezado { backdrop-filter: blur(5px); }
}

.navegacion {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--espaciado-medio);
    min-height: 72px;
    flex-wrap: wrap;
}

.marca {
    color: var(--color-suave);
    font-size: 1.4rem;
    font-weight: bold;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 10px;
}
.marca:hover, .marca:focus, .marca:active { color: var(--color-suave); text-decoration: none; }

.boton-hamburguesa {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    flex-direction: column;
    gap: 5px;
    order: 2;
}
.linea-hamburguesa {
    display: block;
    width: 25px; height: 3px;
    background-color: var(--color-suave);
    border-radius: 2px;
    transition: all var(--transicion-rapida);
}
.boton-hamburguesa:hover .linea-hamburguesa { background-color: var(--color-claro); }

.menu {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: var(--espaciado-chico);
    margin-bottom: 0;
}
.menu a {
    color: var(--color-suave);
    display: block;
    padding: 8px 10px;
    text-decoration: none;
}
.menu a:hover, .menu a.active {
    background-color: var(--color-terciario);
    color: var(--color-claro);
    text-decoration: none;
}

/* --- HERO --- */
.hero {
    border-bottom: 1px solid rgba(61, 79, 102, 0.4);
    padding: 100px 0;
}
.hero-contenido { max-width: 820px; }
.etiqueta {
    color: var(--color-primario);
    font-weight: bold;
    margin-bottom: var(--espaciado-chico);
    text-transform: uppercase;
    letter-spacing: 2px;
}
.hero h1 {
    color: var(--color-claro);
    font-size: 2.8rem;
    margin-bottom: var(--espaciado-medio);
    text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}
.hero p { color: var(--color-blanco-suave); font-size: 1.1rem; max-width: 720px; }

.acciones {
    display: flex;
    flex-wrap: wrap;
    gap: var(--espaciado-medio);
    margin-top: var(--espaciado-grande);
}
.boton {
    border-radius: var(--radio-borde);
    display: inline-block;
    font-weight: bold;
    padding: 10px 18px;
    text-decoration: none;
}
.boton-principal { background-color: var(--color-primario); color: var(--color-claro); }
.boton-principal:hover { background-color: var(--color-borde); text-decoration: none; }
.boton-secundario { background-color: var(--color-secundario); color: var(--color-claro); border: 1px solid var(--color-borde); }
.boton-secundario:hover { background-color: var(--color-borde); text-decoration: none; }

/* --- SECCIONES --- */
.seccion {
    background-color: rgba(28, 35, 51, 0.6);
    padding: 56px 0;
    border-top: 1px solid rgba(61, 79, 102, 0.3);
}
.seccion:last-of-type {
    border-bottom: 1px solid rgba(61, 79, 102, 0.3);
}
.seccion h1, .seccion h2, .seccion h3 { color: var(--color-claro); }
.seccion p { color: var(--color-blanco-suave); }

/* --- TARJETAS --- */
.tarjeta {
    background-color: rgba(42, 54, 71, 0.9);
    border: 1px solid var(--color-borde);
    border-radius: var(--radio-borde);
    height: 100%;
    padding: var(--espaciado-grande);
}
.tarjeta-servicio {
    background-color: rgba(42, 54, 71, 0.9);
    border: 1px solid var(--color-borde);
    color: var(--color-suave);
    cursor: pointer;
    transition: transform var(--transicion-rapida);
}
.tarjeta-servicio:hover {
    background-color: rgba(33, 44, 61, 0.95);
    transform: translateY(-4px);
}
.tarjeta-servicio:focus { outline: 3px solid var(--color-suave); outline-offset: 3px; }

/* --- LISTA DE DATOS --- */
.lista-datos {
    background-color: rgba(33, 44, 61, 0.9);
    border: 1px solid var(--color-borde);
    border-radius: var(--radio-borde);
    color: var(--color-suave);
    padding: var(--espaciado-grande);
}
.lista-datos li { margin-bottom: var(--espaciado-medio); }
.lista-datos li:last-child { margin-bottom: 0; }
.lista-datos strong { color: var(--color-claro); }

/* --- FORMULARIOS DEL SITIO --- */
.formulario {
    background-color: rgba(42, 54, 71, 0.9);
    border: 1px solid var(--color-borde);
    border-radius: var(--radio-borde);
    padding: var(--espaciado-grande);
}
.grupo-formulario { margin-bottom: var(--espaciado-medio); }
label { color: var(--color-claro); display: block; font-weight: bold; margin-bottom: var(--espaciado-chico); }
.campo-activo { background-color: rgba(42, 54, 71, 0.9); border-color: var(--color-primario); }

/* --- FOOTER --- */
.pie {
    background-color: rgba(33, 44, 61, 0.95);
    border-top: 1px solid var(--color-borde);
    color: var(--color-suave);
    padding: var(--espaciado-medio) 0;
}
.pie p { margin-bottom: 0; }

/* --- UTILIDADES --- */
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); border: 0; }
.d-none { display: none !important; }
.texto-ayuda { color: var(--color-suave); font-size: 0.875rem; display: block; margin-top: var(--espaciado-chico); }
.text-center { text-align: center; }

/* --- SISTEMA DE GRID --- */
.row { display: flex; flex-wrap: wrap; margin-left: -15px; margin-right: -15px; }
.col-md-4, .col-md-6, .col-md-8 { padding-left: 15px; padding-right: 15px; width: 100%; }

/* --- RESPONSIVO --- */
@media (min-width: 768px) {
    .col-md-4 { width: 33.333%; }
    .col-md-6 { width: 50%; }
    .col-md-8 { width: 66.666%; }
}

@media (max-width: 768px) {
    .contenedor { padding-left: var(--espaciado-chico); padding-right: var(--espaciado-chico); }
    .navegacion { flex-wrap: wrap; align-items: flex-start; }
    .boton-hamburguesa { display: flex; }
    .menu {
        display: none;
        flex-direction: column;
        width: 100%;
        order: 3;
        margin-top: var(--espaciado-medio);
        justify-content: flex-start;
    }
    .menu.menu-activo { display: flex; }
    .menu a { padding: 12px 10px; border-bottom: 1px solid var(--color-borde); }
    .menu a:last-child { border-bottom: none; }
    .row { flex-direction: column; margin-left: 0; margin-right: 0; }
    .col-md-4, .col-md-6, .col-md-8 { width: 100%; margin-bottom: var(--espaciado-medio); }
    body { background-attachment: scroll; }
    .hero h1 { font-size: 2rem; }
}

@media (max-width: 480px) {
    h1 { font-size: 1.5rem; } h2 { font-size: 1.25rem; }
    .hero h1 { font-size: 1.8rem; }
    .acciones { flex-direction: column; }
    .boton { text-align: center; width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
    * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}

/* ============================================================
   LOGIN - Estilos especificos para la pagina de login
   Estas reglas sobreescriben componentes de Bootstrap
   (.card, .form-control, .btn-primary) para combinar con
   la paleta oscura definida en las variables arriba.
   ============================================================ */

/* Card que envuelve el formulario de login */
.card {
    background-color: rgba(42, 54, 71, 0.95);
    border: 1px solid var(--color-borde);
    border-radius: var(--radio-borde);
    color: var(--color-texto);
}

/* Labels de cada campo (Email, Password) */
.form-label {
    color: var(--color-claro);
    font-weight: bold;
}

/* Campos de texto de Bootstrap */
.form-control {
    background-color: rgba(33, 44, 61, 0.9);
    border: 1px solid var(--color-borde);
    color: var(--color-texto);
}

/* Estado cuando el usuario esta escribiendo dentro del campo */
.form-control:focus {
    background-color: rgba(33, 44, 61, 0.9);
    border-color: var(--color-primario);
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.30);
    color: var(--color-texto);
}

.form-control::placeholder {
    color: var(--color-suave);
}

/* Boton primario de Bootstrap, ahora con el color verde de la marca */
.btn-primary {
    background-color: var(--color-primario);
    border-color: var(--color-primario);
}
.btn-primary:hover {
    background-color: var(--color-terciario);
    border-color: var(--color-terciario);
}

/* Mensaje de exito, activado desde script.js al remover d-none
   y agregar alerta-exito */
#mensaje-resultado.alerta-exito,
#mensaje-registro.alerta-exito {
    background-color: rgba(29, 185, 84, 0.15);
    border: 1px solid var(--color-primario);
    border-radius: var(--radio-borde);
    color: var(--color-primario);
    padding: var(--espaciado-chico) var(--espaciado-medio);
}

/* Mensaje de error, activado desde script.js al agregar alerta-error */
#mensaje-resultado.alerta-error,
#mensaje-registro.alerta-error {
    background-color: rgba(220, 53, 69, 0.15);
    border: 1px solid #dc3545;
    border-radius: var(--radio-borde);
    color: #f5a8ae;
    padding: var(--espaciado-chico) var(--espaciado-medio);
}
```

---

## 14. Crear .gitignore

Crear el archivo `docker/.gitignore` en la carpeta docker:

```bash
nano docker/.gitignore
```

Pegar:

```
.env
.venv/
venv/
__pycache__/
```

**Por que es necesario:** El archivo `.env` contiene contrasenas. Si el proyecto se sube a un repositorio Git, esas contrasenas quedarian expuestas para siempre en el historial de versiones. El `.gitignore` le dice a Git que ignore estos archivos.

---

## 15. Ejecutar el laboratorio

### Paso 1: Levantar Docker Compose

Desde la carpeta `docker/`:

```bash
cd docker_login/docker

# Construir las imagenes e iniciar los contenedores
sudo docker compose up --build -d
```

El flag `--build` fuerza a Docker a reconstruir la imagen de la API (necesario la primera vez o si cambiaste algo). El flag `-d` ejecuta en modo detached (detras de escena, sin bloquear la terminal).

### Paso 2: Verificar que los contenedores estan corriendo

```bash
sudo docker compose ps
```

Deberias ver algo como:

```
NAME                STATUS          PORTS
docker-basedatos-1   Up (healthy)   0.0.0.0:3306->3306/tcp
docker-api-1         Up              0.0.0.0:5000->5000/tcp
```

Si `basedatos` no muestra "healthy", espera unos segundos y vuelve a ejecutar el comando.

### Paso 3: Verificar que la API responde

```bash
curl http://127.0.0.1:5000/
```

Deberia responder:

```json
{"message":"Welcome to my first Flask API"}
```

### Paso 4: Ver los logs de la API (opcional)

```bash
sudo docker compose logs api
```

Deberias ver los logs de Gunicorn con cada peticion que llegue.

### Paso 5: Ver los logs de MySQL (opcional)

```bash
sudo docker compose logs basedatos
```

---

## 16. Probar el flujo completo

### Paso 1: Abrir el frontend

Abre una terminal nueva y ejecuta desde la carpeta `login/`:

```bash
cd docker_login/login
python3 -m http.server 8080
```

Esto sirve los archivos HTML en `http://localhost:8080`.

**IMPORTANTE:** Debes servir los archivos con `python3 -m http.server 8080`. No abras el `index.html` directamente con doble clic (eso usa el protocolo `file://` y CORS lo bloqueara).

Ahora abre en tu navegador:

```
http://localhost:8080
```

### Paso 2: Crear una cuenta

1. Haz clic en "Create account" (o ve a `http://localhost:8080/registro.html`)
2. Completa el formulario:
   - Name: `Juan`
   - Email: `juan@test.com`
   - Password: `123456`
   - Confirm password: `123456`
3. Haz clic en "Register"
4. Deberias ver "Account created successfully. You can now log in."
5. Automaticamente seras redirigido al login

### Paso 3: Iniciar sesion

1. Ingresa el correo: `juan@test.com`
2. Ingresa la contrasena: `123456`
3. Haz clic en "Log in"
4. Deberias ver "Welcome, Juan" en verde
5. Despues de 1.2 segundos seras redirigido al dashboard
6. El dashboard muestra "Welcome, Juan" en el encabezado

### Paso 4: Cerrar sesion

1. Haz clic en "Log out"
2. Seras redirigido al login
3. Si intentas acceder directamente a `dashboard.html`, seras redirigido al login

### Paso 5: Verificar proteccion fuerza bruta

1. Intenta loguearte 5 veces con la contrasena incorrecta
2. En el quinto intento deberias ver: "Account temporarily locked. Try again in 14m Xs"
3. Cualquier intento posterior devolvera el mismo mensaje hasta que pasen 15 minutos

---

## 17. Solucion de problemas

### Error: "Incorrect email or password" al loguearte con credenciales correctas

**Causa mas comun:** La cuenta fue bloqueada por intentos fallidos anteriores.

**Solucion:**

```bash
# Conectarse a MySQL y eliminar los registros de intentos fallidos
sudo docker compose exec basedatos mysql -u api_usuario -puna_clave_segura_api practica_db -e "DELETE FROM intentos_login WHERE correo = 'tu_correo@email.com';"
```

O para borrar TODOS los bloqueos:

```bash
sudo docker compose exec basedatos mysql -u api_usuario -puna_clave_segura_api practica_db -e "TRUNCATE TABLE intentos_login;"
```

### Error: "Failed to fetch" o "Network Error" en el navegador

**Causa:** El frontend no puede comunicarse con la API.

**Verificaciones:**

1. Verificar que la API esta corriendo:
```bash
sudo docker compose ps
```

2. Verificar que la API responde:
```bash
curl http://127.0.0.1:5000/
```

3. Verificar que CORS no esta bloqueando. Abre la consola del navegador (F12) y busca errores de CORS.

4. **IMPORTANTE:** El frontend DEBE servirse desde `http://localhost:8080`. Si lo abres con `file://` o desde otro puerto, CORS bloqueara la peticion.

### Error: "An account with that email already exists"

El correo ya esta registrado. Usa otro correo o borra el usuario de la base de datos:

```bash
sudo docker compose exec basedatos mysql -u api_usuario -puna_clave_segura_api practica_db -e "DELETE FROM usuarios WHERE correo = 'correo@existente.com';"
```

### Error: Los contenedores no inician

```bash
# Ver logs detallados
sudo docker compose logs

# Si hay problemas de permisos con MySQL
sudo docker compose down -v
sudo docker compose up --build
```

El flag `-v` borra los volumes (datos de MySQL). Esto hace que se pierdan los usuarios creados, pero resuelve problemas corruptos de la base de datos.

### Error: "Connection refused" al conectar a MySQL

El contenedor de MySQL todavia no esta listo. Espera unos segundos y verifica el estado:

```bash
sudo docker compose ps
```

Si `basedatos` no muestra "healthy", la API no podra conectarse. El healthcheck deberia resolver esto automaticamente, pero a veces toma unos segundos extra en la primera ejecucion.

### Error: Gunicorn no muestra logs

Gunicorn no muestra peticiones por defecto. Si no ves nada en los logs, asegurate de que la linea `--access-logfile -` este en el Dockerfile.

### Error: La imagen de fondo no carga

Si no tienes la imagen `infosec_orami_.png` en la carpeta `login/img/`, comenta las lineas de background-image en `style.css`:

```css
/* background-image: url('../img/infosec_orami_.png'); */
```

### Detener el laboratorio

```bash
# Detener los contenedores (los datos se conservan en el volume)
sudo docker compose down

# Detener y borrar los datos (MySQL empieza limpio)
sudo docker compose down -v
```

### Verificar la base de datos manualmente

```bash
# Conectarse a MySQL dentro del contenedor
sudo docker compose exec basedatos mysql -u api_usuario -puna_clave_segura_api practica_db

# Ver los usuarios registrados
SELECT id, nombre, correo FROM usuarios;

# Ver los intentos de login
SELECT * FROM intentos_login;

# Ver los hashes de contrasena (no los textos planos)
SELECT id, nombre, correo, password FROM usuarios;
```

---

## Resumen de puertos

| Servicio | Puerto | URL |
|---|---|---|
| Frontend | 8080 | http://localhost:8080 |
| API Flask | 5000 | http://127.0.0.1:5000 |
| MySQL | 3306 | 127.0.0.1:3306 |

## Resumen de rutas de la API

| Ruta | Metodo | Requiere token | Descripcion |
|---|---|---|---|
| `/` | GET | No | Mensaje de bienvenida |
| `/saludo` | GET | No | Mensaje de prueba |
| `/registro` | GET | No | Crear cuenta nueva |
| `/login` | POST | No | Iniciar sesion, devuelve JWT |
| `/usuarios` | GET | Si | Listar todos los usuarios |
| `/usuarios` | POST | Si | Crear usuario (admin) |
| `/usuarios/<id>` | PUT | Si | Editar usuario |
| `/usuarios/<id>` | DELETE | Si | Eliminar usuario |
| `/verificar-sesion` | GET | Si | Verificar si el token es valido |
