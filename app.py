from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, render_template, request, url_for
from flask_login import current_user

from config import Config
from extensions import csrf, db, login_manager
from routes import admin_bp, auth_bp, student_bp, teacher_bp
from schema_upgrade import ensure_schema_compatibility


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration before initializing extensions.
    app.config.from_object(Config)

    # Ensure local folders exist on a fresh computer.
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["FACE_DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["REPORTS_DIR"]).mkdir(parents=True, exist_ok=True)

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

    # Upgrade older local SQLite files without deleting existing data.
    with app.app_context():
        applied_upgrades = ensure_schema_compatibility()
        if applied_upgrades:
            print("Applied database upgrades:", ", ".join(applied_upgrades))

    @app.context_processor
    def shared_navigation_context() -> dict:
        """Provide a safe Back link and role dashboard URL to every page."""
        dashboard_url = url_for("home")

        if current_user.is_authenticated:
            dashboard_url = url_for(
                current_user.get_dashboard_endpoint()
            )

        back_url = dashboard_url
        referrer = request.referrer

        if referrer:
            parsed_referrer = urlparse(referrer)
            parsed_host = urlparse(request.host_url)

            same_host = (
                parsed_referrer.scheme == parsed_host.scheme
                and parsed_referrer.netloc == parsed_host.netloc
            )

            if same_host and referrer != request.url:
                back_url = referrer

        return {
            "global_back_url": back_url,
            "role_dashboard_url": dashboard_url,
            "show_global_back": request.endpoint != "home",
        }

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
            "attendance_methods": [
                "face recognition",
                "teacher manual review",
            ],
        }

    @app.errorhandler(400)
    def bad_request(error):
        """Display a friendly page for invalid form submissions."""
        return render_template(
            "errors/400.html",
            error=error,
        ), 400

    @app.errorhandler(403)
    def forbidden(error):
        """Display a friendly page for unauthorized role access."""
        return render_template(
            "errors/403.html",
            error=error,
        ), 403

    @app.errorhandler(404)
    def page_not_found(error):
        """Display a friendly page when a route is not found."""
        return render_template(
            "errors/404.html",
            error=error,
        ), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        """Display a friendly page for unexpected local errors."""
        db.session.rollback()
        return render_template(
            "errors/500.html",
            error=error,
        ), 500

    return app


if __name__ == "__main__":
    application = create_app()

    application.run(
        host="127.0.0.1",
        port=5000,
        debug=application.config["DEBUG"],
    )
