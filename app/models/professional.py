from datetime import datetime, timezone

from app.extensions import db

PROFESSIONAL_TYPE_INDIVIDUAL = "individual"
PROFESSIONAL_TYPE_REGISTERED_BUSINESS = "registered_business"
PROFESSIONAL_TYPES = (PROFESSIONAL_TYPE_INDIVIDUAL, PROFESSIONAL_TYPE_REGISTERED_BUSINESS)

PRICING_TYPE_NOT_SPECIFIED = "not_specified"
PRICING_TYPE_STARTS_FROM = "starts_from"
PRICING_TYPE_HOURLY = "hourly"
PRICING_TYPE_DAILY = "daily"
PRICING_TYPES = (PRICING_TYPE_NOT_SPECIFIED, PRICING_TYPE_STARTS_FROM, PRICING_TYPE_HOURLY, PRICING_TYPE_DAILY)
PRICING_TYPE_LABELS = {
    PRICING_TYPE_NOT_SPECIFIED: "Not specified",
    PRICING_TYPE_STARTS_FROM: "Starts from",
    PRICING_TYPE_HOURLY: "Per hour",
    PRICING_TYPE_DAILY: "Per day",
}


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

    # Public - shown on the profile, in search, and on Featured Professionals.
    profile_photo_filename = db.Column(db.String(255), nullable=True)

    # "Individual" professionals never need a business name/CAC number to
    # reach 100% completion - only "registered_business" ones do (see
    # app/utils/profile_completion.py). is_business_verified is deliberately
    # separate from is_verified: a professional's identity/skills and their
    # business registration can be reviewed independently and at different
    # times, and conflating them now would be hard to undo later.
    professional_type = db.Column(db.String(30), nullable=False, default=PROFESSIONAL_TYPE_INDIVIDUAL)
    business_name = db.Column(db.String(150), nullable=True)
    business_registration_number = db.Column(db.String(50), nullable=True)
    is_business_verified = db.Column(db.Boolean, nullable=False, default=False)

    # Flexible pricing: pricing_type/pricing_amount is the primary rate
    # structure, while requires_inspection and consultation_fee are
    # independent flags that can combine with any pricing_type (e.g. "Starts
    # from N5,000, inspection required, N1,000 consultation fee") rather
    # than forcing a single mutually-exclusive choice.
    pricing_type = db.Column(db.String(30), nullable=False, default=PRICING_TYPE_NOT_SPECIFIED)
    pricing_amount = db.Column(db.Integer, nullable=True)
    requires_inspection = db.Column(db.Boolean, nullable=False, default=False)
    consultation_fee = db.Column(db.Integer, nullable=True)

    # Private - accountability info, visible only to the professional
    # themselves and admins. NEVER reference these columns in a public
    # template (browse/, search cards, Featured Professionals).
    guarantor_name = db.Column(db.String(150), nullable=True)
    guarantor_relationship = db.Column(db.String(100), nullable=True)
    guarantor_phone = db.Column(db.String(20), nullable=True)
    guarantor_address = db.Column(db.Text, nullable=True)
    emergency_contact_name = db.Column(db.String(150), nullable=True)
    emergency_contact_relationship = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.CheckConstraint(professional_type.in_(PROFESSIONAL_TYPES), name="ck_professional_profiles_type_valid"),
        db.CheckConstraint(pricing_type.in_(PRICING_TYPES), name="ck_professional_profiles_pricing_type_valid"),
    )

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
    def profile_completion_percentage(self):
        from app.utils.profile_completion import profile_completion_percentage

        return profile_completion_percentage(self)

    @property
    def profile_completion_checklist(self):
        from app.utils.profile_completion import profile_completion_checklist

        return profile_completion_checklist(self)

    @property
    def trust_score(self):
        """A transparent 0-100 score derived entirely from real signals -
        not a black box. See app/utils/trust_score.py for the weights and
        the reasoning behind them (kept there, not here, so they can be
        retuned without touching this model)."""
        from app.utils.trust_score import compute_trust_score

        return compute_trust_score(self)

    def __repr__(self):
        return f"<ProfessionalProfile user_id={self.user_id} profession={self.profession!r}>"
