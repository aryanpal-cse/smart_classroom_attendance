from extensions import db


class ClassSection(db.Model):
    """Represents one academic class or section."""

    __tablename__ = "classes"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(100),
        nullable=False,
    )

    section = db.Column(
        db.String(20),
        nullable=False,
    )

    semester = db.Column(
        db.Integer,
        nullable=False,
        default=3,
    )

    academic_year = db.Column(
        db.String(20),
        nullable=False,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "name",
            "section",
            "semester",
            "academic_year",
            name="uq_class_section_semester_year",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ClassSection {self.name} "
            f"Section {self.section}>"
        )