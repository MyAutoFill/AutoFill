"""Main application entry point."""

from flask import Flask
from Config import Config
from database import init_db


def create_app():
    """Create and configure the app."""
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db(app)

    return app

