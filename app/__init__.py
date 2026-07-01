"""Application factory for FidelBridge."""
import os
from datetime import datetime

from flask import Flask, render_template

from app.config import config
from app.extensions import db, login_manager, migrate


def create_app(config_name=None):
    """Build and configure the Flask application instance."""
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "error"

    with app.app_context():
        from app import models  # noqa: F401  (registers models on the metadata)

    register_blueprints(app)
    register_error_handlers(app)
    register_context_processors(app)
    register_cli_commands(app)

    return app


def register_context_processors(app):
    @app.context_processor
    def inject_current_year():
        return {"current_year": datetime.utcnow().year}

    @app.context_processor
    def inject_dashboard_url():
        from app.utils.auth_helpers import dashboard_url_for

        return {"dashboard_url_for": dashboard_url_for}

    @app.context_processor
    def inject_unread_notification_count():
        from flask_login import current_user

        if not current_user.is_authenticated:
            return {"unread_notification_count": 0}

        from app.models.notification import Notification

        count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {"unread_notification_count": count}

    @app.context_processor
    def inject_unread_message_count():
        from flask_login import current_user

        if not current_user.is_authenticated:
            return {"unread_message_count": 0}

        from app.utils.messaging import unread_message_count

        return {"unread_message_count": unread_message_count(current_user)}


def register_blueprints(app):
    from app.blueprints.auth import auth_bp
    from app.blueprints.browse import browse_bp
    from app.blueprints.corporate import corporate_bp
    from app.blueprints.customer import customer_bp
    from app.blueprints.main import main_bp
    from app.blueprints.messages import messages_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.professional import professional_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(browse_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(professional_bp)
    app.register_blueprint(corporate_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(messages_bp)


def register_cli_commands(app):
    @app.cli.command("seed-categories")
    def seed_categories_command():
        """Populate the default service categories (safe to re-run)."""
        from app.seeds import seed_categories

        created = seed_categories()
        print(f"Seeded {created} new categories.")


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return render_template("errors/400.html"), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500
