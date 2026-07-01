"""Flask extension instances, created here to avoid circular imports.

Each extension is initialized against the app inside the application
factory (see app/__init__.py::create_app).
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
