from extensions import db


class TeachingAssignment(db.Model):
    """Connects a teacher, subject, and class section."""

    __tablename__ = "teaching_assignments"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    class_id = db.Column(
        db.Integer,
        db.ForeignKey("classes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    teacher = db.relationship(
        "Teacher",
        backref=db.backref(
            "teaching_assignments",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    subject = db.relationship(
        "Subject",
        backref=db.backref(
            "teaching_assignments",
            lazy=True,
        ),
    )

    class_section = db.relationship(
        "ClassSection",
        backref=db.backref(
            "teaching_assignments",
            lazy=True,
        ),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "teacher_id",
            "subject_id",
            "class_id",
            name="uq_teacher_subject_class",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TeachingAssignment teacher={self.teacher_id} "
            f"subject={self.subject_id} class={self.class_id}>"
        )