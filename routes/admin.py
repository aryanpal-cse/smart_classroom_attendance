from flask import (
    Blueprint,
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
)
from models import(
     AuditLog,
     ClassSection,
     Student, 
     Subject, 
     TeachingAssignment,
     Timetable,
     Teacher, 
     User,

)        


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


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
                f"{class_section.name} "
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
        form.name.data = class_section.name
        form.section.data = class_section.section
        form.semester.data = class_section.semester
        form.academic_year.data = class_section.academic_year
        form.is_active.data = class_section.is_active

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

                class_section.name = class_name
                class_section.section = section
                class_section.semester = semester
                class_section.academic_year = academic_year
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
                    face_registered=False,
                )

                db.session.add(user)
                db.session.add(student)
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
                student.user.username = username
                student.user.is_active = form.is_active.data

                student.roll_number = roll_number
                student.full_name = full_name
                student.email = email
                student.class_section = selected_class

                if form.new_password.data:
                    student.user.set_password(
                        form.new_password.data
                    )

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
        form.is_active.data = teacher.user.is_active

    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        employee_id = form.employee_id.data.strip().upper()
        full_name = form.full_name.data.strip()
        department = form.department.data.strip()

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
                    name=class_name,
                    section=section,
                    semester=semester,
                    academic_year=academic_year,
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
def _format_timetable_time(value):
    """Return a readable timetable time."""
    if value is None:
        return "Not specified"

    if hasattr(value, "strftime"):
        return value.strftime("%I:%M %p")

    return str(value)


@admin_bp.route("/timetable")
@role_required("admin")
def timetable_list():
    """Display all timetable entries for the administrator."""
    entries = Timetable.query.all()

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
            day_order.get(
                getattr(entry, "day_of_week", ""),
                99,
            ),
            str(getattr(entry, "start_time", "")),
        )
    )

    timetable_rows = []

    for entry in entries:
        assignment_id = getattr(
            entry,
            "teaching_assignment_id",
            None,
        )

        assignment = (
            db.session.get(
                TeachingAssignment,
                assignment_id,
            )
            if assignment_id is not None
            else None
        )

        teacher = None
        subject = None
        class_section = None

        if assignment is not None:
            teacher_id = getattr(
                assignment,
                "teacher_id",
                None,
            )

            subject_id = getattr(
                assignment,
                "subject_id",
                None,
            )

            class_section_id = getattr(
                assignment,
                "class_section_id",
                getattr(
                    assignment,
                    "class_id",
                    None,
                ),
            )

            if teacher_id is not None:
                teacher = db.session.get(
                    Teacher,
                    teacher_id,
                )

            if subject_id is not None:
                subject = db.session.get(
                    Subject,
                    subject_id,
                )

            if class_section_id is not None:
                class_section = db.session.get(
                    ClassSection,
                    class_section_id,
                )

        timetable_rows.append(
            {
                "id": entry.id,
                "day": getattr(
                    entry,
                    "day_of_week",
                    "Not specified",
                ),
                "start_time": _format_timetable_time(
                    getattr(
                        entry,
                        "start_time",
                        None,
                    )
                ),
                "end_time": _format_timetable_time(
                    getattr(
                        entry,
                        "end_time",
                        None,
                    )
                ),
                "room": getattr(
                    entry,
                    "room_number",
                    "Not specified",
                ),
                "is_active": getattr(
                    entry,
                    "is_active",
                    True,
                ),
                "teacher_name": getattr(
                    teacher,
                    "full_name",
                    "Unknown Teacher",
                ),
                "employee_id": getattr(
                    teacher,
                    "employee_id",
                    "—",
                ),
                "subject_name": getattr(
                    subject,
                    "name",
                    "Unknown Subject",
                ),
                "subject_code": getattr(
                    subject,
                    "code",
                    "—",
                ),
                "class_name": getattr(
                    class_section,
                    "name",
                    "Unknown Class",
                ),
                "section": getattr(
                    class_section,
                    "section",
                    "—",
                ),
                "semester": getattr(
                    class_section,
                    "semester",
                    "—",
                ),
            }
        )

    summary = {
        "total": len(timetable_rows),
        "active": sum(
            1
            for row in timetable_rows
            if row["is_active"]
        ),
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
def _get_timetable_assignment_choices():
    """Build readable teaching-assignment choices."""
    assignments = TeachingAssignment.query.order_by(
        TeachingAssignment.id.asc()
    ).all()

    choices = []

    for assignment in assignments:
        if not getattr(assignment, "is_active", True):
            continue

        teacher = db.session.get(
            Teacher,
            assignment.teacher_id,
        )

        subject = db.session.get(
            Subject,
            assignment.subject_id,
        )

        class_section_id = getattr(
            assignment,
            "class_section_id",
            getattr(assignment, "class_id", None),
        )

        class_section = (
            db.session.get(
                ClassSection,
                class_section_id,
            )
            if class_section_id is not None
            else None
        )

        teacher_name = getattr(
            teacher,
            "full_name",
            "Unknown Teacher",
        )

        subject_name = getattr(
            subject,
            "name",
            "Unknown Subject",
        )

        subject_code = getattr(
            subject,
            "code",
            "—",
        )

        class_name = getattr(
            class_section,
            "name",
            "Unknown Class",
        )

        section = getattr(
            class_section,
            "section",
            "—",
        )

        label = (
            f"{teacher_name} · {subject_name} "
            f"({subject_code}) · {class_name} "
            f"Section {section}"
        )

        choices.append(
            (
                assignment.id,
                label,
            )
        )

    return choices


def _times_overlap(
    first_start,
    first_end,
    second_start,
    second_end,
):
    """Return True when two timetable time ranges overlap."""
    return (
        first_start < second_end
        and first_end > second_start
    )


@admin_bp.route(
    "/timetable/add",
    methods=["GET", "POST"],
)
@role_required("admin")
def add_timetable():
    """Create a timetable entry with conflict checks."""
    form = AddTimetableForm()

    form.teaching_assignment_id.choices = (
        _get_timetable_assignment_choices()
    )

    if not form.teaching_assignment_id.choices:
        flash(
            (
                "Create an active teaching assignment before "
                "adding a timetable entry."
            ),
            "warning",
        )

        return redirect(
            url_for("admin.timetable_list")
        )

    if form.validate_on_submit():
        assignment = db.get_or_404(
            TeachingAssignment,
            form.teaching_assignment_id.data,
        )

        day = form.day_of_week.data
        start_time = form.start_time.data
        end_time = form.end_time.data
        room_number = form.room_number.data.strip().upper()

        class_section_id = getattr(
            assignment,
            "class_section_id",
            getattr(assignment, "class_id", None),
        )

        existing_entries = Timetable.query.filter_by(
            day_of_week=day,
        ).all()

        conflict_messages = []

        for existing_entry in existing_entries:
            if not getattr(
                existing_entry,
                "is_active",
                True,
            ):
                continue

            if not _times_overlap(
                start_time,
                end_time,
                existing_entry.start_time,
                existing_entry.end_time,
            ):
                continue

            existing_assignment = db.session.get(
                TeachingAssignment,
                existing_entry.teaching_assignment_id,
            )

            if existing_assignment is None:
                continue

            existing_class_id = getattr(
                existing_assignment,
                "class_section_id",
                getattr(
                    existing_assignment,
                    "class_id",
                    None,
                ),
            )

            if (
                existing_assignment.teacher_id
                == assignment.teacher_id
            ):
                conflict_messages.append(
                    "The selected teacher already has a class "
                    "during this time."
                )

            if existing_class_id == class_section_id:
                conflict_messages.append(
                    "The selected class section already has another "
                    "subject during this time."
                )

            existing_room = str(
                getattr(
                    existing_entry,
                    "room_number",
                    "",
                )
            ).strip().upper()

            if (
                existing_room
                and existing_room == room_number
            ):
                conflict_messages.append(
                    "The selected room is already occupied during "
                    "this time."
                )

        conflict_messages = list(
            dict.fromkeys(conflict_messages)
        )

        if conflict_messages:
            for message in conflict_messages:
                form.start_time.errors.append(message)

        else:
            try:
                timetable_entry = Timetable(
                    teaching_assignment_id=assignment.id,
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time,
                    room_number=room_number,
                    is_active=form.is_active.data,
                )

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="TIMETABLE_ENTRY_CREATED",
                    details=(
                        f"Created timetable entry for assignment "
                        f"{assignment.id} on {day}, "
                        f"{start_time.strftime('%H:%M')} to "
                        f"{end_time.strftime('%H:%M')}, "
                        f"room {room_number}."
                    ),
                )

                db.session.add(timetable_entry)
                db.session.add(audit_log)
                db.session.commit()

                flash(
                    "Timetable entry was added successfully.",
                    "success",
                )

                return redirect(
                    url_for("admin.timetable_list")
                )

            except Exception as error:
                db.session.rollback()

                print(
                    "ADD TIMETABLE ERROR:",
                    error,
                )

                flash(
                    (
                        "The timetable entry could not be added. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/add_timetable.html",
        form=form,
    )
@admin_bp.route(
    "/timetable/<int:timetable_id>/edit",
    methods=["GET", "POST"],
)
@role_required("admin")
def edit_timetable(timetable_id: int):
    """Update an existing timetable entry with conflict checks."""
    timetable_entry = db.get_or_404(
        Timetable,
        timetable_id,
    )

    form = EditTimetableForm(
        obj=timetable_entry,
    )

    form.teaching_assignment_id.choices = (
        _get_timetable_assignment_choices()
    )

    if form.validate_on_submit():
        assignment = db.get_or_404(
            TeachingAssignment,
            form.teaching_assignment_id.data,
        )

        day = form.day_of_week.data
        start_time = form.start_time.data
        end_time = form.end_time.data
        room_number = (
            form.room_number.data
            .strip()
            .upper()
        )

        class_section_id = getattr(
            assignment,
            "class_section_id",
            getattr(
                assignment,
                "class_id",
                None,
            ),
        )

        existing_entries = Timetable.query.filter_by(
            day_of_week=day,
        ).all()

        conflict_messages = []

        for existing_entry in existing_entries:
            if existing_entry.id == timetable_entry.id:
                continue

            if not getattr(
                existing_entry,
                "is_active",
                True,
            ):
                continue

            if not _times_overlap(
                start_time,
                end_time,
                existing_entry.start_time,
                existing_entry.end_time,
            ):
                continue

            existing_assignment = db.session.get(
                TeachingAssignment,
                existing_entry.teaching_assignment_id,
            )

            if existing_assignment is None:
                continue

            existing_class_id = getattr(
                existing_assignment,
                "class_section_id",
                getattr(
                    existing_assignment,
                    "class_id",
                    None,
                ),
            )

            if (
                existing_assignment.teacher_id
                == assignment.teacher_id
            ):
                conflict_messages.append(
                    "The selected teacher already has a class "
                    "during this time."
                )

            if existing_class_id == class_section_id:
                conflict_messages.append(
                    "The selected class section already has another "
                    "subject during this time."
                )

            existing_room = str(
                getattr(
                    existing_entry,
                    "room_number",
                    "",
                )
            ).strip().upper()

            if (
                existing_room
                and existing_room == room_number
            ):
                conflict_messages.append(
                    "The selected room is already occupied during "
                    "this time."
                )

        conflict_messages = list(
            dict.fromkeys(conflict_messages)
        )

        if conflict_messages:
            for message in conflict_messages:
                form.start_time.errors.append(
                    message
                )

        else:
            try:
                old_schedule = (
                    f"{timetable_entry.day_of_week}, "
                    f"{timetable_entry.start_time} to "
                    f"{timetable_entry.end_time}, "
                    f"room {timetable_entry.room_number}"
                )

                timetable_entry.teaching_assignment_id = (
                    assignment.id
                )
                timetable_entry.day_of_week = day
                timetable_entry.start_time = start_time
                timetable_entry.end_time = end_time
                timetable_entry.room_number = room_number
                timetable_entry.is_active = (
                    form.is_active.data
                )

                audit_log = AuditLog(
                    user_id=current_user.id,
                    action="TIMETABLE_ENTRY_UPDATED",
                    details=(
                        f"Updated timetable entry "
                        f"{timetable_entry.id} from "
                        f"{old_schedule} to {day}, "
                        f"{start_time.strftime('%H:%M')} to "
                        f"{end_time.strftime('%H:%M')}, "
                        f"room {room_number}."
                    ),
                )

                db.session.add(audit_log)
                db.session.commit()

                flash(
                    "Timetable entry was updated successfully.",
                    "success",
                )

                return redirect(
                    url_for(
                        "admin.timetable_list"
                    )
                )

            except Exception as error:
                db.session.rollback()

                print(
                    "EDIT TIMETABLE ERROR:",
                    error,
                )

                flash(
                    (
                        "The timetable entry could not be updated. "
                        "Please check the information and try again."
                    ),
                    "danger",
                )

    return render_template(
        "admin/edit_timetable.html",
        form=form,
        timetable_entry=timetable_entry,
    )