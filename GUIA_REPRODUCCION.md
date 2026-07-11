# Step-by-step Guide: Docker + Flask + MySQL + Login Project
# Reproduce from scratch on any Linux machine

This guide documents the entire process to set up the complete project.
Each step includes what to do, why it is done, and what result to expect.

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

**Why sudo?** Belonging to the `docker` group is equivalent to root privileges.
Keeping sudo is a conscious security decision.

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
- `COPY requirements.txt .`: copies the dependencies file BEFORE the code
- `RUN pip install...`: installs dependencies (cached if requirements.txt has not changed)
- `COPY config.py .` and `COPY api.py .`: copies the source code
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

**Why a class?** It centralizes all configuration in one place.
If tomorrow the MySQL password changes, you change it ONCE in .env,
no need to search through all the code.

---

## STEP 5: Create api.py

Create `docker_login/docker/api.py` with the complete project content.
This is the largest file: it contains the Flask API with:

- Routes: `/`, `/welcome`, `/users` (CRUD), `/login`, `/check-session`
- `@token_required` decorator to protect routes with JWT
- MySQL connection using mysql.connector
- Password hashing with werkzeug.security
- Automatic creation of the `usuarios` table on startup

**The complete file is at `docker_login/docker/api.py`.**
The English comments explain every function and every relevant line.

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
SECRET_KEY=0b855363bc44f16d8f73342325475f27d21bdef8263a24de8f468603d0466ef2
```

**IMPORTANT:** In a real project, NEVER upload this file to Git.
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

**Why `.venv/` and `venv/`?** Depending on how the virtual environment is created,
the folder may or may not have a dot. Both should be excluded.

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
- `basedatos`: starts MySQL 8.0 with credentials from .env
- `volumes`: persists MySQL data in a named volume
- `healthcheck`: verifies that MySQL is ready before starting the API
- `api`: builds the image from the Dockerfile and connects it to MySQL
- `depends_on: condition: service_healthy`: waits for MySQL to respond

---

## STEP 9: Start the backend with Docker

```bash
# Enter the docker folder
cd docker_login/docker

# Build the image and start both containers
sudo docker compose up --build
```

**Expected result:**
- First you will see Docker build the API image
- Then it starts MySQL and waits for the healthcheck to respond
- Finally it starts the API with Gunicorn
- You will see Gunicorn logs in the terminal showing requests

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
The file uses Bootstrap 5.3.8 via CDN and jQuery 3.7.1 via CDN.

**The complete file is at `docker_login/login/index.html`.**
Key elements:
- `id="login-form"`: the form that script.js captures
- `id="email"` and `id="password"`: the inputs that script.js reads
- `id="result-message"`: div for success/error messages
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
- Configurable API_URL for the `/check-session` endpoint

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

**Why python -m http.server?** Some browsers block Ajax requests
when HTML is opened directly as a file://. A local server
prevents that problem.

---

## STEP 16: Test the login

1. Make sure Docker is running (`sudo docker compose up --build` in `docker/`)
2. Open `http://localhost:8080` (or the index.html file)
3. Enter an email and password
4. If it is the first time, there are no users: you will get "Incorrect email or password"
5. To create a user, use curl or Postman:

```bash
# First log in with an existing user, or create one with curl:
curl -X POST http://127.0.0.1:5000/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token_you_got>" \
  -d '{"name":"orami","email":"orami@technova.com","password":"my_secure_password"}'
```

6. Once a user is created, go back to the login and enter those credentials
7. You should see the dashboard with "Welcome, orami"

---

## STEP 17: Test the logout

1. On the dashboard, click "Log out"
2. You should return to the login
3. Try to access `dashboard.html` directly in the URL
4. It should redirect you to the login automatically (the token was deleted)

---

## USEFUL COMMANDS FOR DAILY USE

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

# Stop everything and delete volumes (WARNING: deletes the database)
sudo docker compose down -v

# Rebuild from scratch (if you changed something in the Dockerfile)
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
