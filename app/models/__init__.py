"""Database models package.

Importing every model here ensures they are registered on SQLAlchemy's
metadata before Flask-Migrate compares the schema, regardless of which
module first imports `app.models`.
"""
from app.models.corporate import CorporateProfile  # noqa: F401
from app.models.customer import CustomerProfile  # noqa: F401
from app.models.professional import ProfessionalProfile  # noqa: F401
from app.models.user import User  # noqa: F401
