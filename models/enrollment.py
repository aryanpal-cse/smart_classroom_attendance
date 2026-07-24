from datetime import datetime, timezone

from extensions import db


class Enrollment(db.Model):
    """Connects a student with a class and subject."""

    __tablename__ = "enrollments"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    class_id = db.Column(
        db.Integer,
        db.ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    enrolled_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    student = db.relationship(
        "Student",
        backref=db.backref(
            "enrollments",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    class_section = db.relationship(
        "ClassSection",
        backref=db.backref(
            "enrollments",
            lazy=True,
        ),
    )

    subject = db.relationship(
        "Subject",
        backref=db.backref(
            "enrollments",
            lazy=True,
        ),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "class_id",
            "subject_id",
            name="uq_student_class_subject",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Enrollment student={self.student_id} "
            f"class={self.class_id} subject={self.subject_id}>"
        )