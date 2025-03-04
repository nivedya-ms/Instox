from flask import Flask
from .views import main  # Import the Blueprint


def create_app():
    app = Flask(__name__)

    # Set the secret key on the app instance
    app.secret_key = 'your_super_secret_key'  # Use a unique and secure key

    # Register the Blueprint
    app.register_blueprint(main, url_prefix='/')

    return app
