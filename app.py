# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from threading import Lock
import sqlite3

from db import get_conn, ensure_schema

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"  # set SECRET_KEY in prod

# -------- Health (for Render) --------
@app.get("/health")
def health():
    return "OK", 200

# -------- Ensure schema once per worker (Flask 3.x safe) --------
_schema_ready = False
_schema_lock = Lock()

@app.before_request
def _ensure_schema_once():
    global _schema_ready
    if not _schema_ready:
        with _schema_lock:
            if not _schema_ready:
                try:
                    with get_conn() as conn:
                        ensure_schema(conn)
                    _schema_ready = True
                except Exception:
                    # don't block requests if schema init fails
                    pass

# -------- Helpers --------
def _data():
    """Return data from HTML form or JSON, never raising BadRequest."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form

def _parse_date(value, fmt="%Y-%m-%d"):
    if not value:
        return None
    try:
        return datetime.strptime(value, fmt)
    except Exception:
        return None

def _commit(conn):
    """Force-commit for both MySQL and SQLite (no-op if autocommit)."""
    try:
        conn.commit()
    except Exception:
        pass

def _lazy_create_coupon(conn):
    """If COUPON table is missing (SQLite partial init), create it quickly."""
    ddl = """
    CREATE TABLE IF NOT EXISTS COUPON (
      Coupon_ID INTEGER PRIMARY KEY AUTOINCREMENT,
      Code TEXT UNIQUE NOT NULL,
      Discount NUMERIC NOT NULL,
      Expiry_Date TEXT
    );
    """
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
    except Exception:
        # Ignore; main schema creation already tries this too
        pass

# ---------- Home (Dashboard) ----------
@app.route("/")
def home():
    stats = {}
    latest_orders = []
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM RESTAURANT")
            row = cur.fetchone(); stats["restaurants"] = (row["c"] if isinstance(row, dict) else row[0]) if row else 0

            cur.execute("SELECT COUNT(*) AS c FROM CUSTOMER")
            row = cur.fetchone(); stats["customers"] = (row["c"] if isinstance(row, dict) else row[0]) if row else 0

            cur.execute("SELECT COUNT(*) AS c FROM FOOD_ITEM")
            row = cur.fetchone(); stats["food_items"] = (row["c"] if isinstance(row, dict) else row[0]) if row else 0

            cur.execute("SELECT COUNT(*) AS c FROM ORDERS")
            row = cur.fetchone(); stats["orders"] = (row["c"] if isinstance(row, dict) else row[0]) if row else 0

            cur.execute("SELECT COUNT(*) AS c FROM DELIVERY_AGENT")
            row = cur.fetchone(); stats["agents"] = (row["c"] if isinstance(row, dict) else row[0]) if row else 0

            cur.execute("""
                SELECT o.Order_ID, c.Name AS customer, r.Name AS restaurant, o.Order_Date, o.Total_Amount
                FROM ORDERS o
                JOIN CUSTOMER c ON o.Customer_ID = c.Customer_ID
                JOIN RESTAURANT r ON o.Restaurant_ID = r.Restaurant_ID
                ORDER BY o.Order_Date DESC
                LIMIT 5
            """)
            latest_orders = cur.fetchall()
    return render_template("home.html", stats=stats, latest_orders=latest_orders)

# ---------- Restaurants ----------
@app.route("/restaurants")
def restaurants():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM RESTAURANT ORDER BY Name")
            rows = cur.fetchall()
    return render_template("restaurants.html", rows=rows)

# POST shim so templates that post to /restaurants still work
@app.route("/restaurants", methods=["POST"])
def restaurants_post():
    return add_restaurant()

@app.route("/restaurants/add", methods=["POST"])
def add_restaurant():
    data = _data()
    name = (data.get("name") or data.get("restaurant_name") or "").strip()
    address = (data.get("address") or data.get("restaurant_address") or "").strip()
    phone = (data.get("phone") or data.get("restaurant_phone") or "").strip()
    opening_hours = (data.get("opening_hours") or data.get("hours") or "").strip()

    if not name:
        flash("Restaurant name is required", "error")
        return redirect(url_for("restaurants"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO RESTAURANT (Name, Address, Phone, Opening_Hours) VALUES (%s, %s, %s, %s)",
                (name, address, phone, opening_hours),
            )
        _commit(conn)
    flash("Restaurant added", "success")
    return redirect(url_for("restaurants"))

@app.route("/restaurants/delete/<int:restaurant_id>")
def delete_restaurant(restaurant_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM RESTAURANT WHERE Restaurant_ID = %s", (restaurant_id,))
        _commit(conn)
    flash("Restaurant deleted", "success")
    return redirect(url_for("restaurants"))

# ---------- Customers ----------
@app.route("/customers")
def customers():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM CUSTOMER ORDER BY Name")
            rows = cur.fetchall()
    return render_template("customers.html", rows=rows)

@app.route("/customers", methods=["POST"])
def customers_post():
    return add_customer()

@app.route("/customers/add", methods=["POST"])
def add_customer():
    data = _data()
    name = (data.get("name") or data.get("customer_name") or "").strip()
    email = (data.get("email") or data.get("customer_email") or "").strip()
    phone = (data.get("phone") or data.get("customer_phone") or "").strip()
    address = (data.get("address") or data.get("customer_address") or "").strip()

    if not name:
        flash("Customer name is required", "error")
        return redirect(url_for("customers"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO CUSTOMER (Name, Email, Phone, Address) VALUES (%s, %s, %s, %s)",
                (name, email, phone, address),
            )
        _commit(conn)
    flash("Customer added", "success")
    return redirect(url_for("customers"))

@app.route("/customers/delete/<int:customer_id>")
def delete_customer(customer_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM CUSTOMER WHERE Customer_ID = %s", (customer_id,))
        _commit(conn)
    flash("Customer deleted", "success")
    return redirect(url_for("customers"))

# ---------- Food Items ----------
@app.route("/food_items")
def food_items():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.*, r.Name AS Restaurant_Name
                FROM FOOD_ITEM f
                JOIN RESTAURANT r ON f.Restaurant_ID = r.Restaurant_ID
                ORDER BY r.Name, f.Name
            """)
            rows = cur.fetchall()
    return render_template("food_items.html", rows=rows)

@app.route("/food_items", methods=["POST"])
def food_items_post():
    return add_food_item()

@app.route("/food_items/add", methods=["POST"])
def add_food_item():
    data = _data()
    name = (data.get("name") or data.get("item_name") or "").strip()
    price = (data.get("price") or data.get("item_price") or "").strip()
    restaurant_id = (data.get("restaurant_id") or data.get("rest_id") or "").strip()

    if not name or not price or not restaurant_id:
        flash("Name, Price and Restaurant are required", "error")
        return redirect(url_for("food_items"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO FOOD_ITEM (Name, Price, Restaurant_ID) VALUES (%s, %s, %s)",
                (name, price, restaurant_id),
            )
        _commit(conn)
    flash("Food item added", "success")
    return redirect(url_for("food_items"))

@app.route("/food_items/delete/<int:item_id>")
def delete_food_item(item_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM FOOD_ITEM WHERE Item_ID = %s", (item_id,))
        _commit(conn)
    flash("Food item deleted", "success")
    return redirect(url_for("food_items"))

# ---------- Orders ----------
@app.route("/orders")
def orders():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.*, c.Name AS Customer_Name, r.Name AS Restaurant_Name, d.Name AS Agent_Name
                FROM ORDERS o
                JOIN CUSTOMER c ON o.Customer_ID = c.Customer_ID
                JOIN RESTAURANT r ON o.Restaurant_ID = r.Restaurant_ID
                LEFT JOIN DELIVERY_AGENT d ON o.Agent_ID = d.Agent_ID
                ORDER BY o.Order_Date DESC
            """)
            rows = cur.fetchall()
    return render_template("orders.html", rows=rows)

@app.route("/orders", methods=["POST"])
def orders_post():
    return add_order()

@app.route("/orders/add", methods=["POST"])
def add_order():
    data = _data()
    customer_id = data.get("customer_id") or data.get("cust_id")
    restaurant_id = data.get("restaurant_id") or data.get("rest_id")
    order_date = _parse_date(data.get("order_date")) or datetime.utcnow()
    total_amount = data.get("total_amount") or data.get("amount") or 0
    agent_id = data.get("agent_id") or None

    if not customer_id or not restaurant_id:
        flash("Customer and Restaurant are required", "error")
        return redirect(url_for("orders"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ORDERS (Customer_ID, Restaurant_ID, Order_Date, Total_Amount, Agent_ID)
                VALUES (%s, %s, %s, %s, %s)
            """, (customer_id, restaurant_id, order_date, total_amount, agent_id))
        _commit(conn)
    flash("Order added", "success")
    return redirect(url_for("orders"))

@app.route("/orders/delete/<int:order_id>")
def delete_order(order_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ORDERS WHERE Order_ID = %s", (order_id,))
        _commit(conn)
    flash("Order deleted", "success")
    return redirect(url_for("orders"))

# ---------- Order Details ----------
@app.route("/order_details/<int:order_id>")
def order_details(order_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT od.*, f.Name AS Food_Name
                FROM ORDER_DETAIL od
                JOIN FOOD_ITEM f ON od.Item_ID = f.Item_ID
                WHERE od.Order_ID = %s
            """, (order_id,))
            rows = cur.fetchall()
    return render_template("order_details.html", rows=rows, order_id=order_id)

@app.route("/order_details/add/<int:order_id>", methods=["POST"])
def add_order_detail(order_id):
    data = _data()
    item_id = data.get("item_id")
    quantity = data.get("quantity") or 1

    if not item_id:
        flash("Item is required", "error")
        return redirect(url_for("order_details", order_id=order_id))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ORDER_DETAIL (Order_ID, Item_ID, Quantity)
                VALUES (%s, %s, %s)
            """, (order_id, item_id, quantity))
        _commit(conn)
    flash("Item added to order", "success")
    return redirect(url_for("order_details", order_id=order_id))

@app.route("/order_details/delete/<int:order_id>/<int:item_id>")
def delete_order_detail(order_id, item_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ORDER_DETAIL WHERE Order_ID = %s AND Item_ID = %s", (order_id, item_id))
        _commit(conn)
    flash("Item removed from order", "success")
    return redirect(url_for("order_details", order_id=order_id))

# ---------- Delivery Agents ----------
@app.route("/delivery_agents")
def delivery_agents():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM DELIVERY_AGENT ORDER BY Name")
            rows = cur.fetchall()
    return render_template("delivery_agents.html", rows=rows)

@app.route("/delivery_agents", methods=["POST"])
def delivery_agents_post():
    return add_delivery_agent()

@app.route("/delivery_agents/add", methods=["POST"])
def add_delivery_agent():
    data = _data()
    name = (data.get("name") or data.get("agent_name") or "").strip()
    phone = (data.get("phone") or data.get("agent_phone") or "").strip()

    if not name:
        flash("Agent name is required", "error")
        return redirect(url_for("delivery_agents"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO DELIVERY_AGENT (Name, Phone) VALUES (%s, %s)", (name, phone))
        _commit(conn)
    flash("Delivery agent added", "success")
    return redirect(url_for("delivery_agents"))

@app.route("/delivery_agents/delete/<int:agent_id>")
def delete_delivery_agent(agent_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM DELIVERY_AGENT WHERE Agent_ID = %s", (agent_id,))
        _commit(conn)
    flash("Delivery agent deleted", "success")
    return redirect(url_for("delivery_agents"))

# ---------- Deliveries ----------
@app.route("/deliveries")
def deliveries():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.*, a.Name AS Agent_Name, o.Order_Date
                FROM DELIVERY d
                JOIN DELIVERY_AGENT a ON d.Agent_ID = a.Agent_ID
                JOIN ORDERS o ON d.Order_ID = o.Order_ID
                ORDER BY d.Delivery_Date DESC
            """)
            rows = cur.fetchall()
    return render_template("deliveries.html", rows=rows)

@app.route("/deliveries", methods=["POST"])
def deliveries_post():
    return add_delivery()

@app.route("/deliveries/add", methods=["POST"])
def add_delivery():
    data = _data()
    order_id = data.get("order_id")
    agent_id = data.get("agent_id")
    delivery_date = _parse_date(data.get("delivery_date")) or datetime.utcnow()
    status = (data.get("status") or "").strip()

    if not order_id or not agent_id:
        flash("Order and Agent are required", "error")
        return redirect(url_for("deliveries"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO DELIVERY (Order_ID, Agent_ID, Delivery_Date, Status)
                VALUES (%s, %s, %s, %s)
            """, (order_id, agent_id, delivery_date, status))
        _commit(conn)
    flash("Delivery recorded", "success")
    return redirect(url_for("deliveries"))

@app.route("/deliveries/delete/<int:delivery_id>")
def delete_delivery(delivery_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM DELIVERY WHERE Delivery_ID = %s", (delivery_id,))
        _commit(conn)
    flash("Delivery deleted", "success")
    return redirect(url_for("deliveries"))

# ---------- Coupons ----------
@app.route("/coupons")
def coupons():
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT * FROM COUPON ORDER BY Code")
            except Exception:
                # If schema init was partial, create COUPON lazily and retry
                _lazy_create_coupon(conn)
                cur.execute("SELECT * FROM COUPON ORDER BY Code")
            rows = cur.fetchall()
    return render_template("coupons.html", rows=rows)

@app.route("/coupons", methods=["POST"])
def coupons_post():
    return add_coupon()

@app.route("/coupons/add", methods=["POST"])
def add_coupon():
    data = _data()
    code = (data.get("code") or "").strip()
    discount = (data.get("discount") or data.get("amount") or "").strip()
    expiry_date = (data.get("expiry_date") or data.get("expires") or "").strip() or None

    if not code or not discount:
        flash("Code and Discount are required", "error")
        return redirect(url_for("coupons"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("INSERT INTO COUPON (Code, Discount, Expiry_Date) VALUES (%s, %s, %s)",
                            (code, discount, expiry_date))
            except Exception as e:
                # If the table was missing, create and retry once
                if isinstance(e, sqlite3.OperationalError) and "no such table" in str(e).lower():
                    _lazy_create_coupon(conn)
                    cur.execute("INSERT INTO COUPON (Code, Discount, Expiry_Date) VALUES (%s, %s, %s)",
                                (code, discount, expiry_date))
                else:
                    raise
        _commit(conn)
    flash("Coupon added", "success")
    return redirect(url_for("coupons"))

if __name__ == "__main__":
    app.run(debug=True)
