from datetime import datetime
from typing import Any

from extensions import db
from models import (
    Attendance,
    AuditLog,
    ClassSession,
    Enrollment,
    ManualReviewRequest,
    Student,
    Teacher,
)
from services.class_session_service import is_session_active


class AttendanceValidationError(ValueError):
    """Raised when attendance rules reject a student or class session."""


def validate_student_session(
    student: Student,
    class_session: ClassSession,
) -> Any:
    """Validate login, enrollment, active session and duplicate rules."""
    if not is_session_active(class_session):
        raise AttendanceValidationError(
            "This class session is closed or its code has expired."
        )

    timetable_entry = class_session.timetable_entry
    assignment = timetable_entry.assignment if timetable_entry else None

    if assignment is None:
        raise AttendanceValidationError(
            "This class session is not linked to a teaching assignment."
        )

    if assignment.class_id != student.class_id:
        raise AttendanceValidationError(
            "This class code belongs to a different class section."
        )

    enrollment = Enrollment.query.filter_by(
        student_id=student.id,
        class_id=assignment.class_id,
        subject_id=assignment.subject_id,
        is_active=True,
    ).first()

    if enrollment is None:
        raise AttendanceValidationError(
            "You are not enrolled in this subject and class section."
        )

    duplicate = Attendance.query.filter_by(
        session_id=class_session.id,
        student_id=student.id,
    ).first()

    if duplicate is not None:
        raise AttendanceValidationError(
            "Attendance has already been recorded for this class session."
        )

    return assignment


def record_attendance(
    student: Student,
    class_session: ClassSession,
    status: str,
    method: str,
    recognition_confidence: float | None = None,
    notes: str | None = None,
    audit_user_id: int | None = None,
    require_active: bool = True,
) -> Attendance:
    """Create one duplicate-safe attendance record and its audit entry."""
    if require_active:
        validate_student_session(student, class_session)
    else:
        duplicate = Attendance.query.filter_by(
            session_id=class_session.id,
            student_id=student.id,
        ).first()
        if duplicate is not None:
            raise AttendanceValidationError(
                "Attendance has already been recorded for this class session."
            )

    attendance = Attendance(
        session_id=class_session.id,
        student_id=student.id,
        status=status.upper(),
        method=method.upper(),
        recognition_confidence=recognition_confidence,
        notes=notes,
    )

    db.session.add(attendance)
    db.session.flush()

    db.session.add(
        AuditLog(
            user_id=audit_user_id,
            session_id=class_session.id,
            student_id=student.id,
            action="ATTENDANCE_RECORDED",
            details=(
                f"Attendance {attendance.id} recorded as {attendance.status} "
                f"using {attendance.method}."
            ),
        )
    )

    return attendance


def get_or_create_manual_review(
    student: Student,
    class_session: ClassSession,
    failure_reason: str,
    student_note: str | None,
    audit_user_id: int | None,
) -> ManualReviewRequest:
    """Create or refresh a pending manual-review request."""
    validate_student_session(student, class_session)

    review = ManualReviewRequest.query.filter_by(
        session_id=class_session.id,
        student_id=student.id,
    ).first()

    if review is None:
        review = ManualReviewRequest(
            session_id=class_session.id,
            student_id=student.id,
        )
        db.session.add(review)

    review.failure_reason = failure_reason[:255]
    review.student_note = student_note or None
    review.status = "PENDING"
    review.teacher_note = None
    review.reviewed_at = None
    review.reviewed_by_teacher_id = None

    db.session.flush()

    db.session.add(
        AuditLog(
            user_id=audit_user_id,
            session_id=class_session.id,
            student_id=student.id,
            action="MANUAL_REVIEW_REQUESTED",
            details=(
                f"Manual review {review.id} requested after face "
                "verification failure."
            ),
        )
    )

    return review


def decide_manual_review(
    review: ManualReviewRequest,
    teacher: Teacher,
    decision: str,
    teacher_note: str | None,
    audit_user_id: int | None,
) -> Attendance | None:
    """Approve or reject a request owned by the assigned teacher."""
    decision = decision.strip().upper()
    if decision not in {"APPROVE", "REJECT"}:
        raise AttendanceValidationError("Invalid manual-review decision.")

    assignment = review.class_session.timetable_entry.assignment
    if assignment.teacher_id != teacher.id:
        raise AttendanceValidationError(
            "This manual-review request belongs to another teacher."
        )

    if review.status != "PENDING":
        raise AttendanceValidationError(
            "This manual-review request has already been decided."
        )

    review.reviewed_by_teacher_id = teacher.id
    review.reviewed_at = datetime.now()
    review.teacher_note = teacher_note or None

    attendance = None

    if decision == "APPROVE":
        attendance = record_attendance(
            student=review.student,
            class_session=review.class_session,
            status="PRESENT",
            method="MANUAL_REVIEW",
            notes=teacher_note or "Approved after manual review.",
            audit_user_id=audit_user_id,
            require_active=False,
        )
        review.status = "APPROVED"
    else:
        review.status = "REJECTED"

    db.session.add(
        AuditLog(
            user_id=audit_user_id,
            session_id=review.session_id,
            student_id=review.student_id,
            action=f"MANUAL_REVIEW_{review.status}",
            details=(
                f"Teacher {teacher.employee_id} marked manual review "
                f"{review.id} as {review.status}."
            ),
        )
    )

    return attendance
