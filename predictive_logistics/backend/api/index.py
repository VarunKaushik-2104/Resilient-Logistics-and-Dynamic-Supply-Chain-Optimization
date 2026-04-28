from flask import Flask, jsonify, request
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Logistics Optimization API is running!"

@app.route('/predict', methods=['POST'])
def predict():
    # Example endpoint for your supply chain logic
    data = request.get_json()
    # Insert your model prediction logic here
    return jsonify({"status": "success", "message": "Data received"})

# DO NOT use app.run() here. Vercel handles the server.