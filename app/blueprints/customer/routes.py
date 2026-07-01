from flask import render_template
from flask_login import current_user

from app.blueprints.customer import customer_bp
from app.models import roles
from app.utils.decorators import role_required


@customer_bp.route("/dashboard")
@role_required(roles.CUSTOMER)
def dashboard():
    return render_template("customer/dashboard.html", user=current_user)
