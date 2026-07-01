from urllib.parse import urlparse

from flask import redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm

from app.blueprints.notifications import notifications_bp
from app.extensions import db
from app.models.notification import Notification


def _is_safe_redirect_target(target):
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.netloc and not parsed.scheme and target.startswith("/")


@notifications_bp.route("/")
@login_required
def index():
    mark_read_form = FlaskForm()
    return render_template(
        "notifications/index.html", notifications=current_user.notifications, mark_read_form=mark_read_form
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notification.is_read = True
    db.session.commit()

    if _is_safe_redirect_target(notification.link):
        return redirect(notification.link)
    return redirect(url_for("notifications.index"))


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return redirect(url_for("notifications.index"))
