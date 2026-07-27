from datetime import datetime
from typing import Any

from flask import Blueprint, abort, render_template
from flask_login import current_user

from decorators import role_required
from extensions import db
from models import (
    ClassSection,
    Subject,
    Teacher,
    TeachingAssignment,
    Timetable,
)


teacher_bp = Blueprint(
    "teacher",
    __name__,
    url_prefix="/teacher",
)


def get_value(
    object_instance: Any,
    *attribute_names: str,
    default: Any = None,
) -> Any:
    """Return the first available attribute from a model object."""
    for attribute_name in attribute_names:
        if hasattr(object_instance, attribute_name):
            return getattr(object_instance, attribute_name)

    return default


def get_model_column(
    model: Any,
    *column_names: str,
) -> Any:
    """Return the first matching SQLAlchemy model column."""
    for column_name in column_names:
        if hasattr(model, column_name):
            return getattr(model, column_name)

    return None


def format_time(value: Any) -> str:
    """Convert a stored time value into a readable value."""
    if value is None:
        return "Not specified"

    if hasattr(value, "strftime"):
        return value.strftime("%I:%M %p")

    value_text = str(value).strip()

    try:
        parsed_time = datetime.strptime(
            value_text,
            "%H:%M:%S",
        )

        return parsed_time.strftime("%I:%M %p")

    except ValueError:
        try:
            parsed_time = datetime.strptime(
                value_text,
                "%H:%M",
            )

            return parsed_time.strftime("%I:%M %p")

        except ValueError:
            return value_text


def load_teacher_profile() -> Teacher:
    """Find the teacher profile belonging to the logged-in user."""
    user_id_column = get_model_column(
        Teacher,
        "user_id",
    )

    if user_id_column is None:
        abort(
            500,
            description="Teacher user relationship is not configured.",
        )

    teacher = Teacher.query.filter(
        user_id_column == current_user.id,
    ).first()

    if teacher is None:
        abort(
            404,
            description="Teacher profile was not found.",
        )

    return teacher


def load_teacher_assignments(
    teacher: Teacher,
) -> list[TeachingAssignment]:
    """Return active assignments belonging to a teacher."""
    teacher_id_column = get_model_column(
        TeachingAssignment,
        "teacher_id",
    )

    if teacher_id_column is None:
        return []

    assignments = TeachingAssignment.query.filter(
        teacher_id_column == teacher.id,
    ).order_by(
        TeachingAssignment.id.asc(),
    ).all()

    return [
        assignment
        for assignment in assignments
        if get_value(
            assignment,
            "is_active",
            "active",
            default=True,
        )
    ]


def load_timetable_entries(
    assignment_ids: list[int],
) -> list[Timetable]:
    """Return timetable entries for the supplied assignments."""
    if not assignment_ids:
        return []

    assignment_id_column = get_model_column(
        Timetable,
        "teaching_assignment_id",
        "assignment_id",
    )

    if assignment_id_column is None:
        return []

    entries = Timetable.query.filter(
        assignment_id_column.in_(assignment_ids),
    ).order_by(
        Timetable.id.asc(),
    ).all()

    return [
        entry
        for entry in entries
        if get_value(
            entry,
            "is_active",
            "active",
            default=True,
        )
    ]


def create_assignment_details(
    assignments: list[TeachingAssignment],
) -> list[dict[str, Any]]:
    """Prepare assignment information for the dashboard template."""
    assignment_details = []

    for assignment in assignments:
        subject_id = get_value(
            assignment,
            "subject_id",
        )

        class_section_id = get_value(
            assignment,
            "class_section_id",
            "class_id",
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

        assignment_details.append(
            {
                "id": assignment.id,
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
                "subject_id": subject_id,
                "class_section_id": class_section_id,
            }
        )

    return assignment_details


def create_timetable_details(
    timetable_entries: list[Timetable],
    assignment_map: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Prepare timetable entries for the dashboard template."""
    timetable_details = []

    for entry in timetable_entries:
        assignment_id = get_value(
            entry,
            "teaching_assignment_id",
            "assignment_id",
        )

        assignment = assignment_map.get(
            assignment_id,
            {},
        )

        timetable_details.append(
            {
                "id": entry.id,
                "assignment_id": assignment_id,
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
                "subject_name": assignment.get(
                    "subject_name",
                    "Unknown Subject",
                ),
                "subject_code": assignment.get(
                    "subject_code",
                    "—",
                ),
                "class_name": assignment.get(
                    "class_name",
                    "Unknown Class",
                ),
                "section": assignment.get(
                    "section",
                    "—",
                ),
            }
        )

    return timetable_details


@teacher_bp.route("/dashboard")
@role_required("teacher")
def dashboard():
    """Display the logged-in teacher's academic dashboard."""
    teacher = load_teacher_profile()

    assignments = load_teacher_assignments(
        teacher,
    )

    assignment_details = create_assignment_details(
        assignments,
    )

    assignment_map = {
        assignment["id"]: assignment
        for assignment in assignment_details
    }

    assignment_ids = list(
        assignment_map.keys()
    )

    timetable_entries = load_timetable_entries(
        assignment_ids,
    )

    timetable_details = create_timetable_details(
        timetable_entries,
        assignment_map,
    )

    today_name = datetime.now().strftime("%A")

    today_timetable = [
        entry
        for entry in timetable_details
        if str(entry["day"]).casefold()
        == today_name.casefold()
    ]

    unique_subjects = {
        assignment["subject_id"]
        for assignment in assignment_details
        if assignment["subject_id"] is not None
    }

    unique_classes = {
        assignment["class_section_id"]
        for assignment in assignment_details
        if assignment["class_section_id"] is not None
    }

    summary = {
        "assignment_count": len(
            assignment_details
        ),
        "subject_count": len(
            unique_subjects
        ),
        "class_count": len(
            unique_classes
        ),
        "today_class_count": len(
            today_timetable
        ),
    }

    return render_template(
        "teacher/dashboard.html",
        teacher=teacher,
        assignments=assignment_details,
        today_timetable=today_timetable,
        full_timetable=timetable_details,
        today_name=today_name,
        summary=summary,
    )
@teacher_bp.route("/classes")
@role_required("teacher")
def class_list():
    """Display the logged-in teacher's assigned classes."""
    teacher = load_teacher_profile()

    assignments = load_teacher_assignments(teacher)

    assignment_details = create_assignment_details(assignments)

    return render_template(
        "teacher/classes.html",
        teacher=teacher,
        assignments=assignment_details,
    )