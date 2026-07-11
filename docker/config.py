import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "basedatos")
    MYSQL_USER = os.environ.get("MYSQL_USER")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")

    # Secret key used to sign and verify JWT tokens.
    # Read from .env, never hardcoded here.
    SECRET_KEY = os.environ.get("SECRET_KEY")
