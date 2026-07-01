from datetime import datetime, timezone

from app.extensions import db


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_one_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user_two_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Conversations are started from an accepted booking, so the thread has
    # context. Unique per booking: each job gets at most one conversation.
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user_one = db.relationship("User", foreign_keys=[user_one_id])
    user_two = db.relationship("User", foreign_keys=[user_two_id])
    booking = db.relationship("Booking")
    messages = db.relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )

    def other_participant(self, user):
        return self.user_two if user.id == self.user_one_id else self.user_one

    def is_participant(self, user):
        return user.id in (self.user_one_id, self.user_two_id)

    def __repr__(self):
        return f"<Conversation {self.user_one_id}<->{self.user_two_id}>"
