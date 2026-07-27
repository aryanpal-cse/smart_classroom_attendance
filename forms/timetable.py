from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    SelectField,
    StringField,
    SubmitField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    Length,
)


DAY_CHOICES = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
]


class AddTimetableForm(FlaskForm):
    """Create a timetable entry for a teaching assignment."""

    teaching_assignment_id = SelectField(
        "Teaching Assignment",
        coerce=int,
        validators=[
            DataRequired(
                message="Please select a teaching assignment."
            ),
        ],
    )

    day_of_week = SelectField(
        "Day",
        choices=DAY_CHOICES,
        validators=[
            DataRequired(message="Please select a day."),
        ],
    )

    start_time = TimeField(
        "Start Time",
        format="%H:%M",
        validators=[
            DataRequired(message="Start time is required."),
        ],
    )

    end_time = TimeField(
        "End Time",
        format="%H:%M",
        validators=[
            DataRequired(message="End time is required."),
        ],
    )

    room_number = StringField(
        "Room Number",
        validators=[
            DataRequired(message="Room number is required."),
            Length(
                min=1,
                max=30,
                message="Room number cannot exceed 30 characters.",
            ),
        ],
    )

    is_active = BooleanField(
        "Activate timetable entry",
        default=True,
    )

    submit = SubmitField("Add Timetable Entry")

    def validate(self, extra_validators=None) -> bool:
        """Validate fields and ensure the end time is later."""
        valid = super().validate(
            extra_validators=extra_validators
        )

        if not valid:
            return False

        if (
            self.start_time.data
            and self.end_time.data
            and self.end_time.data <= self.start_time.data
        ):
            self.end_time.errors.append(
                "End time must be later than start time."
            )
            return False

        return True


class EditTimetableForm(FlaskForm):
    """Update an existing timetable entry."""

    teaching_assignment_id = SelectField(
        "Teaching Assignment",
        coerce=int,
        validators=[
            DataRequired(
                message="Please select a teaching assignment."
            ),
        ],
    )

    day_of_week = SelectField(
        "Day",
        choices=DAY_CHOICES,
        validators=[
            DataRequired(message="Please select a day."),
        ],
    )

    start_time = TimeField(
        "Start Time",
        format="%H:%M",
        validators=[
            DataRequired(message="Start time is required."),
        ],
    )

    end_time = TimeField(
        "End Time",
        format="%H:%M",
        validators=[
            DataRequired(message="End time is required."),
        ],
    )

    room_number = StringField(
        "Room Number",
        validators=[
            DataRequired(message="Room number is required."),
            Length(
                min=1,
                max=30,
                message="Room number cannot exceed 30 characters.",
            ),
        ],
    )

    is_active = BooleanField(
        "Activate timetable entry",
    )

    submit = SubmitField("Save Changes")

    def validate(self, extra_validators=None) -> bool:
        """Validate fields and ensure the end time is later."""
        valid = super().validate(
            extra_validators=extra_validators
        )

        if not valid:
            return False

        if (
            self.start_time.data
            and self.end_time.data
            and self.end_time.data <= self.start_time.data
        ):
            self.end_time.errors.append(
                "End time must be later than start time."
            )
            return False

        return True