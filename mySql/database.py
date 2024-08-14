"""Database connection and setup."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Initialize the mySql."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
