from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import sqlite3
from flask import flash


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
@main.route('/logout')
def logout():
    session.clear()  # Clear session
    flash("You have successfully logged out.", "success")  # Flash Message
    return redirect(url_for('main.owner_login'))  # Redirect to Login Pa

# Stock Management Route
@main.route('/features/inventory')
def inventory_feature():
    return render_template('Inventoryhome.html')

# Demand Forecasting Route
@main.route('/features/forecast')
def forecast_feature():
    return render_template('demandforecasthome.html')

# Product Recommendations Route
@main.route('/features/recommendations')
def recommendations_feature():
    return render_template('productrecommendhome.html')

# Reduction Sales Route
@main.route('/features/reduction_sales')
def reduction_sales_feature():
    return render_template('reductionsaleshome.html')

# Turnover Calculation Route
@main.route('/features/turnover')
def turnover():
    return render_template('turnoverhome.html')

# Business Growth Analytics Route
@main.route('/features/growth_analytics')
def growth_analytics_feature():
    return render_template('growthanalyticshome.html')

@main.route("/add_inventory", methods=["POST"])
def add_inventory():
    product_name = request.form.get("product_name")
    stock_level = request.form.get("stock_level")
    price = request.form.get("price")

    # Insert into the database
    cursor.execute("INSERT INTO inventory (name, stock_level, price) VALUES (?, ?, ?)",
                   (product_name, stock_level, price))
    db.commit()

    flash("Item added successfully!", "success")
    return redirect(url_for("main.inventory"))
@main.route("/delete_inventory/<int:id>", methods=["GET"])
def delete_inventory(id):
    # Delete the item from the database
    cursor.execute("DELETE FROM inventory WHERE id = ?", (id,))
    db.commit()

    flash("Item deleted successfully!", "success")
    return redirect(url_for("main.inventory"))

@main.route("/edit_inventory/<int:id>", methods=["GET", "POST"])
def edit_inventory(id):
    if request.method == "POST":
        product_name = request.form.get("product_name")
        stock_level = request.form.get("stock_level")
        price = request.form.get("price")

        # Update the item in the database
        cursor.execute("UPDATE inventory SET name = ?, stock_level = ?, price = ? WHERE id = ?",
                       (product_name, stock_level, price, id))
        db.commit()

        flash("Item updated successfully!", "success")
        return redirect(url_for("main.inventory"))

    # Fetch the item to edit
    cursor.execute("SELECT * FROM inventory WHERE id = ?", (id,))
    item = cursor.fetchone()

    return render_template("edit_inventory.html", item=item)
@main.route("/upload_growth_data", methods=["POST"])
def upload_growth_data():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file = request.files['file']
    analysis_type = request.form.get("analysis_type")

    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    if file and file.filename.endswith('.pdf'):
        # Save the file (for demonstration purposes)
        filename = secure_filename(file.filename)
        filepath = os.path.join("uploads", filename)
        file.save(filepath)

        # Process the file and generate analysis (dummy response for now)
        return jsonify({
            "success": True,
            "message": "File uploaded and analyzed successfully!",
            "analysis_type": analysis_type
        })
    else:
        return jsonify({"success": False, "error": "Invalid file type"}), 400