from datetime import datetime, timezone

from app.extensions import db


class PortfolioItem(db.Model):
    __tablename__ = "portfolio_items"

    id = db.Column(db.Integer, primary_key=True)
    professional_profile_id = db.Column(db.Integer, db.ForeignKey("professional_profiles.id"), nullable=False)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    professional = db.relationship("ProfessionalProfile", back_populates="portfolio_items")

    @property
    def image_url(self):
        """Public URL for the portfolio image, or None if no image is
        set. See ProfessionalProfile.profile_photo_url - same delegation
        to app/utils/uploads.py, same reasoning."""
        from app.utils.uploads import portfolio_image_url

        return portfolio_image_url(self.image_filename)

    def __repr__(self):
        return f"<PortfolioItem {self.title!r}>"
