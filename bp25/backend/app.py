from flask import Flask, jsonify
from flask_cors import CORS  # You'll need to install this

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy"})

# Add more API endpoints here 