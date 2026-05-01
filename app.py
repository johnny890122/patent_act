import os
from flask import Flask, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configure MongoDB using the MONGO_URI environment variable
# Provide a fallback for local development
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
client = MongoClient(MONGO_URI)

@app.route('/')
def index():
    return jsonify({"message": "Hello from Flask & MongoDB on Heroku!"})

@app.route('/ping_db')
def ping_db():
    try:
        # A simple command to verify the database connection
        client.admin.command('ping')
        return jsonify({"status": "Database connection successful!"})
    except Exception as e:
        return jsonify({"status": "Database connection failed", "error": str(e)}), 500

if __name__ == '__main__':
    # Heroku dynamically assigns a port via the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
