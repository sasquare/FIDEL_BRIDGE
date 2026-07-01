from flask import render_template

from app.blueprints.main import main_bp
from app.models.category import Category


@main_bp.route("/")
def index():
    categories = Category.query.order_by(Category.name).limit(12).all()
    return render_template("main/index.html", categories=categories)
