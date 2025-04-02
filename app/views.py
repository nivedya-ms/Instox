import secrets
import requests
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import joblib
import google.generativeai as genai  # Import Google Generative AI
from flask import flash
from werkzeug.utils import secure_filename
import os
import fitz



main = Blueprint("main", __name__)

# Set the secret key for session management
main.secret_key = secrets.token_hex(32)
# Database connection setup
db = sqlite3.connect('instox.db', check_same_thread=False)
cursor = db.cursor()

# Check database connection and print status
try:
    cursor.execute("SELECT 1")
    print("Database connection successful")
except Exception as e:
    print(f"Database connection failed: {e}")

# Set your OpenAI API key
genai.configure(api_key="AIzaSyB3LOuTzD_6VdUF0q0jj63wWTHIX0xNUZI")  # Replace with your actual API key

verification_codes = {}


# Load the trained model
model = joblib.load('demand_model.pkl')

# Define feature names (must match what was used in training)
features = ['week_num', 'month', 'sale_price', 'stock_age_days', 'price_age_interaction',
            'category_Beachwear', 'category_Casual Wear', 'category_Cultural Souvenirs',
            'category_DIY Craft Kits', 'category_Dance Costumes', 'category_Eco-Friendly Textiles',
            'category_Ethnic Footwear', 'category_Fabrics', 'category_Festive Wear', 'category_Formal Wear',
            'category_Handicraft Textiles', 'category_Home Textiles', 'category_Industrial Textiles',
            'category_Kids’ Clothing', 'category_Luxury Textiles', 'category_Maternity Wear',
            'category_Medical Textiles', 'category_Nightwear & Loungewear', 'category_Outdoor Gear Textiles',
            'category_Party Wear', 'category_Pet Clothing', 'category_Plus-Size Clothing',
            'category_Rain Accessories', 'category_Religious Attire', 'category_School Uniforms',
            'category_Seasonal Textiles', 'category_Sleep Accessories', 'category_Specialty Fabrics',
            'category_Sports & Activewear', 'category_Traditional Wear', 'category_Travel Textiles',
            'category_Vintage Textiles', 'category_Wedding Collection', 'category_Western Wear',
            'category_Winter Wear', 'category_Workwear', 'category_Yoga & Meditation Wear']



@main.route("/")
def home():
    return render_template("home.html")


@main.route("/inventory")
def inventory():
    if 'user_id' in session:
        user_id = session['user_id']

        try:
            print("Session Content:", session)
            cursor.execute("SELECT uid, name, stock_level, price FROM inventory WHERE uid = ?", (user_id,))
            inventory_items = cursor.fetchall()

            # Convert rows to dictionary-like objects
            inventory_items = [
                {"id": item[0], "name": item[1], "stock_level": item[2], "price": item[3]}
                for item in inventory_items
            ]

            print(f"Inventory Items for User {user_id}: {inventory_items}")
            return render_template("inventory.html", inventory_items=inventory_items)

        except Exception as e:
            print(f"Database query failed: {e}")
            return "Failed to load inventory items"

    else:
        print("User not logged in")
        return "Unauthorized Access"


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


@main.route('/predict', methods=['POST'])
def predict():
    # Get data from request
    input_data = request.get_json()

    # Validate input
    if not input_data:
        return jsonify({"error": "No input data provided"}), 400

    # Check for missing features
    missing_features = [feature for feature in features if feature not in input_data]
    if missing_features:
        return jsonify({"error": f"Missing required features: {missing_features}"}), 400

    try:
        # Prepare input in correct order
        ordered_input = [input_data[feature] for feature in features]

        # Make prediction
        prediction = model.predict([ordered_input])

        # Return prediction
        return jsonify({
            "prediction": prediction[0],
            "status": "success"
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "message": "Failed to make prediction"
        }), 500


@main.route("/forecast", methods=['GET', 'POST'])
def forecast():
    # Fetch all products for the dropdown
    products = Product.query.all()

    if request.method == 'POST':
        # Get the selected product ID from the form
        product_id = request.form.get('product')
        if not product_id or product_id == "Choose a product...":
            return render_template('forecast.html', products=products, error="Please select a product")

        try:
            # Convert product_id to integer and fetch the product
            product = Product.query.get(int(product_id))
            if not product:
                return render_template('forecast.html', products=products, error="Invalid product selected")

            # Get the product's category
            category = product.category

            # Initialize total forecast demand
            forecast_demand = 0
            current_date = datetime.today()

            # Generate predictions for the next 4 weeks
            for i in range(4):
                future_date = current_date + timedelta(weeks=i)
                week_num = future_date.isocalendar()[1]
                month = future_date.month

                # Prepare input data for the model
                input_data = {feat: 0 for feat in features}
                input_data['week_num'] = week_num
                input_data['month'] = month
                input_data['sale_price'] = 100  # Placeholder; adjust as needed
                input_data['stock_age_days'] = 14  # Placeholder
                input_data['price_age_interaction'] = 100 * 14  # Derived feature

                # Set the category feature (e.g., 'category_Casual Wear')
                category_feature = f'category_{category}'
                if category_feature not in features:
                    return render_template('forecast.html', products=products, error=f"Category '{category}' not recognized")
                input_data[category_feature] = 1

                # Order the input data according to the model's feature list
                ordered_input = [input_data[feat] for feat in features]

                # Make prediction and add to total
                prediction = model.predict([ordered_input])[0]
                forecast_demand += prediction

            # Render the template with the forecast result
            return render_template('forecast.html', products=products, forecast_demand=forecast_demand)

        except Exception as e:
            return render_template('forecast.html', products=products, error=f"An error occurred: {str(e)}")

    # For GET requests, just render the form
    return render_template('forecast.html', products=products)


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


@main.route("/growth_analytics")
def growth_analytics():
    # Placeholder for business growth analytics logic
    return render_template("growth_analytics.html")


# Configure Google Generative AI


# Function to set up the Gemini model
def setup_model():
    """
    Configure and return the Gemini generative model with appropriate settings.
    """
    model = genai.GenerativeModel(
        model_name="models/gemini-1.5-flash",
        generation_config={
            "temperature": 0.7,
            "max_output_tokens": 500,
        }
    )
    return model


# Chatbot route using Gemini
@main.route("/chatbot", methods=["POST"])
def chatbot():
    user_message = request.json.get("message")

    conversation = []

    SYSTEM_PROMPT = '''
You are **Instox Assistant**, an AI-powered chatbot for the **Smart Retail Management System**. Your goal is to assist users with inventory management, sales analytics, demand forecasting, and business growth optimization. Your responses should be **clear, concise, and actionable**.

### **Chatbot Guidelines:**

1. **Greet the User:**
   Start with a **friendly and professional** greeting.
   _Example:_ "Hello! Welcome to Instox. How can I assist you today?"

2. **Understand the Query:**
   Ask clarifying questions if the user's query is unclear.
   _Example:_ "Could you provide more details about your inventory issue?"

3. **Inventory Management:**
   - Provide guidance on tracking stock levels, reordering products, and optimizing inventory.
   - Suggest tools like the **Inventory Management** dashboard.
   _Example:_ "You can track your inventory levels in real-time using the Inventory Management section. Would you like to learn more?"

4. **Sales Analytics:**
   - Help users analyze sales trends, profit margins, and turnover rates.
   - Suggest tools like the **Profit Analysis** and **Turnover Calculation** features.
   _Example:_ "You can analyze your sales trends and profit margins using the Profit Analysis tool. Would you like to explore it?"

5. **Demand Forecasting:**
   - Assist with predicting future product demand based on historical data.
   - Suggest tools like the **Demand Forecasting** feature.
   _Example:_ "You can predict future demand using the Demand Forecasting tool. Would you like to generate a forecast?"

6. **Business Growth Analytics:**
   - Provide insights into business growth and profitability.
   - Suggest tools like the **Growth Analytics** dashboard.
   _Example:_ "You can track your business growth and profitability using the Growth Analytics tool. Would you like to see your performance metrics?"

7. **Reduction Sales Recommendations:**
   - Offer strategies for clearing old or slow-moving stock.
   - Suggest tools like the **Reduction Sales** feature.
   _Example:_ "You can get recommendations for clearing old stock using the Reduction Sales tool. Would you like to explore it?"

8. **Troubleshooting:**
   - If the user encounters issues with the platform, guide them through troubleshooting steps.
   _Example:_ "It seems like you're having trouble accessing the dashboard. Have you tried clearing your browser cache?"

9. **Escalation (If Unresolved):**
   - If the issue cannot be resolved, recommend contacting support or visiting the help section.
   _Example:_ "If the issue persists, please contact our support team for further assistance."

10. **Polite Closing:**
   - End on a positive note.
   _Example:_ "Thank you for using Instox! Let me know if you need further assistance."

11. **Handle Unexpected Input:**
   - If the user's input is unclear, ask clarifying questions without looping.
   _Example:_ "I'm not sure I understand. Could you provide more details?"

12. **Log Queries:**
   - Ensure all user queries are logged for future analysis and system improvement.

### **Rules:**
- Responses should be **short and clear**.
- Focus on **retail management and inventory control**.
- Avoid discussing unrelated topics.
- Always maintain a **professional and helpful tone**.
'''

    try:
        # Add user message to conversation history
        conversation.append({"role": "user", "content": user_message})

        # Combine conversation history into a single context string
        context = SYSTEM_PROMPT + "\nPrevious Conversations:\n" + "\n".join([msg["content"] for msg in conversation[-6:]]) + "\n\nCurrent Query:\n" + user_message

        # Generate response using Gemini model
        model = setup_model()
        response = model.generate_content(context)
        chatbot_reply = response.text

        # Add chatbot response to conversation history
        conversation.append({"role": "assistant", "content": chatbot_reply})
        session.modified = True

        return jsonify({"reply": chatbot_reply})

    except Exception as e:
        print(f"Error in chatbot route: {str(e)}")
        return jsonify({"error": "An error occurred while processing your request. Please try again."}), 500

# Other routes remain unchanged
@main.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@main.route("/owner_login", methods=["GET", "POST"])
def owner_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        cursor.execute("SELECT * FROM owners WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            return render_template("dashboard.html"), 200
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


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Extract text from PDF
        pdf_text = extract_text_from_pdf(filepath)

        # Use Gemini Model for AI-based table extraction
        model = setup_model()
        ai_response = model.generate_content(f"Extract tabular data from the following text:\n\n{pdf_text}")
        table_data = ai_response.text

        # Process extracted data into JSON format
        extracted_data = process_table_data(table_data)

        return jsonify({"data": extracted_data})

    return jsonify({"error": "Invalid file type"}), 400


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF using PyMuPDF.
    """
    text = ""
    pdf = fitz.open(pdf_path)
    for page in pdf:
        text += page.get_text()
    return text


def process_table_data(response_text):
    """
    Convert Gemini model text response to structured JSON table data.
    """
    table_data = []
    lines = response_text.split("\n")
    for line in lines:
        parts = line.split(",")
        if len(parts) == 4:
            table_data.append({
                "Product Name": parts[0].strip(),
                "Product Quantity": parts[1].strip(),
                "Quantifier": parts[2].strip(),
                "Price": parts[3].strip()
            })
    return table_data

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
def turnover_feature():
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
    try:
        if session:
            print(f"Session Content: {session}")  # Printing session content
            print("Session data accessed successfully")
        else:
            print("Session is empty")
    except Exception as e:
        print(f"Failed to access session data: {e}")
    # Insert into the database
    cursor.execute("INSERT INTO inventory (uid,name, stock_level, price) VALUES (?, ?, ?, ?)",
                   (session['user_id'],product_name, stock_level, price))
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
    db.row_factory = sqlite3.Row  # Enable row access by column name

    try:
        cursor = db.cursor()  # Create a new cursor for each request

        if request.method == "POST":
            product_name = request.form.get("product_name")
            stock_level = request.form.get("stock_level")
            price = request.form.get("price")

            try:
                # Update the selected item based on its ID and user_id
                cursor.execute("UPDATE inventory SET name = ?, stock_level = ?, price = ? WHERE id = ? AND uid = ?",
                               (product_name, stock_level, price, id, session['user_id']))
                db.commit()
                flash("Item updated successfully!", "success")
                return redirect(url_for("main.inventory"))
            except Exception as e:
                print("Failed to update item:", e)
                flash("Failed to update item!", "danger")

        # Fetch the specific item by its ID and user_id
        cursor.execute("SELECT * FROM inventory WHERE id = ? AND uid = ?", (id, session['user_id']))
        item = cursor.fetchone()

        if not item:
            flash("Item not found!", "danger")
            return redirect(url_for("main.inventory"))

        print("Item fetched:", dict(item))

    except Exception as e:
        print("Database query failed:", e)
        flash("Failed to load item!", "danger")
        return redirect(url_for("main.inventory"))
    finally:
        cursor.close()  # Close the cursor to prevent memory leaks

    return render_template("edit_inventory.html", item=item)
