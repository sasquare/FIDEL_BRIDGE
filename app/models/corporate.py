from datetime import datetime, timezone

from app.extensions import db


class CorporateProfile(db.Model):
    __tablename__ = "corporate_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    company_name = db.Column(db.String(150), nullable=False)
    rc_number = db.Column(db.String(50), nullable=True)
    industry = db.Column(db.String(120), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="corporate_profile")
    requests = db.relationship(
        "CorporateRequest",
        back_populates="corporate",
        cascade="all, delete-orphan",
        order_by="CorporateRequest.created_at.desc()",
    )

    def __repr__(self):
        return f"<CorporateProfile user_id={self.user_id} company={self.company_name!r}>"
