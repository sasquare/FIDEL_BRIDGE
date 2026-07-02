"""Flask extension instances, created here to avoid circular imports.

Each extension is initialized against the app inside the application
factory (see app/__init__.py::create_app).
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    # In-memory storage is fine for a single-instance MVP deployment (see
    # PRODUCTION_CHECKLIST.md) - explicit here just to silence the
    # "no storage specified" warning, not a behavior change.
    storage_uri="memory://",
)
