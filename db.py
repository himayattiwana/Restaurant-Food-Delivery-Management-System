import os
import pymysql
from urllib.parse import urlparse
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")

if db_url:
    parsed = urlparse(db_url)
    DB_HOST = parsed.hostname
    DB_PORT = parsed.port or 3306
    DB_USER = parsed.username
    DB_PASSWORD = parsed.password
    DB_NAME = parsed.path.lstrip("/")
else:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "restaurant_db")

def get_conn(dict_rows: bool = True):
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        autocommit=True,
        cursorclass=DictCursor if dict_rows else pymysql.cursors.Cursor,
        charset="utf8mb4"
    )
