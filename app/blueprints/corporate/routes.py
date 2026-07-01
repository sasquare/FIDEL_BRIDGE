from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm

from app.blueprints.corporate import corporate_bp
from app.extensions import db
from app.forms.corporate import CorporateProfileForm, CorporateRequestForm
from app.models import roles
from app.models.corporate_request import (
    ALL_TYPES,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    CorporateRequest,
)
from app.utils.decorators import role_required


def _sidebar_items():
    return [
        {"key": "dashboard", "label": "Dashboard", "url": url_for("corporate.dashboard")},
        {"key": "profile", "label": "My Profile", "url": url_for("corporate.profile")},
        {"key": "requests", "label": "Service Requests", "url": url_for("corporate.requests")},
    ]


def _current_corporate():
    return current_user.corporate_profile


@corporate_bp.route("/dashboard")
@role_required(roles.CORPORATE)
def dashboard():
    corporate = _current_corporate()
    all_requests = corporate.requests

    stats = {
        "total": len(all_requests),
        "pending": sum(1 for r in all_requests if r.status == STATUS_PENDING),
        "in_progress": sum(1 for r in all_requests if r.status == STATUS_IN_PROGRESS),
        "completed": sum(1 for r in all_requests if r.status == STATUS_COMPLETED),
    }

    return render_template(
        "corporate/dashboard.html",
        user=current_user,
        corporate=corporate,
        stats=stats,
        recent_requests=all_requests[:5],
        active="dashboard",
        sidebar_items=_sidebar_items(),
    )


@corporate_bp.route("/profile", methods=["GET", "POST"])
@role_required(roles.CORPORATE)
def profile():
    corporate = _current_corporate()
    form = CorporateProfileForm(
        company_name=corporate.company_name,
        rc_number=corporate.rc_number,
        industry=corporate.industry,
        address=corporate.address,
        city=corporate.city,
        state=corporate.state,
    )

    if form.validate_on_submit():
        corporate.company_name = form.company_name.data.strip()
        corporate.rc_number = form.rc_number.data.strip() if form.rc_number.data else None
        corporate.industry = form.industry.data.strip() if form.industry.data else None
        corporate.address = form.address.data.strip() if form.address.data else None
        corporate.city = form.city.data.strip() if form.city.data else None
        corporate.state = form.state.data.strip() if form.state.data else None

        db.session.commit()
        flash("Your company profile has been updated.", "success")
        return redirect(url_for("corporate.profile"))

    return render_template(
        "corporate/profile.html", form=form, active="profile", sidebar_items=_sidebar_items()
    )


@corporate_bp.route("/requests")
@role_required(roles.CORPORATE)
def requests():
    corporate = _current_corporate()
    status_filter = request.args.get("status", "").strip()

    all_requests = corporate.requests
    if status_filter:
        all_requests = [r for r in all_requests if r.status == status_filter]

    return render_template(
        "corporate/requests.html",
        requests=all_requests,
        status_filter=status_filter,
        active="requests",
        sidebar_items=_sidebar_items(),
    )


@corporate_bp.route("/requests/new", methods=["GET", "POST"])
@role_required(roles.CORPORATE)
def new_request():
    corporate = _current_corporate()
    preselected_type = request.args.get("type", "")
    form = CorporateRequestForm(request_type=preselected_type if preselected_type in ALL_TYPES else None)

    if form.validate_on_submit():
        db.session.add(
            CorporateRequest(
                corporate_profile_id=corporate.id,
                request_type=form.request_type.data,
                title=form.title.data.strip(),
                description=form.description.data.strip(),
                location=form.location.data.strip() if form.location.data else None,
                budget_naira=form.budget_naira.data,
                preferred_date=form.preferred_date.data,
            )
        )
        db.session.commit()
        flash("Your request has been submitted.", "success")
        return redirect(url_for("corporate.requests"))

    return render_template(
        "corporate/request_form.html", form=form, active="requests", sidebar_items=_sidebar_items()
    )


@corporate_bp.route("/requests/<int:request_id>")
@role_required(roles.CORPORATE)
def request_detail(request_id):
    corporate = _current_corporate()
    service_request = CorporateRequest.query.filter_by(
        id=request_id, corporate_profile_id=corporate.id
    ).first_or_404()
    cancel_form = FlaskForm()

    return render_template(
        "corporate/request_detail.html",
        service_request=service_request,
        cancel_form=cancel_form,
        active="requests",
        sidebar_items=_sidebar_items(),
    )


@corporate_bp.route("/requests/<int:request_id>/cancel", methods=["POST"])
@role_required(roles.CORPORATE)
def cancel_request(request_id):
    corporate = _current_corporate()
    service_request = CorporateRequest.query.filter_by(
        id=request_id, corporate_profile_id=corporate.id
    ).first_or_404()

    if service_request.status != STATUS_PENDING:
        abort(400)

    service_request.status = STATUS_CANCELLED
    db.session.commit()
    flash("Request cancelled.", "success")
    return redirect(url_for("corporate.request_detail", request_id=service_request.id))
