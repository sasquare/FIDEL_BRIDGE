from datetime import datetime, timezone

from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    icon_path = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    # Legacy: a manually-typed path to a self-hosted file under
    # app/static/images/, from before category images could be uploaded
    # directly. Kept for backward compatibility with any category that
    # already has one set - see image_display_url below, which prefers
    # image_filename (the uploaded-via-admin path) and falls back to this.
    image_url = db.Column(db.String(500), nullable=True)
    # Photo uploaded through the admin category form, stored via
    # app/utils/storage.py (local disk in dev, Cloudflare R2 in
    # production) - same pattern as ProfessionalProfile.profile_photo_filename.
    image_filename = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    professional_profiles = db.relationship("ProfessionalProfile", back_populates="category")

    @property
    def image_display_url(self):
        """The photo to show instead of the icon on the homepage card, or
        None to keep showing the icon. Prefers an uploaded image_filename;
        falls back to the legacy manually-typed image_url for any
        category that still only has that set."""
        from app.utils.uploads import category_image_url

        return category_image_url(self.image_filename) or self.image_url or None

    def __repr__(self):
        return f"<Category {self.slug}>"
