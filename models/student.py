from datetime import datetime, timezone

from extensions import db


class Student(db.Model):
    """Stores academic details for a student user account."""

    __tablename__ = "students"

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

    class_id = db.Column(
        db.Integer,
        db.ForeignKey("classes.id"),
        nullable=False,
        index=True,
    )

    roll_number = db.Column(
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

    phone = db.Column(
        db.String(20),
        nullable=True,
    )

    face_registered = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "student_profile",
            uselist=False,
            cascade="all, delete-orphan",
        ),
    )

    class_section = db.relationship(
        "ClassSection",
        backref=db.backref(
            "students",
            lazy=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Student {self.roll_number} - {self.full_name}>"