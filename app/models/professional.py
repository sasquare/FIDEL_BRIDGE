from datetime import datetime, timezone

from app.extensions import db


class ProfessionalProfile(db.Model):
    __tablename__ = "professional_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True, index=True)

    profession = db.Column(db.String(120), nullable=False)
    # Not indexed: search filters on these with a "%term%" ILIKE, which a
    # plain B-tree index can't accelerate anyway.
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
    is_verified = db.Column(db.Boolean, nullable=False, default=False, index=True)

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
    bookings = db.relationship(
        "Booking", back_populates="professional", cascade="all, delete-orphan", order_by="Booking.created_at.desc()"
    )
    reviews = db.relationship(
        "Review", back_populates="professional", cascade="all, delete-orphan", order_by="Review.created_at.desc()"
    )

    @property
    def available_days_list(self):
        return self.available_days.split(",") if self.available_days else []

    @property
    def review_count(self):
        return len(self.reviews)

    @property
    def average_rating(self):
        if not self.reviews:
            return None
        return sum(review.rating for review in self.reviews) / len(self.reviews)

    @property
    def completed_jobs_count(self):
        from app.models.booking import STATUS_COMPLETED

        return sum(1 for booking in self.bookings if booking.status == STATUS_COMPLETED)

    @property
    def average_response_time(self):
        """Human-readable average time-to-accept, or None if there's no
        accepted_at data yet (bookings accepted before this field existed,
        or a professional who hasn't accepted anything yet)."""
        response_times = [
            (booking.accepted_at - booking.created_at).total_seconds()
            for booking in self.bookings
            if booking.accepted_at is not None
        ]
        if not response_times:
            return None

        avg_minutes = (sum(response_times) / len(response_times)) / 60
        if avg_minutes < 60:
            return "Under 1 hour"
        if avg_minutes < 24 * 60:
            return f"{round(avg_minutes / 60)}h"
        return f"{round(avg_minutes / (24 * 60))}d"

    @property
    def trust_score(self):
        """A transparent 0-100 score derived entirely from real signals -
        not a black box. Verification is weighted heaviest since it's the
        platform's core promise; rating, review volume and completed jobs
        are each capped so a single outlier can't dominate the score."""
        score = 40 if self.is_verified else 0
        if self.average_rating:
            score += (self.average_rating / 5) * 30
        score += min(self.review_count, 10) / 10 * 15
        score += min(self.completed_jobs_count, 10) / 10 * 15
        return round(score)

    def __repr__(self):
        return f"<ProfessionalProfile user_id={self.user_id} profession={self.profession!r}>"
