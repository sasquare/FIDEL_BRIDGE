from datetime import datetime, timezone

from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Composite index: the unread-count context processor runs this exact
    # (user_id, is_read) lookup on every authenticated page view.
    __table_args__ = (db.Index("ix_notifications_user_unread", "user_id", "is_read"),)

    user = db.relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification user_id={self.user_id} read={self.is_read}>"
