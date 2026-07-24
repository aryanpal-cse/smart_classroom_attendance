from datetime import datetime, timezone

from extensions import db


class FaceData(db.Model):
    """Stores metadata for a student's locally registered face samples."""

    __tablename__ = "face_data"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "students.id",
            ondelete="CASCADE",
        ),
        unique=True,
        nullable=False,
        index=True,
    )

    # LBPH will use the student ID as its numeric recognition label.
    recognition_label = db.Column(
        db.Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    dataset_path = db.Column(
        db.String(255),
        nullable=False,
    )

    sample_count = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    is_trained = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    registered_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    last_trained_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    student = db.relationship(
        "Student",
        backref=db.backref(
            "face_data",
            uselist=False,
            cascade="all, delete-orphan",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<FaceData student={self.student_id} "
            f"samples={self.sample_count} "
            f"trained={self.is_trained}>"
        )