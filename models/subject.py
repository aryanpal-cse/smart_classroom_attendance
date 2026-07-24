from extensions import db


class Subject(db.Model):
    """Represents a subject taught in the college."""

    __tablename__ = "subjects"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(100),
        nullable=False,
    )

    code = db.Column(
        db.String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    semester = db.Column(
        db.Integer,
        nullable=False,
        default=3,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    def __repr__(self) -> str:
        return f"<Subject {self.code} - {self.name}>"