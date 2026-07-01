from app.extensions import db
from app.models.notification import Notification


def notify(user, message, link=None):
    """Queue a notification for `user`. Does not commit — the caller commits
    it together with whatever change triggered the notification."""
    db.session.add(Notification(user_id=user.id, message=message, link=link))
