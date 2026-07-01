from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm

from app.blueprints.customer import customer_bp
from app.extensions import db
from app.forms.booking import BookingForm
from app.forms.customer import CustomerProfileForm
from app.models import roles
from app.models.booking import (
    CANCELLABLE_STATUSES,
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    Booking,
)
from app.models.category import Category
from app.models.user import User
from app.utils.decorators import role_required
from app.utils.messaging import unread_message_count
from app.utils.notifications import notify


def _sidebar_items():
    return [
        {"key": "dashboard", "label": "Dashboard", "url": url_for("customer.dashboard")},
        {"key": "profile", "label": "My Profile", "url": url_for("customer.profile")},
        {"key": "bookings", "label": "My Bookings", "url": url_for("customer.bookings")},
        {"key": "messages", "label": "Messages", "url": url_for("messages.conversations")},
        {"key": "browse", "label": "Find Professionals", "url": url_for("browse.professionals")},
    ]


@customer_bp.route("/dashboard")
@role_required(roles.CUSTOMER)
def dashboard():
    all_bookings = current_user.customer_profile.bookings
    stats = {
        "active": sum(1 for b in all_bookings if b.status in (STATUS_PENDING, STATUS_ACCEPTED, STATUS_IN_PROGRESS)),
        "completed": sum(1 for b in all_bookings if b.status == STATUS_COMPLETED),
        "unread_messages": unread_message_count(current_user),
    }
    return render_template(
        "customer/dashboard.html",
        user=current_user,
        active="dashboard",
        sidebar_items=_sidebar_items(),
        categories=Category.query.order_by(Category.name).limit(6).all(),
        stats=stats,
        recent_bookings=all_bookings[:5],
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


@customer_bp.route("/book/<int:professional_user_id>", methods=["GET", "POST"])
@role_required(roles.CUSTOMER)
def book_professional(professional_user_id):
    professional_user = User.query.filter_by(id=professional_user_id, role=roles.PROFESSIONAL).first_or_404()
    professional = professional_user.professional_profile
    form = BookingForm()

    if form.validate_on_submit():
        booking = Booking(
            customer_profile_id=current_user.customer_profile.id,
            professional_profile_id=professional.id,
            title=form.title.data.strip(),
            description=form.description.data.strip(),
            location=form.location.data.strip() if form.location.data else None,
            budget_naira=form.budget_naira.data,
            preferred_date=form.preferred_date.data,
        )
        db.session.add(booking)
        db.session.flush()  # assign booking.id before building the notification link

        notify(
            professional_user,
            f"New job request from {current_user.full_name}: {booking.title}",
            link=url_for("professional.booking_detail", booking_id=booking.id),
        )
        db.session.commit()
        flash("Your request has been sent to the professional.", "success")
        return redirect(url_for("customer.booking_detail", booking_id=booking.id))

    return render_template(
        "customer/book_professional.html",
        form=form,
        professional=professional,
        active="browse",
        sidebar_items=_sidebar_items(),
    )


@customer_bp.route("/bookings")
@role_required(roles.CUSTOMER)
def bookings():
    status_filter = request.args.get("status", "").strip()
    all_bookings = current_user.customer_profile.bookings
    if status_filter:
        all_bookings = [b for b in all_bookings if b.status == status_filter]

    return render_template(
        "customer/bookings.html",
        bookings=all_bookings,
        status_filter=status_filter,
        active="bookings",
        sidebar_items=_sidebar_items(),
    )


@customer_bp.route("/bookings/<int:booking_id>")
@role_required(roles.CUSTOMER)
def booking_detail(booking_id):
    booking = Booking.query.filter_by(
        id=booking_id, customer_profile_id=current_user.customer_profile.id
    ).first_or_404()
    cancel_form = FlaskForm()

    return render_template(
        "customer/booking_detail.html",
        booking=booking,
        cancel_form=cancel_form,
        active="bookings",
        sidebar_items=_sidebar_items(),
    )


@customer_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@role_required(roles.CUSTOMER)
def cancel_booking(booking_id):
    booking = Booking.query.filter_by(
        id=booking_id, customer_profile_id=current_user.customer_profile.id
    ).first_or_404()

    if booking.status not in CANCELLABLE_STATUSES:
        abort(400)

    booking.status = STATUS_CANCELLED
    notify(
        booking.professional.user,
        f"Booking cancelled by customer: {booking.title}",
        link=url_for("professional.booking_detail", booking_id=booking.id),
    )
    db.session.commit()
    flash("Booking cancelled.", "success")
    return redirect(url_for("customer.booking_detail", booking_id=booking.id))
