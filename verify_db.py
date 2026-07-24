from sqlalchemy import inspect, text

from app import create_app
from extensions import db

# Register all database models.
import models  # noqa: F401


EXPECTED_TABLES = {
    "users",
    "students",
    "teachers",
    "classes",
    "subjects",
    "teaching_assignments",
    "enrollments",
    "timetable",
    "class_sessions",
    "face_data",
    "attendance",
    "manual_review_requests",
    "audit_logs",
}


def verify_database() -> None:
    """Check tables and SQLite foreign-key enforcement."""
    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        print("\nDATABASE VERIFICATION")
        print("=" * 40)

        missing_tables = EXPECTED_TABLES - existing_tables

        if missing_tables:
            print("Status: FAILED")
            print("Missing tables:")

            for table_name in sorted(missing_tables):
                print(f"- {table_name}")

            return

        print("Table check: PASSED")
        print(f"Tables found: {len(existing_tables)}")

        foreign_key_status = db.session.execute(
            text("PRAGMA foreign_keys")
        ).scalar()

        if foreign_key_status == 1:
            print("Foreign-key enforcement: ENABLED")
        else:
            print("Foreign-key enforcement: DISABLED")

        database_url = app.config["SQLALCHEMY_DATABASE_URI"]

        print(f"Database URL: {database_url}")
        print("Status: DATABASE READY")


if __name__ == "__main__":
    verify_database()