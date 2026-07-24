from flask import Blueprint, render_template
from flask_login import current_user

from decorators import role_required


student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/student",
)


@student_bp.get("/dashboard")
@role_required("student")
def dashboard():
    """Display the student dashboard."""
    student_profile = current_user.student_profile

    return render_template(
        "student/dashboard.html",
        student=student_profile,
    )