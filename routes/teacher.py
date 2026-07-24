from flask import Blueprint, render_template
from flask_login import current_user

from decorators import role_required


teacher_bp = Blueprint(
    "teacher",
    __name__,
    url_prefix="/teacher",
)


@teacher_bp.get("/dashboard")
@role_required("teacher")
def dashboard():
    """Display the teacher dashboard."""
    teacher_profile = current_user.teacher_profile

    return render_template(
        "teacher/dashboard.html",
        teacher=teacher_profile,
    )