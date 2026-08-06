from datetime import datetime, timezone

from extensions import db


class TeacherAttendance(db.Model):
    """Stores one teacher's attendance record for one calendar date."""

    __tablename__ = "teacher_attendance"

    VALID_STATUSES = {
        "PRESENT",
        "ABSENT",
        "LATE",
        "HALF_DAY",
        "LEAVE",
        "HOLIDAY",
    }

    id = db.Column(db.Integer, primary_key=True)

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    attendance_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PRESENT",
        index=True,
    )

    check_in = db.Column(db.Time, nullable=True)
    check_out = db.Column(db.Time, nullable=True)

    scheduled_classes = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    conducted_classes = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    remarks = db.Column(db.String(255), nullable=True)

    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    updated_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    teacher = db.relationship(
        "Teacher",
        backref=db.backref(
            "attendance_records",
            lazy=True,
            cascade="all, delete-orphan",
        ),
    )

    created_by = db.relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )

    updated_by = db.relationship(
        "User",
        foreign_keys=[updated_by_user_id],
    )

    __table_args__ = (
        db.UniqueConstraint(
            "teacher_id",
            "attendance_date",
            name="uq_teacher_attendance_date",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<TeacherAttendance teacher={self.teacher_id} "
            f"date={self.attendance_date} status={self.status}>"
        )
