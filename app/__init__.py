# app/__init__.py

from flask import Flask
from .views import main  # Make sure the Blueprint is imported from views

def create_app():
    app = Flask(__name__)

    # Register the Blueprint
    app.register_blueprint(main, url_prefix='/')

    return app

