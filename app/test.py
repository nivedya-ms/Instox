from flask import Flask, Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
import joblib
from dateutil.relativedelta import relativedelta

# Initialize Flask app and blueprint
app = Flask(__name__)
main = Blueprint('main', __name__)

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

# Route to serve the HTML page
@main.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Prediction route (original)
@main.route('/predict', methods=['POST'])
def predict():
    input_data = request.get_json()
    if not input_data:
        return jsonify({"error": "No input data provided"}), 400

    missing_features = [feature for feature in features if feature not in input_data]
    if missing_features:
        return jsonify({"error": f"Missing required features: {missing_features}"}), 400

    try:
        ordered_input = [input_data[feature] for feature in features]
        prediction = model.predict([ordered_input])
        return jsonify({"prediction": float(prediction[0]), "status": "success"})
    except Exception as e:
        return jsonify({"error": str(e), "message": "Failed to make prediction"}), 500

@main.route('/forecast', methods=['POST'])
def forecast():
    input_data = request.get_json()
    if not input_data:
        return jsonify({"error": "No input data provided"}), 400

    required_fields = ['category', 'sale_price', 'stock_age_days', 'period']
    missing_fields = [field for field in required_fields if field not in input_data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400

    try:
        # Extract input data
        category = input_data['category']
        sale_price = float(input_data['sale_price'])
        stock_age_days = int(input_data['stock_age_days'])
        period = input_data['period']
        sub_period = input_data.get('sub_period')

        # Validate numerical inputs
        if sale_price <= 0 or stock_age_days < 0:
            return jsonify({"error": "Sale price must be positive and stock age non-negative"}), 400

        # Validate period-specific requirements
        if period in ['month', 'year']:
            if not sub_period:
                return jsonify({"error": f"sub_period required for {period} period"}), 400
            if period == 'month' and sub_period not in ['day', 'week']:
                return jsonify({"error": "Invalid sub_period for month. Use 'day' or 'week'"}), 400
            if period == 'year' and sub_period not in ['day', 'week', 'month']:
                return jsonify({"error": "Invalid sub_period for year. Use 'day', 'week' or 'month'"}), 400

        current_date = datetime.now()
        predictions = []

        def calculate_prediction(target_date):
            """Helper function to generate prediction for a specific date"""
            week_num = target_date.isocalendar()[1]
            month = target_date.month
            price_age_interaction = sale_price * stock_age_days

            model_input = {
                'week_num': week_num,
                'month': month,
                'sale_price': sale_price,
                'stock_age_days': stock_age_days,
                'price_age_interaction': price_age_interaction
            }

            # Handle category encoding
            for feature in features:
                if feature.startswith('category_'):
                    model_input[feature] = 1 if feature == f'category_{category}' else 0
                elif feature not in model_input:
                    model_input[feature] = 0

            ordered_input = [model_input[feature] for feature in features]
            return float(model.predict([ordered_input])[0])

        # Generate predictions based on period
        if period == 'day':
            # Hourly predictions for next day
            start_date = (current_date + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            for hour in range(24):
                segment_date = start_date + timedelta(hours=hour)
                predictions.append({
                    "label": segment_date.strftime("%H:%M"),
                    "value": calculate_prediction(segment_date)
                })

        elif period == 'week':
            # Daily predictions for next week
            for day in range(7):
                segment_date = current_date + timedelta(days=day + 1)
                predictions.append({
                    "label": segment_date.strftime("%A"),
                    "value": calculate_prediction(segment_date)
                })

        elif period == 'month':
            start_date = current_date + timedelta(days=1)
            if sub_period == 'day':
                # Daily predictions for next month
                end_date = start_date + relativedelta(months=1)
                delta = (end_date - start_date).days
                for day in range(delta):
                    segment_date = start_date + timedelta(days=day)
                    predictions.append({
                        "label": segment_date.strftime("%Y-%m-%d"),
                        "value": calculate_prediction(segment_date)
                    })
            elif sub_period == 'week':
                # Weekly predictions for next month
                for week in range(4):
                    segment_date = start_date + timedelta(weeks=week)
                    predictions.append({
                        "label": f"Week {week + 1}",
                        "value": calculate_prediction(segment_date)
                    })

        elif period == 'year':
            start_date = current_date + timedelta(days=1)
            if sub_period == 'day':
                # Daily predictions for next year
                end_date = start_date + relativedelta(years=1)
                delta = (end_date - start_date).days
                for day in range(delta):
                    segment_date = start_date + timedelta(days=day)
                    predictions.append({
                        "label": segment_date.strftime("%Y-%m-%d"),
                        "value": calculate_prediction(segment_date)
                    })
            elif sub_period == 'week':
                # Weekly predictions for next year
                for week in range(52):
                    segment_date = start_date + timedelta(weeks=week)
                    predictions.append({
                        "label": f"Week {week + 1}",
                        "value": calculate_prediction(segment_date)
                    })
            elif sub_period == 'month':
                # Monthly predictions for next year
                for month in range(12):
                    segment_date = start_date + relativedelta(months=month)
                    predictions.append({
                        "label": segment_date.strftime("%B"),
                        "value": calculate_prediction(segment_date)
                    })

        else:
            return jsonify({"error": "Invalid period specified"}), 400

        return jsonify({
            "status": "success",
            "period": period,
            "sub_period": sub_period,
            "predictions": predictions
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "message": "Failed to generate forecast"
        }), 500
# Register blueprint
app.register_blueprint(main)

if __name__ == '__main__':
    app.run(debug=True)