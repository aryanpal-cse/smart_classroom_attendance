from sqlalchemy import inspect, text

from extensions import db


COLUMN_UPGRADES = {
    "teachers": [
        ("designation", "VARCHAR(100) NOT NULL DEFAULT 'Assistant Professor'"),
        ("phone", "VARCHAR(20)"),
        ("joining_date", "DATE"),
    ],
    "students": [
        ("phone", "VARCHAR(20)"),
    ],
    "classes": [
        ("course", "VARCHAR(100) NOT NULL DEFAULT 'B.Tech'"),
        ("group_name", "VARCHAR(50) NOT NULL DEFAULT 'General'"),
    ],
}


def ensure_schema_compatibility() -> list[str]:
    """Create missing tables and add final-version SQLite columns safely."""
    # All models are imported before create_app() calls this function.
    # create_all() creates only missing tables and preserves existing data.
    db.create_all()

    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    applied: list[str] = []

    with db.engine.begin() as connection:
        for table_name, columns in COLUMN_UPGRADES.items():
            if table_name not in table_names:
                continue

            existing = {
                column["name"]
                for column in inspector.get_columns(table_name)
            }

            for column_name, definition in columns:
                if column_name in existing:
                    continue

                connection.execute(
                    text(
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN "{column_name}" {definition}'
                    )
                )
                applied.append(f"{table_name}.{column_name}")

    return applied
