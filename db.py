# db.py
import os
import sqlite3
import pymysql

MYSQL_URL = os.getenv("MYSQL_URL")  # e.g., mysql://user:pass@host:3306/dbname

def get_conn():
    if MYSQL_URL:
        # Parse MYSQL_URL -> user, password, host, port, db
        import urllib.parse as up
        u = up.urlparse(MYSQL_URL)
        return pymysql.connect(
            host=u.hostname,
            user=u.username,
            password=u.password,
            port=u.port or 3306,
            database=u.path.lstrip('/'),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    else:
        # SQLite fallback for demo
        conn = sqlite3.connect("demo.db", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
