# db.py
import os
import sqlite3
import pymysql
import urllib.parse as up

MYSQL_URL = os.getenv("MYSQL_URL")  # e.g. mysql://user:pass@127.0.0.1:3306/restaurant
SQLITE_PATH = os.getenv("SQLITE_PATH", "/tmp/demo.db")  # writable on Render

# ------------------------- Connection factory -------------------------

def get_conn():
    """
    Returns a connection to MySQL if MYSQL_URL is set; otherwise a SQLite connection
    (wrapped in a proxy so context managers & %s placeholders still work).
    """
    if MYSQL_URL:
        u = up.urlparse(MYSQL_URL)
        return pymysql.connect(
            host=u.hostname,
            user=u.username,
            password=u.password,
            port=u.port or 3306,
            database=u.path.lstrip("/"),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    # SQLite fallback
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return _SQLiteConnProxy(conn)

def is_sqlite_conn(conn) -> bool:
    """True if the connection is our SQLite proxy."""
    return isinstance(conn, _SQLiteConnProxy)

# ------------------------- Cursor compatibility -------------------------

def _convert_percent_s_to_qmark(query: str) -> str:
    return query.replace("%s", "?")

def _row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    return row

class _SQLiteCompatCursor:
    """Wrapper so you can keep using MySQL-style `%s` placeholders and context managers."""
    def __init__(self, inner):
        self._cur = inner
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        try:
            self._cur.close()
        except Exception:
            pass
    def execute(self, query, params=None):
        q = _convert_percent_s_to_qmark(query)
        if params is None:
            return self._cur.execute(q)
        if isinstance(params, dict):
            params = tuple(params[k] for k in sorted(params.keys()))
        elif not isinstance(params, (list, tuple)):
            params = (params,)
        return self._cur.execute(q, params)
    def executemany(self, query, seq_of_params):
        q = _convert_percent_s_to_qmark(query)
        norm = []
        for p in seq_of_params:
            if isinstance(p, dict):
                p = tuple(p[k] for k in sorted(p.keys()))
            elif not isinstance(p, (list, tuple)):
                p = (p,)
            norm.append(p)
        return self._cur.executemany(q, norm)
    def fetchone(self):
        return _row_to_dict(self._cur.fetchone())
    def fetchall(self):
        return [_row_to_dict(r) for r in self._cur.fetchall()]
    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size else self._cur.fetchmany()
        return [_row_to_dict(r) for r in rows]
    def close(self):
        return self._cur.close()
    @property
    def lastrowid(self):
        return getattr(self._cur, "lastrowid", None)

class _SQLiteConnProxy:
    """
    Proxy around sqlite3.Connection so your code can keep doing:
        with get_conn() as conn:
            with conn.cursor() as cur:
                ...
    """
    def __init__(self, conn):
        self._conn = conn
    # context manager passthrough
    def __enter__(self):
        self._conn.__enter__()
        return self
    def __exit__(self, exc_type, exc, tb):
        return self._conn.__exit__(exc_type, exc, tb)
    # attribute passthrough
    def __getattr__(self, name):
        return getattr(self._conn, name)
    # cursor wrapper
    def cursor(self):
        return _SQLiteCompatCursor(self._conn.cursor())
    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

# ------------------------- Schema bootstrap (idempotent) -------------------------

def ensure_schema(conn):
    """
    Create the full schema if it doesn't exist. Runs safely multiple times.
    Uses MySQL-friendly DDL when on MySQL and SQLite-friendly DDL on SQLite.
    """
    if is_sqlite_conn(conn):
        _ensure_schema_sqlite(conn)
    else:
        _ensure_schema_mysql(conn)

def _ensure_schema_mysql(conn):
    ddl = """
    CREATE TABLE IF NOT EXISTS RESTAURANT (
      Restaurant_ID INT PRIMARY KEY AUTO_INCREMENT,
      Name VARCHAR(100) NOT NULL,
      Address VARCHAR(255),
      Phone VARCHAR(20),
      Opening_Hours VARCHAR(100)
    );
    CREATE TABLE IF NOT EXISTS CUSTOMER (
      Customer_ID INT PRIMARY KEY AUTO_INCREMENT,
      Name VARCHAR(100) NOT NULL,
      Email VARCHAR(100),
      Phone VARCHAR(20),
      Address VARCHAR(255)
    );
    CREATE TABLE IF NOT EXISTS DELIVERY_AGENT (
      Agent_ID INT PRIMARY KEY AUTO_INCREMENT,
      Name VARCHAR(100) NOT NULL,
      Phone VARCHAR(20)
    );
    CREATE TABLE IF NOT EXISTS FOOD_ITEM (
      Item_ID INT PRIMARY KEY AUTO_INCREMENT,
      Name VARCHAR(100) NOT NULL,
      Price DECIMAL(10,2) NOT NULL,
      Restaurant_ID INT NOT NULL,
      CONSTRAINT FK_Food_Rest FOREIGN KEY (Restaurant_ID)
        REFERENCES RESTAURANT(Restaurant_ID)
        ON UPDATE CASCADE ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS ORDERS (
      Order_ID INT PRIMARY KEY AUTO_INCREMENT,
      Customer_ID INT,
      Restaurant_ID INT,
      Order_Date DATETIME NOT NULL,
      Total_Amount DECIMAL(10,2) NOT NULL,
      Agent_ID INT,
      CONSTRAINT FK_Order_Cust FOREIGN KEY (Customer_ID)
        REFERENCES CUSTOMER(Customer_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
      CONSTRAINT FK_Order_Rest FOREIGN KEY (Restaurant_ID)
        REFERENCES RESTAURANT(Restaurant_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
      CONSTRAINT FK_Order_Agent FOREIGN KEY (Agent_ID)
        REFERENCES DELIVERY_AGENT(Agent_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS ORDER_DETAIL (
      Order_ID INT,
      Item_ID INT,
      Quantity INT NOT NULL,
      PRIMARY KEY (Order_ID, Item_ID),
      CONSTRAINT FK_OD_Order FOREIGN KEY (Order_ID)
        REFERENCES ORDERS(Order_ID)
        ON UPDATE CASCADE ON DELETE CASCADE,
      CONSTRAINT FK_OD_Item FOREIGN KEY (Item_ID)
        REFERENCES FOOD_ITEM(Item_ID)
        ON UPDATE CASCADE ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS DELIVERY (
      Delivery_ID INT PRIMARY KEY AUTO_INCREMENT,
      Order_ID INT NOT NULL,
      Agent_ID INT NOT NULL,
      Delivery_Date DATE,
      Status VARCHAR(50),
      CONSTRAINT FK_Del_Order FOREIGN KEY (Order_ID)
        REFERENCES ORDERS(Order_ID)
        ON UPDATE CASCADE ON DELETE CASCADE,
      CONSTRAINT FK_Del_Agent FOREIGN KEY (Agent_ID)
        REFERENCES DELIVERY_AGENT(Agent_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS REVIEW (
      Review_ID INT PRIMARY KEY AUTO_INCREMENT,
      Customer_ID INT,
      Restaurant_ID INT,
      Review_Date DATE,
      Rating INT,
      Comment1 TEXT,
      CONSTRAINT FK_Rev_Cust FOREIGN KEY (Customer_ID)
        REFERENCES CUSTOMER(Customer_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
      CONSTRAINT FK_Rev_Rest FOREIGN KEY (Restaurant_ID)
        REFERENCES RESTAURANT(Restaurant_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS PAYMENT (
      Payment_ID INT PRIMARY KEY AUTO_INCREMENT,
      Order_ID INT,
      Amount DECIMAL(10,2),
      Payment_Method VARCHAR(50),
      Payment_Date DATE,
      CONSTRAINT FK_Pay_Order FOREIGN KEY (Order_ID)
        REFERENCES ORDERS(Order_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS RIDER_LOCATION (
      Agent_ID INT PRIMARY KEY,
      Latitude DECIMAL(9,6),
      Longitude DECIMAL(9,6),
      Last_Updated DATETIME,
      CONSTRAINT FK_RL_Agent FOREIGN KEY (Agent_ID)
        REFERENCES DELIVERY_AGENT(Agent_ID)
        ON UPDATE CASCADE ON DELETE CASCADE
    );
    """
    with conn.cursor() as cur:
        for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
            cur.execute(stmt)

def _ensure_schema_sqlite(conn):
    # SQLite types are looser; use INTEGER PRIMARY KEY AUTOINCREMENT and NUMERIC
    ddl = """
    CREATE TABLE IF NOT EXISTS RESTAURANT (
      Restaurant_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Name TEXT NOT NULL,
      Address TEXT,
      Phone TEXT,
      Opening_Hours TEXT
    );
    CREATE TABLE IF NOT EXISTS CUSTOMER (
      Customer_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Name TEXT NOT NULL,
      Email TEXT,
      Phone TEXT,
      Address TEXT
    );
    CREATE TABLE IF NOT EXISTS DELIVERY_AGENT (
      Agent_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Name TEXT NOT NULL,
      Phone TEXT
    );
    CREATE TABLE IF NOT EXISTS FOOD_ITEM (
      Item_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Name TEXT NOT NULL,
      Price NUMERIC NOT NULL,
      Restaurant_ID INTEGER NOT NULL,
      FOREIGN KEY (Restaurant_ID) REFERENCES RESTAURANT(Restaurant_ID)
        ON UPDATE CASCADE ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS ORDERS (
      Order_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Customer_ID INTEGER,
      Restaurant_ID INTEGER,
      Order_Date TEXT NOT NULL,         -- store ISO string
      Total_Amount NUMERIC NOT NULL,
      Agent_ID INTEGER,
      FOREIGN KEY (Customer_ID) REFERENCES CUSTOMER(Customer_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
      FOREIGN KEY (Restaurant_ID) REFERENCES RESTAURANT(Restaurant_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
      FOREIGN KEY (Agent_ID) REFERENCES DELIVERY_AGENT(Agent_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS ORDER_DETAIL (
      Order_ID INTEGER,
      Item_ID INTEGER,
      Quantity INTEGER NOT NULL,
      PRIMARY KEY (Order_ID, Item_ID),
      FOREIGN KEY (Order_ID) REFERENCES ORDERS(Order_ID)
        ON UPDATE CASCADE ON DELETE CASCADE,
      FOREIGN KEY (Item_ID) REFERENCES FOOD_ITEM(Item_ID)
        ON UPDATE CASCADE ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS DELIVERY (
      Delivery_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Order_ID INTEGER NOT NULL,
      Agent_ID INTEGER NOT NULL,
      Delivery_Date TEXT,
      Status TEXT,
      FOREIGN KEY (Order_ID) REFERENCES ORDERS(Order_ID)
        ON UPDATE CASCADE ON DELETE CASCADE,
      FOREIGN KEY (Agent_ID) REFERENCES DELIVERY_AGENT(Agent_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS REVIEW (
      Review_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Customer_ID INTEGER,
      Restaurant_ID INTEGER,
      Review_Date TEXT,
      Rating INTEGER,
      Comment1 TEXT,
      FOREIGN KEY (Customer_ID) REFERENCES CUSTOMER(Customer_ID)
        ON UPDATE CASCADE ON DELETE SET NULL,
      FOREIGN KEY (Restaurant_ID) REFERENCES RESTAURANT(Restaurant_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS PAYMENT (
      Payment_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Order_ID INTEGER,
      Amount NUMERIC,
      Payment_Method TEXT,
      Payment_Date TEXT,
      FOREIGN KEY (Order_ID) REFERENCES ORDERS(Order_ID)
        ON UPDATE CASCADE ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS RIDER_LOCATION (
      Agent_ID INTEGER PRIMARY KEY,
      Latitude NUMERIC,
      Longitude NUMERIC,
      Last_Updated TEXT,
      FOREIGN KEY (Agent_ID) REFERENCES DELIVERY_AGENT(Agent_ID)
        ON UPDATE CASCADE ON DELETE CASCADE
    );
    """
    with conn.cursor() as cur:
        for stmt in [s.strip() for s in ddl.split(";") if s.strip()]:
            cur.execute(stmt)
