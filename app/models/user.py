import secrets
from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager
from app.models.roles import ALL_ROLES, CUSTOMER

RESET_TOKEN_LIFETIME = timedelta(hours=1)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=CUSTOMER)
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)

    # Password reset: a random single-use token, cleared once redeemed or
    # once a fresh one is issued. Not indexed as unique - collisions are
    # astronomically unlikely with 32 bytes of randomness, and a plain
    # index is enough to make the lookup in verify_reset_token() fast.
    reset_token = db.Column(db.String(64), nullable=True, index=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    customer_profile = db.relationship(
        "CustomerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    professional_profile = db.relationship(
        "ProfessionalProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    corporate_profile = db.relationship(
        "CorporateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )

    __table_args__ = (db.CheckConstraint(role.in_(ALL_ROLES), name="ck_users_role_valid"),)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def generate_reset_token(self):
        """Issue a new single-use password reset token, replacing any
        previous one (so an old, leaked reset link stops working the moment
        a new one is requested)."""
        token = secrets.token_urlsafe(32)
        self.reset_token = token
        self.reset_token_expires_at = datetime.now(timezone.utc) + RESET_TOKEN_LIFETIME
        return token

    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expires_at = None

    @classmethod
    def query_by_valid_reset_token(cls, token):
        user = cls.query.filter_by(reset_token=token).first()
        if user is None or user.reset_token_expires_at is None:
            return None
        expires_at = user.reset_token_expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None
        return user

    @property
    def is_active(self):
        return self.is_active_account

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
