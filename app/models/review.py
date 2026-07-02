from datetime import datetime, timezone

from app.extensions import db


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    # One review per booking - a completed job can only be rated once.
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), unique=True, nullable=False)
    customer_profile_id = db.Column(db.Integer, db.ForeignKey("customer_profiles.id"), nullable=False)
    professional_profile_id = db.Column(db.Integer, db.ForeignKey("professional_profiles.id"), nullable=False)

    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_range"),)

    booking = db.relationship("Booking", back_populates="review")
    customer = db.relationship("CustomerProfile")
    professional = db.relationship("ProfessionalProfile", back_populates="reviews")

    def __repr__(self):
        return f"<Review booking_id={self.booking_id} rating={self.rating}>"
