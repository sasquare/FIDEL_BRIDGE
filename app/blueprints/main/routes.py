from flask import jsonify, render_template

from app.blueprints.main import main_bp
from app.extensions import limiter
from app.models.category import Category


@main_bp.route("/")
def index():
    categories = Category.query.order_by(Category.name).limit(12).all()
    return render_template("main/index.html", categories=categories)


@main_bp.route("/healthz")
@limiter.exempt
def healthz():
    """Liveness endpoint for Render's health check and uptime monitors."""
    return jsonify(status="ok"), 200
