from extensions import db


class Timetable(db.Model):
    """Stores one scheduled class period in the weekly timetable."""

    __tablename__ = "timetable"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "teaching_assignments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    day_of_week = db.Column(
        db.String(10),
        nullable=False,
    )

    start_time = db.Column(
        db.Time,
        nullable=False,
    )

    end_time = db.Column(
        db.Time,
        nullable=False,
    )

    room_number = db.Column(
        db.String(30),
        nullable=True,
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    assignment = db.relationship(
        "TeachingAssignment",
        backref=db.backref(
            "timetable_entries",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "assignment_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_assignment_day_time",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Timetable assignment={self.assignment_id} "
            f"day={self.day_of_week} "
            f"time={self.start_time}-{self.end_time}>"
        )