from datetime import date, timedelta
import csv
import io

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy import func


from decorators import role_required
from extensions import db
from forms import (
    AddClassSectionForm,
    AddStudentForm,
    AddSubjectForm,
    AddTeacherForm,
    AddTimetableForm,
    EditClassSectionForm,
    EditStudentForm,
    EditSubjectForm,
    EditTeacherForm,
    EditTimetableForm,
    TeacherAttendanceForm,
    AttendanceCorrectionForm,
    TeachingAssignmentForm,
)
from models import (
     Attendance,
     AuditLog,
     ClassSession,
     Enrollment,
     ManualReviewRequest,
     ClassSection,
     Student, 
     Subject, 
     TeachingAssignment,
     Timetable,
     Teacher,
     TeacherAttendance,
     User,

)        


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


def _current_week_dates() -> dict[str, date]:
    """Map Monday-to-Sunday names to dates in the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    return {
        day_name: monday + timedelta(days=day_index)
        for day_index, day_name in enumerate(
            [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
        )
    }


def get_class_choices() -> list[tuple[int, str]]:
    """Return class-section choices for admin forms."""
    class_sections = ClassSection.query.order_by(
        ClassSection.name.asc(),
        ClassSection.section.asc(),
    ).all()

    return [
        (
            class_section.id,
            (
                f"{class_section.course} · {class_section.name} "
                f"· {class_section.group_name} · "
                f"Section {class_section.section} "
                f"— Semester {class_section.semester}"
            ),
        )
        for class_section in class_sections
    ]
@admin_bp.route(
    "/classes/<int:class_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_class(class_id: int):
    """Update an existing academic class section."""
    class_section = db.get_or_404(ClassSection, class_id)
    form = EditClassSectionForm()

    if request.method == "GET":
        form.course.data = class_section.course
        form.name.data = class_section.name
        form.section.data = class_section.section
        form.semester.data = class_section.semester
        form.academic_year.data = class_section.academic_year
        form.group_name.data = class_section.group_name
        form.is_active.data = class_section.is_active

    if form.validate_on_submit():
        course = form.course.data.strip()
        course = form.course.data.strip()
        class_name = form.name.data.strip().upper()
        section = form.section.data.strip().upper()
        semester = form.semester.data
        academic_year = form.academic_year.data.strip()
        group_name = form.group_name.data.strip().upper()
        group_name = form.group_name.data.strip().upper()

        duplicate_class = ClassSection.query.filter(
            func.lower(ClassSection.name) == class_name.lower(),
            func.lower(ClassSection.section) == section.lower(),
            ClassSection.semester == semester,
            func.lower(ClassSection.academic_year)
            == academic_year.lower(),
            ClassSection.id != class_section.id,
        ).first()

        if duplicate_class:
            form.name.errors.append(
                (
                    "This class section already exists for the "
                    "selected semester and academic year."
                )
            )

        form_has_errors = any(field.errors for field in form)

        if not form_has_errors:
            try:
                old_description = (
                    f"{class_section.name} "
                    f"Section {class_section.section}, "
                    f"Semester {class_section.semester}, "
                    f"{class_section.academic_year}"
                )

                class_section.course = course
                class_section.name = class_name
                class_section.section = section
                class_section.semester = semester
                class_section.academic_year = academic_year
                class_section.group_name = group_name
                class_section.is_active = form.is_active.data

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="CLASS_SECTION_UPDATED",
                    details=(
                        f"Class section {old_description} was updated "
                        f"to {class_name} Section {section}, "
                        f"Semester {semester}, {academic_year}."
                    ),
                )

                db.session.add(audit_log)
                db.session.commit()

                flash(
                    (
                        f"{class_section.name} Section "
                        f"{class_section.section} was updated "
                        "successfully."
                    ),
                    "success",
                )

                return redirect(url_for("admin.class_list"))

            except Exception as error:
                db.session.rollback()

                print("EDIT CLASS ERROR:", error)

                flash(
                    (
                        "The class section could not be updated. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/edit_class.html",
        form=form,
        class_section=class_section,
    )

@admin_bp.get("/dashboard")
@role_required("admin")
def dashboard():
    """Display the administrator dashboard with database totals."""
    dashboard_totals = {
        "students": Student.query.count(),
        "teachers": Teacher.query.count(),
        "subjects": Subject.query.count(),
        "classes": ClassSection.query.count(),
    }

    return render_template(
        "admin/dashboard.html",
        totals=dashboard_totals,
    )


@admin_bp.get("/students")
@role_required("admin")
def student_list():
    """Display all student profiles."""
    students = Student.query.order_by(
        Student.roll_number.asc()
    ).all()

    return render_template(
        "admin/students.html",
        students=students,
    )


@admin_bp.route(
    "/students/add",
    methods=["GET", "POST"],
)
@role_required("admin")
def add_student():
    """Create a student login account and academic profile."""
    form = AddStudentForm()
    form.class_id.choices = get_class_choices()

    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        roll_number = form.roll_number.data.strip().upper()
        full_name = form.full_name.data.strip()

        email = (
            form.email.data.strip().lower()
            if form.email.data
            else None
        )
        phone = form.phone.data.strip() if form.phone.data else None

        existing_username = User.query.filter(
            func.lower(User.username) == username
        ).first()

        if existing_username:
            form.username.errors.append(
                "This username is already in use."
            )

        existing_roll_number = Student.query.filter(
            func.lower(Student.roll_number)
            == roll_number.lower()
        ).first()

        if existing_roll_number:
            form.roll_number.errors.append(
                "This roll number is already registered."
            )

        if email:
            existing_email = Student.query.filter(
                func.lower(Student.email) == email
            ).first()

            if existing_email:
                form.email.errors.append(
                    "This email is already registered."
                )

        selected_class = db.session.get(
            ClassSection,
            form.class_id.data,
        )

        if selected_class is None:
            form.class_id.errors.append(
                "Please select a valid class section."
            )

        form_has_errors = any(
            field.errors
            for field in form
        )

        if not form_has_errors:
            try:
                user = User(
                    username=username,
                    role="student",
                    is_active=form.is_active.data,
                )

                user.set_password(form.password.data)

                student = Student(
                    user=user,
                    class_section=selected_class,
                    roll_number=roll_number,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    face_registered=False,
                )

                db.session.add(user)
                db.session.add(student)
                db.session.flush()
                _sync_student_enrollments(student)
                db.session.commit()

                flash(
                    f"Student {full_name} was added successfully.",
                    "success",
                )

                return redirect(
                    url_for("admin.student_list")
                )

            except Exception:
                db.session.rollback()

                flash(
                    (
                        "The student could not be added. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/add_student.html",
        form=form,
        class_count=len(form.class_id.choices),
    )


@admin_bp.route(
    "/students/<int:student_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_student(student_id: int):
    """Update a student account and academic profile."""
    student = db.get_or_404(Student, student_id)

    if student.user is None:
        flash(
            "The selected student does not have a valid user account.",
            "danger",
        )
        return redirect(url_for("admin.student_list"))

    form = EditStudentForm()
    form.class_id.choices = get_class_choices()

    if request.method == "GET":
        form.username.data = student.user.username
        form.roll_number.data = student.roll_number
        form.full_name.data = student.full_name
        form.email.data = student.email
        form.phone.data = student.phone
        form.class_id.data = student.class_id
        form.is_active.data = student.user.is_active

    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        roll_number = form.roll_number.data.strip().upper()
        full_name = form.full_name.data.strip()

        email = (
            form.email.data.strip().lower()
            if form.email.data
            else None
        )
        phone = form.phone.data.strip() if form.phone.data else None

        existing_username = User.query.filter(
            func.lower(User.username) == username,
            User.id != student.user_id,
        ).first()

        if existing_username:
            form.username.errors.append(
                "This username is already in use."
            )

        existing_roll_number = Student.query.filter(
            func.lower(Student.roll_number)
            == roll_number.lower(),
            Student.id != student.id,
        ).first()

        if existing_roll_number:
            form.roll_number.errors.append(
                "This roll number is already registered."
            )

        if email:
            existing_email = Student.query.filter(
                func.lower(Student.email) == email,
                Student.id != student.id,
            ).first()

            if existing_email:
                form.email.errors.append(
                    "This email is already registered."
                )

        selected_class = db.session.get(
            ClassSection,
            form.class_id.data,
        )

        if selected_class is None:
            form.class_id.errors.append(
                "Please select a valid class section."
            )

        form_has_errors = any(
            field.errors
            for field in form
        )

        if not form_has_errors:
            try:
                old_class_id = student.class_id
                student.user.username = username
                student.user.is_active = form.is_active.data

                student.roll_number = roll_number
                student.full_name = full_name
                student.email = email
                student.phone = phone
                student.class_section = selected_class

                if form.new_password.data:
                    student.user.set_password(
                        form.new_password.data
                    )

                if old_class_id != selected_class.id:
                    for enrollment in student.enrollments:
                        enrollment.is_active = False
                    db.session.flush()
                _sync_student_enrollments(student)

                db.session.commit()

                flash(
                    (
                        f"Student {student.full_name} "
                        "was updated successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for("admin.student_list")
                )

            except Exception:
                db.session.rollback()

                flash(
                    (
                        "The student could not be updated. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/edit_student.html",
        form=form,
        student=student,
    )
@admin_bp.post(
    "/students/<int:student_id>/toggle-status"
)
@role_required("admin")
def toggle_student_status(student_id: int):
    """Activate or deactivate a student login account."""
    student = db.get_or_404(Student, student_id)

    if student.user is None:
        flash(
            "The selected student does not have a valid user account.",
            "danger",
        )
        return redirect(url_for("admin.student_list"))

    try:
        student.user.is_active = not student.user.is_active

        status_text = (
            "activated"
            if student.user.is_active
            else "deactivated"
        )

        audit_log = AuditLog(
            user_id=current_user.id,
            student_id=student.id,
            action="STUDENT_ACCOUNT_STATUS_CHANGED",
            details=(
                f"Student account {student.user.username} "
                f"was {status_text} by the administrator."
            ),
        )

        db.session.add(audit_log)
        db.session.commit()

        flash(
            (
                f"Student {student.full_name} was "
                f"{status_text} successfully."
            ),
            "success",
        )

    except Exception:
        db.session.rollback()

        flash(
            "The student account status could not be changed.",
            "danger",
        )

    return redirect(url_for("admin.student_list"))
@admin_bp.get("/teachers")
@role_required("admin")
def teacher_list():
    """Display all teacher accounts and academic profiles."""
    teachers = Teacher.query.order_by(
        Teacher.employee_id.asc()
    ).all()

    return render_template(
        "admin/teachers.html",
        teachers=teachers,
    )
@admin_bp.route(
    "/teachers/add",
    methods=["GET", "POST"],
)
@role_required("admin")
def add_teacher():
    """Create a teacher login account and teacher profile."""
    form = AddTeacherForm()

    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        employee_id = form.employee_id.data.strip().upper()
        full_name = form.full_name.data.strip()
        department = form.department.data.strip()
        designation = form.designation.data
        phone = form.phone.data.strip() if form.phone.data else None
        joining_date = form.joining_date.data

        email = (
            form.email.data.strip().lower()
            if form.email.data
            else None
        )

        existing_username = User.query.filter(
            func.lower(User.username) == username
        ).first()

        if existing_username:
            form.username.errors.append(
                "This username is already in use."
            )

        existing_employee_id = Teacher.query.filter(
            func.lower(Teacher.employee_id)
            == employee_id.lower()
        ).first()

        if existing_employee_id:
            form.employee_id.errors.append(
                "This employee ID is already registered."
            )

        if email:
            existing_email = Teacher.query.filter(
                func.lower(Teacher.email) == email
            ).first()

            if existing_email:
                form.email.errors.append(
                    "This email is already registered."
                )

        form_has_errors = any(
            field.errors
            for field in form
        )

        if not form_has_errors:
            try:
                teacher_user = User(
                    username=username,
                    role="teacher",
                    is_active=form.is_active.data,
                )

                teacher_user.set_password(
                    form.password.data
                )

                teacher = Teacher(
                    user=teacher_user,
                    employee_id=employee_id,
                    full_name=full_name,
                    email=email,
                    department=department,
                    designation=designation,
                    phone=phone,
                    joining_date=joining_date,
                )

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="TEACHER_CREATED",
                    details=(
                        f"Teacher account {username} "
                        f"with employee ID {employee_id} "
                        "was created by the administrator."
                    ),
                )

                db.session.add(teacher_user)
                db.session.add(teacher)
                db.session.add(audit_log)
                db.session.commit()

                flash(
                    (
                        f"Teacher {full_name} "
                        "was added successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for("admin.teacher_list")
                )

            except Exception:
                db.session.rollback()

                flash(
                    (
                        "The teacher could not be added. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/add_teacher.html",
        form=form,
    )
@admin_bp.route(
    "/teachers/<int:teacher_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_teacher(teacher_id: int):
    """Update a teacher account and academic profile."""
    teacher = db.get_or_404(Teacher, teacher_id)

    if teacher.user is None:
        flash(
            "The selected teacher does not have a valid user account.",
            "danger",
        )
        return redirect(url_for("admin.teacher_list"))

    form = EditTeacherForm()

    if request.method == "GET":
        form.username.data = teacher.user.username
        form.employee_id.data = teacher.employee_id
        form.full_name.data = teacher.full_name
        form.email.data = teacher.email
        form.department.data = teacher.department
        form.designation.data = teacher.designation
        form.phone.data = teacher.phone
        form.joining_date.data = teacher.joining_date
        form.is_active.data = teacher.user.is_active

    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        employee_id = form.employee_id.data.strip().upper()
        full_name = form.full_name.data.strip()
        department = form.department.data.strip()
        designation = form.designation.data
        phone = form.phone.data.strip() if form.phone.data else None
        joining_date = form.joining_date.data

        email = (
            form.email.data.strip().lower()
            if form.email.data
            else None
        )

        existing_username = User.query.filter(
            func.lower(User.username) == username,
            User.id != teacher.user_id,
        ).first()

        if existing_username:
            form.username.errors.append(
                "This username is already in use."
            )

        existing_employee_id = Teacher.query.filter(
            func.lower(Teacher.employee_id)
            == employee_id.lower(),
            Teacher.id != teacher.id,
        ).first()

        if existing_employee_id:
            form.employee_id.errors.append(
                "This employee ID is already registered."
            )

        if email:
            existing_email = Teacher.query.filter(
                func.lower(Teacher.email) == email,
                Teacher.id != teacher.id,
            ).first()

            if existing_email:
                form.email.errors.append(
                    "This email is already registered."
                )

        form_has_errors = any(
            field.errors
            for field in form
        )

        if not form_has_errors:
            try:
                old_username = teacher.user.username

                teacher.user.username = username
                teacher.user.is_active = form.is_active.data

                teacher.employee_id = employee_id
                teacher.full_name = full_name
                teacher.email = email
                teacher.department = department
                teacher.designation = designation
                teacher.phone = phone
                teacher.joining_date = joining_date

                if form.new_password.data:
                    teacher.user.set_password(
                        form.new_password.data
                    )

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="TEACHER_UPDATED",
                    details=(
                        f"Teacher account {old_username} "
                        f"was updated. Current username: {username}, "
                        f"employee ID: {employee_id}."
                    ),
                )

                db.session.add(audit_log)
                db.session.commit()

                flash(
                    (
                        f"Teacher {teacher.full_name} "
                        "was updated successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for("admin.teacher_list")
                )

            except Exception as error:
                db.session.rollback()

                print("EDIT TEACHER ERROR:", error)

                flash(
                    (
                        "The teacher could not be updated. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/edit_teacher.html",
        form=form,
        teacher=teacher,
    )
@admin_bp.get("/subjects")
@role_required("admin")
def subject_list():
    """Display all academic subjects."""
    subjects = Subject.query.order_by(
        Subject.semester.asc(),
        Subject.code.asc(),
    ).all()

    return render_template(
        "admin/subjects.html",
        subjects=subjects,
    )
@admin_bp.route(
    "/subjects/add",
    methods=["GET", "POST"],
)
@role_required("admin")
def add_subject():
    """Create a new academic subject."""
    form = AddSubjectForm()

    if form.validate_on_submit():
        subject_name = form.name.data.strip()
        subject_code = form.code.data.strip().upper()

        existing_code = Subject.query.filter(
            func.lower(Subject.code)
            == subject_code.lower()
        ).first()

        if existing_code:
            form.code.errors.append(
                "This subject code is already registered."
            )

        duplicate_subject = Subject.query.filter(
            func.lower(Subject.name)
            == subject_name.lower(),
            Subject.semester == form.semester.data,
        ).first()

        if duplicate_subject:
            form.name.errors.append(
                (
                    "A subject with this name already exists "
                    "in the selected semester."
                )
            )

        form_has_errors = any(
            field.errors
            for field in form
        )

        if not form_has_errors:
            try:
                subject = Subject(
                    name=subject_name,
                    code=subject_code,
                    semester=form.semester.data,
                    is_active=form.is_active.data,
                )

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="SUBJECT_CREATED",
                    details=(
                        f"Subject {subject_code} — {subject_name} "
                        f"was created for semester "
                        f"{form.semester.data}."
                    ),
                )

                db.session.add(subject)
                db.session.add(audit_log)
                db.session.commit()

                flash(
                    (
                        f"Subject {subject_code} — "
                        f"{subject_name} was added successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for("admin.subject_list")
                )

            except Exception as error:
                db.session.rollback()

                print("ADD SUBJECT ERROR:", error)

                flash(
                    (
                        "The subject could not be added. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/add_subject.html",
        form=form,
    )
@admin_bp.route(
    "/subjects/<int:subject_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_subject(subject_id: int):
    """Update an existing academic subject."""
    subject = db.get_or_404(Subject, subject_id)
    form = EditSubjectForm()

    if request.method == "GET":
        form.name.data = subject.name
        form.code.data = subject.code
        form.semester.data = subject.semester
        form.is_active.data = subject.is_active

    if form.validate_on_submit():
        subject_name = form.name.data.strip()
        subject_code = form.code.data.strip().upper()
        semester = form.semester.data

        existing_code = Subject.query.filter(
            func.lower(Subject.code) == subject_code.lower(),
            Subject.id != subject.id,
        ).first()

        if existing_code:
            form.code.errors.append(
                "This subject code is already registered."
            )

        duplicate_subject = Subject.query.filter(
            func.lower(Subject.name) == subject_name.lower(),
            Subject.semester == semester,
            Subject.id != subject.id,
        ).first()

        if duplicate_subject:
            form.name.errors.append(
                (
                    "A subject with this name already exists "
                    "in the selected semester."
                )
            )

        form_has_errors = any(
            field.errors
            for field in form
        )

        if not form_has_errors:
            try:
                old_code = subject.code
                old_name = subject.name

                subject.name = subject_name
                subject.code = subject_code
                subject.semester = semester
                subject.is_active = form.is_active.data

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="SUBJECT_UPDATED",
                    details=(
                        f"Subject {old_code} — {old_name} "
                        f"was updated to {subject_code} — "
                        f"{subject_name}, semester {semester}."
                    ),
                )

                db.session.add(audit_log)
                db.session.commit()

                flash(
                    (
                        f"Subject {subject.code} — "
                        f"{subject.name} was updated successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for("admin.subject_list")
                )

            except Exception as error:
                db.session.rollback()

                print("EDIT SUBJECT ERROR:", error)

                flash(
                    (
                        "The subject could not be updated. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/edit_subject.html",
        form=form,
        subject=subject,
    )
@admin_bp.get("/classes")
@role_required("admin")
def class_list():
    """Display all registered class sections."""
    class_sections = ClassSection.query.order_by(
        ClassSection.academic_year.desc(),
        ClassSection.semester.asc(),
        ClassSection.name.asc(),
        ClassSection.section.asc(),
    ).all()

    return render_template(
        "admin/classes.html",
        class_sections=class_sections,
    )
@admin_bp.route(
    "/classes/add",
    methods=["GET", "POST"],
)
@role_required("admin")
def add_class():
    """Create a new academic class section."""
    form = AddClassSectionForm()

    if form.validate_on_submit():
        class_name = form.name.data.strip().upper()
        section = form.section.data.strip().upper()
        semester = form.semester.data
        academic_year = form.academic_year.data.strip()

        duplicate_class = ClassSection.query.filter(
            func.lower(ClassSection.name) == class_name.lower(),
            func.lower(ClassSection.section) == section.lower(),
            ClassSection.semester == semester,
            func.lower(ClassSection.academic_year)
            == academic_year.lower(),
        ).first()

        if duplicate_class:
            form.name.errors.append(
                (
                    "This class section already exists for the "
                    "selected semester and academic year."
                )
            )

        form_has_errors = any(
            field.errors
            for field in form
        )

        if not form_has_errors:
            try:
                class_section = ClassSection(
                    course=course,
                    name=class_name,
                    section=section,
                    semester=semester,
                    academic_year=academic_year,
                    group_name=group_name,
                    is_active=form.is_active.data,
                )

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="CLASS_SECTION_CREATED",
                    details=(
                        f"Class {class_name} Section {section}, "
                        f"semester {semester}, academic year "
                        f"{academic_year} was created."
                    ),
                )

                db.session.add(class_section)
                db.session.add(audit_log)
                db.session.commit()

                flash(
                    (
                        f"{class_name} Section {section} "
                        "was added successfully."
                    ),
                    "success",
                )

                return redirect(
                    url_for("admin.class_list")
                )

            except Exception as error:
                db.session.rollback()

                print("ADD CLASS ERROR:", error)

                flash(
                    (
                        "The class section could not be added. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/add_class.html",
        form=form,
    )
# =========================================================
# Timetable helpers
# =========================================================


def _format_timetable_time(value):
    """Return a readable timetable time."""
    if value is None:
        return "Not specified"

    return value.strftime("%I:%M %p")


def _get_timetable_assignment_id(
    timetable_entry: Timetable,
) -> int:
    """Return the real assignment_id column used by Timetable."""
    return timetable_entry.assignment_id


def _get_timetable_assignment_choices() -> list[tuple[int, str]]:
    """Build readable active teaching-assignment choices."""
    assignments = TeachingAssignment.query.filter_by(
        is_active=True,
    ).order_by(
        TeachingAssignment.id.asc(),
    ).all()

    return [
        (
            assignment.id,
            (
                f"{assignment.teacher.full_name} · "
                f"{assignment.subject.name} "
                f"({assignment.subject.code}) · "
                f"{assignment.class_section.name} "
                f"Section {assignment.class_section.section}"
            ),
        )
        for assignment in assignments
    ]


def _times_overlap(
    first_start,
    first_end,
    second_start,
    second_end,
) -> bool:
    """Return True when two class periods overlap."""
    return first_start < second_end and first_end > second_start


def _find_timetable_conflicts(
    assignment: TeachingAssignment,
    day: str,
    start_time,
    end_time,
    room_number: str,
    excluded_timetable_id: int | None = None,
) -> list[str]:
    """Find teacher, class-section and room timetable conflicts."""
    conflicts: list[str] = []

    existing_entries = Timetable.query.filter_by(
        day_of_week=day,
        is_active=True,
    ).all()

    for existing_entry in existing_entries:
        if (
            excluded_timetable_id is not None
            and existing_entry.id == excluded_timetable_id
        ):
            continue

        if not _times_overlap(
            start_time,
            end_time,
            existing_entry.start_time,
            existing_entry.end_time,
        ):
            continue

        existing_assignment = existing_entry.assignment

        if existing_assignment.teacher_id == assignment.teacher_id:
            conflicts.append(
                "The selected teacher already has a class during this time."
            )

        if existing_assignment.class_id == assignment.class_id:
            conflicts.append(
                "The selected section already has another class during this time."
            )

        existing_room = (existing_entry.room_number or "").strip().upper()
        if existing_room and existing_room == room_number:
            conflicts.append(
                "The selected room is already occupied during this time."
            )

    return list(dict.fromkeys(conflicts))


def _build_timetable_rows(
    entries: list[Timetable],
) -> list[dict]:
    """Prepare timetable entries for Admin templates."""
    day_order = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7,
    }

    entries.sort(
        key=lambda entry: (
            day_order.get(entry.day_of_week, 99),
            entry.start_time,
            entry.end_time,
        )
    )

    return [
        {
            "id": entry.id,
            "day": entry.day_of_week,
            "start_time": _format_timetable_time(entry.start_time),
            "end_time": _format_timetable_time(entry.end_time),
            "room": entry.room_number or "Not specified",
            "is_active": entry.is_active,
            "teacher_name": entry.assignment.teacher.full_name,
            "employee_id": entry.assignment.teacher.employee_id,
            "subject_name": entry.assignment.subject.name,
            "subject_code": entry.assignment.subject.code,
            "class_name": entry.assignment.class_section.name,
            "section": entry.assignment.class_section.section,
            "semester": entry.assignment.class_section.semester,
            "academic_year": entry.assignment.class_section.academic_year,
        }
        for entry in entries
    ]


# =========================================================
# Master timetable
# =========================================================


@admin_bp.get("/timetable")
@role_required("admin")
def timetable_list():
    """Display all timetable entries for the administrator."""
    timetable_rows = _build_timetable_rows(Timetable.query.all())

    summary = {
        "total": len(timetable_rows),
        "active": sum(1 for row in timetable_rows if row["is_active"]),
        "inactive": sum(
            1
            for row in timetable_rows
            if not row["is_active"]
        ),
    }

    return render_template(
        "admin/timetable.html",
        timetable_rows=timetable_rows,
        summary=summary,
    )


@admin_bp.route("/timetable/add", methods=["GET", "POST"])
@role_required("admin")
def add_timetable():
    """Create a timetable entry with conflict protection."""
    form = AddTimetableForm()
    form.teaching_assignment_id.choices = (
        _get_timetable_assignment_choices()
    )

    if not form.teaching_assignment_id.choices:
        flash(
            "Create an active teaching assignment before adding a timetable entry.",
            "warning",
        )
        return redirect(url_for("admin.timetable_list"))

    if form.validate_on_submit():
        assignment = db.get_or_404(
            TeachingAssignment,
            form.teaching_assignment_id.data,
        )
        room_number = form.room_number.data.strip().upper()

        conflicts = _find_timetable_conflicts(
            assignment=assignment,
            day=form.day_of_week.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            room_number=room_number,
        )

        if conflicts:
            form.start_time.errors.extend(conflicts)
        else:
            try:
                timetable_entry = Timetable(
                    assignment_id=assignment.id,
                    day_of_week=form.day_of_week.data,
                    start_time=form.start_time.data,
                    end_time=form.end_time.data,
                    room_number=room_number,
                    is_active=form.is_active.data,
                )

                db.session.add(timetable_entry)
                db.session.flush()
                db.session.add(
                    AuditLog(
                        user_id=current_user.id,
                        action="TIMETABLE_ENTRY_CREATED",
                        details=(
                            f"Created timetable entry {timetable_entry.id} "
                            f"for assignment {assignment.id}."
                        ),
                    )
                )
                db.session.commit()

                flash("Timetable entry was added successfully.", "success")
                return redirect(url_for("admin.timetable_list"))

            except Exception as error:
                db.session.rollback()
                print("ADD TIMETABLE ERROR:", error)
                flash(
                    "The timetable entry could not be added.",
                    "danger",
                )

    return render_template("admin/add_timetable.html", form=form)


@admin_bp.route(
    "/timetable/<int:timetable_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_timetable(timetable_id: int):
    """Update one timetable entry with conflict protection."""
    timetable_entry = db.get_or_404(Timetable, timetable_id)
    form = EditTimetableForm()
    form.teaching_assignment_id.choices = (
        _get_timetable_assignment_choices()
    )

    if request.method == "GET":
        form.teaching_assignment_id.data = timetable_entry.assignment_id
        form.day_of_week.data = timetable_entry.day_of_week
        form.start_time.data = timetable_entry.start_time
        form.end_time.data = timetable_entry.end_time
        form.room_number.data = timetable_entry.room_number
        form.is_active.data = timetable_entry.is_active

    if form.validate_on_submit():
        assignment = db.get_or_404(
            TeachingAssignment,
            form.teaching_assignment_id.data,
        )
        room_number = form.room_number.data.strip().upper()

        conflicts = _find_timetable_conflicts(
            assignment=assignment,
            day=form.day_of_week.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            room_number=room_number,
            excluded_timetable_id=timetable_entry.id,
        )

        if conflicts:
            form.start_time.errors.extend(conflicts)
        else:
            try:
                timetable_entry.assignment_id = assignment.id
                timetable_entry.day_of_week = form.day_of_week.data
                timetable_entry.start_time = form.start_time.data
                timetable_entry.end_time = form.end_time.data
                timetable_entry.room_number = room_number
                timetable_entry.is_active = form.is_active.data

                db.session.add(
                    AuditLog(
                        user_id=current_user.id,
                        action="TIMETABLE_ENTRY_UPDATED",
                        details=(
                            f"Updated timetable entry {timetable_entry.id} "
                            f"for assignment {assignment.id}."
                        ),
                    )
                )
                db.session.commit()

                flash("Timetable entry was updated successfully.", "success")
                return redirect(url_for("admin.timetable_list"))

            except Exception as error:
                db.session.rollback()
                print("EDIT TIMETABLE ERROR:", error)
                flash(
                    "The timetable entry could not be updated.",
                    "danger",
                )

    return render_template(
        "admin/edit_timetable.html",
        form=form,
        timetable_entry=timetable_entry,
    )


@admin_bp.get("/timetable/sections")
@role_required("admin")
def section_timetable():
    """Display a dated weekly timetable for one class section."""
    from datetime import date, datetime, timedelta

    class_sections = ClassSection.query.order_by(
        ClassSection.name.asc(),
        ClassSection.section.asc(),
    ).all()

    selected_class_id = request.args.get("class_id", type=int)
    if selected_class_id is None and class_sections:
        selected_class_id = class_sections[0].id

    selected_class = (
        db.session.get(ClassSection, selected_class_id)
        if selected_class_id is not None
        else None
    )

    week_start_text = request.args.get("week_start", "").strip()

    try:
        selected_week_start = datetime.strptime(
            week_start_text,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        selected_week_start = date.today()

    selected_week_start -= timedelta(
        days=selected_week_start.weekday()
    )
    selected_week_end = selected_week_start + timedelta(days=6)

    timetable_rows: list[dict] = []

    if selected_class is not None:
        assignments = TeachingAssignment.query.filter_by(
            class_id=selected_class.id,
            is_active=True,
        ).all()
        assignment_ids = [assignment.id for assignment in assignments]

        entries = (
            Timetable.query.filter(
                Timetable.assignment_id.in_(assignment_ids),
            ).all()
            if assignment_ids
            else []
        )

        timetable_rows = _build_timetable_rows(entries)

        day_offsets = {
            "Monday": 0,
            "Tuesday": 1,
            "Wednesday": 2,
            "Thursday": 3,
            "Friday": 4,
            "Saturday": 5,
            "Sunday": 6,
        }

        for row in timetable_rows:
            offset = day_offsets.get(row["day"])
            row["date"] = (
                selected_week_start + timedelta(days=offset)
                if offset is not None
                else None
            )

    return render_template(
        "admin/section_timetable.html",
        class_sections=class_sections,
        selected_class=selected_class,
        selected_class_id=selected_class_id,
        timetable_rows=timetable_rows,
        week_start=selected_week_start,
        week_end=selected_week_end,
        previous_week=selected_week_start - timedelta(days=7),
        next_week=selected_week_start + timedelta(days=7),
    )


# =========================================================
# Admin management home pages
# =========================================================


@admin_bp.get("/management/teachers")
@role_required("admin")
def teacher_management_home():
    """Show teacher departments as the first management level."""
    teachers = Teacher.query.order_by(
        Teacher.department.asc(),
        Teacher.full_name.asc(),
    ).all()

    department_map: dict[str, list[Teacher]] = {}
    for teacher in teachers:
        department_map.setdefault(teacher.department, []).append(teacher)

    departments = [
        {
            "name": name,
            "teacher_count": len(department_teachers),
        }
        for name, department_teachers in department_map.items()
    ]

    return render_template(
        "admin/teacher_management_home.html",
        departments=departments,
        teacher_count=len(teachers),
    )


@admin_bp.get("/management/teachers/department")
@role_required("admin")
def teacher_department():
    """Show teachers belonging to one selected department."""
    department_name = request.args.get("name", "").strip()

    teachers = Teacher.query.filter_by(
        department=department_name,
    ).order_by(
        Teacher.full_name.asc(),
    ).all()

    return render_template(
        "admin/teacher_department.html",
        department_name=department_name,
        teachers=teachers,
    )


@admin_bp.get("/management/teachers/<int:teacher_id>")
@role_required("admin")
def teacher_detail(teacher_id: int):
    """Show one teacher's profile, classes, timetable and attendance."""
    teacher = db.get_or_404(Teacher, teacher_id)
    assignments = TeachingAssignment.query.filter_by(
        teacher_id=teacher.id,
        is_active=True,
    ).all()

    assignment_ids = [assignment.id for assignment in assignments]
    timetable_rows = _build_timetable_rows(
        Timetable.query.filter(
            Timetable.assignment_id.in_(assignment_ids)
        ).all()
        if assignment_ids
        else []
    )

    attendance_records = TeacherAttendance.query.filter_by(
        teacher_id=teacher.id,
    ).order_by(
        TeacherAttendance.attendance_date.desc(),
    ).all()

    return render_template(
        "admin/teacher_detail.html",
        teacher=teacher,
        assignments=assignments,
        timetable_rows=timetable_rows,
        week_dates=_current_week_dates(),
        attendance_records=attendance_records,
    )


@admin_bp.get("/management/teachers/timetables")
@role_required("admin")
def teacher_timetables():
    """Display one selected teacher's combined weekly timetable."""
    teachers = Teacher.query.order_by(Teacher.full_name.asc()).all()
    selected_teacher_id = request.args.get("teacher_id", type=int)

    if selected_teacher_id is None and teachers:
        selected_teacher_id = teachers[0].id

    selected_teacher = (
        db.session.get(Teacher, selected_teacher_id)
        if selected_teacher_id is not None
        else None
    )

    timetable_rows: list[dict] = []

    if selected_teacher is not None:
        assignment_ids = [
            assignment.id
            for assignment in TeachingAssignment.query.filter_by(
                teacher_id=selected_teacher.id,
                is_active=True,
            ).all()
        ]

        if assignment_ids:
            timetable_rows = _build_timetable_rows(
                Timetable.query.filter(
                    Timetable.assignment_id.in_(assignment_ids)
                ).all()
            )

    return render_template(
        "admin/teacher_timetable.html",
        teachers=teachers,
        selected_teacher=selected_teacher,
        selected_teacher_id=selected_teacher_id,
        timetable_rows=timetable_rows,
        week_dates=_current_week_dates(),
    )


@admin_bp.get("/management/students")
@role_required("admin")
def student_management_home():
    """Start student management with real course selection."""
    courses = [
        row[0]
        for row in db.session.query(ClassSection.course)
        .distinct()
        .order_by(ClassSection.course.asc())
        .all()
    ]

    items = []
    for course in courses:
        sections = ClassSection.query.filter_by(course=course).all()
        section_ids = [section.id for section in sections]
        items.append(
            {
                "name": course,
                "section_count": len(sections),
                "student_count": (
                    Student.query.filter(Student.class_id.in_(section_ids)).count()
                    if section_ids
                    else 0
                ),
            }
        )

    return render_template(
        "admin/student_hierarchy.html",
        level="Course",
        title="Select Course",
        description="Choose a course to continue to branch selection.",
        items=items,
        breadcrumb=[("Student Management", None)],
    )


@admin_bp.get("/management/students/branches")
@role_required("admin")
def student_branch_selection():
    """Show branches available inside the selected course."""
    course = request.args.get("course", "").strip()
    branches = [
        row[0]
        for row in db.session.query(ClassSection.name)
        .filter(ClassSection.course == course)
        .distinct()
        .order_by(ClassSection.name.asc())
        .all()
    ]

    items = []
    for branch in branches:
        sections = ClassSection.query.filter_by(
            course=course,
            name=branch,
        ).all()
        section_ids = [section.id for section in sections]
        items.append(
            {
                "name": branch,
                "section_count": len(sections),
                "student_count": (
                    Student.query.filter(Student.class_id.in_(section_ids)).count()
                    if section_ids
                    else 0
                ),
            }
        )

    return render_template(
        "admin/student_hierarchy.html",
        level="Branch",
        title="Select Branch",
        description=f"Course: {course}",
        items=items,
        course=course,
        breadcrumb=[
            ("Student Management", url_for("admin.student_management_home")),
            (course, None),
        ],
    )


@admin_bp.get("/management/students/years")
@role_required("admin")
def student_year_selection():
    """Show academic years for one course and branch."""
    course = request.args.get("course", "").strip()
    branch = request.args.get("branch", "").strip()

    years = [
        row[0]
        for row in db.session.query(ClassSection.academic_year)
        .filter(
            ClassSection.course == course,
            ClassSection.name == branch,
        )
        .distinct()
        .order_by(ClassSection.academic_year.desc())
        .all()
    ]

    items = []
    for academic_year in years:
        sections = ClassSection.query.filter_by(
            course=course,
            name=branch,
            academic_year=academic_year,
        ).all()
        section_ids = [section.id for section in sections]
        items.append(
            {
                "name": academic_year,
                "section_count": len(sections),
                "student_count": (
                    Student.query.filter(Student.class_id.in_(section_ids)).count()
                    if section_ids
                    else 0
                ),
            }
        )

    return render_template(
        "admin/student_hierarchy.html",
        level="Academic Year",
        title="Select Academic Year",
        description=f"{course} · {branch}",
        items=items,
        course=course,
        branch=branch,
        breadcrumb=[
            ("Student Management", url_for("admin.student_management_home")),
            (course, url_for("admin.student_branch_selection", course=course)),
            (branch, None),
        ],
    )


@admin_bp.get("/management/students/groups")
@role_required("admin")
def student_group_selection():
    """Show real group/batch records for the selected academic year."""
    course = request.args.get("course", "").strip()
    branch = request.args.get("branch", "").strip()
    academic_year = request.args.get("year", "").strip()

    group_rows = (
        db.session.query(ClassSection.group_name, ClassSection.semester)
        .filter(
            ClassSection.course == course,
            ClassSection.name == branch,
            ClassSection.academic_year == academic_year,
        )
        .distinct()
        .order_by(ClassSection.semester.asc(), ClassSection.group_name.asc())
        .all()
    )

    items = []
    for group_name, semester in group_rows:
        sections = ClassSection.query.filter_by(
            course=course,
            name=branch,
            academic_year=academic_year,
            semester=semester,
            group_name=group_name,
        ).all()
        section_ids = [section.id for section in sections]
        items.append(
            {
                "name": f"{group_name} · Semester {semester}",
                "group_name": group_name,
                "semester": semester,
                "section_count": len(sections),
                "student_count": (
                    Student.query.filter(Student.class_id.in_(section_ids)).count()
                    if section_ids
                    else 0
                ),
            }
        )

    return render_template(
        "admin/student_hierarchy.html",
        level="Group",
        title="Select Group / Batch",
        description=f"{course} · {branch} · {academic_year}",
        items=items,
        course=course,
        branch=branch,
        academic_year=academic_year,
        breadcrumb=[
            ("Student Management", url_for("admin.student_management_home")),
            (course, url_for("admin.student_branch_selection", course=course)),
            (branch, url_for("admin.student_year_selection", course=course, branch=branch)),
            (academic_year, None),
        ],
    )


@admin_bp.get("/management/students/sections")
@role_required("admin")
def student_section_selection():
    """Show sections inside the selected course, year and group."""
    course = request.args.get("course", "").strip()
    branch = request.args.get("branch", "").strip()
    academic_year = request.args.get("year", "").strip()
    group_name = request.args.get("group", "").strip()
    semester = request.args.get("semester", type=int)

    sections = ClassSection.query.filter_by(
        course=course,
        name=branch,
        academic_year=academic_year,
        group_name=group_name,
        semester=semester,
    ).order_by(ClassSection.section.asc()).all()

    items = [
        {
            "id": section.id,
            "name": f"Section {section.section}",
            "section_count": 1,
            "student_count": Student.query.filter_by(class_id=section.id).count(),
        }
        for section in sections
    ]

    return render_template(
        "admin/student_hierarchy.html",
        level="Section",
        title="Select Section",
        description=(
            f"{course} · {branch} · {academic_year} · "
            f"{group_name} · Semester {semester}"
        ),
        items=items,
        course=course,
        branch=branch,
        academic_year=academic_year,
        group_name=group_name,
        semester=semester,
        breadcrumb=[
            ("Student Management", url_for("admin.student_management_home")),
            (course, url_for("admin.student_branch_selection", course=course)),
            (branch, url_for("admin.student_year_selection", course=course, branch=branch)),
            (academic_year, url_for("admin.student_group_selection", course=course, branch=branch, year=academic_year)),
            (f"{group_name} · Semester {semester}", None),
        ],
    )


def _student_attendance_summary(student: Student) -> dict:
    """Calculate attendance counts for an Admin section roster."""
    records = student.attendance_records
    present = sum(1 for record in records if record.status == "PRESENT")
    late = sum(1 for record in records if record.status == "LATE")
    absent = sum(1 for record in records if record.status == "ABSENT")
    total = len(records)

    return {
        "total": total,
        "present": present,
        "late": late,
        "absent": absent,
        "percentage": round((present + late) / total * 100, 1)
        if total
        else 0.0,
    }


@admin_bp.get("/management/students/sections/<int:class_id>")
@role_required("admin")
def student_section_detail(class_id: int):
    """Show section timetable, student names and attendance summaries."""
    class_section = db.get_or_404(ClassSection, class_id)
    students = Student.query.filter_by(
        class_id=class_section.id,
    ).order_by(Student.roll_number.asc()).all()

    student_rows = [
        {
            "student": student,
            "attendance": _student_attendance_summary(student),
        }
        for student in students
    ]

    assignment_ids = [
        assignment.id
        for assignment in TeachingAssignment.query.filter_by(
            class_id=class_section.id,
            is_active=True,
        ).all()
    ]

    timetable_rows = _build_timetable_rows(
        Timetable.query.filter(
            Timetable.assignment_id.in_(assignment_ids)
        ).all()
        if assignment_ids
        else []
    )

    return render_template(
        "admin/student_section_detail.html",
        class_section=class_section,
        student_rows=student_rows,
        timetable_rows=timetable_rows,
    )


# =========================================================
# Teacher attendance administration
# =========================================================


def _teacher_attendance_choices() -> list[tuple[int, str]]:
    """Return teacher choices for attendance forms."""
    teachers = Teacher.query.order_by(Teacher.full_name.asc()).all()

    return [
        (
            teacher.id,
            f"{teacher.full_name} · {teacher.employee_id}",
        )
        for teacher in teachers
    ]


@admin_bp.get("/management/teachers/attendance")
@role_required("admin")
def teacher_attendance_list():
    """Display teacher attendance records with an optional filter."""
    teachers = Teacher.query.order_by(Teacher.full_name.asc()).all()
    selected_teacher_id = request.args.get("teacher_id", type=int)

    query = TeacherAttendance.query
    if selected_teacher_id is not None:
        query = query.filter_by(teacher_id=selected_teacher_id)

    records = query.order_by(
        TeacherAttendance.attendance_date.desc(),
        TeacherAttendance.id.desc(),
    ).all()

    working_records = [
        record
        for record in records
        if record.status != "HOLIDAY"
    ]
    attended_units = sum(
        1.0
        if record.status in {"PRESENT", "LATE"}
        else 0.5
        if record.status == "HALF_DAY"
        else 0.0
        for record in working_records
    )

    summary = {
        "records": len(records),
        "working_days": len(working_records),
        "present": sum(
            1 for record in records if record.status == "PRESENT"
        ),
        "late": sum(
            1 for record in records if record.status == "LATE"
        ),
        "absent": sum(
            1 for record in records if record.status == "ABSENT"
        ),
        "leave": sum(
            1 for record in records if record.status == "LEAVE"
        ),
        "scheduled_classes": sum(
            record.scheduled_classes for record in records
        ),
        "conducted_classes": sum(
            record.conducted_classes for record in records
        ),
        "percentage": round(
            attended_units / len(working_records) * 100,
            1,
        )
        if working_records
        else 0.0,
    }

    return render_template(
        "admin/teacher_attendance.html",
        teachers=teachers,
        selected_teacher_id=selected_teacher_id,
        records=records,
        summary=summary,
    )


@admin_bp.route(
    "/management/teachers/attendance/add",
    methods=["GET", "POST"],
)
@role_required("admin")
def add_teacher_attendance():
    """Create one teacher attendance record."""
    from datetime import date

    form = TeacherAttendanceForm()
    form.teacher_id.choices = _teacher_attendance_choices()

    if request.method == "GET":
        form.attendance_date.data = date.today()

    if form.validate_on_submit():
        duplicate = TeacherAttendance.query.filter_by(
            teacher_id=form.teacher_id.data,
            attendance_date=form.attendance_date.data,
        ).first()

        if duplicate is not None:
            form.attendance_date.errors.append(
                "An attendance record already exists for this teacher and date."
            )
        else:
            try:
                record = TeacherAttendance(
                    teacher_id=form.teacher_id.data,
                    attendance_date=form.attendance_date.data,
                    status=form.status.data,
                    check_in=form.check_in.data,
                    check_out=form.check_out.data,
                    scheduled_classes=form.scheduled_classes.data,
                    conducted_classes=form.conducted_classes.data,
                    remarks=(form.remarks.data or "").strip() or None,
                    created_by_user_id=current_user.id,
                    updated_by_user_id=current_user.id,
                )

                db.session.add(record)
                db.session.flush()
                db.session.add(
                    AuditLog(
                        user_id=current_user.id,
                        action="TEACHER_ATTENDANCE_CREATED",
                        details=(
                            f"Created teacher attendance record {record.id} "
                            f"for teacher {record.teacher_id} on "
                            f"{record.attendance_date}."
                        ),
                    )
                )
                db.session.commit()

                flash("Teacher attendance was added successfully.", "success")
                return redirect(
                    url_for(
                        "admin.teacher_attendance_list",
                        teacher_id=record.teacher_id,
                    )
                )

            except Exception as error:
                db.session.rollback()
                print("ADD TEACHER ATTENDANCE ERROR:", error)
                flash("Teacher attendance could not be saved.", "danger")

    return render_template(
        "admin/teacher_attendance_form.html",
        form=form,
        page_title="Add Teacher Attendance",
    )


@admin_bp.route(
    "/management/teachers/attendance/<int:record_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_teacher_attendance(record_id: int):
    """Edit a teacher attendance record and preserve an audit log."""
    record = db.get_or_404(TeacherAttendance, record_id)
    form = TeacherAttendanceForm()
    form.teacher_id.choices = _teacher_attendance_choices()

    if request.method == "GET":
        form.teacher_id.data = record.teacher_id
        form.attendance_date.data = record.attendance_date
        form.status.data = record.status
        form.check_in.data = record.check_in
        form.check_out.data = record.check_out
        form.scheduled_classes.data = record.scheduled_classes
        form.conducted_classes.data = record.conducted_classes
        form.remarks.data = record.remarks

    form_is_valid = form.validate_on_submit()

    if form_is_valid and not (form.remarks.data or "").strip():
        form.remarks.errors.append(
            "A correction reason is required when editing teacher attendance."
        )
        form_is_valid = False

    if form_is_valid:
        duplicate = TeacherAttendance.query.filter(
            TeacherAttendance.teacher_id == form.teacher_id.data,
            TeacherAttendance.attendance_date == form.attendance_date.data,
            TeacherAttendance.id != record.id,
        ).first()

        if duplicate is not None:
            form.attendance_date.errors.append(
                "Another record already exists for this teacher and date."
            )
        else:
            try:
                old_value = (
                    f"teacher={record.teacher_id}, date={record.attendance_date}, "
                    f"status={record.status}"
                )

                record.teacher_id = form.teacher_id.data
                record.attendance_date = form.attendance_date.data
                record.status = form.status.data
                record.check_in = form.check_in.data
                record.check_out = form.check_out.data
                record.scheduled_classes = form.scheduled_classes.data
                record.conducted_classes = form.conducted_classes.data
                record.remarks = (form.remarks.data or "").strip() or None
                record.updated_by_user_id = current_user.id

                db.session.add(
                    AuditLog(
                        user_id=current_user.id,
                        action="TEACHER_ATTENDANCE_UPDATED",
                        details=(
                            f"Updated teacher attendance record {record.id}. "
                            f"Previous: {old_value}. New status: {record.status}. "
                            f"Reason: {record.remarks or 'Not provided'}."
                        ),
                    )
                )
                db.session.commit()

                flash("Teacher attendance was updated successfully.", "success")
                return redirect(
                    url_for(
                        "admin.teacher_attendance_list",
                        teacher_id=record.teacher_id,
                    )
                )

            except Exception as error:
                db.session.rollback()
                print("EDIT TEACHER ATTENDANCE ERROR:", error)
                flash("Teacher attendance could not be updated.", "danger")

    return render_template(
        "admin/teacher_attendance_form.html",
        form=form,
        page_title="Edit Teacher Attendance",
        record=record,
    )


# =========================================================
# Student attendance, analytics, reports and audit logs
# =========================================================


def _attendance_record_details(record: Attendance) -> dict:
    """Prepare one readable attendance record for Admin pages."""
    class_session = record.class_session
    timetable_entry = class_session.timetable_entry if class_session else None
    assignment = timetable_entry.assignment if timetable_entry else None

    return {
        "record": record,
        "date": (
            class_session.session_date.strftime("%d %b %Y")
            if class_session
            else record.recorded_at.strftime("%d %b %Y")
        ),
        "student_name": record.student.full_name,
        "roll_number": record.student.roll_number,
        "subject_name": assignment.subject.name if assignment else "Unknown",
        "subject_code": assignment.subject.code if assignment else "—",
        "teacher_name": assignment.teacher.full_name if assignment else "Unknown",
        "class_name": assignment.class_section.name if assignment else "Unknown",
        "section": assignment.class_section.section if assignment else "—",
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


def _student_analytics_row(student: Student) -> dict:
    """Calculate Admin attendance analytics for one student."""
    records = student.attendance_records
    present = sum(1 for record in records if record.status == "PRESENT")
    late = sum(1 for record in records if record.status == "LATE")
    absent = sum(1 for record in records if record.status == "ABSENT")
    excused = sum(1 for record in records if record.status == "EXCUSED")
    total = len(records)
    percentage = round((present + late) / total * 100, 1) if total else 0.0

    return {
        "student": student,
        "total": total,
        "present": present,
        "late": late,
        "absent": absent,
        "excused": excused,
        "percentage": percentage,
        "low_attendance": (
            total > 0
            and percentage < current_app.config["ATTENDANCE_THRESHOLD"]
        ),
    }


@admin_bp.get("/attendance")
@role_required("admin")
def attendance_records():
    """Display filterable student attendance records."""
    selected_student_id = request.args.get("student_id", type=int)
    selected_status = request.args.get("status", "").strip().upper()
    selected_subject_id = request.args.get("subject_id", type=int)

    query = Attendance.query

    if selected_student_id is not None:
        query = query.filter_by(student_id=selected_student_id)

    if selected_status:
        query = query.filter_by(status=selected_status)

    if selected_subject_id is not None:
        query = (
            query.join(ClassSession)
            .join(Timetable)
            .join(TeachingAssignment)
            .filter(TeachingAssignment.subject_id == selected_subject_id)
        )

    records = query.order_by(
        Attendance.recorded_at.desc(),
        Attendance.id.desc(),
    ).all()

    return render_template(
        "admin/attendance_records.html",
        rows=[_attendance_record_details(record) for record in records],
        students=Student.query.order_by(Student.roll_number.asc()).all(),
        subjects=Subject.query.order_by(Subject.code.asc()).all(),
        selected_student_id=selected_student_id,
        selected_status=selected_status,
        selected_subject_id=selected_subject_id,
    )


@admin_bp.route(
    "/attendance/<int:attendance_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_attendance(attendance_id: int):
    """Correct one attendance status with a mandatory audit reason."""
    attendance = db.get_or_404(Attendance, attendance_id)
    form = AttendanceCorrectionForm()

    if request.method == "GET":
        form.status.data = attendance.status

    if form.validate_on_submit():
        old_status = attendance.status
        new_status = form.status.data
        reason = form.correction_reason.data.strip()

        try:
            attendance.status = new_status
            existing_notes = attendance.notes.strip() if attendance.notes else ""
            correction_note = f"Admin correction: {reason}"
            attendance.notes = (
                f"{existing_notes} | {correction_note}"
                if existing_notes
                else correction_note
            )[:255]

            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    session_id=attendance.session_id,
                    student_id=attendance.student_id,
                    action="ATTENDANCE_CORRECTED",
                    details=(
                        f"Attendance {attendance.id} changed from "
                        f"{old_status} to {new_status}. Reason: {reason}"
                    ),
                )
            )
            db.session.commit()
            flash("Attendance correction saved with an audit log.", "success")
            return redirect(url_for("admin.attendance_records"))

        except Exception as error:
            db.session.rollback()
            print("ATTENDANCE CORRECTION ERROR:", error)
            flash("The attendance correction could not be saved.", "danger")

    return render_template(
        "admin/edit_attendance.html",
        form=form,
        row=_attendance_record_details(attendance),
    )


@admin_bp.get("/attendance/analytics")
@role_required("admin")
def attendance_analytics():
    """Show simple overall, subject and low-attendance analytics."""
    students = Student.query.order_by(Student.roll_number.asc()).all()
    student_rows = [_student_analytics_row(student) for student in students]
    records = Attendance.query.all()

    overall = {
        "total": len(records),
        "present": sum(1 for record in records if record.status == "PRESENT"),
        "late": sum(1 for record in records if record.status == "LATE"),
        "absent": sum(1 for record in records if record.status == "ABSENT"),
        "manual_review": sum(
            1 for record in records if record.method == "MANUAL_REVIEW"
        ),
    }

    subject_rows = []
    for subject in Subject.query.order_by(Subject.code.asc()).all():
        subject_records = (
            Attendance.query.join(ClassSession)
            .join(Timetable)
            .join(TeachingAssignment)
            .filter(TeachingAssignment.subject_id == subject.id)
            .all()
        )
        attended = sum(
            1
            for record in subject_records
            if record.status in {"PRESENT", "LATE"}
        )
        total = len(subject_records)
        subject_rows.append(
            {
                "subject": subject,
                "total": total,
                "percentage": round(attended / total * 100, 1)
                if total
                else 0.0,
            }
        )

    return render_template(
        "admin/attendance_analytics.html",
        overall=overall,
        student_rows=student_rows,
        low_attendance_rows=[
            row for row in student_rows if row["low_attendance"]
        ],
        subject_rows=subject_rows,
        threshold=current_app.config["ATTENDANCE_THRESHOLD"],
    )


@admin_bp.get("/attendance/export.csv")
@role_required("admin")
def export_attendance_csv():
    """Generate a local CSV attendance report without a paid service."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Attendance ID",
            "Date",
            "Roll Number",
            "Student",
            "Class",
            "Section",
            "Subject Code",
            "Subject",
            "Teacher",
            "Status",
            "Method",
            "Recognition Score",
            "Notes",
        ]
    )

    for record in Attendance.query.order_by(Attendance.id.asc()).all():
        row = _attendance_record_details(record)
        writer.writerow(
            [
                record.id,
                row["date"],
                row["roll_number"],
                row["student_name"],
                row["class_name"],
                row["section"],
                row["subject_code"],
                row["subject_name"],
                row["teacher_name"],
                row["status"],
                row["method"],
                row["confidence"],
                row["notes"],
            ]
        )

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=smart_classroom_attendance.csv"
            )
        },
    )


@admin_bp.get("/audit-logs")
@role_required("admin")
def audit_logs():
    """Display the latest transparent attendance and management actions."""
    logs = AuditLog.query.order_by(
        AuditLog.created_at.desc(),
        AuditLog.id.desc(),
    ).limit(500).all()

    return render_template(
        "admin/audit_logs.html",
        logs=logs,
    )


# =========================================================
# Teaching assignments and automatic subject enrolments
# =========================================================


def _assignment_form_choices(form: TeachingAssignmentForm) -> None:
    """Populate teacher, subject and class-section choices."""
    form.teacher_id.choices = [
        (
            teacher.id,
            f"{teacher.full_name} · {teacher.employee_id} · {teacher.designation}",
        )
        for teacher in Teacher.query.order_by(Teacher.full_name.asc()).all()
    ]
    form.subject_id.choices = [
        (subject.id, f"{subject.code} · {subject.name}")
        for subject in Subject.query.order_by(Subject.code.asc()).all()
    ]
    form.class_id.choices = get_class_choices()


def _sync_student_enrollments(student: Student) -> None:
    """Ensure a student is enrolled in active subjects for their class."""
    assignments = TeachingAssignment.query.filter_by(
        class_id=student.class_id,
        is_active=True,
    ).all()

    subject_ids = {assignment.subject_id for assignment in assignments}

    for subject_id in subject_ids:
        enrollment = Enrollment.query.filter_by(
            student_id=student.id,
            class_id=student.class_id,
            subject_id=subject_id,
        ).first()

        if enrollment is None:
            db.session.add(
                Enrollment(
                    student_id=student.id,
                    class_id=student.class_id,
                    subject_id=subject_id,
                    is_active=True,
                )
            )
        else:
            enrollment.is_active = True


def _sync_class_subject_enrollments(
    class_id: int,
    subject_id: int,
    active: bool,
) -> None:
    """Synchronize subject enrolments after an assignment change."""
    students = Student.query.filter_by(class_id=class_id).all()

    for student in students:
        enrollment = Enrollment.query.filter_by(
            student_id=student.id,
            class_id=class_id,
            subject_id=subject_id,
        ).first()

        if enrollment is None and active:
            db.session.add(
                Enrollment(
                    student_id=student.id,
                    class_id=class_id,
                    subject_id=subject_id,
                    is_active=True,
                )
            )
        elif enrollment is not None:
            enrollment.is_active = active


@admin_bp.get("/assignments")
@role_required("admin")
def assignment_list():
    """Display teacher, subject and section assignments."""
    assignments = TeachingAssignment.query.order_by(
        TeachingAssignment.id.asc()
    ).all()

    return render_template(
        "admin/assignments.html",
        assignments=assignments,
    )


@admin_bp.route("/assignments/add", methods=["GET", "POST"])
@role_required("admin")
def add_assignment():
    """Assign a teacher to one subject and class section."""
    form = TeachingAssignmentForm()
    _assignment_form_choices(form)

    if form.validate_on_submit():
        duplicate = TeachingAssignment.query.filter_by(
            teacher_id=form.teacher_id.data,
            subject_id=form.subject_id.data,
            class_id=form.class_id.data,
        ).first()

        if duplicate:
            form.teacher_id.errors.append(
                "This teacher, subject and section assignment already exists."
            )
        else:
            try:
                assignment = TeachingAssignment(
                    teacher_id=form.teacher_id.data,
                    subject_id=form.subject_id.data,
                    class_id=form.class_id.data,
                    is_active=form.is_active.data,
                )
                db.session.add(assignment)
                db.session.flush()

                _sync_class_subject_enrollments(
                    assignment.class_id,
                    assignment.subject_id,
                    assignment.is_active,
                )

                db.session.add(
                    AuditLog(
                        user_id=current_user.id,
                        action="TEACHING_ASSIGNMENT_CREATED",
                        details=(
                            f"Assignment {assignment.id}: teacher "
                            f"{assignment.teacher_id}, subject "
                            f"{assignment.subject_id}, class "
                            f"{assignment.class_id}."
                        ),
                    )
                )
                db.session.commit()
                flash("Teaching assignment created successfully.", "success")
                return redirect(url_for("admin.assignment_list"))

            except Exception as error:
                db.session.rollback()
                print("ADD ASSIGNMENT ERROR:", error)
                flash("The teaching assignment could not be created.", "danger")

    return render_template(
        "admin/assignment_form.html",
        form=form,
        page_title="Add Teaching Assignment",
    )


@admin_bp.route(
    "/assignments/<int:assignment_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_assignment(assignment_id: int):
    """Update a teacher-subject-section assignment."""
    assignment = db.get_or_404(TeachingAssignment, assignment_id)
    form = TeachingAssignmentForm()
    _assignment_form_choices(form)

    if request.method == "GET":
        form.teacher_id.data = assignment.teacher_id
        form.subject_id.data = assignment.subject_id
        form.class_id.data = assignment.class_id
        form.is_active.data = assignment.is_active

    if form.validate_on_submit():
        duplicate = TeachingAssignment.query.filter(
            TeachingAssignment.teacher_id == form.teacher_id.data,
            TeachingAssignment.subject_id == form.subject_id.data,
            TeachingAssignment.class_id == form.class_id.data,
            TeachingAssignment.id != assignment.id,
        ).first()

        if duplicate:
            form.teacher_id.errors.append(
                "This teacher, subject and section assignment already exists."
            )
        else:
            try:
                old_class_id = assignment.class_id
                old_subject_id = assignment.subject_id

                assignment.teacher_id = form.teacher_id.data
                assignment.subject_id = form.subject_id.data
                assignment.class_id = form.class_id.data
                assignment.is_active = form.is_active.data

                # Deactivate old enrolments only when no other active assignment
                # still teaches that subject in the old section.
                old_still_active = TeachingAssignment.query.filter(
                    TeachingAssignment.class_id == old_class_id,
                    TeachingAssignment.subject_id == old_subject_id,
                    TeachingAssignment.is_active.is_(True),
                    TeachingAssignment.id != assignment.id,
                ).first()

                if old_still_active is None:
                    _sync_class_subject_enrollments(
                        old_class_id,
                        old_subject_id,
                        False,
                    )

                _sync_class_subject_enrollments(
                    assignment.class_id,
                    assignment.subject_id,
                    assignment.is_active,
                )

                db.session.add(
                    AuditLog(
                        user_id=current_user.id,
                        action="TEACHING_ASSIGNMENT_UPDATED",
                        details=f"Teaching assignment {assignment.id} was updated.",
                    )
                )
                db.session.commit()
                flash("Teaching assignment updated successfully.", "success")
                return redirect(url_for("admin.assignment_list"))

            except Exception as error:
                db.session.rollback()
                print("EDIT ASSIGNMENT ERROR:", error)
                flash("The teaching assignment could not be updated.", "danger")

    return render_template(
        "admin/assignment_form.html",
        form=form,
        page_title="Edit Teaching Assignment",
        assignment=assignment,
    )
