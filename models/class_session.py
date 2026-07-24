from datetime import datetime, timezone

from extensions import db


class ClassSession(db.Model):
    """Represents one actual class session for a scheduled timetable entry."""

    __tablename__ = "class_sessions"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    timetable_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "timetable.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    session_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="SCHEDULED",
        index=True,
    )

    class_code = db.Column(
        db.String(20),
        unique=True,
        nullable=True,
        index=True,
    )

    code_expires_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    started_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    attendance_closed_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    finalized_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    timetable_entry = db.relationship(
        "Timetable",
        backref=db.backref(
            "class_sessions",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "timetable_id",
            "session_date",
            name="uq_timetable_session_date",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ClassSession timetable={self.timetable_id} "
            f"date={self.session_date} status={self.status}>"
        )

    @property
    def is_attendance_open(self) -> bool:
        """Return True only when the session accepts attendance."""
        return self.status in {"STARTED", "ACTIVE", "ATTENDANCE_OPEN"}