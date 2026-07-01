from datetime import datetime, timezone

from app.extensions import db


class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    professional_profile_id = db.Column(db.Integer, db.ForeignKey("professional_profiles.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    professional = db.relationship("ProfessionalProfile", back_populates="skills")

    def __repr__(self):
        return f"<Skill {self.name!r}>"
