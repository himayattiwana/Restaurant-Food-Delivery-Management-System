import os
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv


load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "restaurant_db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

def get_conn(dict_rows: bool = True):
    """
    Return a PyMySQL connection.
    dict_rows=True gives rows as dicts (easier in Jinja).
    """
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
