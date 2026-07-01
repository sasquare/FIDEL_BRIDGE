from flask import render_template
from flask_login import current_user

from app.blueprints.corporate import corporate_bp
from app.models import roles
from app.utils.decorators import role_required


@corporate_bp.route("/dashboard")
@role_required(roles.CORPORATE)
def dashboard():
    return render_template("corporate/dashboard.html", user=current_user)
