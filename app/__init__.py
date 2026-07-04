"""Application factory for FidelBridge."""
import os
from datetime import datetime

import click
from flask import Flask, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import DEV_SECRET_KEY, config
from app.extensions import db, limiter, login_manager, migrate


def create_app(config_name=None):
    """Build and configure the Flask application instance."""
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    if config_name == "production" and app.config["SECRET_KEY"] == DEV_SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY is not set (or still the development default). "
            "Set a long, random SECRET_KEY environment variable before "
            "running in production."
        )

    if config_name == "production":
        # Render (like most PaaS providers) terminates TLS at its edge and
        # forwards requests to the app over plain HTTP within its network.
        # Without this, Flask would see every request as http://, breaking
        # PREFERRED_URL_SCHEME/secure cookies and any client-IP-based logic
        # (e.g. rate limiting) would see the proxy's IP instead of the
        # visitor's.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

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
    register_security(app)

    from app.utils.assets import asset_url

    app.jinja_env.globals["asset_url"] = asset_url

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
    from app.blueprints.admin import admin_bp
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
    app.register_blueprint(admin_bp)


def register_cli_commands(app):
    @app.cli.command("seed-categories")
    def seed_categories_command():
        """Populate the default service categories (safe to re-run)."""
        from app.seeds import seed_categories

        created = seed_categories()
        print(f"Seeded {created} new categories.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--full-name", prompt="Full name")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin_command(email, full_name, password):
        """Create an admin account. There's no public admin sign-up route."""
        from app.extensions import db
        from app.models import roles
        from app.models.user import User

        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            print(f"A user with email {email} already exists.")
            return

        admin = User(full_name=full_name.strip(), email=email, role=roles.ADMIN)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin account created for {email}.")


def register_security(app):
    @app.after_request
    def set_security_headers(response):
        from flask import request
        from flask_login import current_user

        # Every authenticated page renders per-user state (unread
        # notification/message badges) via a Jinja context processor -
        # there's no client-side refresh for it. Without this header,
        # browsers can restore a fully-rendered previous page from the
        # back/forward cache after the user navigates back, showing a
        # stale badge count without ever asking the server again. Scoped
        # to authenticated, non-static responses so public pages and
        # static assets keep their normal caching.
        if current_user.is_authenticated and not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # 'unsafe-eval' is required by Alpine.js's expression evaluator
        # (x-data/x-show attributes); 'unsafe-inline' on style-src covers
        # the inline width:% styles used for the admin reports bar charts.
        # Everything else (scripts, stylesheets, fonts, images) is
        # self-hosted, so there's no need to allow any other origin.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "frame-ancestors 'none'"
        )
        if app.config.get("PREFERRED_URL_SCHEME") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


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

    @app.errorhandler(413)
    def payload_too_large(error):
        return render_template("errors/413.html"), 413

    @app.errorhandler(429)
    def rate_limited(error):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500
