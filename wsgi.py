"""
WSGI entry point for gunicorn
"""
# Import the app object from the app.py file
from app import app

# This variable is used by the gunicorn server to serve the Flask app
# This enables gunicorn to find the Flask application
application = app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)