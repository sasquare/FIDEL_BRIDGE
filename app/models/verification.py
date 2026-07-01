from datetime import datetime, timezone

from app.extensions import db

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
ALL_STATUSES = (STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED)


class Verification(db.Model):
    __tablename__ = "verifications"

    id = db.Column(db.Integer, primary_key=True)
    professional_profile_id = db.Column(db.Integer, db.ForeignKey("professional_profiles.id"), nullable=False)

    document_type = db.Column(db.String(80), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    admin_notes = db.Column(db.Text, nullable=True)

    uploaded_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (db.CheckConstraint(status.in_(ALL_STATUSES), name="ck_verifications_status_valid"),)

    professional = db.relationship("ProfessionalProfile", back_populates="verifications")

    def __repr__(self):
        return f"<Verification {self.document_type!r} status={self.status}>"
