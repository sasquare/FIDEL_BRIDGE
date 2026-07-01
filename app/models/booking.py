from datetime import datetime, timezone

from app.extensions import db

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
ALL_STATUSES = (
    STATUS_PENDING,
    STATUS_ACCEPTED,
    STATUS_REJECTED,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
)

STATUS_LABELS = {
    STATUS_PENDING: "Pending",
    STATUS_ACCEPTED: "Accepted",
    STATUS_REJECTED: "Rejected",
    STATUS_IN_PROGRESS: "In Progress",
    STATUS_COMPLETED: "Completed",
    STATUS_CANCELLED: "Cancelled",
}

# States a customer may cancel from, and the only state a professional may
# accept/reject from - kept here so the rules live next to the data they govern.
CANCELLABLE_STATUSES = (STATUS_PENDING, STATUS_ACCEPTED)


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    customer_profile_id = db.Column(db.Integer, db.ForeignKey("customer_profiles.id"), nullable=False)
    professional_profile_id = db.Column(db.Integer, db.ForeignKey("professional_profiles.id"), nullable=False)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(150), nullable=True)
    preferred_date = db.Column(db.Date, nullable=True)
    budget_naira = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (db.CheckConstraint(status.in_(ALL_STATUSES), name="ck_bookings_status_valid"),)

    customer = db.relationship("CustomerProfile", back_populates="bookings")
    professional = db.relationship("ProfessionalProfile", back_populates="bookings")

    @property
    def status_label(self):
        return STATUS_LABELS.get(self.status, self.status)

    def __repr__(self):
        return f"<Booking {self.title!r} ({self.status})>"
