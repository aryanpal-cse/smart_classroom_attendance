from flask import Blueprint, render_template

from decorators import role_required


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


@admin_bp.get("/dashboard")
@role_required("admin")
def dashboard():
    """Display the administrator dashboard."""
    return render_template("admin/dashboard.html")