from flask import Flask
from flask import jsonify
from flask import request

from flask_cors import CORS

from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

# We import the jwt library, which allows us to create (encode) and
# verify (decode) tokens.
import jwt

# datetime lets us calculate the token expiration date.
import datetime

# functools.wraps is used inside our custom decorator
# so that Flask continues to correctly recognize the name of each
# protected function, instead of confusing them with each other.
from functools import wraps

import mysql.connector
from config import Config

app = Flask(__name__)
# CORS is configured to accept requests ONLY from http://localhost:8080,
# which is where the frontend is served (python -m http.server 8080).
# This prevents other websites from making unauthorized requests to our API.
# In production, change this to the actual domain (e.g., "https://mydomain.com").
CORS(app, origins=["http://localhost:8080", "http://127.0.0.1:8080"])


def get_connection():
    connection = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
    )
    return connection


def create_table():
    connection = get_connection()
    cursor = connection.cursor()
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
    # Table to track failed login attempts for brute force protection.
    # Each row stores: the email, the number of consecutive failed attempts,
    # when the first attempt occurred, and when the account is blocked until.
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


# This is a custom decorator. A decorator is a function that
# wraps another function to add extra behavior, in this
# case, verifying the token before letting the request through.
def token_required(original_function):
    # @wraps preserves the original name of the decorated function,
    # needed so that Flask does not confuse multiple protected
    # routes with each other.
    @wraps(original_function)
    def wrapper_function(*args, **kwargs):
        token = None

        # The token is expected in the HTTP "Authorization" header,
        # with the format "Bearer <token>". We check if that header
        # exists in the request.
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            # We split the word "Bearer" from the actual token.
            parts = auth_header.split(" ")
            if len(parts) == 2 and parts[0] == "Bearer":
                token = parts[1]

        if not token:
            return jsonify({"error": "Authentication token required"}), 401

        try:
            # jwt.decode verifies the token signature using the same
            # secret key it was created with. If someone modified the
            # token, or if it expired, this line raises an exception.
            token_data = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return (
                jsonify({"error": "Token has expired, please log in again"}),
                401,
            )
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        # If everything went well, we let the request through to the
        # original function, passing the verified user data as the
        # first argument.
        return original_function(token_data, *args, **kwargs)

    return wrapper_function


@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Welcome to my first Flask API"})


@app.route("/saludo", methods=["GET"])
def greeting():
    return jsonify({"message": "Hello orami, this is another API route"})


# This route now requires a token. Listing users is an operation
# that only an authenticated user should be able to perform, because
# it reveals information about all records in the table. Even without
# returning passwords, the list of emails and IDs is still sensitive.
@app.route("/usuarios", methods=["GET"])
@token_required
def list_users(token_data):
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


# Now requires a token. The function receives token_data as the first
# argument, automatically injected by the decorator.
@app.route("/usuarios", methods=["POST"])
@token_required
def create_user(token_data):
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


# Here token_data comes first, and user_id (from the URL) comes
# after. The order matters: the decorator always injects token_data
# as the first positional argument.
@app.route("/usuarios/<int:user_id>", methods=["PUT"])
@token_required
def edit_user(token_data, user_id):
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


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or "correo" not in data or "password" not in data:
        return jsonify({"error": "Fields correo and password are required"}), 400

    correo = data["correo"]
    password = data["password"]

    connection = get_connection()
    cursor = connection.cursor()

    # --- BRUTE FORCE PROTECTION ---
    # Before checking credentials, we verify if this email is currently
    # blocked due to too many failed attempts.
    # MAX_INTENTOS = maximum failed attempts allowed before blocking.
    # TIEMPO_BLOQUEO = minutes the account stays blocked after exceeding the limit.
    MAX_INTENTOS = 5
    TIEMPO_BLOQUEO = 15

    cursor.execute(
        "SELECT intentos, bloqueado_hasta FROM intentos_login WHERE correo = %s",
        (correo,),
    )
    registro = cursor.fetchone()

    if registro:
        intentos, bloqueado_hasta = registro

        # If the account is blocked and the block time has not expired,
        # we reject the request immediately with 429 (Too Many Requests).
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

    # --- CREDENTIAL VERIFICATION ---
    # This is the original logic: search the user by email and compare
    # the password hash. The generic error message prevents user enumeration.
    cursor.execute(
        "SELECT id, nombre, correo, password FROM usuarios WHERE correo = %s", (correo,)
    )
    user = cursor.fetchone()

    generic_error = jsonify({"error": "Incorrect email or password"}), 401

    if user is None:
        # If the user does not exist, we still register a failed attempt
        # to prevent an attacker from detecting valid emails by checking
        # whether the counter increments.
        _registrar_intento_fallido(cursor, correo, MAX_INTENTOS, TIEMPO_BLOQUEO)
        connection.commit()
        cursor.close()
        connection.close()
        return generic_error

    user_id, nombre, correo_bd, password_hash = user

    if not check_password_hash(password_hash, password):
        # Wrong password: register the failed attempt and block if limit reached.
        _registrar_intento_fallido(cursor, correo, MAX_INTENTOS, TIEMPO_BLOQUEO)
        connection.commit()
        cursor.close()
        connection.close()
        return generic_error

    # --- SUCCESSFUL LOGIN ---
    # If credentials are correct, we clear any failed attempt records
    # for this email so the counter resets.
    cursor.execute("DELETE FROM intentos_login WHERE correo = %s", (correo,))
    connection.commit()
    cursor.close()
    connection.close()

    # We build the token payload. "exp" is a special key
    # that jwt automatically recognizes as an expiration date.
    # Here the token will be valid for 1 hour from creation time.
    payload = {
        "id": user_id,
        "nombre": nombre,
        "correo": correo_bd,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }

    # jwt.encode signs the payload with our secret key, using
    # the HS256 algorithm, one of the most common for this purpose.
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
    # This helper function handles the logic of recording a failed login attempt.
    # It is called from the login route when credentials are invalid.
    #
    # Parameters:
    #   cursor: the active database cursor
    #   correo: the email that failed to authenticate
    #   max_intentos: the maximum number of attempts allowed
    #   tiempo_bloqueo: minutes to block after exceeding the limit
    #
    # If no record exists for this email, a new one is created with 1 attempt.
    # If a record exists and the block period has expired, the counter resets.
    # If a record exists and is not blocked, the counter increments.
    # If the counter reaches max_intentos, the account is blocked.

    now = datetime.datetime.utcnow()

    cursor.execute(
        "SELECT intentos, primer_intento FROM intentos_login WHERE correo = %s",
        (correo,),
    )
    registro = cursor.fetchone()

    if registro is None:
        # First failed attempt for this email: create a new record.
        cursor.execute(
            "INSERT INTO intentos_login (correo, intentos, primer_intento) "
            "VALUES (%s, 1, %s)",
            (correo, now),
        )
    else:
        intentos, primer_intento = registro

        # If more than tiempo_bloqueo minutes have passed since the first
        # attempt in this window, we reset the counter.
        if (now - primer_intento).total_seconds() > tiempo_bloqueo * 60:
            cursor.execute(
                "UPDATE intentos_login SET intentos = 1, primer_intento = %s, "
                "bloqueado_hasta = NULL WHERE correo = %s",
                (now, correo),
            )
        else:
            # Increment the counter. If it reaches the limit, block the account.
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
# PUBLIC ROUTE: /registro
# ============================================================
# This route does NOT require a token because it is the entry point
# for new users. Anyone can create an account.
#
# Difference with POST /usuarios:
# - POST /usuarios: requires a token (only authenticated users
#   can create other users, like in an admin panel)
# - POST /registro: no token required (anyone can register,
#   like on a public website)
#
# This separation is a common practice in real applications:
# there are public routes (register, login) and protected routes (CRUD).
@app.route("/registro", methods=["POST"])
def register():
    data = request.get_json()

    # We validate that the three required fields are present.
    # If any is missing, we return a 400 (Bad Request) error.
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

    # Basic security validation: the password must be at least
    # 6 characters long. This prevents passwords like "123".
    if len(password) < 6:
        return (
            jsonify({"error": "Password must be at least 6 characters long"}),
            400,
        )

    # generate_password_hash converts the password into a secure hash.
    # We never store the password in plain text. The hash automatically
    # includes a "salt" (random value) that makes two identical
    # passwords produce different hashes.
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
        # If the email already exists in the database, MySQL throws
        # an integrity error (due to the UNIQUE constraint).
        # We catch that error and return a friendly message.
        cursor.close()
        connection.close()
        return (
            jsonify({"error": "An account with that email already exists"}),
            409,
        )
    finally:
        # finally always executes, whether everything went well
        # or there was an error. Here we make sure to close
        # the database connection to avoid leaving connections open.
        cursor.close()
        connection.close()

    # We return 201 (Created), which is the correct code when
    # a new resource is created successfully.
    return jsonify({"id": new_id, "nombre": nombre, "correo": correo}), 201


# Protected route: only responds if the token is valid.
# The @token_requerido decorator is placed right before the function,
# and handles all the verification work before the
# code inside here is executed.
@app.route("/verificar-sesion", methods=["GET"])
@token_required
def verify_session(token_data):
    # token_data arrives from the decorator, already verified, with the
    # information we stored in the payload when creating the token.
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


create_table()

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
