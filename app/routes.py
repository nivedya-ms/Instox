from flask import Blueprint, render_template, request, jsonify, redirect, url_for

main = Blueprint("main", __name__)

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
