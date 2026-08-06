from datetime import date, datetime, timedelta
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session as flask_session,
    url_for,
)
from flask_login import current_user
from sqlalchemy import func

from decorators import role_required
from extensions import db
from forms import (
    FaceCaptureForm,
    JoinClassSessionForm,
    ManualReviewRequestForm,
)
from models import (
    Attendance,
    AuditLog,
    ClassSection,
    ClassSession,
    Enrollment,
    FaceData,
    ManualReviewRequest,
    Student,
    TeachingAssignment,
    Timetable,
)
from services import (
    AttendanceValidationError,
    FaceImageError,
    FaceRecognitionUnavailable,
    get_or_create_manual_review,
    is_session_active,
    record_attendance,
    save_face_sample,
    train_lbph_model,
    validate_student_session,
    verify_student_face,
)


student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/student",
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
# Logged-in student helpers
# =========================================================


def load_student_profile() -> Student:
    """Return the student profile linked to the logged-in account."""
    student = Student.query.filter_by(
        user_id=current_user.id,
    ).first()

    if student is None:
        abort(
            404,
            description=(
                "A student profile is not linked to this login account."
            ),
        )

    return student


def load_student_class(
    student: Student,
) -> ClassSection | None:
    """Return the logged-in student's assigned class section."""
    return db.session.get(ClassSection, student.class_id)


def load_student_enrollments(
    student: Student,
) -> list[Enrollment]:
    """Return active subject enrolments for the student."""
    return Enrollment.query.filter_by(
        student_id=student.id,
        is_active=True,
    ).order_by(
        Enrollment.id.asc(),
    ).all()


def load_student_assignments(
    student: Student,
    enrollments: list[Enrollment],
) -> list[TeachingAssignment]:
    """Resolve active teaching assignments for enrolled subjects."""
    subject_ids = {
        enrollment.subject_id
        for enrollment in enrollments
    }

    query = TeachingAssignment.query.filter_by(
        class_id=student.class_id,
        is_active=True,
    )

    if subject_ids:
        query = query.filter(
            TeachingAssignment.subject_id.in_(subject_ids)
        )

    return query.order_by(
        TeachingAssignment.id.asc(),
    ).all()


def build_subject_rows(
    enrollments: list[Enrollment],
    assignments: list[TeachingAssignment],
) -> list[dict[str, Any]]:
    """Prepare enrolled subjects and assigned teacher names."""
    teachers_by_subject: dict[int, list[str]] = {}

    for assignment in assignments:
        teachers_by_subject.setdefault(
            assignment.subject_id,
            [],
        ).append(assignment.teacher.full_name)

    rows: list[dict[str, Any]] = []

    for enrollment in enrollments:
        class_section = enrollment.class_section
        subject = enrollment.subject
        teacher_names = teachers_by_subject.get(subject.id, [])

        rows.append(
            {
                "id": enrollment.id,
                "subject_id": subject.id,
                "subject_name": subject.name,
                "subject_code": subject.code,
                "teacher_names": teacher_names,
                "teacher_display": (
                    ", ".join(teacher_names)
                    if teacher_names
                    else "Teacher not assigned"
                ),
                "class_name": class_section.name,
                "section": class_section.section,
                "semester": class_section.semester,
                "academic_year": class_section.academic_year,
            }
        )

    return rows


def load_student_timetable(
    assignments: list[TeachingAssignment],
) -> list[dict[str, Any]]:
    """Return the student's complete active weekly timetable."""
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
                "teacher_name": assignment.teacher.full_name,
                "class_name": assignment.class_section.name,
                "section": assignment.class_section.section,
            }
        )

    return rows


def group_timetable_by_day(
    timetable_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group a student's timetable from Monday to Saturday."""
    grouped = {
        day_name: []
        for day_name in WEEK_DAYS
    }

    for row in timetable_rows:
        grouped.setdefault(row["day"], []).append(row)

    return grouped


def load_active_student_sessions(
    assignments: list[TeachingAssignment],
) -> list[dict[str, Any]]:
    """Return active class sessions belonging to the student's section."""
    assignment_ids = [assignment.id for assignment in assignments]
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
                "subject_name": assignment.subject.name,
                "subject_code": assignment.subject.code,
                "teacher_name": assignment.teacher.full_name,
                "section": assignment.class_section.section,
                "expires_at": (
                    class_session.code_expires_at.strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                    if class_session.code_expires_at
                    else "Not specified"
                ),
            }
        )

    return rows


# =========================================================
# Student attendance helpers
# =========================================================


def load_student_attendance(
    student: Student,
) -> list[Attendance]:
    """Return attendance records belonging only to this student."""
    return Attendance.query.filter_by(
        student_id=student.id,
    ).order_by(
        Attendance.recorded_at.desc(),
        Attendance.id.desc(),
    ).all()


def build_attendance_summary(
    records: list[Attendance],
) -> dict[str, Any]:
    """Calculate the student's overall attendance summary."""
    summary: dict[str, Any] = {
        "total": len(records),
        "present": 0,
        "absent": 0,
        "late": 0,
        "excused": 0,
        "pending": 0,
        "percentage": 0.0,
    }

    for record in records:
        status = record.status.strip().lower()
        if status in summary:
            summary[status] += 1
        else:
            summary["pending"] += 1

    attended = summary["present"] + summary["late"]

    if summary["total"]:
        summary["percentage"] = round(
            attended / summary["total"] * 100,
            1,
        )

    return summary


def _attendance_assignment(record: Attendance):
    class_session = record.class_session
    timetable_entry = (
        class_session.timetable_entry
        if class_session
        else None
    )
    return (
        timetable_entry.assignment
        if timetable_entry
        else None
    )


def build_subject_attendance(
    records: list[Attendance],
) -> list[dict[str, Any]]:
    """Calculate subject-wise attendance percentages."""
    grouped: dict[int, dict[str, Any]] = {}

    for record in records:
        assignment = _attendance_assignment(record)
        if assignment is None:
            continue

        subject = assignment.subject
        row = grouped.setdefault(
            subject.id,
            {
                "subject_name": subject.name,
                "subject_code": subject.code,
                "total": 0,
                "present": 0,
                "late": 0,
                "absent": 0,
                "excused": 0,
                "percentage": 0.0,
            },
        )

        row["total"] += 1
        status = record.status.strip().lower()
        if status in row:
            row[status] += 1

    for row in grouped.values():
        attended = row["present"] + row["late"]
        if row["total"]:
            row["percentage"] = round(
                attended / row["total"] * 100,
                1,
            )

    return sorted(
        grouped.values(),
        key=lambda row: row["subject_code"],
    )


def build_attendance_rows(
    records: list[Attendance],
) -> list[dict[str, Any]]:
    """Prepare readable student-attendance history rows."""
    rows: list[dict[str, Any]] = []

    for record in records:
        class_session = record.class_session
        timetable_entry = (
            class_session.timetable_entry
            if class_session
            else None
        )
        assignment = (
            timetable_entry.assignment
            if timetable_entry
            else None
        )

        rows.append(
            {
                "id": record.id,
                "date": (
                    class_session.session_date.strftime("%d %b %Y")
                    if class_session
                    else record.recorded_at.strftime("%d %b %Y")
                ),
                "subject_name": (
                    assignment.subject.name
                    if assignment
                    else "Unknown Subject"
                ),
                "subject_code": (
                    assignment.subject.code
                    if assignment
                    else "—"
                ),
                "teacher_name": (
                    assignment.teacher.full_name
                    if assignment
                    else "Unknown Teacher"
                ),
                "time": (
                    (
                        f"{timetable_entry.start_time.strftime('%I:%M %p')} "
                        f"to {timetable_entry.end_time.strftime('%I:%M %p')}"
                    )
                    if timetable_entry
                    else "Not specified"
                ),
                "status": record.status.replace("_", " ").title(),
                "status_key": record.status.lower(),
                "method": record.method.replace("_", " ").title(),
                "confidence": (
                    f"{record.recognition_confidence:.1f}%"
                    if record.recognition_confidence is not None
                    else "—"
                ),
                "notes": record.notes or "—",
            }
        )

    return rows


def get_pending_class_session(
    student: Student,
) -> ClassSession:
    """Return and revalidate the class selected by the student."""
    class_session_id = flask_session.get("pending_class_session_id")
    if not class_session_id:
        raise AttendanceValidationError(
            "Enter a valid temporary class code before face verification."
        )

    class_session = db.session.get(ClassSession, class_session_id)
    if class_session is None:
        flask_session.pop("pending_class_session_id", None)
        raise AttendanceValidationError("The selected class session no longer exists.")

    validate_student_session(student, class_session)
    return class_session


# =========================================================
# Student dashboards and personal pages
# =========================================================


@student_bp.get("/dashboard")
@role_required("student")
def dashboard():
    """Display only the logged-in student's own information."""
    student = load_student_profile()
    class_section = load_student_class(student)
    enrollments = load_student_enrollments(student)
    assignments = load_student_assignments(student, enrollments)
    subject_rows = build_subject_rows(enrollments, assignments)
    timetable_rows = load_student_timetable(assignments)
    attendance_records = load_student_attendance(student)
    attendance_summary = build_attendance_summary(attendance_records)

    today_name = datetime.now().strftime("%A")
    today_timetable = [
        row
        for row in timetable_rows
        if row["day"] == today_name
    ]

    threshold = current_app.config["ATTENDANCE_THRESHOLD"]

    return render_template(
        "student/dashboard.html",
        student=student,
        class_section=class_section,
        subjects=subject_rows,
        today_timetable=today_timetable,
        weekly_timetable=group_timetable_by_day(timetable_rows),
        week_days=WEEK_DAYS,
        today_name=today_name,
        attendance=attendance_summary,
        attendance_threshold=threshold,
        low_attendance=(
            attendance_summary["total"] > 0
            and attendance_summary["percentage"] < threshold
        ),
        active_sessions=load_active_student_sessions(assignments),
    )


@student_bp.get("/profile")
@role_required("student")
def profile():
    """Display the logged-in student's profile only."""
    student = load_student_profile()
    class_section = load_student_class(student)
    attendance_records = load_student_attendance(student)

    return render_template(
        "student/profile.html",
        student=student,
        class_section=class_section,
        attendance=build_attendance_summary(attendance_records),
        face_data=student.face_data,
    )


@student_bp.get("/course")
@role_required("student")
def course_section():
    """Display the student's assigned course and section."""
    student = load_student_profile()
    class_section = load_student_class(student)

    return render_template(
        "student/course.html",
        student=student,
        class_section=class_section,
    )


@student_bp.get("/subjects")
@role_required("student")
def subject_list():
    """Display only subjects assigned to the logged-in student."""
    student = load_student_profile()
    class_section = load_student_class(student)
    enrollments = load_student_enrollments(student)
    assignments = load_student_assignments(student, enrollments)

    return render_template(
        "student/subjects.html",
        student=student,
        class_section=class_section,
        subjects=build_subject_rows(enrollments, assignments),
    )


@student_bp.get("/timetable")
@role_required("student")
def timetable():
    """Display the student's complete weekly section timetable."""
    student = load_student_profile()
    class_section = load_student_class(student)
    enrollments = load_student_enrollments(student)
    assignments = load_student_assignments(student, enrollments)
    timetable_rows = load_student_timetable(assignments)

    return render_template(
        "student/timetable.html",
        student=student,
        class_section=class_section,
        week_days=WEEK_DAYS,
        week_dates=build_current_week_dates(),
        weekly_timetable=group_timetable_by_day(timetable_rows),
        total_classes=len(timetable_rows),
    )


@student_bp.get("/attendance")
@role_required("student")
def attendance():
    """Display personal overall and subject-wise attendance history."""
    student = load_student_profile()
    records = load_student_attendance(student)
    summary = build_attendance_summary(records)
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]

    return render_template(
        "student/attendance.html",
        student=student,
        attendance_rows=build_attendance_rows(records),
        attendance=summary,
        subject_attendance=build_subject_attendance(records),
        attendance_threshold=threshold,
        low_attendance=(
            summary["total"] > 0
            and summary["percentage"] < threshold
        ),
    )


@student_bp.get("/face-recognition")
@role_required("student")
def face_recognition_center():
    """Display the logged-in student's local face-recognition center."""
    student = load_student_profile()
    face_data = student.face_data
    target = int(current_app.config["FACE_SAMPLE_TARGET"])
    stored_sample_count = face_data.sample_count if face_data else 0
    sample_count = min(stored_sample_count, target)

    return render_template(
        "student/face_recognition.html",
        student=student,
        face_data=face_data,
        sample_count=sample_count,
        target=target,
        progress=(
            min(100, round(sample_count / target * 100))
            if target
            else 0
        ),
        registered=bool(student.face_registered),
        trained=bool(face_data and face_data.is_trained),
        model_exists=current_app.config["FACE_MODEL_PATH"].exists(),
    )


# =========================================================
# Dynamic-code, face verification and manual review
# =========================================================


@student_bp.route("/join", methods=["GET", "POST"])
@role_required("student")
def join_class():
    """Validate a temporary class code without marking attendance."""
    student = load_student_profile()
    form = JoinClassSessionForm()

    if form.validate_on_submit():
        class_session = ClassSession.query.filter(
            func.upper(ClassSession.class_code)
            == form.class_code.data.upper()
        ).first()

        if class_session is None:
            form.class_code.errors.append(
                "The temporary class code is invalid."
            )
        else:
            try:
                validate_student_session(student, class_session)
                flask_session["pending_class_session_id"] = class_session.id
                flask_session.pop("face_failure_reason", None)

                flash(
                    "Class code accepted. Complete face verification next.",
                    "success",
                )
                return redirect(url_for("student.verify_face"))

            except AttendanceValidationError as error:
                form.class_code.errors.append(str(error))

    return render_template(
        "student/join_class.html",
        student=student,
        form=form,
    )


@student_bp.route("/face/register", methods=["GET", "POST"])
@role_required("student")
def register_face():
    """Register the logged-in student's face using local camera samples."""
    student = load_student_profile()
    form = FaceCaptureForm()
    target = int(current_app.config["FACE_SAMPLE_TARGET"])
    face_data = student.face_data
    stored_sample_count = face_data.sample_count if face_data else 0

    if request.method == "POST" and stored_sample_count >= target:
        flash(
            "Face registration already has the required "
            f"{target} samples. No additional sample was saved.",
            "info",
        )
        return redirect(url_for("student.register_face"))

    if form.validate_on_submit():
        try:
            dataset_path, sample_count = save_face_sample(
                student.id,
                form.image_data.data,
            )

            if face_data is None:
                face_data = FaceData(
                    student_id=student.id,
                    recognition_label=student.id,
                    dataset_path=str(
                        current_app.config["FACE_DATA_DIR"]
                        / f"student_{student.id}"
                    ),
                )
                db.session.add(face_data)

            sample_count = min(sample_count, target)
            face_data.sample_count = sample_count

            if sample_count >= target:
                image_count, student_count = train_lbph_model()
                student.face_registered = True
                face_data.is_trained = True
                face_data.last_trained_at = datetime.now()

                db.session.add(
                    AuditLog(
                        user_id=current_user.id,
                        student_id=student.id,
                        action="FACE_REGISTRATION_COMPLETED",
                        details=(
                            f"Local LBPH model trained with {image_count} "
                            f"samples for {student_count} students."
                        ),
                    )
                )
                flash(
                    "Face registration completed and the local model was trained.",
                    "success",
                )
            else:
                flash(
                    f"Face sample saved ({sample_count}/{target}). "
                    "Capture more samples from slightly different angles.",
                    "success",
                )

            db.session.commit()
            return redirect(url_for("student.register_face"))

        except (FaceImageError, FaceRecognitionUnavailable) as error:
            db.session.rollback()
            flash(str(error), "danger")
        except Exception as error:
            db.session.rollback()
            print("FACE REGISTRATION ERROR:", error)
            flash("The face sample could not be saved.", "danger")

    elif request.method == "POST":
        errors = [
            message
            for field_errors in form.errors.values()
            for message in field_errors
        ]
        flash(
            errors[0] if errors else "No captured camera image was submitted.",
            "danger",
        )

    stored_sample_count = face_data.sample_count if face_data else 0
    sample_count = min(stored_sample_count, target)

    return render_template(
        "student/face_register.html",
        student=student,
        form=form,
        sample_count=sample_count,
        target=target,
        progress=min(100, round(sample_count / target * 100)) if target else 0,
        trained=bool(face_data and face_data.is_trained),
    )


@student_bp.route("/face/verify", methods=["GET", "POST"])
@role_required("student")
def verify_face():
    """Verify the logged-in student before recording attendance."""
    student = load_student_profile()

    try:
        class_session = get_pending_class_session(student)
    except AttendanceValidationError as error:
        flash(str(error), "warning")
        return redirect(url_for("student.join_class"))

    assignment = class_session.timetable_entry.assignment
    form = FaceCaptureForm()

    if form.validate_on_submit():
        try:
            result = verify_student_face(
                expected_student_id=student.id,
                image_data=form.image_data.data,
            )

            if result.matched:
                record_attendance(
                    student=student,
                    class_session=class_session,
                    status="PRESENT",
                    method="FACE_RECOGNITION",
                    recognition_confidence=result.similarity_score,
                    notes=(
                        "Verified with local LBPH face recognition. "
                        f"LBPH distance: {result.distance}."
                    ),
                    audit_user_id=current_user.id,
                )
                db.session.commit()

                flask_session.pop("pending_class_session_id", None)
                flask_session.pop("face_failure_reason", None)

                return render_template(
                    "student/verification_result.html",
                    success=True,
                    title="Attendance Recorded",
                    message=(
                        "Your face matched your logged-in student account."
                    ),
                    assignment=assignment,
                    class_session=class_session,
                    similarity_score=result.similarity_score,
                )

            flask_session["face_failure_reason"] = result.reason
            flash(
                "Face verification failed. Retry or request manual review.",
                "warning",
            )
            return redirect(url_for("student.manual_review"))

        except FaceImageError as error:
            flash(str(error), "danger")
        except FaceRecognitionUnavailable as error:
            flask_session["face_failure_reason"] = str(error)
            flash(
                "Automatic face verification is unavailable. "
                "Submit a manual-review request.",
                "warning",
            )
            return redirect(url_for("student.manual_review"))
        except AttendanceValidationError as error:
            db.session.rollback()
            flash(str(error), "warning")
            return redirect(url_for("student.attendance"))
        except Exception as error:
            db.session.rollback()
            print("FACE VERIFICATION ERROR:", error)
            flash("Face verification could not be completed.", "danger")

    return render_template(
        "student/face_verify.html",
        student=student,
        form=form,
        assignment=assignment,
        class_session=class_session,
        face_registered=student.face_registered,
    )


@student_bp.route("/manual-review", methods=["GET", "POST"])
@role_required("student")
def manual_review():
    """Submit a fallback request after face verification failure."""
    student = load_student_profile()

    try:
        class_session = get_pending_class_session(student)
    except AttendanceValidationError as error:
        flash(str(error), "warning")
        return redirect(url_for("student.join_class"))

    assignment = class_session.timetable_entry.assignment
    failure_reason = flask_session.get("face_failure_reason")

    # Manual review is a fallback only after an actual face-verification
    # failure or when the local recognition service is unavailable.
    if not failure_reason:
        flash(
            "Attempt face verification before requesting manual review.",
            "warning",
        )
        return redirect(url_for("student.verify_face"))

    form = ManualReviewRequestForm()

    existing_review = ManualReviewRequest.query.filter_by(
        session_id=class_session.id,
        student_id=student.id,
    ).first()

    if form.validate_on_submit():
        try:
            review = get_or_create_manual_review(
                student=student,
                class_session=class_session,
                failure_reason=failure_reason,
                student_note=form.student_note.data,
                audit_user_id=current_user.id,
            )
            db.session.commit()

            flask_session.pop("pending_class_session_id", None)
            flask_session.pop("face_failure_reason", None)

            return render_template(
                "student/verification_result.html",
                success=False,
                title="Manual Review Requested",
                message=(
                    "Your request is pending. The assigned teacher can "
                    "approve or reject it from the live session dashboard."
                ),
                assignment=assignment,
                class_session=class_session,
                review=review,
                similarity_score=None,
            )

        except AttendanceValidationError as error:
            db.session.rollback()
            flash(str(error), "warning")
            return redirect(url_for("student.attendance"))
        except Exception as error:
            db.session.rollback()
            print("MANUAL REVIEW REQUEST ERROR:", error)
            flash("The manual-review request could not be submitted.", "danger")

    return render_template(
        "student/manual_review.html",
        student=student,
        form=form,
        assignment=assignment,
        class_session=class_session,
        failure_reason=failure_reason,
        existing_review=existing_review,
    )
