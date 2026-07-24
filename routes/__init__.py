from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.student import student_bp
from routes.teacher import teacher_bp


__all__ = [
    "auth_bp",
    "admin_bp",
    "teacher_bp",
    "student_bp",
]