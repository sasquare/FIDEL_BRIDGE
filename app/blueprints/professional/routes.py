from flask import render_template
from flask_login import current_user

from app.blueprints.professional import professional_bp
from app.models import roles
from app.utils.decorators import role_required


@professional_bp.route("/dashboard")
@role_required(roles.PROFESSIONAL)
def dashboard():
    return render_template("professional/dashboard.html", user=current_user)
