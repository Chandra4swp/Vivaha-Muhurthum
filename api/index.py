import sys
import os
from flask import Flask, jsonify

# Add the parent directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import the Flask app from app.py
app = None
import_error = None
try:
    from app import app
except Exception as e:
    print(f"Error importing app: {e}")
    import_error = str(e)
    # Create a minimal fallback app if import fails
    app = Flask(__name__)
    
    @app.route('/')
    def error():
        return jsonify({"error": "Import failed", "details": import_error}), 500

# Export for Vercel serverless - Vercel looks for one of these
handler = app
application = app

__all__ = ['app', 'handler', 'application']
