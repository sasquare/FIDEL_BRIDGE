"""Application configuration classes for each environment."""
import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


DEV_SECRET_KEY = "dev-secret-key-change-in-production"


class Config:
    """Base configuration shared by every environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'fidelbridge.db'}"
    )

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB upload limit

    # Session/remember-me cookies: locked down further in ProductionConfig,
    # where the app is always served over HTTPS.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"

    # Cache static assets (compiled CSS, vendored JS, fonts) for a day by
    # default; ProductionConfig extends this since those files rarely change
    # between deploys and aren't cache-busted by filename.
    SEND_FILE_MAX_AGE_DEFAULT = 86400

    # Portfolio images are shown on public profiles, so they live under static/.
    PORTFOLIO_UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "portfolio"
    # Profile photos are also public-facing (profile page, search, Featured
    # Professionals), so they follow the same static/ pattern as portfolio images.
    PROFILE_PHOTO_UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "profile_photos"
    # Verification documents are sensitive (IDs, certificates) and must never
    # be served directly by the static file server. They live under instance/
    # (gitignored, outside static/) and are only reachable via an
    # authenticated, ownership-checked download route.
    VERIFICATION_UPLOAD_FOLDER = BASE_DIR / "instance" / "uploads" / "verifications"

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
    ALLOWED_DOCUMENT_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

    # Optional outbound email (password reset). If MAIL_SERVER isn't set,
    # app/utils/mail.py logs the message instead of sending it, so the
    # reset flow works locally without real SMTP credentials.
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@fidelbridge.com")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False

    # Route uploads to a throwaway directory so test runs never write into
    # the real instance/ or app/static/ folders used by the dev server.
    _TEST_UPLOAD_ROOT = Path(tempfile.mkdtemp(prefix="fidelbridge-test-uploads-"))
    PORTFOLIO_UPLOAD_FOLDER = _TEST_UPLOAD_ROOT / "portfolio"
    VERIFICATION_UPLOAD_FOLDER = _TEST_UPLOAD_ROOT / "verifications"
    PROFILE_PHOTO_UPLOAD_FOLDER = _TEST_UPLOAD_ROOT / "profile_photos"


class ProductionConfig(Config):
    DEBUG = False
    # SQLALCHEMY_DATABASE_URI is expected to point at PostgreSQL in production
    # via the DATABASE_URL environment variable.

    # Render terminates TLS at its edge and always proxies to the app over
    # HTTPS, so these are safe unconditionally in production (see the
    # ProxyFix wiring in app/__init__.py, which makes Flask see the
    # original https:// scheme rather than the proxy's internal http://).
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
