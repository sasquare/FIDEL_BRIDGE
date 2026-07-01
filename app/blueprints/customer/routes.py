from flask import flash, redirect, render_template, url_for
from flask_login import current_user

from app.blueprints.customer import customer_bp
from app.extensions import db
from app.forms.customer import CustomerProfileForm
from app.models import roles
from app.models.category import Category
from app.utils.decorators import role_required


def _sidebar_items():
    return [
        {"key": "dashboard", "label": "Dashboard", "url": url_for("customer.dashboard")},
        {"key": "profile", "label": "My Profile", "url": url_for("customer.profile")},
        {"key": "browse", "label": "Find Professionals", "url": url_for("browse.professionals")},
    ]


@customer_bp.route("/dashboard")
@role_required(roles.CUSTOMER)
def dashboard():
    return render_template(
        "customer/dashboard.html",
        user=current_user,
        active="dashboard",
        sidebar_items=_sidebar_items(),
        categories=Category.query.order_by(Category.name).limit(6).all(),
    )


@customer_bp.route("/profile", methods=["GET", "POST"])
@role_required(roles.CUSTOMER)
def profile():
    profile = current_user.customer_profile
    form = CustomerProfileForm(obj=current_user, city=profile.city, state=profile.state, address=profile.address)

    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None
        profile.address = form.address.data.strip() if form.address.data else None
        profile.city = form.city.data.strip() if form.city.data else None
        profile.state = form.state.data.strip() if form.state.data else None

        db.session.commit()
        flash("Your profile has been updated.", "success")
        return redirect(url_for("customer.profile"))

    return render_template(
        "customer/profile.html",
        form=form,
        active="profile",
        sidebar_items=_sidebar_items(),
    )
