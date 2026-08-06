import secrets
import string
from datetime import datetime, timedelta
from typing import Any

from extensions import db
from models import ClassSession, Timetable


CODE_CHARACTERS = string.ascii_uppercase + string.digits
CODE_LENGTH = 6
MAX_CODE_GENERATION_ATTEMPTS = 100


def get_model_attribute(
    model_or_object: Any,
    *attribute_names: str,
) -> str | None:
    """Return the first supported attribute name."""
    for attribute_name in attribute_names:
        if hasattr(model_or_object, attribute_name):
            return attribute_name

    return None


def set_first_supported_attribute(
    object_instance: Any,
    value: Any,
    *attribute_names: str,
) -> str | None:
    """Set the first supported attribute."""
    attribute_name = get_model_attribute(
        object_instance,
        *attribute_names,
    )

    if attribute_name is None:
        return None

    setattr(
        object_instance,
        attribute_name,
        value,
    )

    return attribute_name


def get_first_supported_value(
    object_instance: Any,
    *attribute_names: str,
    default: Any = None,
) -> Any:
    """Read the first supported attribute value."""
    if object_instance is None:
        return default

    attribute_name = get_model_attribute(
        object_instance,
        *attribute_names,
    )

    if attribute_name is None:
        return default

    return getattr(
        object_instance,
        attribute_name,
        default,
    )


def get_code_column():
    """Return the column used to store temporary class codes."""
    column_name = get_model_attribute(
        ClassSession,
        "class_code",
        "session_code",
        "attendance_code",
        "temporary_code",
        "code",
    )

    if column_name is None:
        raise RuntimeError(
            "ClassSession has no supported class-code column."
        )

    return getattr(
        ClassSession,
        column_name,
    )


def generate_random_code() -> str:
    """Generate a secure six-character temporary code."""
    return "".join(
        secrets.choice(CODE_CHARACTERS)
        for _ in range(CODE_LENGTH)
    )


def generate_unique_class_code() -> str:
    """Generate a class code not already stored in SQLite."""
    code_column = get_code_column()

    for _ in range(MAX_CODE_GENERATION_ATTEMPTS):
        class_code = generate_random_code()

        existing_session = ClassSession.query.filter(
            code_column == class_code,
        ).first()

        if existing_session is None:
            return class_code

    raise RuntimeError(
        "A unique temporary class code could not be generated."
    )


def get_timetable_assignment_id(
    timetable_entry: Timetable,
) -> int | None:
    """Read the teaching-assignment ID from a timetable entry."""
    return get_first_supported_value(
        timetable_entry,
        "teaching_assignment_id",
        "assignment_id",
    )


def resolve_timetable_for_assignment(
    teaching_assignment_id: int,
) -> Timetable:
    """
    Find an active timetable entry connected to an assignment.

    Today's timetable entry is preferred. When no entry exists for
    today, the first active timetable entry is used.
    """
    assignment_column_name = get_model_attribute(
        Timetable,
        "teaching_assignment_id",
        "assignment_id",
    )

    if assignment_column_name is None:
        raise RuntimeError(
            "Timetable has no supported teaching-assignment column."
        )

    assignment_column = getattr(
        Timetable,
        assignment_column_name,
    )

    timetable_entries = Timetable.query.filter(
        assignment_column == teaching_assignment_id,
    ).order_by(
        Timetable.id.asc(),
    ).all()

    active_entries = [
        entry
        for entry in timetable_entries
        if bool(
            get_first_supported_value(
                entry,
                "is_active",
                "active",
                default=True,
            )
        )
    ]

    if not active_entries:
        raise RuntimeError(
            "No active timetable entry exists for the selected "
            "teaching assignment."
        )

    today_name = datetime.now().strftime("%A")

    for entry in active_entries:
        entry_day = str(
            get_first_supported_value(
                entry,
                "day_of_week",
                "day",
                "weekday",
                default="",
            )
        ).strip()

        if entry_day.casefold() == today_name.casefold():
            return entry

    return active_entries[0]


def create_class_session(
    teaching_assignment_id: int,
    teacher_id: int,
    validity_minutes: int,
) -> ClassSession:
    """
    Create a class session connected to a timetable record.

    teacher_id is accepted for compatibility with the Teacher route.
    Teacher ownership is obtained through:
    ClassSession → Timetable → TeachingAssignment → Teacher.
    """
    if validity_minutes < 1 or validity_minutes > 30:
        raise ValueError(
            "Code validity must be between 1 and 30 minutes."
        )

    timetable_entry = resolve_timetable_for_assignment(
        teaching_assignment_id
    )

    now = datetime.now()

    expires_at = now + timedelta(
        minutes=validity_minutes,
    )

    class_session = ClassSession.query.filter_by(
        timetable_id=timetable_entry.id,
        session_date=now.date(),
    ).first()

    if class_session is None:
        class_session = ClassSession(
            timetable_id=timetable_entry.id,
            session_date=now.date(),
        )
    else:
        existing_status = str(class_session.status or "").upper()
        if (
            existing_status in {"CLOSED", "ENDED", "FINALIZED"}
            or class_session.attendance_closed_at is not None
        ):
            raise RuntimeError(
                "Today's class session for this timetable entry is "
                "already closed and cannot be reopened."
            )

    # Reuse an attendance-open session only when its temporary code
    # expired before the teacher ended the class.
    class_session.status = "ACTIVE"
    class_session.class_code = generate_unique_class_code()
    class_session.code_expires_at = expires_at
    class_session.started_at = now
    class_session.attendance_closed_at = None
    class_session.finalized_at = None

    return class_session


def end_class_session(
    class_session: ClassSession,
) -> None:
    """Close an active class session."""
    now = datetime.now()

    set_first_supported_attribute(
        class_session,
        now,
        "attendance_closed_at",
        "ended_at",
        "end_time",
        "closed_at",
    )

    set_first_supported_attribute(
        class_session,
        now,
        "code_expires_at",
        "expires_at",
        "expiry_time",
    )

    set_first_supported_attribute(
        class_session,
        "CLOSED",
        "status",
        "session_status",
    )


def is_session_active(
    class_session: ClassSession,
) -> bool:
    """Check session status and temporary-code expiry."""
    status = str(
        get_first_supported_value(
            class_session,
            "status",
            "session_status",
            default="SCHEDULED",
        )
    ).strip().upper()

    if status in {
        "CLOSED",
        "ENDED",
        "FINALIZED",
        "CANCELLED",
        "INACTIVE",
    }:
        return False

    attendance_closed_at = get_first_supported_value(
        class_session,
        "attendance_closed_at",
        "ended_at",
        "closed_at",
    )

    if attendance_closed_at is not None:
        return False

    expires_at = get_first_supported_value(
        class_session,
        "code_expires_at",
        "expires_at",
        "expiry_time",
        "expiration_time",
    )

    if (
        expires_at is not None
        and datetime.now() > expires_at
    ):
        return False

    return status in {
        "ACTIVE",
        "OPEN",
        "SCHEDULED",
        "STARTED",
    }


def save_class_session(
    class_session: ClassSession,
) -> None:
    """
    Add and flush a class session.

    The Teacher route performs the final commit together with its
    audit-log record so both records are saved atomically.
    """
    try:
        db.session.add(class_session)
        db.session.flush()

    except Exception:
        db.session.rollback()
        raise