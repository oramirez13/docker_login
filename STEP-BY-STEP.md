# Laboratorio: Login con Docker, Flask y MySQL

Guia paso a paso para levantar el laboratorio.

---

## Indice

1. [Levantar Docker](#1-levantar-docker)
2. [Levantar el frontend](#2-levantar-el-frontend)
3. [Probar el flujo completo](#3-probar-el-flujo-completo)
4. [Solucion de problemas](#4-solucion-de-problemas)

---

## 1. Levantar Docker

Desde la carpeta `docker_login/docker`, construir las imagenes e iniciar los contenedores en modo detached:

```bash
cd docker_login/docker
sudo docker compose up --build -d
```

El flag `--build` fuerza a Docker a reconstruir la imagen de la API (necesario la primera vez o si cambiaste algo). El flag `-d` ejecuta en modo detached (detras de escena, sin bloquear la terminal).

Verificar que los contenedores estan corriendo:

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

Verificar que la API responde:

```bash
curl http://127.0.0.1:5000/
```

Deberia responder con un JSON indicando "Welcome to my first Flask API".

---

## 2. Levantar el frontend

Desde la carpeta `docker_login/login`, ejecutar un servidor local de archivos en el puerto 8080:

```bash
cd docker_login/login
python3 -m http.server 8080
```

Esto sirve los archivos HTML en `http://localhost:8080`.

**IMPORTANTE:** Debes servir los archivos con `python3 -m http.server 8080`. No abras el `index.html` directamente con doble clic (eso usa el protocolo `file://` y CORS lo bloqueara).

Abrir en el navegador:

```
http://localhost:8080
```

### Resumen de puertos

| Servicio | Puerto | URL |
|---|---|---|
| Frontend | 8080 | http://localhost:8080 |
| API Flask | 5000 | http://127.0.0.1:5000 |
| MySQL | 3306 | 127.0.0.1:3306 |

---

## 3. Probar el flujo completo

### Crear una cuenta

1. Haz clic en "Create account" (o ve a `http://localhost:8080/registro.html`)
2. Completa el formulario con nombre, correo y password (minimo 6 caracteres)
3. Confirma el password
4. Haz clic en "Register"
5. Deberias ver "Account created successfully. You can now log in."
6. Automaticamente seras redirigido al login

### Iniciar sesion

1. Ingresa el correo y contrasena que registraste
2. Haz clic en "Log in"
3. Deberias ver "Welcome, [tu nombre]" en verde
4. Despues de 1.2 segundos seras redirigido al dashboard
5. El dashboard muestra "Welcome, [tu nombre]" en el encabezado

### Cerrar sesion

1. Haz clic en "Log out"
2. Seras redirigido al login
3. Si intentas acceder directamente a `dashboard.html`, seras redirigido al login

### Verificar proteccion fuerza bruta

1. Intenta loguearte 5 veces con la contrasena incorrecta
2. En el quinto intento deberias ver: "Account temporarily locked. Try again in 14m Xs"
3. Cualquier intento posterior devolvera el mismo mensaje hasta que pasen 15 minutos

---

## 4. Solucion de problemas

### Error: "Incorrect email or password" al loguearte con credenciales correctas

**Causa mas comun:** La cuenta fue bloqueada por intentos fallidos anteriores.

**Solucion:** Eliminar los registros de intentos fallidos desde MySQL:

```bash
# Eliminar bloqueo de un correo especifico
sudo docker compose exec basedatos mysql -u api_usuario -puna_clave_segura_api practica_db -e "DELETE FROM intentos_login WHERE correo = 'tu_correo@email.com';"

# O borrar TODOS los bloqueos
sudo docker compose exec basedatos mysql -u api_usuario -puna_clave_segura_api practica_db -e "TRUNCATE TABLE intentos_login;"
```

### Error: "Failed to fetch" o "Network Error" en el navegador

**Causa:** El frontend no puede comunicarse con la API.

**Verificaciones:**

1. Verificar que la API esta corriendo con `sudo docker compose ps`
2. Verificar que la API responde con `curl http://127.0.0.1:5000/`
3. Verificar que CORS no esta bloqueando (abrir consola del navegador F12 y buscar errores de CORS)
4. **IMPORTANTE:** El frontend DEBE servirse desde `http://localhost:8080`. Si lo abres con `file://` o desde otro puerto, CORS bloqueara la peticion

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

El contenedor de MySQL todavia no esta listo. Espera unos segundos y verifica el estado con `sudo docker compose ps`. Si `basedatos` no muestra "healthy", la API no podra conectarse. El healthcheck deberia resolver esto automaticamente, pero a veces toma unos segundos extra en la primera ejecucion.

### Error: Gunicorn no muestra logs

Gunicorn no muestra peticiones por defecto. Si no ves nada en los logs, asegurate de que la linea `--access-logfile -` este en el Dockerfile.

### Error: La imagen de fondo no carga

Si no tienes la imagen `infosec_orami_.png` en la carpeta `login/img/`, comenta las lineas de background-image en `style.css`.

---

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
```
