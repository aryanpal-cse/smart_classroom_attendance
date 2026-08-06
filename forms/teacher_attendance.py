from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


class TeacherAttendanceForm(FlaskForm):
    """Create or edit a teacher attendance record."""

    teacher_id = SelectField(
        "Teacher",
        coerce=int,
        validators=[DataRequired(message="Please select a teacher.")],
    )

    attendance_date = DateField(
        "Attendance Date",
        validators=[DataRequired(message="Attendance date is required.")],
    )

    status = SelectField(
        "Attendance Status",
        choices=[
            ("PRESENT", "Present"),
            ("ABSENT", "Absent"),
            ("LATE", "Late"),
            ("HALF_DAY", "Half Day"),
            ("LEAVE", "Leave"),
            ("HOLIDAY", "Holiday"),
        ],
        validators=[DataRequired(message="Attendance status is required.")],
    )

    check_in = TimeField(
        "Check-in Time",
        validators=[Optional()],
    )

    check_out = TimeField(
        "Check-out Time",
        validators=[Optional()],
    )

    scheduled_classes = IntegerField(
        "Scheduled Classes",
        validators=[
            InputRequired(message="Scheduled class count is required."),
            NumberRange(min=0, max=20),
        ],
        default=0,
    )

    conducted_classes = IntegerField(
        "Conducted Classes",
        validators=[
            InputRequired(message="Conducted class count is required."),
            NumberRange(min=0, max=20),
        ],
        default=0,
    )

    remarks = StringField(
        "Remarks / Correction Reason",
        validators=[Optional(), Length(max=255)],
    )

    submit = SubmitField("Save Attendance Record")

    def validate_check_out(self, field) -> None:
        """Check-out cannot be before check-in."""
        if self.check_in.data and field.data:
            if field.data < self.check_in.data:
                raise ValidationError(
                    "Check-out time cannot be earlier than check-in time."
                )

    def validate_conducted_classes(self, field) -> None:
        """Conducted classes cannot exceed scheduled classes."""
        if (
            self.scheduled_classes.data is not None
            and field.data is not None
            and field.data > self.scheduled_classes.data
        ):
            raise ValidationError(
                "Conducted classes cannot exceed scheduled classes."
            )
