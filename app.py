from flask import Flask, render_template

from config import Config
from extensions import csrf, db, login_manager
from routes import admin_bp, auth_bp, student_bp, teacher_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration before initializing extensions.
    app.config.from_object(Config)

    # Initialize database, login sessions and CSRF protection.
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configure Flask-Login.
    login_manager.login_view = "auth.login"
    login_manager.login_message = (
        "Please log in to access this page."
    )
    login_manager.login_message_category = "warning"

    # Register application route groups.
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)

    @app.get("/")
    def home():
        """Display the public project homepage."""
        return render_template("home.html")

    @app.get("/health")
    def health():
        """Return the local application health status."""
        return {
            "status": "success",
            "message": (
                "Smart Classroom Attendance System is running"
            ),
            "database": "SQLite configured",
            "authentication": "Flask-Login configured",
            "csrf_protection": "enabled",
            "registered_panels": [
                "admin",
                "teacher",
                "student",
            ],
        }

    @app.errorhandler(403)
    def forbidden(error):
        """Display a friendly page for unauthorized role access."""
        del error

        return render_template(
            "errors/403.html",
        ), 403

    @app.errorhandler(404)
    def page_not_found(error):
        """Display a friendly page when a route is not found."""
        del error

        return render_template(
            "errors/404.html",
        ), 404

    return app


if __name__ == "__main__":
    application = create_app()

    application.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )