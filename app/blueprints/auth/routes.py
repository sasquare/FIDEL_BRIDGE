from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.blueprints.auth import auth_bp
from app.extensions import db, limiter
from app.forms.auth import (
    CorporateRegistrationForm,
    CustomerRegistrationForm,
    ForgotPasswordForm,
    LoginForm,
    ProfessionalRegistrationForm,
    ResetPasswordForm,
)
from app.models import roles
from app.models.category import Category
from app.models.corporate import CorporateProfile
from app.models.customer import CustomerProfile
from app.models.professional import ProfessionalProfile
from app.models.user import User
from app.utils.auth_helpers import dashboard_url_for
from app.utils.mail import send_email
from app.utils.profile_emails import send_welcome_email


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
@limiter.limit("20 per hour", methods=["POST"])
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
@limiter.limit("20 per hour", methods=["POST"])
def register_professional():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))

    form = ProfessionalRegistrationForm()
    form.category_id.choices = [
        (category.id, category.name) for category in Category.query.order_by(Category.name).all()
    ]

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
            category_id=form.category_id.data,
            city=form.city.data.strip() if form.city.data else None,
        )

        db.session.add(user)
        db.session.commit()

        # Sent after the account is safely committed - a failed send is
        # logged, never raised, so it can't turn a successful registration
        # into an error page (see send_welcome_email's docstring).
        send_welcome_email(user.professional_profile)
        db.session.commit()

        login_user(user)
        flash("Welcome to FidelBridge! Your professional account has been created.", "success")
        return redirect(dashboard_url_for(user))

    return render_template("auth/register_professional.html", form=form)


@auth_bp.route("/register/corporate", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
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
@limiter.limit("10 per minute", methods=["POST"])
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


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is not None and user.is_active:
            token = user.generate_reset_token()
            db.session.commit()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_email(
                user.email,
                "Reset your FidelBridge password",
                f"Hi {user.full_name},\n\n"
                f"Click the link below to set a new password. This link expires in 1 hour.\n\n"
                f"{reset_url}\n\n"
                f"If you didn't request this, you can safely ignore this email.",
            )
        # Same message regardless of whether the email exists, so this
        # route can't be used to check which emails have an account.
        flash("If an account exists for that email, a reset link has been sent.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(dashboard_url_for(current_user))

    user = User.query_by_valid_reset_token(token)
    if user is None:
        flash("That reset link is invalid or has expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_reset_token()
        db.session.commit()
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)
