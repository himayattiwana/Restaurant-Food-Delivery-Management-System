import os, pymysql
from urllib.parse import urlparse
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_HOST, DB_PORT, DB_USER, DB_NAME]):
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        DB_HOST = parsed.hostname
        DB_PORT = parsed.port or 3306
        DB_USER = parsed.username
        DB_PASSWORD = parsed.password
        DB_NAME = parsed.path.lstrip("/")
    else:
        DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME = "localhost", 3306, "root", "", "restaurant_db"
else:
    DB_PORT = int(DB_PORT)

def get_conn(dict_rows=True):
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, port=DB_PORT, autocommit=True,
        cursorclass=DictCursor if dict_rows else pymysql.cursors.Cursor,
        charset="utf8mb4"
    )
