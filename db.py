# db.py
import os
import sqlite3
import pymysql
import urllib.parse as up

# --- Config ---
MYSQL_URL = os.getenv("MYSQL_URL")  # e.g. mysql://user:pass@127.0.0.1:3306/restaurant
SQLITE_PATH = os.getenv("SQLITE_PATH", "/tmp/demo.db")  # writable on Render

# =========================
# Connection factory
# =========================
def get_conn():
    """
    MySQL if MYSQL_URL is set, else SQLite.
    SQLite is opened in AUTOCOMMIT mode so inserts/updates are visible immediately.
    For SQLite, returns a proxy that:
      - supports `with conn.cursor() as cur:`
      - converts %s -> ? so your existing queries work unchanged
    """
    if MYSQL_URL:
        u = up.urlparse(MYSQL_URL)
        return pymysql.connect(
            host=u.hostname,
            user=u.username,
            password=u.password,
            port=u.port or 3306,
            database=(u.path or "/").lstrip("/"),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,  # MySQL autocommit
        )

    # SQLite: autocommit ON (isolation_level=None)
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return _SQLiteConnProxy(conn)

def is_sqlite_conn(conn) -> bool:
    return isinstance(conn, _SQLiteConnProxy)

# =========================
# SQLite compatibility layer
# =========================
def _convert_percent_s_to_qmark(query: str) -> str:
    # naive but effective for typical CRUD
    return query.replace("%s", "?")

def _row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    return row

class _SQLiteCompatCursor:
    """Context-manager cursor that accepts %s placeholders, returns dict-like rows."""
    def __init__(self, inner):
        self._cur = inner

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        try: self._cur.close()
        except Exception: pass

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

    def fetchone(self): return _row_to_dict(self._cur.fetchone())
    def fetchall(self): return [_row_to_dict(r) for r in self._cur.fetchall()]
    def fetchmany(self, size=None):
        rows = self._cur.fetchmany(size) if size else self._cur.fetchmany()
        return [_row_to_dict(r) for r in rows]
    def close(self): return self._cur.close()
    @property
    def lastrowid(self): return getattr(self._cur, "lastrowid", None)

class _SQLiteConnProxy:
    """Proxy so you can keep using `with get_conn() as conn:` and `with conn.cursor() as cur:`."""
    def __init__(self, conn):
        self._conn = conn

    # context manager passthrough
    def __enter__(self):
        # In autocommit mode this is a no-op, but keep API parity
        return self
    def __exit__(self, exc_type, exc, tb):
        # No implicit commit needed (autocommit). Close handled by platform.
        return False

    # attributes passthrough
    def __getattr__(self, name):
        return getattr(self._conn, name)

    # cursor that understands %s + returns dict rows
    def cursor(self):
        return _SQLiteCompatCursor(self._conn.cursor())

    def commit(self):
        try: self._conn.commit()
        except Exception: pass

    def close(self):
        try: self._conn.close()
        except Exception: pass

# =========================
# Schema bootstrap (idempotent)
# =========================
def ensure_schema(conn):
    """Create tables if missing. Safe to run multiple times."""
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
    CREATE TABLE IF NOT EXISTS COUPON (
      Coupon_ID INT PRIMARY KEY AUTO_INCREMENT,
      Code VARCHAR(50) UNIQUE NOT NULL,
      Discount DECIMAL(10,2) NOT NULL,
      Expiry_Date DATE
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
      Order_Date TEXT NOT NULL,
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
    CREATE TABLE IF NOT EXISTS COUPON (
      Coupon_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Code TEXT UNIQUE NOT NULL,
      Discount NUMERIC NOT NULL,
      Expiry_Date TEXT
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

# =========================
# Sample Data Insertion
# =========================
def insert_sample_data(conn):
    """Insert sample data if tables are empty. Safe to run multiple times."""
    try:
        with conn.cursor() as cur:
            # Check if we already have data
            cur.execute("SELECT COUNT(*) as c FROM RESTAURANT")
            row = cur.fetchone()
            count = row["c"] if isinstance(row, dict) else row[0]
            
            if count > 0:
                # Data already exists, skip insertion
                return
            
            print("Inserting sample data...")
            
            # Insert Restaurants
            restaurants = [
                ("Pizza Palace", "123 Main St, New York", "555-0100", "11:00-23:00"),
                ("Burger House", "456 Oak Ave, Los Angeles", "555-0101", "10:00-22:00"),
                ("Sushi World", "789 Pine Rd, San Francisco", "555-0102", "12:00-21:00"),
                ("Taco Town", "321 Elm St, Chicago", "555-0103", "11:00-23:00"),
                ("Pasta Paradise", "654 Maple Dr, Miami", "555-0104", "12:00-22:00"),
            ]
            cur.executemany(
                "INSERT INTO RESTAURANT (Name, Address, Phone, Opening_Hours) VALUES (%s, %s, %s, %s)",
                restaurants
            )
            
            # Insert Customers
            customers = [
                ("John Doe", "john@example.com", "555-1001", "10 Park Ave, New York"),
                ("Jane Smith", "jane@example.com", "555-1002", "20 Broadway, Los Angeles"),
                ("Bob Johnson", "bob@example.com", "555-1003", "30 Market St, San Francisco"),
                ("Alice Williams", "alice@example.com", "555-1004", "40 State St, Chicago"),
                ("Charlie Brown", "charlie@example.com", "555-1005", "50 Ocean Dr, Miami"),
                ("Diana Prince", "diana@example.com", "555-1006", "60 Hill St, New York"),
                ("Eve Adams", "eve@example.com", "555-1007", "70 Valley Rd, Los Angeles"),
                ("Frank Castle", "frank@example.com", "555-1008", "80 River Ln, San Francisco"),
            ]
            cur.executemany(
                "INSERT INTO CUSTOMER (Name, Email, Phone, Address) VALUES (%s, %s, %s, %s)",
                customers
            )
            
            # Insert Delivery Agents
            agents = [
                ("Mike Driver", "555-2001"),
                ("Sarah Rider", "555-2002"),
                ("Tom Wheeler", "555-2003"),
                ("Lisa Fast", "555-2004"),
                ("Jack Quick", "555-2005"),
            ]
            cur.executemany(
                "INSERT INTO DELIVERY_AGENT (Name, Phone) VALUES (%s, %s)",
                agents
            )
            
            # Insert Food Items
            food_items = [
                ("Margherita Pizza", 12.99, 1),
                ("Pepperoni Pizza", 14.99, 1),
                ("Veggie Pizza", 13.99, 1),
                ("Cheeseburger", 9.99, 2),
                ("Bacon Burger", 11.99, 2),
                ("Veggie Burger", 10.99, 2),
                ("California Roll", 8.99, 3),
                ("Salmon Nigiri", 12.99, 3),
                ("Tuna Sashimi", 15.99, 3),
                ("Beef Tacos", 7.99, 4),
                ("Chicken Tacos", 6.99, 4),
                ("Fish Tacos", 8.99, 4),
                ("Spaghetti Carbonara", 13.99, 5),
                ("Fettuccine Alfredo", 14.99, 5),
                ("Penne Arrabbiata", 12.99, 5),
            ]
            cur.executemany(
                "INSERT INTO FOOD_ITEM (Name, Price, Restaurant_ID) VALUES (%s, %s, %s)",
                food_items
            )
            
            # Insert Sample Orders
            orders = [
                (1, 1, "2024-11-01 12:00:00", 25.98, 1),
                (2, 2, "2024-11-01 13:30:00", 21.98, 2),
                (3, 3, "2024-11-02 19:00:00", 24.98, 3),
                (4, 4, "2024-11-02 20:15:00", 14.98, 4),
                (5, 5, "2024-11-03 12:45:00", 28.98, 5),
            ]
            cur.executemany(
                "INSERT INTO ORDERS (Customer_ID, Restaurant_ID, Order_Date, Total_Amount, Agent_ID) VALUES (%s, %s, %s, %s, %s)",
                orders
            )
            
            # Insert Coupons
            coupons = [
                ("SAVE10", 10.00, "2025-12-31"),
                ("SAVE20", 20.00, "2025-12-31"),
                ("FREESHIP", 5.00, "2025-11-30"),
                ("NEWYEAR25", 25.00, "2025-01-31"),
            ]
            cur.executemany(
                "INSERT INTO COUPON (Code, Discount, Expiry_Date) VALUES (%s, %s, %s)",
                coupons
            )
            
            conn.commit()
            print("Sample data inserted successfully!")
            
    except Exception as e:
        print(f"Error inserting sample data: {e}")
        # Don't raise - app should continue even if sample data fails