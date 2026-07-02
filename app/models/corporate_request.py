from datetime import datetime, timezone

from app.extensions import db

TYPE_PROCUREMENT = "procurement"
TYPE_FACILITY_MANAGEMENT = "facility_management"
TYPE_JANITORIAL = "janitorial"
TYPE_OTHER = "other"
ALL_TYPES = (TYPE_PROCUREMENT, TYPE_FACILITY_MANAGEMENT, TYPE_JANITORIAL, TYPE_OTHER)

TYPE_LABELS = {
    TYPE_PROCUREMENT: "Procurement",
    TYPE_FACILITY_MANAGEMENT: "Facility Management",
    TYPE_JANITORIAL: "Janitorial Services",
    TYPE_OTHER: "Other",
}

STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
ALL_STATUSES = (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_CANCELLED)

STATUS_LABELS = {
    STATUS_PENDING: "Pending",
    STATUS_IN_PROGRESS: "In Progress",
    STATUS_COMPLETED: "Completed",
    STATUS_CANCELLED: "Cancelled",
}


class CorporateRequest(db.Model):
    __tablename__ = "corporate_requests"

    id = db.Column(db.Integer, primary_key=True)
    corporate_profile_id = db.Column(
        db.Integer, db.ForeignKey("corporate_profiles.id"), nullable=False, index=True
    )

    request_type = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(150), nullable=True)
    budget_naira = db.Column(db.Integer, nullable=True)
    preferred_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING, index=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint(request_type.in_(ALL_TYPES), name="ck_corporate_requests_type_valid"),
        db.CheckConstraint(status.in_(ALL_STATUSES), name="ck_corporate_requests_status_valid"),
    )

    corporate = db.relationship("CorporateProfile", back_populates="requests")

    @property
    def type_label(self):
        return TYPE_LABELS.get(self.request_type, self.request_type)

    @property
    def status_label(self):
        return STATUS_LABELS.get(self.status, self.status)

    def __repr__(self):
        return f"<CorporateRequest {self.title!r} ({self.request_type})>"
