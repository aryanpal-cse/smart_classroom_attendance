from flask_wtf import FlaskForm
from wtforms import (
    HiddenField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional


class FaceCaptureForm(FlaskForm):
    """Submit one browser-camera frame to the local Flask server."""

    image_data = HiddenField(
        "Captured Image",
        validators=[
            DataRequired(message="Capture a camera image first."),
        ],
    )

    submit = SubmitField("Capture and Submit")


class ManualReviewRequestForm(FlaskForm):
    """Allow a student to explain a failed face verification."""

    student_note = TextAreaField(
        "Optional Note",
        validators=[
            Optional(),
            Length(
                max=255,
                message="The note cannot exceed 255 characters.",
            ),
        ],
    )

    submit = SubmitField("Request Manual Review")


class ManualReviewDecisionForm(FlaskForm):
    """Allow the assigned teacher to approve or reject one request."""

    decision = HiddenField(
        "Decision",
        validators=[DataRequired()],
    )

    teacher_note = StringField(
        "Teacher Note",
        validators=[
            Optional(),
            Length(
                max=255,
                message="The note cannot exceed 255 characters.",
            ),
        ],
    )

    submit = SubmitField("Save Decision")


class AttendanceCorrectionForm(FlaskForm):
    """Allow an administrator to correct one attendance record."""

    status = SelectField(
        "Attendance Status",
        choices=[
            ("PRESENT", "Present"),
            ("ABSENT", "Absent"),
            ("LATE", "Late"),
            ("EXCUSED", "Excused"),
            ("PENDING", "Pending Review"),
        ],
        validators=[DataRequired()],
    )

    correction_reason = TextAreaField(
        "Correction Reason",
        validators=[
            DataRequired(
                message="A correction reason is required for the audit log."
            ),
            Length(
                min=3,
                max=255,
                message="Use 3 to 255 characters.",
            ),
        ],
    )

    submit = SubmitField("Save Attendance Correction")
