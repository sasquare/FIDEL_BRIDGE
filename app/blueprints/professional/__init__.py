from flask import Blueprint

professional_bp = Blueprint("professional", __name__, url_prefix="/professional")

from app.blueprints.professional import routes  # noqa: E402,F401
