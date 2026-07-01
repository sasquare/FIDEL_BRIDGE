from datetime import datetime, timezone

from app.extensions import db


class ProfessionalProfile(db.Model):
    __tablename__ = "professional_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    profession = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    years_experience = db.Column(db.Integer, nullable=True)

    # Comma-separated weekday abbreviations, e.g. "Mon,Tue,Wed". Kept as a
    # simple column rather than a separate table since it's just a filter
    # tag for the MVP, not a real booking calendar (that's a later phase).
    available_days = db.Column(db.String(50), nullable=True)
    available_hours = db.Column(db.String(100), nullable=True)

    # Set once an admin reviews uploaded verification documents (Phase 9).
    is_verified = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="professional_profile")
    category = db.relationship("Category", back_populates="professional_profiles")
    skills = db.relationship(
        "Skill", back_populates="professional", cascade="all, delete-orphan", order_by="Skill.name"
    )
    portfolio_items = db.relationship(
        "PortfolioItem",
        back_populates="professional",
        cascade="all, delete-orphan",
        order_by="PortfolioItem.created_at.desc()",
    )
    verifications = db.relationship(
        "Verification",
        back_populates="professional",
        cascade="all, delete-orphan",
        order_by="Verification.uploaded_at.desc()",
    )

    @property
    def available_days_list(self):
        return self.available_days.split(",") if self.available_days else []

    def __repr__(self):
        return f"<ProfessionalProfile user_id={self.user_id} profession={self.profession!r}>"
