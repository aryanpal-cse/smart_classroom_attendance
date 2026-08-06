from flask_wtf import FlaskForm
from wtforms import (
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Regexp,
)


class StartClassSessionForm(FlaskForm):
    """Start a live class and generate a temporary attendance code."""

    teaching_assignment_id = SelectField(
        "Teaching Assignment",
        coerce=int,
        validators=[
            DataRequired(
                message="Please select a teaching assignment."
            ),
        ],
    )

    code_valid_minutes = IntegerField(
        "Code Validity in Minutes",
        default=10,
        validators=[
            DataRequired(
                message="Code validity is required."
            ),
            NumberRange(
                min=1,
                max=30,
                message=(
                    "The temporary code must remain valid "
                    "for 1 to 30 minutes."
                ),
            ),
        ],
    )

    submit = SubmitField(
        "Start Class and Generate Code"
    )


class JoinClassSessionForm(FlaskForm):
    """Allow a student to enter a temporary class code."""

    class_code = StringField(
        "Temporary Class Code",
        validators=[
            DataRequired(
                message="Please enter the class code."
            ),
            Length(
                min=6,
                max=6,
                message=(
                    "The class code must contain exactly "
                    "6 characters."
                ),
            ),
            Regexp(
                r"^[A-Za-z0-9]{6}$",
                message=(
                    "The class code can contain only "
                    "letters and numbers."
                ),
            ),
        ],
        filters=[
            lambda value: (
                value.strip().upper()
                if value
                else value
            ),
        ],
    )

    submit = SubmitField("Join Class")


class EndClassSessionForm(FlaskForm):
    """End an active class session."""

    submit = SubmitField("End Class Session")

class FinalizeClassSessionForm(FlaskForm):
    """Finalize a closed class session after all reviews are decided."""

    submit = SubmitField("Finalize Session")
