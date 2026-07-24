from sqlalchemy import inspect

from app import create_app
from extensions import db

# Importing models registers every table with SQLAlchemy.
import models  # noqa: F401


def initialize_database() -> None:
    """Create all database tables for the local prototype."""
    app = create_app()

    with app.app_context():
        db.create_all()

        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        print("Database initialized successfully.")
        print(f"Total tables created: {len(table_names)}")

        for table_name in table_names:
            print(f"- {table_name}")


if __name__ == "__main__":
    initialize_database()