import requests
from datetime import datetime, timedelta

# Server endpoint URL
url = "http://127.0.0.1:5000/predict"

# Base data template (excluding time-based features)
base_data = {
    "sale_price": 200,
    "stock_age_days": 30,
    "price_age_interaction": 6000,  # sale_price * stock_age_days
    "category_Beachwear": 0,
    "category_Casual Wear": 1,  # Will be reset in the loop
    "category_Cultural Souvenirs": 0,
    "category_DIY Craft Kits": 0,
    "category_Dance Costumes": 0,
    "category_Eco-Friendly Textiles": 0,
    "category_Ethnic Footwear": 0,
    "category_Fabrics": 0,
    "category_Festive Wear": 0,
    "category_Formal Wear": 0,
    "category_Handicraft Textiles": 0,
    "category_Home Textiles": 0,
    "category_Industrial Textiles": 0,
    "category_Kids’ Clothing": 0,
    "category_Luxury Textiles": 0,
    "category_Maternity Wear": 0,
    "category_Medical Textiles": 0,
    "category_Nightwear & Loungewear": 0,
    "category_Outdoor Gear Textiles": 0,
    "category_Party Wear": 0,
    "category_Pet Clothing": 0,
    "category_Plus-Size Clothing": 0,
    "category_Rain Accessories": 0,
    "category_Religious Attire": 0,
    "category_School Uniforms": 0,
    "category_Seasonal Textiles": 0,
    "category_Sleep Accessories": 0,
    "category_Specialty Fabrics": 0,
    "category_Sports & Activewear": 0,
    "category_Traditional Wear": 0,
    "category_Travel Textiles": 0,
    "category_Vintage Textiles": 0,
    "category_Wedding Collection": 0,
    "category_Western Wear": 0,
    "category_Winter Wear": 0,
    "category_Workwear": 0,
    "category_Yoga & Meditation Wear": 0
}

# Step 1: Extract all category keys from base_data
category_keys = [key for key in base_data if key.startswith("category_")]

# Step 2: Calculate week_num and month for next week
current_date = datetime.today()
next_week_date = current_date + timedelta(weeks=1)
week_num = next_week_date.isocalendar()[1]  # ISO week number
month = next_week_date.month

# Step 3: Store predictions for each category
predictions = []

# Step 4: Predict demand for each category for next week
for category_key in category_keys:
    # Create forecast data with all category flags set to 0
    forecast_data = {key: 0 if key.startswith("category_") else base_data[key] for key in base_data}
    # Set the current category flag to 1
    forecast_data[category_key] = 1
    # Update time-based features for next week
    forecast_data["week_num"] = week_num
    forecast_data["month"] = month

    # Send POST request to the server
    response = requests.post(url, json=forecast_data)

    # Process the response
    if response.status_code == 200:
        try:
            json_response = response.json()
            if json_response.get("status") == "success":
                prediction = json_response["prediction"]
                # Get category name by removing "category_" prefix
                category_name = category_key.replace("category_", "")
                predictions.append({"category": category_name, "prediction": prediction})
            else:
                print(f"Error for {category_key}: {json_response.get('error')}")
        except requests.exceptions.JSONDecodeError:
            print(f"Failed to decode JSON for {category_key}")
    else:
        print(f"Request failed for {category_key}: Status {response.status_code}")

# Step 5: Sort predictions by predicted demand in descending order
sorted_predictions = sorted(predictions, key=lambda x: x["prediction"], reverse=True)

# Step 6: Display the list of most in-demand items
print("\nMost In-Demand Items for Next Week:")
print("Product Name\t\t\tPredicted Sales")
print("-" * 50)
for item in sorted_predictions:
    # Adjust spacing for better alignment; assumes category names < 25 chars
    print(f"{item['category']:<25}\t{item['prediction']:.2f}")