from flask import Flask, render_template


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/health")
    def health():
        return {
            "status": "success",
            "message": "Smart Classroom Attendance System is running",
        }

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(host="127.0.0.1", port=5000, debug=True)