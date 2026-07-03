from datetime import datetime, timezone

from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    icon_path = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    # Optional lifestyle photo for the landing page's category cards. Nullable
    # so an admin can add real photography later (via the category edit form)
    # without a code deploy - the template falls back to a gradient+icon tile
    # when this is unset.
    image_url = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    professional_profiles = db.relationship("ProfessionalProfile", back_populates="category")

    def __repr__(self):
        return f"<Category {self.slug}>"
