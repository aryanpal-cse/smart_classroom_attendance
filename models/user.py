from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(UserMixin, db.Model):
    """Login account shared by admin, teacher, and student roles."""

    __tablename__ = "users"

    VALID_ROLES = {"admin", "teacher", "student"}

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        index=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def set_password(self, password: str) -> None:
        """Hash and store a new password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True when the supplied password is correct."""
        return check_password_hash(self.password_hash, password)

    def has_role(self, role: str) -> bool:
        """Check whether the user has the required role."""
        return self.role == role

    def get_dashboard_endpoint(self) -> str:
        """Return the dashboard endpoint for the user's role."""
        dashboard_endpoints = {
            "admin": "admin.dashboard",
            "teacher": "teacher.dashboard",
            "student": "student.dashboard",
        }

        return dashboard_endpoints.get(
            self.role,
            "auth.login",
        )

    def __repr__(self) -> str:
        return f"<User {self.username} role={self.role}>"