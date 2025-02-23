from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import sqlite3

main = Blueprint("main", __name__)

# Database connection setup
db = sqlite3.connect('instox.db', check_same_thread=False)
cursor = db.cursor()

# Check database connection and print status
try:
    cursor.execute("SELECT 1")
    print("Database connection successful")
except Exception as e:
    print(f"Database connection failed: {e}")

verification_codes = {}

@main.route("/")
def home():
    return render_template("home.html")

@main.route("/inventory")
def inventory():
    # Simulated inventory data
    inventory_data = [
        {"item": "Product A", "stock": 10},
        {"item": "Product B", "stock": 5},
        {"item": "Product C", "stock": 20},
    ]
    return render_template("inventory.html", inventory=inventory_data)

@main.route("/dashboard")
def dashboard():
    # Check if the user is logged in
    if 'user_id' not in session:
        return redirect(url_for("main.owner_login"))
    return render_template("dashboard.html")

@main.route("/owner_login", methods=["GET", "POST"])
def owner_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        cursor.execute("SELECT * FROM owners WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()

        if user:
            # Set the user_id in the session
            session['user_id'] = user[0]
            # Redirect to the dashboard route
            return render_template("dashboard.html")
        else:
            return render_template("login.html", error="Invalid email or password.")

    return render_template("login.html")

@main.route("/owner_register", methods=["GET", "POST"])
def register_owner():
    if request.method == "POST":
        full_name = request.form.get("fullName")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        business_name = request.form.get("businessName")
        business_type = request.form.get("businessType")
        business_address = request.form.get("businessAddress")
        business_reg_number = request.form.get("businessRegNumber")

        cursor.execute('''INSERT INTO owners (name, email, phone, password, business_name, business_type, business_address, business_reg_number)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (full_name, email, phone, password, business_name, business_type, business_address,
                        business_reg_number))
        db.commit()

        return render_template("login.html"), 201

    return render_template("owner_register.html")