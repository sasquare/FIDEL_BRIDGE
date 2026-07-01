"""Application factory for FidelBridge."""
import os
from datetime import datetime

from flask import Flask, render_template

from app.config import config
from app.extensions import db, migrate


def create_app(config_name=None):
    """Build and configure the Flask application instance."""
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    register_blueprints(app)
    register_error_handlers(app)
    register_context_processors(app)

    return app


def register_context_processors(app):
    @app.context_processor
    def inject_current_year():
        return {"current_year": datetime.utcnow().year}


def register_blueprints(app):
    from app.blueprints.main import main_bp

    app.register_blueprint(main_bp)


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500
