from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
)


class AddStudentForm(FlaskForm):
    """Create a student login account and academic profile."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(
                min=3,
                max=50,
                message="Username must contain 3 to 50 characters.",
            ),
        ],
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(
                min=8,
                max=128,
                message="Password must contain 8 to 128 characters.",
            ),
        ],
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm the password."),
            EqualTo(
                "password",
                message="Both password fields must match.",
            ),
        ],
    )

    roll_number = StringField(
        "Roll Number",
        validators=[
            DataRequired(message="Roll number is required."),
            Length(
                min=2,
                max=30,
                message="Roll number must contain 2 to 30 characters.",
            ),
        ],
    )

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Student name is required."),
            Length(
                min=2,
                max=100,
                message="Student name must contain 2 to 100 characters.",
            ),
        ],
    )

    email = StringField(
        "Email",
        validators=[
            Optional(),
            Length(
                max=120,
                message="Email cannot exceed 120 characters.",
            ),
        ],
    )

    class_id = SelectField(
        "Class Section",
        coerce=int,
        validators=[
            DataRequired(
                message="Please select a class section.",
            ),
        ],
    )

    is_active = BooleanField(
        "Activate account",
        default=True,
    )

    submit = SubmitField("Add Student")


class EditStudentForm(FlaskForm):
    """Update an existing student account and academic profile."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(
                min=3,
                max=50,
                message="Username must contain 3 to 50 characters.",
            ),
        ],
    )

    roll_number = StringField(
        "Roll Number",
        validators=[
            DataRequired(message="Roll number is required."),
            Length(
                min=2,
                max=30,
                message="Roll number must contain 2 to 30 characters.",
            ),
        ],
    )

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Student name is required."),
            Length(
                min=2,
                max=100,
                message="Student name must contain 2 to 100 characters.",
            ),
        ],
    )

    email = StringField(
        "Email",
        validators=[
            Optional(),
            Length(
                max=120,
                message="Email cannot exceed 120 characters.",
            ),
        ],
    )

    class_id = SelectField(
        "Class Section",
        coerce=int,
        validators=[
            DataRequired(
                message="Please select a class section.",
            ),
        ],
    )

    new_password = PasswordField(
        "New Password",
        validators=[
            Optional(),
            Length(
                min=8,
                max=128,
                message="Password must contain 8 to 128 characters.",
            ),
        ],
    )

    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[
            EqualTo(
                "new_password",
                message="Both password fields must match.",
            ),
        ],
    )

    is_active = BooleanField(
        "Activate account",
    )

    submit = SubmitField("Save Changes")


class AddTeacherForm(FlaskForm):
    """Create a teacher login account and academic profile."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(
                min=3,
                max=50,
                message="Username must contain 3 to 50 characters.",
            ),
        ],
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(
                min=8,
                max=128,
                message="Password must contain 8 to 128 characters.",
            ),
        ],
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm the password."),
            EqualTo(
                "password",
                message="Both password fields must match.",
            ),
        ],
    )

    employee_id = StringField(
        "Employee ID",
        validators=[
            DataRequired(message="Employee ID is required."),
            Length(
                min=2,
                max=30,
                message="Employee ID must contain 2 to 30 characters.",
            ),
        ],
    )

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Teacher name is required."),
            Length(
                min=2,
                max=100,
                message="Teacher name must contain 2 to 100 characters.",
            ),
        ],
    )

    email = StringField(
        "Email",
        validators=[
            Optional(),
            Length(
                max=120,
                message="Email cannot exceed 120 characters.",
            ),
        ],
    )

    department = StringField(
        "Department",
        validators=[
            DataRequired(message="Department is required."),
            Length(
                min=2,
                max=100,
                message="Department must contain 2 to 100 characters.",
            ),
        ],
        default="Computer Science and Engineering",
    )

    is_active = BooleanField(
        "Activate account",
        default=True,
    )

    submit = SubmitField("Add Teacher")


class EditTeacherForm(FlaskForm):
    """Update an existing teacher account and academic profile."""

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(
                min=3,
                max=50,
                message="Username must contain 3 to 50 characters.",
            ),
        ],
    )

    employee_id = StringField(
        "Employee ID",
        validators=[
            DataRequired(message="Employee ID is required."),
            Length(
                min=2,
                max=30,
                message="Employee ID must contain 2 to 30 characters.",
            ),
        ],
    )

    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Teacher name is required."),
            Length(
                min=2,
                max=100,
                message="Teacher name must contain 2 to 100 characters.",
            ),
        ],
    )

    email = StringField(
        "Email",
        validators=[
            Optional(),
            Length(
                max=120,
                message="Email cannot exceed 120 characters.",
            ),
        ],
    )

    department = StringField(
        "Department",
        validators=[
            DataRequired(message="Department is required."),
            Length(
                min=2,
                max=100,
                message="Department must contain 2 to 100 characters.",
            ),
        ],
    )

    new_password = PasswordField(
        "New Password",
        validators=[
            Optional(),
            Length(
                min=8,
                max=128,
                message="Password must contain 8 to 128 characters.",
            ),
        ],
    )

    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[
            EqualTo(
                "new_password",
                message="Both password fields must match.",
            ),
        ],
    )

    is_active = BooleanField(
        "Activate account",
    )

    submit = SubmitField("Save Changes")


class AddSubjectForm(FlaskForm):
    """Create a new academic subject."""

    name = StringField(
        "Subject Name",
        validators=[
            DataRequired(message="Subject name is required."),
            Length(
                min=2,
                max=100,
                message="Subject name must contain 2 to 100 characters.",
            ),
        ],
    )

    code = StringField(
        "Subject Code",
        validators=[
            DataRequired(message="Subject code is required."),
            Length(
                min=2,
                max=20,
                message="Subject code must contain 2 to 20 characters.",
            ),
        ],
    )

    semester = IntegerField(
        "Semester",
        validators=[
            DataRequired(message="Semester is required."),
            NumberRange(
                min=1,
                max=8,
                message="Semester must be between 1 and 8.",
            ),
        ],
        default=3,
    )

    is_active = BooleanField(
        "Activate subject",
        default=True,
    )

    submit = SubmitField("Add Subject")


class EditSubjectForm(FlaskForm):
    """Update an existing academic subject."""

    name = StringField(
        "Subject Name",
        validators=[
            DataRequired(message="Subject name is required."),
            Length(
                min=2,
                max=100,
                message="Subject name must contain 2 to 100 characters.",
            ),
        ],
    )

    code = StringField(
        "Subject Code",
        validators=[
            DataRequired(message="Subject code is required."),
            Length(
                min=2,
                max=20,
                message="Subject code must contain 2 to 20 characters.",
            ),
        ],
    )

    semester = IntegerField(
        "Semester",
        validators=[
            DataRequired(message="Semester is required."),
            NumberRange(
                min=1,
                max=8,
                message="Semester must be between 1 and 8.",
            ),
        ],
    )

    is_active = BooleanField(
        "Activate subject",
    )

    submit = SubmitField("Save Changes")


class AddClassSectionForm(FlaskForm):
    """Create a new academic class section."""

    name = StringField(
        "Programme / Class Name",
        validators=[
            DataRequired(
                message="Programme or class name is required."
            ),
            Length(
                min=2,
                max=100,
                message="Class name must contain 2 to 100 characters.",
            ),
        ],
    )

    section = StringField(
        "Section",
        validators=[
            DataRequired(message="Section is required."),
            Length(
                min=1,
                max=20,
                message="Section cannot exceed 20 characters.",
            ),
        ],
    )

    semester = IntegerField(
        "Semester",
        validators=[
            DataRequired(message="Semester is required."),
            NumberRange(
                min=1,
                max=8,
                message="Semester must be between 1 and 8.",
            ),
        ],
        default=3,
    )

    academic_year = StringField(
        "Academic Year",
        validators=[
            DataRequired(message="Academic year is required."),
            Regexp(
                r"^\d{4}-\d{2}$",
                message="Use academic-year format such as 2026-27.",
            ),
            Length(
                max=20,
                message="Academic year cannot exceed 20 characters.",
            ),
        ],
        default="2026-27",
    )

    is_active = BooleanField(
        "Activate class section",
        default=True,
    )

    submit = SubmitField("Add Class Section")


class EditClassSectionForm(FlaskForm):
    """Update an existing academic class section."""

    name = StringField(
        "Programme / Class Name",
        validators=[
            DataRequired(
                message="Programme or class name is required."
            ),
            Length(
                min=2,
                max=100,
                message="Class name must contain 2 to 100 characters.",
            ),
        ],
    )

    section = StringField(
        "Section",
        validators=[
            DataRequired(message="Section is required."),
            Length(
                min=1,
                max=20,
                message="Section cannot exceed 20 characters.",
            ),
        ],
    )

    semester = IntegerField(
        "Semester",
        validators=[
            DataRequired(message="Semester is required."),
            NumberRange(
                min=1,
                max=8,
                message="Semester must be between 1 and 8.",
            ),
        ],
    )

    academic_year = StringField(
        "Academic Year",
        validators=[
            DataRequired(message="Academic year is required."),
            Regexp(
                r"^\d{4}-\d{2}$",
                message="Use academic-year format such as 2026-27.",
            ),
            Length(
                max=20,
                message="Academic year cannot exceed 20 characters.",
            ),
        ],
    )

    is_active = BooleanField(
        "Activate class section",
    )

    submit = SubmitField("Save Changes")