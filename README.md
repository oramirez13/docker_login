# Docker + Flask + MySQL: Secure Login System

Step-by-step guide to reproduce this project from scratch on any Linux machine.
Each step includes the action to perform, the technical reason behind it, and the expected result.

---

## PREREQUISITES

- Linux (tested on Arch Linux, works on any distro)
- Docker and docker-compose installed
- Python 3.10+ (only for local development, not for the container)
- A web browser
- A code editor (VS Code, nano, vim, etc.)

### Verify that Docker is installed and running

```bash
# Verify that docker responds
sudo docker --version

# Verify that the service is active
sudo systemctl status docker

# If it is inactive, enable it permanently
sudo systemctl enable --now docker
```

**Note:** The `docker` group grants root-equivalent privileges. Using `sudo` for every command is a deliberate choice to avoid adding the user to that group.

---

## STEP 1: Create the folder structure

```bash
# Create the project root folder
mkdir -p docker_login/docker
mkdir -p docker_login/login/css
mkdir -p docker_login/login/js
mkdir -p docker_login/login/img
```

**Expected result:**
```
docker_login/
├── docker/
└── login/
    ├── css/
    ├── js/
    └── img/
```

---

## STEP 2: Create the Dockerfile

Create the file `docker_login/docker/Dockerfile` with this content:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config.py .
COPY api.py .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--access-logfile", "-", "api:app"]
```

**What each line does:**
- `FROM python:3.12-slim`: uses a lightweight Python image as base
- `WORKDIR /app`: creates and enters the /app folder inside the container
- `COPY requirements.txt .`: copies the dependencies file before the source code (layer caching optimization)
- `RUN pip install...`: installs dependencies. This layer is cached as long as requirements.txt has not changed
- `COPY config.py .` and `COPY api.py .`: copies the application source code
- `EXPOSE 5000`: documents that the container listens on port 5000
- `CMD [...]`: the command executed when the container starts (Gunicorn)

---

## STEP 3: Create requirements.txt

Create `docker_login/docker/requirements.txt`:

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
packaging==6.2
PyJWT==2.13.0
python-dotenv==1.2.2
Werkzeug==3.1.8
```

**If you want to generate your own requirements.txt:**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install packages
pip install flask flask-cors gunicorn mysql-connector-python PyJWT python-dotenv

# Generate requirements.txt
pip freeze > requirements.txt
```

---

## STEP 4: Create config.py

Create `docker_login/docker/config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "basedatos")
    MYSQL_USER = os.environ.get("MYSQL_USER")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")

    # Secret key for signing JWT tokens. Read from .env.
    SECRET_KEY = os.environ.get("SECRET_KEY")
```

**Why a class?** It centralizes all configuration in one place. Any credential change is made in `.env` only, without modifying source code.

---

## STEP 5: Create api.py

Create `docker_login/docker/api.py` with the complete project content.
This is the largest file: it contains the Flask API with:

- Routes: `/`, `/saludo`, `/usuarios` (CRUD), `/registro`, `/login`, `/verificar-sesion`
- `@token_required` decorator to protect routes with JWT
- MySQL connection using mysql.connector
- Password hashing with werkzeug.security
- Automatic creation of the `usuarios` and `intentos_login` tables on startup
- Brute force protection: rate limiting with account lockout (5 attempts / 15 minutes)
- CORS restricted to `http://localhost:8080`

**The complete file is at `docker_login/docker/api.py`.** All functions and routes are documented with inline comments.

---

## STEP 6: Create the .env file

Create `docker_login/docker/.env`:

```bash
# MySQL database
MYSQL_HOST=basedatos
MYSQL_ROOT_PASSWORD=una_clave_segura_root
MYSQL_DATABASE=practica_db
MYSQL_USER=api_usuario
MYSQL_PASSWORD=una_clave_segura_api

# Key for signing JWT tokens (must be long and random)
SECRET_KEY=tu_clave_generada_aqui
```

**Important:** This file must not be committed to version control.
To generate a secure SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## STEP 7: Create .gitignore

Create `docker_login/docker/.gitignore`:

```
.env
.venv/
venv/
__pycache__/
```

Both `venv/` and `.venv/` are excluded because the virtual environment directory name varies depending on how it is created.

---

## STEP 8: Create docker-compose.yml

Create `docker_login/docker/docker-compose.yml`:

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

    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build: .
    env_file:
      - .env
    ports:
      - "5000:5000"

    depends_on:
      basedatos:
        condition: service_healthy

volumes:
  datos_mysql:
```

**What each section does:**
- `basedatos`: starts MySQL 8.0 with credentials from `.env`
- `volumes`: persists MySQL data in a named volume to survive container restarts
- `healthcheck`: verifies that MySQL is accepting connections before the API starts
- `api`: builds the image from the Dockerfile and connects it to the database
- `depends_on: condition: service_healthy`: blocks the API startup until the healthcheck passes

---

## STEP 9: Start the backend with Docker

```bash
# Enter the docker folder
cd docker_login/docker

# Build the image and start both containers
sudo docker compose up --build
```

**Expected result:**
1. Docker builds the API image from the Dockerfile
2. MySQL starts and the healthcheck begins polling
3. Once the healthcheck passes, the API starts with Gunicorn
4. Gunicorn access logs appear in the terminal for each request

**To stop:**
```bash
sudo docker compose down
```

**To view logs in background:**
```bash
sudo docker compose up --build -d
sudo docker compose logs -f
```

---

## STEP 10: Create the frontend - index.html

Create `docker_login/login/index.html` with the login form.
Uses Bootstrap 5.3.8 and jQuery 3.7.1 via CDN.

**The complete file is at `docker_login/login/index.html`.**
Key elements:
- `id="formulario-login"`: the form that script.js captures
- `id="correo"` and `id="password"`: the inputs that script.js reads
- `id="mensaje-resultado"`: div for success/error messages
- Bootstrap CSS CDN in the head
- jQuery and Bootstrap JS CDNs at the end of the body

---

## STEP 11: Create the frontend - script.js

Create `docker_login/login/js/script.js`:

**The complete file is at `docker_login/login/js/script.js`.**
Key elements:
- `var API_URL = "http://127.0.0.1:5000"`: configurable backend URL
- Captures the form submit with `preventDefault()`
- Sends POST to `/login` via `$.ajax()`
- Saves the JWT token in `sessionStorage`
- Redirects to `dashboard.html` after 1.2 seconds

---

## STEP 12: Create the frontend - dashboard.html

Create `docker_login/login/dashboard.html`:

**The complete file is at `docker_login/login/dashboard.html`.**
Key elements:
- Session verification on page load (block 1)
- Real logout with `sessionStorage.clear()` (block 2)
- Displays the user name in the header (block 3)
- Documentation of the 21 project steps
- Configurable API_URL for the `/verificar-sesion` endpoint

---

## STEP 13: Create the frontend - style.css

Create `docker_login/login/css/style.css`:

**The complete file is at `docker_login/login/css/style.css` (452 lines).**
Key elements:
- CSS variables with a dark palette inspired by TryHackMe
- Background parallax with `infosec_orami_.png`
- Responsive styles with breakpoints at 768px and 480px
- Bootstrap overrides for the login form
- Utility classes: `.card`, `.data-list`, `.button`

---

## STEP 14: Add the background image

Copy an image to `docker_login/login/img/infosec_orami_.png`.
This image is used as the parallax background in style.css.

```bash
# If you have the image in another location:
cp /path/to/your/image.png docker_login/login/img/infosec_orami_.png
```

**Note:** The CSS references `../img/infosec_orami_.png`. If the image
has a different name, you need to change the path in style.css line 50.

---

## STEP 15: Open the frontend in the browser

```bash
# Option 1: Open directly with the browser
xdg-open docker_login/login/index.html

# Option 2: Serve with Python (recommended for CORS)
cd docker_login/login
python -m http.server 8080
# Open http://localhost:8080 in the browser
```

**Why python -m http.server?** Some browsers block Ajax requests when HTML is loaded via `file://` protocol. A local HTTP server avoids this restriction by serving files over `http://`.

---

## STEP 16: Test the login

1. Make sure Docker is running (`sudo docker compose up --build` in `docker/`)
2. Open `http://localhost:8080` (or the index.html file)
3. Enter an email and password
4. If there are no users in the database, the response will be "Incorrect email or password"
5. To create a user, send a request via curl or Postman:

```bash
curl -X POST http://127.0.0.1:5000/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre":"orami","correo":"orami@technova.com","password":"my_secure_password"}'
```

6. Once the user is created, return to the login page and enter those credentials
7. The dashboard should display "Welcome, orami"

---

## STEP 17: Test the logout

1. On the dashboard, click "Log out"
2. You should return to the login
3. Attempt to access `dashboard.html` directly via URL
4. The page should redirect to the login, since the token was removed from `sessionStorage`

---

## SECURITY FEATURES

### 1. Brute Force Protection (Rate Limiting)

The API includes a rate limiting system to protect against brute force attacks on the login endpoint.

**How it works:**

- A new table `intentos_login` is automatically created in MySQL when the API starts
- Each failed login attempt is recorded in this table with the email and timestamp
- After **5 consecutive failed attempts**, the account is blocked for **15 minutes**
- During the block period, all login attempts return HTTP 429 (Too Many Requests)
- When credentials are correct, the failed attempt counter resets to zero
- The block time is calculated from the first failed attempt in the window

**Configuration (in `api.py`):**

```python
MAX_INTENTOS = 5      # Maximum failed attempts before blocking
TIEMPO_BLOQUEO = 15   # Block duration in minutes
```

**To modify the limits:**

```python
# In api.py, inside the login() function:
MAX_INTENTOS = 10     # Allow 10 attempts before blocking
TIEMPO_BLOQUEO = 30   # Block for 30 minutes
```

**Frontend behavior:**

The login form (`script.js`) detects HTTP 429 responses and shows a message with the remaining lockout time (e.g., "Account temporarily locked. Try again in 14m 32s").

**To reset a blocked account manually:**

```sql
-- Connect to MySQL
sudo docker compose exec basedatos mysql -u api_usuario -p

-- Select the database
USE practica_db;

-- View failed attempts
SELECT * FROM intentos_login;

-- Manually unblock an email
DELETE FROM intentos_login WHERE correo = 'user@example.com';
```

### 2. CORS Restriction

CORS (Cross-Origin Resource Sharing) is configured to accept requests **only** from the frontend origin.

**Current configuration:**

```python
CORS(app, origins=["http://localhost:8080"])
```

This means only `http://localhost:8080` (where the frontend is served) can make Ajax requests to the API. Any other origin (a malicious website, Postman, curl from another domain) will be blocked by the browser.

**To change the allowed origin:**

```python
# For a specific domain:
CORS(app, origins=["https://mydomain.com"])

# For multiple domains:
CORS(app, origins=["https://mydomain.com", "https://admin.mydomain.com"])

# For development only (NOT recommended for production):
CORS(app, origins=["*"])
```

**Why this matters:**

Without CORS restriction, any website could make requests to your API using the user's browser. Even though JWT tokens are not sent automatically like cookies, a malicious site could still attempt to exploit other vulnerabilities or perform denial-of-service attacks.

---

## COMMON COMMANDS

```bash
# View running containers
sudo docker ps

# View API logs in real time
sudo docker compose logs -f api

# View MySQL logs
sudo docker compose logs -f basedatos

# Enter the API container (for debugging)
sudo docker compose exec api bash

# Enter the MySQL container
sudo docker compose exec basedatos mysql -u api_usuario -p

# Stop all containers and remove volumes (WARNING: deletes database data)
sudo docker compose down -v

# Rebuild images from scratch (use after modifying the Dockerfile)
sudo docker compose up --build --force-recreate
```

---

## FINAL PROJECT STRUCTURE

```
docker_login/
├── docker/
│   ├── .env                    # Credentials (NEVER upload to Git)
│   ├── .gitignore              # Excludes .env, .venv/, __pycache__/
│   ├── Dockerfile              # Defines the API image
│   ├── docker-compose.yml      # Defines services (MySQL + API)
│   ├── requirements.txt        # Python dependencies
│   ├── config.py               # Centralized configuration
│   └── api.py                  # Flask API (CRUD + JWT + login)
│
└── login/
    ├── index.html              # Login page
    ├── dashboard.html          # Post-login page (verification + documentation)
    ├── css/
    │   └── style.css           # Custom styles (dark palette)
    ├── js/
    │   └── script.js           # Login logic via Ajax
    └── img/
        └── infosec_orami_.png  # Parallax background image
```
