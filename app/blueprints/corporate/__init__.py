from flask import Blueprint

corporate_bp = Blueprint("corporate", __name__, url_prefix="/corporate")

from app.blueprints.corporate import routes  # noqa: E402,F401
