from datetime import datetime, timezone

from extensions import db


class AuditLog(db.Model):
    """Stores important actions performed inside the attendance system."""

    __tablename__ = "audit_logs"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "class_sessions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "students.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    action = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    details = db.Column(
        db.String(500),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "audit_logs",
            lazy=True,
        ),
    )

    class_session = db.relationship(
        "ClassSession",
        backref=db.backref(
            "audit_logs",
            lazy=True,
        ),
    )

    student = db.relationship(
        "Student",
        backref=db.backref(
            "audit_logs",
            lazy=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog action={self.action} "
            f"user={self.user_id} "
            f"created_at={self.created_at}>"
        )