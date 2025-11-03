# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from db import get_conn

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"  # change in production

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

            cur.execute("""
                SELECT o.Order_ID, o.Order_Date, o.Total_Amount, o.Order_Status,
                       c.Name AS customer, r.Name AS restaurant
                FROM ORDERS o
                LEFT JOIN CUSTOMER c ON o.Customer_ID=c.Customer_ID
                LEFT JOIN RESTAURANT r ON o.Restaurant_ID=r.Restaurant_ID
                ORDER BY o.Order_ID DESC
                LIMIT 5
            """)
            latest_orders = cur.fetchall()
    return render_template("home.html", stats=stats, latest_orders=latest_orders)

# ---------- Restaurants ----------
from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_conn

@app.route("/restaurants", methods=["GET", "POST"])
def restaurants():
    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            location = request.form.get("location", "").strip()
            contact = request.form.get("contact_number", "").strip()
            opening = request.form.get("opening_hours", "").strip()

            if not name:
                flash("Name is required", "danger")
                return redirect(url_for("restaurants"))

            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO RESTAURANT (Name, Location, Contact_Number, Opening_Hours)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (name, location, contact, opening),
                    )
            flash("Restaurant added!", "success")
            return redirect(url_for("restaurants"))

        # GET list
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT Restaurant_ID, Name, Location, Contact_Number, Opening_Hours, Rating
                    FROM RESTAURANT
                    ORDER BY Name
                    """
                )
                rows = cur.fetchall()

        return render_template("restaurants.html", restaurants=rows)

    except Exception as e:
        # show the exact DB/template error on the page
        flash(f"Restaurants page error: {e}", "danger")
        return render_template("restaurants.html", restaurants=[])

# ---------- Customers ----------
@app.route("/customers", methods=["GET", "POST"])
def customers():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip()
        phone = request.form.get("phone","").strip()
        address = request.form.get("address","").strip()
        user_type = request.form.get("user_type","Customer").strip() or "Customer"
        if not name:
            flash("Name is required", "danger")
            return redirect(url_for("customers"))
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO CUSTOMER (Name, Email, Phone_Number, Address, User_Type, Password)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, email, phone, address, user_type, ""))
        flash("Customer added!", "success")
        return redirect(url_for("customers"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Customer_ID, Name, Email, Phone_Number, Address, User_Type
                FROM CUSTOMER ORDER BY Customer_ID DESC
            """)
            rows = cur.fetchall()
    return render_template("customers.html", customers=rows)

# ---------- Food Items ----------
@app.route("/food-items", methods=["GET", "POST"])
def food_items():
    # For dropdown of restaurants
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT Restaurant_ID, Name FROM RESTAURANT ORDER BY Name")
            restaurants = cur.fetchall()

    if request.method == "POST":
        name = request.form.get("name","").strip()
        desc = request.form.get("description","").strip()
        price = request.form.get("price","0").strip()
        category = request.form.get("category","").strip()
        availability = request.form.get("availability","Y").strip() or "Y"
        rest_id = request.form.get("restaurant_id")
        if not name:
            flash("Food name is required", "danger")
        else:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO FOOD_ITEM (Name, Description, Price, Category, Availability, Restaurant_ID)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (name, desc, price, category, availability, rest_id if rest_id else None))
            flash("Food item added!", "success")
        return redirect(url_for("food_items"))

    # GET list
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.Food_ID, f.Name, f.Category, f.Price, f.Availability,
                       r.Name AS Restaurant
                FROM FOOD_ITEM f
                LEFT JOIN RESTAURANT r ON f.Restaurant_ID = r.Restaurant_ID
                ORDER BY f.Food_ID DESC
            """)
            items = cur.fetchall()
    return render_template("food_items.html", items=items, restaurants=restaurants)

# ---------- Orders (create + list) ----------
@app.route("/orders", methods=["GET", "POST"])
def orders():
    # dropdowns
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT Customer_ID, Name FROM CUSTOMER ORDER BY Name")
            customers = cur.fetchall()
            cur.execute("SELECT Restaurant_ID, Name FROM RESTAURANT ORDER BY Name")
            restaurants = cur.fetchall()

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        restaurant_id = request.form.get("restaurant_id")
        payment_method = request.form.get("payment_method","Cash")
        order_date = datetime.now().date()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ORDERS (Customer_ID, Restaurant_ID, Payment_Method, Order_Date, Total_Amount, Order_Status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (customer_id or None, restaurant_id or None, payment_method, order_date, 0, "Pending"))
                order_id = cur.lastrowid
        flash(f"Order #{order_id} created. Add items next.", "success")
        return redirect(url_for("order_details", order_id=order_id))

    # list orders
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.Order_ID, o.Order_Date, o.Total_Amount, o.Order_Status,
                       c.Name AS customer, r.Name AS restaurant
                FROM ORDERS o
                LEFT JOIN CUSTOMER c ON o.Customer_ID=c.Customer_ID
                LEFT JOIN RESTAURANT r ON o.Restaurant_ID=r.Restaurant_ID
                ORDER BY o.Order_ID DESC
            """)
            orders = cur.fetchall()
    return render_template("orders.html", orders=orders, customers=customers, restaurants=restaurants)

# ---------- Order Details (add items to an order) ----------
@app.route("/orders/<int:order_id>/details", methods=["GET", "POST"])
def order_details(order_id):
    # Find the order and its restaurant to filter food list
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.Order_ID, o.Restaurant_ID, o.Order_Status, r.Name AS restaurant
                FROM ORDERS o
                LEFT JOIN RESTAURANT r ON o.Restaurant_ID=r.Restaurant_ID
                WHERE o.Order_ID=%s
            """, (order_id,))
            order = cur.fetchone()
            if not order:
                flash("Order not found", "danger")
                return redirect(url_for("orders"))

            cur.execute("""
                SELECT Food_ID, Name, Price
                FROM FOOD_ITEM
                WHERE Restaurant_ID=%s OR %s IS NULL
                ORDER BY Name
            """, (order["Restaurant_ID"], order["Restaurant_ID"]))
            food = cur.fetchall()

            if request.method == "POST":
                food_id = request.form.get("food_id")
                qty = int(request.form.get("quantity","1"))
                # Get current price of the food item
                cur.execute("SELECT Price FROM FOOD_ITEM WHERE Food_ID=%s", (food_id,))
                frow = cur.fetchone()
                if not frow:
                    flash("Food item not found", "danger")
                else:
                    price = frow["Price"]
                    cur.execute("""
                        INSERT INTO ORDER_DETAIL (Order_ID, Food_ID, Quantity, Price)
                        VALUES (%s, %s, %s, %s)
                    """, (order_id, food_id, qty, price))
                    # Recompute total
                    cur.execute("""
                        SELECT SUM(Quantity * Price) AS total FROM ORDER_DETAIL WHERE Order_ID=%s
                    """, (order_id,))
                    total = cur.fetchone()["total"] or 0
                    cur.execute("UPDATE ORDERS SET Total_Amount=%s WHERE Order_ID=%s", (total, order_id))
                    flash("Item added", "success")
                return redirect(url_for("order_details", order_id=order_id))

            # fetch details for display
            cur.execute("""
                SELECT od.Order_Detail_ID, od.Quantity, od.Price,
                       f.Name AS item
                FROM ORDER_DETAIL od
                LEFT JOIN FOOD_ITEM f ON od.Food_ID=f.Food_ID
                WHERE od.Order_ID=%s
                ORDER BY od.Order_Detail_ID DESC
            """, (order_id,))
            details = cur.fetchall()

            cur.execute("SELECT Total_Amount FROM ORDERS WHERE Order_ID=%s", (order_id,))
            total = cur.fetchone()["Total_Amount"] or 0

    return render_template("order_details.html",
                           order=order, food=food, details=details, total=total)

# ---------- Coupons ----------
@app.route("/coupons", methods=["GET", "POST"])
def coupons():
    # restaurants for dropdown
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT Restaurant_ID, Name FROM RESTAURANT ORDER BY Name")
            restaurants = cur.fetchall()

    if request.method == "POST":
        code = request.form.get("code","").strip()
        discount = request.form.get("discount","0").strip()
        valid_until = request.form.get("valid_until","").strip() or None
        rest_id = request.form.get("restaurant_id") or None
        if not code:
            flash("Code is required", "danger")
        else:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO COUPON (Code, Discount_Percentage, Valid_Until, Restaurant_ID)
                        VALUES (%s, %s, %s, %s)
                    """, (code, discount, valid_until, rest_id))
            flash("Coupon added", "success")
        return redirect(url_for("coupons"))

    # list coupons (validity indicator)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.Coupon_ID, c.Code, c.Discount_Percentage, c.Valid_Until,
                       r.Name AS Restaurant
                FROM COUPON c
                LEFT JOIN RESTAURANT r ON c.Restaurant_ID=r.Restaurant_ID
                ORDER BY c.Coupon_ID DESC
            """)
            rows = cur.fetchall()
    return render_template("coupons.html", coupons=rows, restaurants=restaurants)

# ---------- Delivery Agents ----------
@app.route("/delivery-agents", methods=["GET", "POST"])
def delivery_agents():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        phone = request.form.get("phone","").strip()
        vehicle = request.form.get("vehicle","").strip()
        avail = request.form.get("availability","Y").strip() or "Y"
        if not name:
            flash("Name is required", "danger")
            return redirect(url_for("delivery_agents"))
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO DELIVERY_AGENT (Name, Phone_Number, Vehicle_Number, Availability_Status)
                    VALUES (%s, %s, %s, %s)
                """, (name, phone, vehicle, avail))
        flash("Delivery agent added!", "success")
        return redirect(url_for("delivery_agents"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Agent_ID, Name, Phone_Number, Vehicle_Number, Availability_Status
                FROM DELIVERY_AGENT ORDER BY Agent_ID DESC
            """)
            rows = cur.fetchall()
    return render_template("delivery_agents.html", agents=rows)

# ---------- Delivery assignment (optional minimal) ----------
@app.route("/deliveries", methods=["GET", "POST"])
def deliveries():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # dropdowns
            cur.execute("""
                SELECT o.Order_ID, CONCAT('#', o.Order_ID, ' - ', IFNULL(o.Order_Status,'')) AS label
                FROM ORDERS o
                ORDER BY o.Order_ID DESC
            """)
            orders = cur.fetchall()
            cur.execute("""
                SELECT Agent_ID, CONCAT(Name, ' (', Availability_Status, ')') AS label
                FROM DELIVERY_AGENT ORDER BY Name
            """)
            agents = cur.fetchall()

    if request.method == "POST":
        order_id = request.form.get("order_id")
        agent_id = request.form.get("agent_id")
        pickup_time = datetime.now()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO DELIVERY (Order_ID, Agent_ID, Pickup_Time, Delivery_Status)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, agent_id, pickup_time, "Picked Up"))
                cur.execute("UPDATE ORDERS SET Order_Status=%s WHERE Order_ID=%s",
                            ("Out for Delivery", order_id))
        flash("Delivery created and order marked 'Out for Delivery'", "success")
        return redirect(url_for("deliveries"))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.Delivery_ID, d.Pickup_Time, d.Delivery_Time, d.Delivery_Status,
                       o.Order_ID, a.Name AS agent
                FROM DELIVERY d
                LEFT JOIN ORDERS o ON d.Order_ID=o.Order_ID
                LEFT JOIN DELIVERY_AGENT a ON d.Agent_ID=a.Agent_ID
                ORDER BY d.Delivery_ID DESC
            """)
            rows = cur.fetchall()
    return render_template("deliveries.html", deliveries=rows, orders=orders, agents=agents)

# app.py (add anywhere once)
@app.route("/health/db")
def health_db():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES;")
                tables = [t for t in cur.fetchall()]
        return {"ok": True, "tables": tables}
    except Exception as e:
        return {"ok": False, "error": str(e)}, 500


if __name__ == "__main__":
    app.run(debug=True)
