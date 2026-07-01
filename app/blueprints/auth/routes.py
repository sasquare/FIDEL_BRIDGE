from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.blueprints.auth import auth_bp
from app.extensions import db
from app.forms.auth import (
    CorporateRegistrationForm,
    CustomerRegistrationForm,
    LoginForm,
    ProfessionalRegistrationForm,
)
from app.models import roles
from app.models.corporate import CorporateProfile
from app.models.customer import CustomerProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User
from app.utils.auth_helpers import dashboard_url_for


def _is_safe_redirect_target(target):
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme and target.startswith("/")


@auth_bp.route("/register")
def register_choice():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))
    return render_template("auth/register_choice.html")


@auth_bp.route("/register/customer", methods=["GET", "POST"])
def register_customer():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))

    form = CustomerRegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=roles.CUSTOMER,
        )
        user.set_password(form.password.data)
        user.customer_profile = CustomerProfile(city=form.city.data.strip() if form.city.data else None)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Welcome to FidelBridge! Your customer account has been created.", "success")
        return redirect(dashboard_url_for(user))

    return render_template("auth/register_customer.html", form=form)


@auth_bp.route("/register/professional", methods=["GET", "POST"])
def register_professional():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))

    form = ProfessionalRegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=roles.PROFESSIONAL,
        )
        user.set_password(form.password.data)
        user.professional_profile = ProfessionalProfile(
            profession=form.profession.data.strip(),
            city=form.city.data.strip() if form.city.data else None,
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Welcome to FidelBridge! Your professional account has been created.", "success")
        return redirect(dashboard_url_for(user))

    return render_template("auth/register_professional.html", form=form)


@auth_bp.route("/register/corporate", methods=["GET", "POST"])
def register_corporate():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))

    form = CorporateRegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=roles.CORPORATE,
        )
        user.set_password(form.password.data)
        user.corporate_profile = CorporateProfile(
            company_name=form.company_name.data.strip(),
            rc_number=form.rc_number.data.strip() if form.rc_number.data else None,
            industry=form.industry.data.strip() if form.industry.data else None,
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Welcome to FidelBridge! Your corporate account has been created.", "success")
        return redirect(dashboard_url_for(user))

    return render_template("auth/register_corporate.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()

        if user is None or not user.check_password(form.password.data):
            flash("Incorrect email or password.", "error")
            return render_template("auth/login.html", form=form)

        if not user.is_active:
            flash("This account has been deactivated. Please contact support.", "error")
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)

        next_url = request.args.get("next")
        if _is_safe_redirect_target(next_url):
            return redirect(next_url)
        return redirect(dashboard_url_for(user))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.index"))
