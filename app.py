from flask import Flask, render_template

from config import Config
from extensions import db


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load application and database settings.
    app.config.from_object(Config)

    # Connect Flask-SQLAlchemy to this Flask application.
    db.init_app(app)

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/health")
    def health():
        return {
            "status": "success",
            "message": "Smart Classroom Attendance System is running",
            "database": "SQLite configured",
        }

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5000, debug=True)