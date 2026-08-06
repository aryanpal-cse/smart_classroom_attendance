from datetime import datetime, timezone

from extensions import db


class Teacher(db.Model):
    """Stores academic details for a teacher user account."""

    __tablename__ = "teachers"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    employee_id = db.Column(
        db.String(30),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name = db.Column(
        db.String(100),
        nullable=False,
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=True,
    )

    department = db.Column(
        db.String(100),
        nullable=False,
        default="Computer Science and Engineering",
    )

    designation = db.Column(
        db.String(100),
        nullable=False,
        default="Assistant Professor",
    )

    phone = db.Column(
        db.String(20),
        nullable=True,
    )

    joining_date = db.Column(
        db.Date,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "teacher_profile",
            uselist=False,
            cascade="all, delete-orphan",
        ),
    )

    def __repr__(self) -> str:
        return f"<Teacher {self.employee_id} - {self.full_name}>"