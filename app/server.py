from flask import Flask, jsonify
import pickle
import numpy as np

app = Flask(__name__)

# Load model
with open('demand_model.pkl', 'rb') as f:
    model = pickle.load(f)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        # Add prediction logic here
        prediction = model.predict([data])[0]
        return jsonify({"status": "success", "prediction": prediction})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

if __name__ == '__main__':
    app.run(port=5000)  # Run on different port if needed