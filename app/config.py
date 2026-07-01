"""Application configuration classes for each environment."""
import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration shared by every environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'fidelbridge.db'}"
    )

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB upload limit

    # Portfolio images are shown on public profiles, so they live under static/.
    PORTFOLIO_UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads" / "portfolio"
    # Verification documents are sensitive (IDs, certificates) and must never
    # be served directly by the static file server. They live under instance/
    # (gitignored, outside static/) and are only reachable via an
    # authenticated, ownership-checked download route.
    VERIFICATION_UPLOAD_FOLDER = BASE_DIR / "instance" / "uploads" / "verifications"

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}
    ALLOWED_DOCUMENT_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    # Route uploads to a throwaway directory so test runs never write into
    # the real instance/ or app/static/ folders used by the dev server.
    _TEST_UPLOAD_ROOT = Path(tempfile.mkdtemp(prefix="fidelbridge-test-uploads-"))
    PORTFOLIO_UPLOAD_FOLDER = _TEST_UPLOAD_ROOT / "portfolio"
    VERIFICATION_UPLOAD_FOLDER = _TEST_UPLOAD_ROOT / "verifications"


class ProductionConfig(Config):
    DEBUG = False
    # SQLALCHEMY_DATABASE_URI is expected to point at PostgreSQL in production
    # via the DATABASE_URL environment variable.


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
