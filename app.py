# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from threading import Lock

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
                    # Don't block requests if schema init fails; real errors will surface in routes
                    pass

# ---------- Home (Dashboard) ----------
@app.route("/")
def home():
    stats = {}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM RESTAURANT")
            stats["restaurants"] = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM CUSTOMER")
            stats["customers"] = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM FOOD_ITEM")
            stats["food_items"] = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM ORDERS")
            stats["orders"] = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM DELIVERY_AGENT")
            stats["agents"] = cur.fetchone()["c"]

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

@app.route("/restaurants/add", methods=["POST"])
def add_restaurant():
    name = request.form["name"].strip()
    address = request.form["address"].strip()
    phone = request.form["phone"].strip()
    opening_hours = request.form["opening_hours"].strip()

    if not name:
        flash("Name is required", "error")
        return redirect(url_for("restaurants"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO RESTAURANT (Name, Address, Phone, Opening_Hours) VALUES (%s, %s, %s, %s)",
                (name, address, phone, opening_hours),
            )
    flash("Restaurant added", "success")
    return redirect(url_for("restaurants"))

@app.route("/restaurants/delete/<int:restaurant_id>")
def delete_restaurant(restaurant_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM RESTAURANT WHERE Restaurant_ID = %s", (restaurant_id,))
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

@app.route("/customers/add", methods=["POST"])
def add_customer():
    name = request.form["name"].strip()
    email = request.form["email"].strip()
    phone = request.form["phone"].strip()
    address = request.form["address"].strip()

    if not name:
        flash("Name is required", "error")
        return redirect(url_for("customers"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO CUSTOMER (Name, Email, Phone, Address) VALUES (%s, %s, %s, %s)",
                (name, email, phone, address),
            )
    flash("Customer added", "success")
    return redirect(url_for("customers"))

@app.route("/customers/delete/<int:customer_id>")
def delete_customer(customer_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM CUSTOMER WHERE Customer_ID = %s", (customer_id,))
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

@app.route("/food_items/add", methods=["POST"])
def add_food_item():
    name = request.form["name"].strip()
    price = request.form["price"].strip()
    restaurant_id = request.form["restaurant_id"].strip()

    if not name or not price or not restaurant_id:
        flash("Name, Price and Restaurant are required", "error")
        return redirect(url_for("food_items"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO FOOD_ITEM (Name, Price, Restaurant_ID) VALUES (%s, %s, %s)",
                (name, price, restaurant_id),
            )
    flash("Food item added", "success")
    return redirect(url_for("food_items"))

@app.route("/food_items/delete/<int:item_id>")
def delete_food_item(item_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM FOOD_ITEM WHERE Item_ID = %s", (item_id,))
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

@app.route("/orders/add", methods=["POST"])
def add_order():
    customer_id = request.form["customer_id"]
    restaurant_id = request.form["restaurant_id"]
    order_date = datetime.strptime(request.form["order_date"], "%Y-%m-%d")
    total_amount = request.form["total_amount"]
    agent_id = request.form.get("agent_id") or None

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ORDERS (Customer_ID, Restaurant_ID, Order_Date, Total_Amount, Agent_ID)
                VALUES (%s, %s, %s, %s, %s)
            """, (customer_id, restaurant_id, order_date, total_amount, agent_id))
    flash("Order added", "success")
    return redirect(url_for("orders"))

@app.route("/orders/delete/<int:order_id>")
def delete_order(order_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ORDERS WHERE Order_ID = %s", (order_id,))
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
    item_id = request.form["item_id"]
    quantity = request.form["quantity"]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ORDER_DETAIL (Order_ID, Item_ID, Quantity)
                VALUES (%s, %s, %s)
            """, (order_id, item_id, quantity))
    flash("Item added to order", "success")
    return redirect(url_for("order_details", order_id=order_id))

@app.route("/order_details/delete/<int:order_id>/<int:item_id>")
def delete_order_detail(order_id, item_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ORDER_DETAIL WHERE Order_ID = %s AND Item_ID = %s", (order_id, item_id))
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

@app.route("/delivery_agents/add", methods=["POST"])
def add_delivery_agent():
    name = request.form["name"].strip()
    phone = request.form["phone"].strip()
    if not name:
        flash("Name is required", "error")
        return redirect(url_for("delivery_agents"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO DELIVERY_AGENT (Name, Phone) VALUES (%s, %s)", (name, phone))
    flash("Delivery agent added", "success")
    return redirect(url_for("delivery_agents"))

@app.route("/delivery_agents/delete/<int:agent_id>")
def delete_delivery_agent(agent_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM DELIVERY_AGENT WHERE Agent_ID = %s", (agent_id,))
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

@app.route("/deliveries/add", methods=["POST"])
def add_delivery():
    order_id = request.form["order_id"]
    agent_id = request.form["agent_id"]
    delivery_date = datetime.strptime(request.form["delivery_date"], "%Y-%m-%d")
    status = request.form["status"].strip()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO DELIVERY (Order_ID, Agent_ID, Delivery_Date, Status)
                VALUES (%s, %s, %s, %s)
            """, (order_id, agent_id, delivery_date, status))
    flash("Delivery recorded", "success")
    return redirect(url_for("deliveries"))

@app.route("/deliveries/delete/<int:delivery_id>")
def delete_delivery(delivery_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM DELIVERY WHERE Delivery_ID = %s", (delivery_id,))
    flash("Delivery deleted", "success")
    return redirect(url_for("deliveries"))

# ---------- Coupons ----------
@app.route("/coupons")
def coupons():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM COUPON ORDER BY Code")
            rows = cur.fetchall()
    return render_template("coupons.html", rows=rows)

@app.route("/coupons/add", methods=["POST"])
def add_coupon():
    code = request.form["code"].strip()
    discount = request.form["discount"].strip()
    expiry_date = request.form["expiry_date"].strip() or None

    if not code or not discount:
        flash("Code and Discount are required", "error")
        return redirect(url_for("coupons"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO COUPON (Code, Discount, Expiry_Date) VALUES (%s, %s, %s)",
                        (code, discount, expiry_date))
    flash("Coupon added", "success")
    return redirect(url_for("coupons"))

@app.route("/coupons/delete/<int:coupon_id>")
def delete_coupon(coupon_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM COUPON WHERE Coupon_ID = %s", (coupon_id,))
    flash("Coupon deleted", "success")
    return redirect(url_for("coupons"))

# ---- POST shims so forms that submit to the list URLs still work ----
@app.route("/restaurants", methods=["POST"])
def restaurants_post():
    return add_restaurant()

@app.route("/food_items", methods=["POST"])
def food_items_post():
    return add_food_item()

@app.route("/customers", methods=["POST"])
def customers_post():
    return add_customer()

@app.route("/orders", methods=["POST"])
def orders_post():
    return add_order()

@app.route("/deliveries", methods=["POST"])
def deliveries_post():
    return add_delivery()

@app.route("/coupons", methods=["POST"])
def coupons_post():
    return add_coupon()


if __name__ == "__main__":
    app.run(debug=True)
