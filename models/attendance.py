from datetime import datetime, timezone

from extensions import db


class Attendance(db.Model):
    """Stores one student's final attendance for one class session."""

    __tablename__ = "attendance"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "class_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "students.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PRESENT",
    )

    method = db.Column(
        db.String(30),
        nullable=False,
    )

    recognition_confidence = db.Column(
        db.Float,
        nullable=True,
    )

    recorded_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    notes = db.Column(
        db.String(255),
        nullable=True,
    )

    class_session = db.relationship(
        "ClassSession",
        backref=db.backref(
            "attendance_records",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    student = db.relationship(
        "Student",
        backref=db.backref(
            "attendance_records",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "session_id",
            "student_id",
            name="uq_attendance_session_student",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Attendance session={self.session_id} "
            f"student={self.student_id} "
            f"status={self.status} method={self.method}>"
        )