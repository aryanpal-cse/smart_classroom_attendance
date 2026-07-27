from datetime import datetime
from typing import Any

from flask import Blueprint, abort, render_template
from flask_login import current_user

from decorators import role_required
from extensions import db
from models import (
    Attendance,
    ClassSection,
    Enrollment,
    Student,
    Subject,
    TeachingAssignment,
    Timetable,
)


student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/student",
)


def get_value(
    object_instance: Any,
    *attribute_names: str,
    default: Any = None,
) -> Any:
    """Return the first available attribute from an object."""
    if object_instance is None:
        return default

    for attribute_name in attribute_names:
        if hasattr(object_instance, attribute_name):
            return getattr(object_instance, attribute_name)

    return default


def get_model_column(
    model: Any,
    *column_names: str,
) -> Any:
    """Return the first available SQLAlchemy model column."""
    for column_name in column_names:
        if hasattr(model, column_name):
            return getattr(model, column_name)

    return None


def format_time(value: Any) -> str:
    """Convert a stored time value into a readable format."""
    if value is None:
        return "Not specified"

    if hasattr(value, "strftime"):
        return value.strftime("%I:%M %p")

    value_text = str(value).strip()

    for time_format in ("%H:%M:%S", "%H:%M"):
        try:
            parsed_time = datetime.strptime(
                value_text,
                time_format,
            )

            return parsed_time.strftime("%I:%M %p")

        except ValueError:
            continue

    return value_text


def load_student_profile() -> Student:
    """Load the profile belonging to the logged-in student."""
    user_id_column = get_model_column(
        Student,
        "user_id",
    )

    if user_id_column is None:
        abort(
            500,
            description="Student user relationship is not configured.",
        )

    student = Student.query.filter(
        user_id_column == current_user.id,
    ).first()

    if student is None:
        abort(
            404,
            description="Student profile was not found.",
        )

    return student


def load_student_class(
    student: Student,
) -> ClassSection | None:
    """Load the student's main class section."""
    class_section_id = get_value(
        student,
        "class_section_id",
        "class_id",
    )

    if class_section_id is None:
        return None

    return db.session.get(
        ClassSection,
        class_section_id,
    )


def load_enrollments(
    student: Student,
) -> list[Enrollment]:
    """Load active enrolments belonging to the student."""
    student_id_column = get_model_column(
        Enrollment,
        "student_id",
    )

    if student_id_column is None:
        return []

    enrollments = Enrollment.query.filter(
        student_id_column == student.id,
    ).order_by(
        Enrollment.id.asc(),
    ).all()

    return [
        enrollment
        for enrollment in enrollments
        if get_value(
            enrollment,
            "is_active",
            "active",
            default=True,
        )
    ]


def create_enrollment_details(
    student: Student,
    enrollments: list[Enrollment],
) -> list[dict[str, Any]]:
    """Prepare enrolled-subject details for the template."""
    enrollment_details = []

    student_class_id = get_value(
        student,
        "class_section_id",
        "class_id",
    )

    for enrollment in enrollments:
        assignment_id = get_value(
            enrollment,
            "teaching_assignment_id",
            "assignment_id",
        )

        assignment = (
            db.session.get(
                TeachingAssignment,
                assignment_id,
            )
            if assignment_id is not None
            else None
        )

        subject_id = get_value(
            enrollment,
            "subject_id",
            default=get_value(
                assignment,
                "subject_id",
            ),
        )

        class_section_id = get_value(
            enrollment,
            "class_section_id",
            "class_id",
            default=get_value(
                assignment,
                "class_section_id",
                "class_id",
                default=student_class_id,
            ),
        )

        subject = (
            db.session.get(Subject, subject_id)
            if subject_id is not None
            else None
        )

        class_section = (
            db.session.get(
                ClassSection,
                class_section_id,
            )
            if class_section_id is not None
            else None
        )

        enrollment_details.append(
            {
                "id": enrollment.id,
                "assignment_id": assignment_id,
                "subject_name": get_value(
                    subject,
                    "name",
                    default="Unknown Subject",
                ),
                "subject_code": get_value(
                    subject,
                    "code",
                    default="—",
                ),
                "class_name": get_value(
                    class_section,
                    "name",
                    default="Unknown Class",
                ),
                "section": get_value(
                    class_section,
                    "section",
                    default="—",
                ),
                "semester": get_value(
                    class_section,
                    "semester",
                    default="—",
                ),
                "academic_year": get_value(
                    class_section,
                    "academic_year",
                    default="—",
                ),
            }
        )

    return enrollment_details


def load_timetable_entries(
    assignment_ids: list[int],
) -> list[Timetable]:
    """Load timetable entries for enrolled assignments."""
    if not assignment_ids:
        return []

    assignment_column = get_model_column(
        Timetable,
        "teaching_assignment_id",
        "assignment_id",
    )

    if assignment_column is None:
        return []

    timetable_entries = Timetable.query.filter(
        assignment_column.in_(assignment_ids),
    ).order_by(
        Timetable.id.asc(),
    ).all()

    return [
        entry
        for entry in timetable_entries
        if get_value(
            entry,
            "is_active",
            "active",
            default=True,
        )
    ]


def create_timetable_details(
    timetable_entries: list[Timetable],
    enrollment_map: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prepare timetable details for the template."""
    timetable_details = []

    for entry in timetable_entries:
        assignment_id = get_value(
            entry,
            "teaching_assignment_id",
            "assignment_id",
        )

        enrollment = enrollment_map.get(
            assignment_id,
            {},
        )

        timetable_details.append(
            {
                "id": entry.id,
                "day": get_value(
                    entry,
                    "day_of_week",
                    "day",
                    "weekday",
                    default="Not specified",
                ),
                "start_time": format_time(
                    get_value(
                        entry,
                        "start_time",
                        "from_time",
                    )
                ),
                "end_time": format_time(
                    get_value(
                        entry,
                        "end_time",
                        "to_time",
                    )
                ),
                "room": get_value(
                    entry,
                    "room_number",
                    "room",
                    "classroom",
                    default="Not specified",
                ),
                "subject_name": enrollment.get(
                    "subject_name",
                    "Unknown Subject",
                ),
                "subject_code": enrollment.get(
                    "subject_code",
                    "—",
                ),
                "class_name": enrollment.get(
                    "class_name",
                    "Unknown Class",
                ),
                "section": enrollment.get(
                    "section",
                    "—",
                ),
            }
        )

    return timetable_details


def create_attendance_summary(
    student: Student,
) -> dict[str, Any]:
    """Calculate a basic attendance summary."""
    student_id_column = get_model_column(
        Attendance,
        "student_id",
    )

    if student_id_column is None:
        records = []
    else:
        records = Attendance.query.filter(
            student_id_column == student.id,
        ).all()

    summary = {
        "total": len(records),
        "present": 0,
        "absent": 0,
        "late": 0,
        "pending": 0,
        "percentage": 0.0,
    }

    for record in records:
        status = str(
            get_value(
                record,
                "status",
                "attendance_status",
                default="pending",
            )
        ).strip().casefold()

        if status == "present":
            summary["present"] += 1
        elif status == "absent":
            summary["absent"] += 1
        elif status == "late":
            summary["late"] += 1
        else:
            summary["pending"] += 1

    attended_classes = (
        summary["present"]
        + summary["late"]
    )

    if summary["total"] > 0:
        summary["percentage"] = round(
            attended_classes
            / summary["total"]
            * 100,
            1,
        )

    return summary


@student_bp.route("/dashboard")
@role_required("student")
def dashboard():
    """Display the logged-in student's dashboard."""
    student = load_student_profile()
    class_section = load_student_class(student)

    enrollments = load_enrollments(student)

    enrollment_details = create_enrollment_details(
        student,
        enrollments,
    )

    enrollment_map = {
        enrollment["assignment_id"]: enrollment
        for enrollment in enrollment_details
        if enrollment["assignment_id"] is not None
    }

    timetable_entries = load_timetable_entries(
        list(enrollment_map.keys()),
    )

    timetable_details = create_timetable_details(
        timetable_entries,
        enrollment_map,
    )

    today_name = datetime.now().strftime("%A")

    today_timetable = [
        entry
        for entry in timetable_details
        if str(entry["day"]).casefold()
        == today_name.casefold()
    ]

    attendance_summary = create_attendance_summary(
        student,
    )

    return render_template(
        "student/dashboard.html",
        student=student,
        class_section=class_section,
        enrollments=enrollment_details,
        today_timetable=today_timetable,
        full_timetable=timetable_details,
        today_name=today_name,
        attendance=attendance_summary,
    )
@student_bp.route("/subjects")
@role_required("student")
def subject_list():
    """Display subjects assigned to the logged-in student."""
    student = load_student_profile()
    class_section = load_student_class(student)

    enrollments = load_enrollments(student)

    enrollment_details = create_enrollment_details(
        student,
        enrollments,
    )

    return render_template(
        "student/subjects.html",
        student=student,
        class_section=class_section,
        enrollments=enrollment_details,
    )