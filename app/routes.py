from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import sqlite3
from flask import session

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

@main.route("/delivery", methods=["GET", "POST"])
def delivery():
    if request.method == "POST":
        delivery_id = request.form.get("delivery_id")
        # Simulate delivery verification
        status = "Verified" if delivery_id == "12345" else "Not Verified"
        return jsonify({"status": status, "id": delivery_id})
    return render_template("delivery.html")

@main.route("/profit-analysis")
def profit_analysis():
    # Simulated profit analysis data
    profit_data = {
        "months": ["January", "February", "March"],
        "sales": [1500, 2000, 2500],
        "profits": [300, 400, 500],
    }
    return render_template("profit_analysis.html", data=profit_data)

@main.route("/contact", methods=["POST"])
def contact():
    data = request.form
    print("Contact Form Data:", data)
    return redirect(url_for("main.home"))

# New Routes
@main.route("/forecast")
def forecast():
    # Placeholder for demand forecasting logic
    return render_template("forecast.html")

@main.route("/recommendations")
def recommendations():
    # Placeholder for product recommendations logic
    return render_template("recommendations.html")

@main.route("/reduction_sales")
def reduction_sales():
    # Placeholder for reduction sales recommendations logic
    return render_template("reduction_sales.html")

@main.route("/turnover")
def turnover():
    # Placeholder for turnover calculation logic
    return render_template("turnover.html")

@main.route("/growth-analytics")
def growth_analytics():
    # Placeholder for business growth analytics logic
    return render_template("growth_analytics.html")


@main.route("/owner_login", methods=["GET", "POST"])
def owner_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        cursor.execute("SELECT * FROM owners WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            return jsonify({"message": "Login successful."}), 200
        else:
            return jsonify({"message": "Invalid email or password."}), 401

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

        return jsonify({"message": "Registration successful."}), 201

    return render_template("owner_register.html")

def send_email_otp(email, otp):
    # Dummy email function (configure properly in production)
    print(f"Sending email to {email} with OTP: {otp}")
    # SMTP setup and email sending can be implemented here.

@main.route("/verify-email", methods=["POST"])
def verify_email():
    email = request.json.get("email")
    otp = request.json.get("otp")
    if email in verification_codes and verification_codes[email]["email_otp"] == otp:
        return jsonify({"message": "Email verified successfully!"}), 200
    return jsonify({"error": "Invalid OTP"}), 400

@main.route("/verify-phone", methods=["POST"])
def verify_phone():
    phone = request.json.get("phone")
    otp = request.json.get("otp")
    for key, value in verification_codes.items():
        if value["phone_otp"] == otp:
            return jsonify({"message": "Phone verified successfully!"}), 200
    return jsonify({"error": "Invalid OTP"}), 400



