from datetime import datetime, timezone

from extensions import db


class ManualReviewRequest(db.Model):
    """Stores a student's manual attendance review request."""

    __tablename__ = "manual_review_requests"

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

    reviewed_by_teacher_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "teachers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    failure_reason = db.Column(
        db.String(255),
        nullable=False,
        default="Face verification failed",
    )

    student_note = db.Column(
        db.String(255),
        nullable=True,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PENDING",
        index=True,
    )

    teacher_note = db.Column(
        db.String(255),
        nullable=True,
    )

    requested_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    reviewed_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    class_session = db.relationship(
        "ClassSession",
        backref=db.backref(
            "manual_review_requests",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    student = db.relationship(
        "Student",
        backref=db.backref(
            "manual_review_requests",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    reviewed_by_teacher = db.relationship(
        "Teacher",
        backref=db.backref(
            "reviewed_manual_requests",
            lazy=True,
        ),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "session_id",
            "student_id",
            name="uq_manual_review_session_student",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ManualReviewRequest session={self.session_id} "
            f"student={self.student_id} status={self.status}>"
        )