from datetime import datetime, timezone

from flask import abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_wtf import FlaskForm
from sqlalchemy import func, or_

from app.blueprints.admin import admin_bp
from app.extensions import db
from app.forms.category import CategoryForm
from app.models import roles
from app.models.booking import ALL_STATUSES as BOOKING_STATUSES
from app.models.booking import (
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    STATUS_REJECTED,
    Booking,
)
from app.models.category import Category
from app.models.corporate_request import ALL_STATUSES as CORPORATE_REQUEST_STATUSES
from app.models.corporate_request import STATUS_LABELS as CORPORATE_REQUEST_STATUS_LABELS
from app.models.corporate_request import STATUS_PENDING as CORPORATE_REQUEST_PENDING
from app.models.corporate_request import CorporateRequest
from app.models.professional import ProfessionalProfile
from app.models.review import Review
from app.models.user import User
from app.models.verification import STATUS_APPROVED
from app.models.verification import STATUS_REJECTED as VERIFICATION_REJECTED
from app.models.verification import Verification
from app.utils.decorators import role_required
from app.utils.notifications import notify
from app.utils.text import slugify

PER_PAGE = 20


def _sidebar_items():
    return [
        {"key": "dashboard", "label": "Dashboard", "url": url_for("admin.dashboard")},
        {"key": "professionals", "label": "Professionals", "url": url_for("admin.professionals")},
        {"key": "categories", "label": "Categories", "url": url_for("admin.categories")},
        {"key": "users", "label": "Users", "url": url_for("admin.users")},
        {"key": "bookings", "label": "Bookings", "url": url_for("admin.bookings")},
        {"key": "corporate_requests", "label": "Corporate Requests", "url": url_for("admin.corporate_requests")},
        {"key": "reports", "label": "Reports", "url": url_for("admin.reports")},
    ]


@admin_bp.route("/dashboard")
@role_required(roles.ADMIN)
def dashboard():
    stats = {
        "total_users": User.query.count(),
        "pending_professionals": ProfessionalProfile.query.filter_by(is_verified=False).count(),
        "pending_corporate_requests": CorporateRequest.query.filter_by(status=CORPORATE_REQUEST_PENDING).count(),
        "active_bookings": Booking.query.filter(
            Booking.status.in_((STATUS_PENDING, STATUS_ACCEPTED, STATUS_IN_PROGRESS))
        ).count(),
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    pending_professionals = (
        ProfessionalProfile.query.filter_by(is_verified=False)
        .order_by(ProfessionalProfile.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_users=recent_users,
        pending_professionals=pending_professionals,
        active="dashboard",
        sidebar_items=_sidebar_items(),
    )


# ---------------------------------------------------------------------------
# Professionals & verification
# ---------------------------------------------------------------------------


@admin_bp.route("/professionals")
@role_required(roles.ADMIN)
def professionals():
    status_filter = request.args.get("status", "pending").strip()

    query = ProfessionalProfile.query.join(User)
    if status_filter == "pending":
        query = query.filter(ProfessionalProfile.is_verified.is_(False))
    elif status_filter == "verified":
        query = query.filter(ProfessionalProfile.is_verified.is_(True))

    all_professionals = query.order_by(ProfessionalProfile.created_at.desc()).all()

    return render_template(
        "admin/professionals.html",
        professionals=all_professionals,
        status_filter=status_filter,
        active="professionals",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/professionals/<int:professional_id>")
@role_required(roles.ADMIN)
def professional_detail(professional_id):
    professional = db.get_or_404(ProfessionalProfile, professional_id)
    action_form = FlaskForm()

    return render_template(
        "admin/professional_detail.html",
        professional=professional,
        action_form=action_form,
        active="professionals",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/professionals/<int:professional_id>/verify", methods=["POST"])
@role_required(roles.ADMIN)
def verify_professional(professional_id):
    professional = db.get_or_404(ProfessionalProfile, professional_id)
    professional.is_verified = True
    notify(
        professional.user,
        "Congratulations! Your FidelBridge profile has been verified.",
        link=url_for("browse.professional_profile", user_id=professional.user_id),
    )
    db.session.commit()
    flash(f"{professional.user.full_name} is now verified.", "success")
    return redirect(url_for("admin.professional_detail", professional_id=professional.id))


@admin_bp.route("/professionals/<int:professional_id>/unverify", methods=["POST"])
@role_required(roles.ADMIN)
def unverify_professional(professional_id):
    professional = db.get_or_404(ProfessionalProfile, professional_id)
    professional.is_verified = False
    notify(
        professional.user,
        "Your FidelBridge verification has been revoked. Please contact support for details.",
        link=url_for("professional.verification"),
    )
    db.session.commit()
    flash(f"Verification revoked for {professional.user.full_name}.", "success")
    return redirect(url_for("admin.professional_detail", professional_id=professional.id))


@admin_bp.route("/verifications/<int:verification_id>/approve", methods=["POST"])
@role_required(roles.ADMIN)
def approve_verification(verification_id):
    doc = db.get_or_404(Verification, verification_id)
    doc.status = STATUS_APPROVED
    doc.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()
    flash("Document approved.", "success")
    return redirect(url_for("admin.professional_detail", professional_id=doc.professional_profile_id))


@admin_bp.route("/verifications/<int:verification_id>/reject", methods=["POST"])
@role_required(roles.ADMIN)
def reject_verification(verification_id):
    doc = db.get_or_404(Verification, verification_id)
    doc.status = VERIFICATION_REJECTED
    doc.admin_notes = request.form.get("admin_notes", "").strip() or None
    doc.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()
    flash("Document rejected.", "success")
    return redirect(url_for("admin.professional_detail", professional_id=doc.professional_profile_id))


@admin_bp.route("/verifications/<int:verification_id>/download")
@role_required(roles.ADMIN)
def download_verification(verification_id):
    doc = db.get_or_404(Verification, verification_id)
    directory = current_app.config["VERIFICATION_UPLOAD_FOLDER"]
    try:
        return send_from_directory(directory, doc.filename)
    except FileNotFoundError:
        abort(404)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


@admin_bp.route("/categories", methods=["GET", "POST"])
@role_required(roles.ADMIN)
def categories():
    form = CategoryForm()
    delete_form = FlaskForm()

    if form.validate_on_submit():
        name = form.name.data.strip()
        if Category.query.filter_by(name=name).first():
            flash("A category with that name already exists.", "error")
        else:
            db.session.add(
                Category(
                    name=name,
                    slug=slugify(name),
                    icon_path=form.icon_path.data.strip() if form.icon_path.data else None,
                    description=form.description.data.strip() if form.description.data else None,
                    image_url=form.image_url.data.strip() if form.image_url.data else None,
                )
            )
            db.session.commit()
            flash("Category created.", "success")
            return redirect(url_for("admin.categories"))

    all_categories = Category.query.order_by(Category.name).all()
    return render_template(
        "admin/categories.html",
        form=form,
        delete_form=delete_form,
        categories=all_categories,
        active="categories",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@role_required(roles.ADMIN)
def edit_category(category_id):
    category = db.get_or_404(Category, category_id)
    form = CategoryForm(
        name=category.name,
        icon_path=category.icon_path,
        description=category.description,
        image_url=category.image_url,
    )

    if form.validate_on_submit():
        category.name = form.name.data.strip()
        category.icon_path = form.icon_path.data.strip() if form.icon_path.data else None
        category.description = form.description.data.strip() if form.description.data else None
        category.image_url = form.image_url.data.strip() if form.image_url.data else None
        db.session.commit()
        flash("Category updated.", "success")
        return redirect(url_for("admin.categories"))

    return render_template(
        "admin/category_form.html",
        form=form,
        category=category,
        active="categories",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@role_required(roles.ADMIN)
def delete_category(category_id):
    category = db.get_or_404(Category, category_id)
    if category.professional_profiles:
        flash("Can't delete a category that still has professionals assigned to it.", "error")
    else:
        db.session.delete(category)
        db.session.commit()
        flash("Category deleted.", "success")
    return redirect(url_for("admin.categories"))


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@admin_bp.route("/users")
@role_required(roles.ADMIN)
def users():
    role_filter = request.args.get("role", "").strip()
    query_text = request.args.get("q", "").strip()

    query = User.query
    if role_filter:
        query = query.filter(User.role == role_filter)
    if query_text:
        like = f"%{query_text}%"
        query = query.filter(or_(User.full_name.ilike(like), User.email.ilike(like)))

    all_users = query.order_by(User.created_at.desc()).all()
    action_form = FlaskForm()

    return render_template(
        "admin/users.html",
        users=all_users,
        role_filter=role_filter,
        query_text=query_text,
        action_form=action_form,
        active="users",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@role_required(roles.ADMIN)
def deactivate_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.role == roles.ADMIN:
        abort(400)
    user.is_active_account = False
    db.session.commit()
    flash(f"{user.full_name}'s account has been deactivated.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/activate", methods=["POST"])
@role_required(roles.ADMIN)
def activate_user(user_id):
    user = db.get_or_404(User, user_id)
    user.is_active_account = True
    db.session.commit()
    flash(f"{user.full_name}'s account has been reactivated.", "success")
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------


@admin_bp.route("/bookings")
@role_required(roles.ADMIN)
def bookings():
    status_filter = request.args.get("status", "").strip()
    query = Booking.query
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    all_bookings = query.order_by(Booking.created_at.desc()).limit(200).all()

    return render_template(
        "admin/bookings.html",
        bookings=all_bookings,
        status_filter=status_filter,
        all_statuses=BOOKING_STATUSES,
        active="bookings",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/bookings/<int:booking_id>")
@role_required(roles.ADMIN)
def booking_detail(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    action_form = FlaskForm()

    return render_template(
        "admin/booking_detail.html",
        booking=booking,
        action_form=action_form,
        active="bookings",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@role_required(roles.ADMIN)
def cancel_booking(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    if booking.status in (STATUS_COMPLETED, STATUS_CANCELLED, STATUS_REJECTED):
        abort(400)

    booking.status = STATUS_CANCELLED
    notify(
        booking.customer.user,
        f"Your booking '{booking.title}' was cancelled by a FidelBridge administrator.",
        link=url_for("customer.booking_detail", booking_id=booking.id),
    )
    notify(
        booking.professional.user,
        f"The booking '{booking.title}' was cancelled by a FidelBridge administrator.",
        link=url_for("professional.booking_detail", booking_id=booking.id),
    )
    db.session.commit()
    flash("Booking cancelled.", "success")
    return redirect(url_for("admin.booking_detail", booking_id=booking.id))


# ---------------------------------------------------------------------------
# Corporate requests
# ---------------------------------------------------------------------------


@admin_bp.route("/corporate-requests")
@role_required(roles.ADMIN)
def corporate_requests():
    status_filter = request.args.get("status", "").strip()
    query = CorporateRequest.query
    if status_filter:
        query = query.filter(CorporateRequest.status == status_filter)
    all_requests = query.order_by(CorporateRequest.created_at.desc()).all()

    return render_template(
        "admin/corporate_requests.html",
        requests=all_requests,
        status_filter=status_filter,
        active="corporate_requests",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/corporate-requests/<int:request_id>")
@role_required(roles.ADMIN)
def corporate_request_detail(request_id):
    service_request = db.get_or_404(CorporateRequest, request_id)
    status_form = FlaskForm()

    return render_template(
        "admin/corporate_request_detail.html",
        service_request=service_request,
        status_form=status_form,
        status_choices=[(s, CORPORATE_REQUEST_STATUS_LABELS[s]) for s in CORPORATE_REQUEST_STATUSES],
        active="corporate_requests",
        sidebar_items=_sidebar_items(),
    )


@admin_bp.route("/corporate-requests/<int:request_id>/status", methods=["POST"])
@role_required(roles.ADMIN)
def update_corporate_request_status(request_id):
    service_request = db.get_or_404(CorporateRequest, request_id)
    new_status = request.form.get("status", "")

    if new_status not in CORPORATE_REQUEST_STATUSES:
        abort(400)

    service_request.status = new_status
    notify(
        service_request.corporate.user,
        f"Your request '{service_request.title}' is now {CORPORATE_REQUEST_STATUS_LABELS[new_status]}.",
        link=url_for("corporate.request_detail", request_id=service_request.id),
    )
    db.session.commit()
    flash("Request status updated.", "success")
    return redirect(url_for("admin.corporate_request_detail", request_id=service_request.id))


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@admin_bp.route("/reports")
@role_required(roles.ADMIN)
def reports():
    users_by_role = dict(db.session.query(User.role, func.count(User.id)).group_by(User.role).all())
    bookings_by_status = dict(db.session.query(Booking.status, func.count(Booking.id)).group_by(Booking.status).all())
    corporate_requests_by_status = dict(
        db.session.query(CorporateRequest.status, func.count(CorporateRequest.id))
        .group_by(CorporateRequest.status)
        .all()
    )
    top_categories = (
        db.session.query(Category.name, func.count(ProfessionalProfile.id).label("total"))
        .outerjoin(ProfessionalProfile, ProfessionalProfile.category_id == Category.id)
        .group_by(Category.id)
        .order_by(func.count(ProfessionalProfile.id).desc())
        .limit(6)
        .all()
    )
    average_platform_rating = db.session.query(func.avg(Review.rating)).scalar()
    completed_bookings_value = (
        db.session.query(func.coalesce(func.sum(Booking.budget_naira), 0))
        .filter(Booking.status == STATUS_COMPLETED)
        .scalar()
    )

    return render_template(
        "admin/reports.html",
        users_by_role=users_by_role,
        bookings_by_status=bookings_by_status,
        corporate_requests_by_status=corporate_requests_by_status,
        corporate_request_status_labels=CORPORATE_REQUEST_STATUS_LABELS,
        top_categories=top_categories,
        average_platform_rating=average_platform_rating,
        completed_bookings_value=completed_bookings_value,
        total_reviews=Review.query.count(),
        total_professionals=ProfessionalProfile.query.count(),
        verified_professionals=ProfessionalProfile.query.filter_by(is_verified=True).count(),
        active="reports",
        sidebar_items=_sidebar_items(),
    )
