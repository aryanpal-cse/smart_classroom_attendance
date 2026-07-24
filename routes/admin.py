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
    EditClassSectionForm,
    EditStudentForm,
    EditSubjectForm,
    EditTeacherForm,
)
from models import(
     AuditLog,
     ClassSection,
     Student, 
     Subject, 
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