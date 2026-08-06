from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user

from decorators import role_required
from extensions import db
from forms import (
    EndClassSessionForm,
    FinalizeClassSessionForm,
    ManualReviewDecisionForm,
    StartClassSessionForm,
)
from models import (
    Attendance,
    AuditLog,
    ClassSession,
    Enrollment,
    ManualReviewRequest,
    Teacher,
    TeacherAttendance,
    TeachingAssignment,
    Timetable,
)
from services import (
    AttendanceValidationError,
    create_class_session,
    decide_manual_review,
    end_class_session,
    is_session_active,
    save_class_session,
)


teacher_bp = Blueprint(
    "teacher",
    __name__,
    url_prefix="/teacher",
)

WEEK_DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]

DAY_ORDER = {
    day_name: index
    for index, day_name in enumerate(WEEK_DAYS)
}


def build_current_week_dates() -> dict[str, date]:
    """Map Monday-to-Saturday to dates in the current calendar week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    return {
        day_name: monday + timedelta(days=day_index)
        for day_index, day_name in enumerate(WEEK_DAYS)
    }


# =========================================================
# Logged-in teacher helpers
# =========================================================


def load_teacher_profile() -> Teacher:
    """Return the teacher profile linked to the logged-in account."""
    teacher = Teacher.query.filter_by(
        user_id=current_user.id,
    ).first()

    if teacher is None:
        abort(
            404,
            description=(
                "A teacher profile is not linked to this login account."
            ),
        )

    return teacher


def load_teacher_assignments(
    teacher: Teacher,
) -> list[TeachingAssignment]:
    """Return active assignments owned by the logged-in teacher."""
    return TeachingAssignment.query.filter_by(
        teacher_id=teacher.id,
        is_active=True,
    ).order_by(
        TeachingAssignment.id.asc(),
    ).all()


def build_assignment_rows(
    assignments: list[TeachingAssignment],
) -> list[dict[str, Any]]:
    """Prepare teacher assignment information for HTML templates."""
    rows: list[dict[str, Any]] = []

    for assignment in assignments:
        subject = assignment.subject
        class_section = assignment.class_section

        rows.append(
            {
                "id": assignment.id,
                "subject_id": assignment.subject_id,
                "class_id": assignment.class_id,
                "subject_name": subject.name,
                "subject_code": subject.code,
                "course": class_section.course,
                "class_name": class_section.name,
                "group_name": class_section.group_name,
                "section": class_section.section,
                "semester": class_section.semester,
                "academic_year": class_section.academic_year,
            }
        )

    return rows


def load_teacher_timetable(
    assignments: list[TeachingAssignment],
) -> list[dict[str, Any]]:
    """Return the complete weekly timetable for one teacher."""
    assignment_map = {
        assignment.id: assignment
        for assignment in assignments
    }

    if not assignment_map:
        return []

    entries = Timetable.query.filter(
        Timetable.assignment_id.in_(assignment_map.keys()),
        Timetable.is_active.is_(True),
    ).all()

    entries.sort(
        key=lambda entry: (
            DAY_ORDER.get(entry.day_of_week, 99),
            entry.start_time,
            entry.end_time,
        )
    )

    rows: list[dict[str, Any]] = []

    for entry in entries:
        assignment = assignment_map.get(entry.assignment_id)
        if assignment is None:
            continue

        rows.append(
            {
                "id": entry.id,
                "assignment_id": assignment.id,
                "day": entry.day_of_week,
                "start_time": entry.start_time.strftime("%I:%M %p"),
                "end_time": entry.end_time.strftime("%I:%M %p"),
                "room": entry.room_number or "Not specified",
                "subject_name": assignment.subject.name,
                "subject_code": assignment.subject.code,
                "class_name": assignment.class_section.name,
                "section": assignment.class_section.section,
                "semester": assignment.class_section.semester,
                "academic_year": assignment.class_section.academic_year,
            }
        )

    return rows


def group_timetable_by_day(
    timetable_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group timetable rows from Monday to Saturday."""
    grouped = {
        day_name: []
        for day_name in WEEK_DAYS
    }

    for row in timetable_rows:
        grouped.setdefault(row["day"], []).append(row)

    return grouped


def build_program_rows(
    assignment_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Group subjects by the teacher's assigned program and section."""
    grouped: dict[int, dict[str, Any]] = {}

    for assignment in assignment_rows:
        class_id = assignment["class_id"]

        if class_id not in grouped:
            grouped[class_id] = {
                "class_id": class_id,
                "course": assignment["course"],
                "class_name": assignment["class_name"],
                "group_name": assignment["group_name"],
                "section": assignment["section"],
                "semester": assignment["semester"],
                "academic_year": assignment["academic_year"],
                "subjects": [],
            }

        grouped[class_id]["subjects"].append(
            {
                "name": assignment["subject_name"],
                "code": assignment["subject_code"],
            }
        )

    return sorted(
        grouped.values(),
        key=lambda row: (
            row["class_name"],
            row["semester"],
            row["section"],
        ),
    )


# =========================================================
# Teacher attendance helpers
# =========================================================


def load_teacher_attendance(
    teacher: Teacher,
) -> list[TeacherAttendance]:
    """Return the logged-in teacher's attendance records."""
    return TeacherAttendance.query.filter_by(
        teacher_id=teacher.id,
    ).order_by(
        TeacherAttendance.attendance_date.desc(),
        TeacherAttendance.id.desc(),
    ).all()


def build_teacher_attendance_summary(
    records: list[TeacherAttendance],
) -> dict[str, Any]:
    """Calculate teacher attendance and class-conducted totals."""
    summary: dict[str, Any] = {
        "total": len(records),
        "present": 0,
        "absent": 0,
        "late": 0,
        "half_day": 0,
        "leave": 0,
        "holiday": 0,
        "percentage": 0.0,
        "scheduled_classes": 0,
        "conducted_classes": 0,
    }

    for record in records:
        status_key = record.status.strip().lower()

        if status_key in summary:
            summary[status_key] += 1

        summary["scheduled_classes"] += record.scheduled_classes
        summary["conducted_classes"] += record.conducted_classes

    working_days = sum(
        1
        for record in records
        if record.status != "HOLIDAY"
    )

    attended_days = sum(
        1
        for record in records
        if record.status in {"PRESENT", "LATE", "HALF_DAY"}
    )

    if working_days:
        summary["percentage"] = round(
            attended_days / working_days * 100,
            1,
        )

    return summary


def build_attendance_rows(
    records: list[TeacherAttendance],
) -> list[dict[str, Any]]:
    """Prepare readable teacher-attendance rows."""
    rows: list[dict[str, Any]] = []

    for record in records:
        rows.append(
            {
                "id": record.id,
                "date": record.attendance_date.strftime("%d %b %Y"),
                "status": record.status.replace("_", " ").title(),
                "status_key": record.status.lower(),
                "check_in": (
                    record.check_in.strftime("%I:%M %p")
                    if record.check_in
                    else "—"
                ),
                "check_out": (
                    record.check_out.strftime("%I:%M %p")
                    if record.check_out
                    else "—"
                ),
                "scheduled_classes": record.scheduled_classes,
                "conducted_classes": record.conducted_classes,
                "remarks": record.remarks or "—",
            }
        )

    return rows


# =========================================================
# Teacher dashboards and personal pages
# =========================================================


@teacher_bp.get("/dashboard")
@role_required("teacher")
def dashboard():
    """Display only the logged-in teacher's own information."""
    teacher = load_teacher_profile()
    assignments = load_teacher_assignments(teacher)
    assignment_rows = build_assignment_rows(assignments)
    timetable_rows = load_teacher_timetable(assignments)
    attendance_records = load_teacher_attendance(teacher)

    today_name = datetime.now().strftime("%A")
    today_timetable = [
        row
        for row in timetable_rows
        if row["day"] == today_name
    ]

    summary = {
        "assignment_count": len(assignment_rows),
        "subject_count": len(
            {row["subject_id"] for row in assignment_rows}
        ),
        "class_count": len(
            {row["class_id"] for row in assignment_rows}
        ),
        "today_class_count": len(today_timetable),
    }

    return render_template(
        "teacher/dashboard.html",
        teacher=teacher,
        assignments=assignment_rows,
        today_timetable=today_timetable,
        weekly_timetable=group_timetable_by_day(timetable_rows),
        week_days=WEEK_DAYS,
        today_name=today_name,
        summary=summary,
        attendance_summary=build_teacher_attendance_summary(
            attendance_records
        ),
    )


@teacher_bp.get("/profile")
@role_required("teacher")
def profile():
    """Display the logged-in teacher's profile only."""
    teacher = load_teacher_profile()
    assignments = load_teacher_assignments(teacher)
    attendance_records = load_teacher_attendance(teacher)

    return render_template(
        "teacher/profile.html",
        teacher=teacher,
        assignment_count=len(assignments),
        attendance_summary=build_teacher_attendance_summary(
            attendance_records
        ),
    )


@teacher_bp.get("/classes")
@role_required("teacher")
def class_list():
    """Display classes and subjects assigned to this teacher."""
    teacher = load_teacher_profile()
    assignments = load_teacher_assignments(teacher)

    return render_template(
        "teacher/classes.html",
        teacher=teacher,
        assignments=build_assignment_rows(assignments),
    )


@teacher_bp.get("/programs")
@role_required("teacher")
def program_list():
    """Display only programs and sections assigned to this teacher."""
    teacher = load_teacher_profile()
    assignments = load_teacher_assignments(teacher)
    assignment_rows = build_assignment_rows(assignments)

    return render_template(
        "teacher/programs.html",
        teacher=teacher,
        programs=build_program_rows(assignment_rows),
    )


@teacher_bp.get("/timetable")
@role_required("teacher")
def timetable():
    """Display the logged-in teacher's complete weekly timetable."""
    teacher = load_teacher_profile()
    assignments = load_teacher_assignments(teacher)
    timetable_rows = load_teacher_timetable(assignments)

    return render_template(
        "teacher/timetable.html",
        teacher=teacher,
        week_days=WEEK_DAYS,
        week_dates=build_current_week_dates(),
        weekly_timetable=group_timetable_by_day(timetable_rows),
        total_classes=len(timetable_rows),
    )


@teacher_bp.get("/attendance")
@role_required("teacher")
def attendance():
    """Display the logged-in teacher's read-only attendance records."""
    teacher = load_teacher_profile()
    records = load_teacher_attendance(teacher)

    return render_template(
        "teacher/attendance.html",
        teacher=teacher,
        attendance_rows=build_attendance_rows(records),
        attendance_summary=build_teacher_attendance_summary(records),
    )


# =========================================================
# Live-class session helpers and routes
# =========================================================


def get_teacher_session_choices(
    assignments: list[TeachingAssignment],
) -> list[tuple[int, str]]:
    """Create live-session choices owned by the teacher."""
    return [
        (
            assignment.id,
            (
                f"{assignment.subject.name} "
                f"({assignment.subject.code}) · "
                f"{assignment.class_section.name} "
                f"Section {assignment.class_section.section}"
            ),
        )
        for assignment in assignments
    ]


def get_session_assignment_id(
    class_session: ClassSession,
) -> int | None:
    """Return the assignment connected through the session timetable."""
    timetable_entry = class_session.timetable_entry
    if timetable_entry is None:
        return None

    return timetable_entry.assignment_id


def find_active_assignment_session(
    assignment_id: int,
) -> ClassSession | None:
    """Find an active session for one teacher-owned assignment."""
    sessions = (
        ClassSession.query.join(Timetable)
        .filter(Timetable.assignment_id == assignment_id)
        .order_by(ClassSession.id.desc())
        .all()
    )

    for class_session in sessions:
        if is_session_active(class_session):
            return class_session

    return None


def get_teacher_active_sessions(
    assignment_ids: list[int],
) -> list[dict[str, Any]]:
    """Return active sessions belonging only to this teacher."""
    if not assignment_ids:
        return []

    sessions = (
        ClassSession.query.join(Timetable)
        .filter(Timetable.assignment_id.in_(assignment_ids))
        .order_by(ClassSession.id.desc())
        .all()
    )

    rows: list[dict[str, Any]] = []

    for class_session in sessions:
        if not is_session_active(class_session):
            continue

        assignment = class_session.timetable_entry.assignment

        rows.append(
            {
                "id": class_session.id,
                "assignment_id": assignment.id,
                "code": class_session.class_code or "------",
                "subject_name": assignment.subject.name,
                "subject_code": assignment.subject.code,
                "class_name": assignment.class_section.name,
                "section": assignment.class_section.section,
                "started_at": (
                    class_session.started_at.strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                    if class_session.started_at
                    else "Not specified"
                ),
                "expires_at": (
                    class_session.code_expires_at.strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                    if class_session.code_expires_at
                    else "Not specified"
                ),
                "status": class_session.status,
            }
        )

    return rows


@teacher_bp.route("/sessions", methods=["GET", "POST"])
@role_required("teacher")
def session_list():
    """Start and display the logged-in teacher's live sessions."""
    teacher = load_teacher_profile()
    assignments = load_teacher_assignments(teacher)
    assignment_ids = [assignment.id for assignment in assignments]

    form = StartClassSessionForm()
    form.teaching_assignment_id.choices = get_teacher_session_choices(
        assignments
    )

    if form.validate_on_submit():
        selected_assignment = next(
            (
                assignment
                for assignment in assignments
                if assignment.id == form.teaching_assignment_id.data
            ),
            None,
        )

        if selected_assignment is None:
            abort(403)

        existing_session = find_active_assignment_session(
            selected_assignment.id
        )

        if existing_session is not None:
            flash(
                (
                    "An active session already exists for this class. "
                    f"Current code: {existing_session.class_code}"
                ),
                "warning",
            )
            return redirect(url_for("teacher.session_list"))

        try:
            class_session = create_class_session(
                teaching_assignment_id=selected_assignment.id,
                teacher_id=teacher.id,
                validity_minutes=form.code_valid_minutes.data,
            )

            save_class_session(class_session)

            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    session_id=class_session.id,
                    action="CLASS_SESSION_STARTED",
                    details=(
                        f"Teacher {teacher.employee_id} started session "
                        f"{class_session.id} for assignment "
                        f"{selected_assignment.id}."
                    ),
                )
            )
            db.session.commit()

            flash(
                (
                    "Class session started successfully. "
                    f"Temporary code: {class_session.class_code}"
                ),
                "success",
            )
            return redirect(url_for("teacher.session_list"))

        except Exception as error:
            db.session.rollback()
            print("START CLASS SESSION ERROR:", error)
            flash(
                (
                    "The class session could not be started. "
                    "Confirm that an active timetable entry exists."
                ),
                "danger",
            )

    return render_template(
        "teacher/sessions.html",
        teacher=teacher,
        form=form,
        end_form=EndClassSessionForm(),
        active_sessions=get_teacher_active_sessions(assignment_ids),
    )


@teacher_bp.post("/sessions/<int:session_id>/end")
@role_required("teacher")
def end_session(session_id: int):
    """End a live session only when it belongs to this teacher."""
    teacher = load_teacher_profile()
    assignment_ids = {
        assignment.id
        for assignment in load_teacher_assignments(teacher)
    }

    class_session = db.get_or_404(ClassSession, session_id)

    if get_session_assignment_id(class_session) not in assignment_ids:
        abort(403)

    form = EndClassSessionForm()
    if not form.validate_on_submit():
        abort(400)

    already_closed = (
        class_session.status in {"CLOSED", "ENDED", "FINALIZED"}
        or class_session.attendance_closed_at is not None
    )
    if already_closed:
        flash("This class session is already closed.", "warning")
        return redirect(url_for("teacher.session_list"))

    try:
        old_code = class_session.class_code or "------"
        end_class_session(class_session)

        db.session.add(
            AuditLog(
                user_id=current_user.id,
                session_id=class_session.id,
                action="CLASS_SESSION_ENDED",
                details=(
                    f"Teacher {teacher.employee_id} ended session "
                    f"{class_session.id} with code {old_code}."
                ),
            )
        )
        db.session.commit()
        flash("The class session was ended successfully.", "success")

    except Exception as error:
        db.session.rollback()
        print("END CLASS SESSION ERROR:", error)
        flash("The class session could not be ended.", "danger")

    return redirect(url_for("teacher.session_list"))


# =========================================================
# Live attendance monitoring, review decisions and history
# =========================================================


def load_owned_session(
    teacher: Teacher,
    session_id: int,
) -> ClassSession:
    """Return a class session only when it belongs to this teacher."""
    class_session = db.get_or_404(ClassSession, session_id)
    assignment = class_session.timetable_entry.assignment

    if assignment.teacher_id != teacher.id:
        abort(403)

    return class_session


def build_session_roster(
    class_session: ClassSession,
) -> list[dict[str, Any]]:
    """Build the enrolled-student live attendance roster."""
    assignment = class_session.timetable_entry.assignment

    enrollments = Enrollment.query.filter_by(
        class_id=assignment.class_id,
        subject_id=assignment.subject_id,
        is_active=True,
    ).all()

    students = sorted(
        {enrollment.student for enrollment in enrollments},
        key=lambda student: student.roll_number,
    )

    attendance_map = {
        attendance.student_id: attendance
        for attendance in Attendance.query.filter_by(
            session_id=class_session.id,
        ).all()
    }

    review_map = {
        review.student_id: review
        for review in ManualReviewRequest.query.filter_by(
            session_id=class_session.id,
        ).all()
    }

    rows: list[dict[str, Any]] = []

    for student in students:
        attendance = attendance_map.get(student.id)
        review = review_map.get(student.id)

        if attendance is not None:
            display_status = attendance.status.replace("_", " ").title()
            status_key = attendance.status.lower()
            method = attendance.method.replace("_", " ").title()
        elif review is not None:
            display_status = review.status.replace("_", " ").title()
            status_key = review.status.lower()
            method = "Manual Review"
        else:
            display_status = "Pending"
            status_key = "pending"
            method = "—"

        rows.append(
            {
                "student": student,
                "attendance": attendance,
                "review": review,
                "status": display_status,
                "status_key": status_key,
                "method": method,
            }
        )

    return rows


def build_session_summary(
    roster_rows: list[dict[str, Any]],
) -> dict[str, int]:
    """Calculate live class attendance counters."""
    summary = {
        "total": len(roster_rows),
        "present": 0,
        "pending": 0,
        "manual_review": 0,
        "rejected": 0,
    }

    for row in roster_rows:
        attendance = row["attendance"]
        review = row["review"]

        if attendance is not None and attendance.status in {
            "PRESENT",
            "LATE",
        }:
            summary["present"] += 1
        elif review is not None and review.status == "PENDING":
            summary["manual_review"] += 1
        elif review is not None and review.status == "REJECTED":
            summary["rejected"] += 1
        else:
            summary["pending"] += 1

    return summary


@teacher_bp.get("/sessions/<int:session_id>")
@role_required("teacher")
def session_detail(session_id: int):
    """Monitor recognized, pending and manual-review students."""
    teacher = load_teacher_profile()
    class_session = load_owned_session(teacher, session_id)
    roster_rows = build_session_roster(class_session)

    return render_template(
        "teacher/session_detail.html",
        teacher=teacher,
        class_session=class_session,
        assignment=class_session.timetable_entry.assignment,
        roster_rows=roster_rows,
        summary=build_session_summary(roster_rows),
        active=is_session_active(class_session),
        display_status=(
            "EXPIRED"
            if (
                class_session.status == "ACTIVE"
                and not is_session_active(class_session)
                and class_session.attendance_closed_at is None
            )
            else class_session.status
        ),
        decision_form=ManualReviewDecisionForm(),
        end_form=EndClassSessionForm(),
        finalize_form=FinalizeClassSessionForm(),
    )


@teacher_bp.post("/manual-reviews/<int:review_id>/decision")
@role_required("teacher")
def manual_review_decision(review_id: int):
    """Approve or reject one exceptional face-verification failure."""
    teacher = load_teacher_profile()
    review = db.get_or_404(ManualReviewRequest, review_id)
    load_owned_session(teacher, review.session_id)

    form = ManualReviewDecisionForm()
    if not form.validate_on_submit():
        abort(400)

    try:
        decide_manual_review(
            review=review,
            teacher=teacher,
            decision=form.decision.data,
            teacher_note=form.teacher_note.data,
            audit_user_id=current_user.id,
        )
        db.session.commit()
        flash(
            f"Manual-review request marked as {review.status.title()}.",
            "success",
        )

    except AttendanceValidationError as error:
        db.session.rollback()
        flash(str(error), "warning")
    except Exception as error:
        db.session.rollback()
        print("MANUAL REVIEW DECISION ERROR:", error)
        flash("The manual-review decision could not be saved.", "danger")

    return redirect(
        url_for("teacher.session_detail", session_id=review.session_id)
    )


@teacher_bp.post("/sessions/<int:session_id>/finalize")
@role_required("teacher")
def finalize_session(session_id: int):
    """Finalize a closed session after all manual reviews are decided."""
    teacher = load_teacher_profile()
    class_session = load_owned_session(teacher, session_id)
    form = FinalizeClassSessionForm()

    if not form.validate_on_submit():
        abort(400)

    pending_count = ManualReviewRequest.query.filter_by(
        session_id=class_session.id,
        status="PENDING",
    ).count()

    if class_session.attendance_closed_at is None:
        flash("Close attendance before finalizing the session.", "warning")
    elif pending_count:
        flash(
            f"Decide {pending_count} pending manual-review request(s) first.",
            "warning",
        )
    elif class_session.status == "FINALIZED":
        flash("This session is already finalized.", "warning")
    else:
        assignment = class_session.timetable_entry.assignment
        enrollments = Enrollment.query.filter_by(
            class_id=assignment.class_id,
            subject_id=assignment.subject_id,
            is_active=True,
        ).all()

        enrolled_students = {
            enrollment.student_id: enrollment.student
            for enrollment in enrollments
        }

        absent_count = 0
        for student in enrolled_students.values():
            existing_attendance = Attendance.query.filter_by(
                session_id=class_session.id,
                student_id=student.id,
            ).first()

            if existing_attendance is not None:
                continue

            record_attendance(
                student=student,
                class_session=class_session,
                status="ABSENT",
                method="SESSION_FINALIZATION",
                notes=(
                    "No verified attendance was recorded before "
                    "the teacher finalized the session."
                ),
                audit_user_id=current_user.id,
                require_active=False,
            )
            absent_count += 1

        class_session.status = "FINALIZED"
        class_session.finalized_at = datetime.now()

        db.session.add(
            AuditLog(
                user_id=current_user.id,
                session_id=class_session.id,
                action="CLASS_SESSION_FINALIZED",
                details=(
                    f"Teacher {teacher.employee_id} finalized session "
                    f"{class_session.id}; {absent_count} missing student "
                    "record(s) were saved as absent."
                ),
            )
        )
        db.session.commit()
        flash(
            (
                "Class session finalized successfully. "
                f"{absent_count} missing attendance record(s) "
                "were marked absent."
            ),
            "success",
        )

    return redirect(
        url_for("teacher.session_detail", session_id=class_session.id)
    )


@teacher_bp.get("/history")
@role_required("teacher")
def session_history():
    """Display all class sessions conducted by the logged-in teacher."""
    teacher = load_teacher_profile()
    assignment_ids = [
        assignment.id
        for assignment in load_teacher_assignments(teacher)
    ]

    sessions = []
    if assignment_ids:
        sessions = (
            ClassSession.query.join(Timetable)
            .filter(Timetable.assignment_id.in_(assignment_ids))
            .order_by(
                ClassSession.session_date.desc(),
                ClassSession.id.desc(),
            )
            .all()
        )

    rows: list[dict[str, Any]] = []
    for class_session in sessions:
        assignment = class_session.timetable_entry.assignment
        rows.append(
            {
                "session": class_session,
                "assignment": assignment,
                "attendance_count": Attendance.query.filter_by(
                    session_id=class_session.id,
                ).count(),
                "pending_reviews": ManualReviewRequest.query.filter_by(
                    session_id=class_session.id,
                    status="PENDING",
                ).count(),
                "active": is_session_active(class_session),
                "display_status": (
                    "EXPIRED"
                    if (
                        class_session.status == "ACTIVE"
                        and not is_session_active(class_session)
                        and class_session.attendance_closed_at is None
                    )
                    else class_session.status
                ),
            }
        )

    return render_template(
        "teacher/history.html",
        teacher=teacher,
        rows=rows,
    )
