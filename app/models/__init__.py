"""Database models package.

Importing every model here ensures they are registered on SQLAlchemy's
metadata before Flask-Migrate compares the schema, regardless of which
module first imports `app.models`.
"""
from app.models.booking import Booking  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.corporate import CorporateProfile  # noqa: F401
from app.models.corporate_request import CorporateRequest  # noqa: F401
from app.models.customer import CustomerProfile  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.portfolio import PortfolioItem  # noqa: F401
from app.models.professional import ProfessionalProfile  # noqa: F401
from app.models.skill import Skill  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.verification import Verification  # noqa: F401
