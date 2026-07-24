import sqlite3

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine


db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(
    database_connection,
    connection_record,
) -> None:
    """Enable foreign-key enforcement for SQLite connections."""
    del connection_record

    if isinstance(database_connection, sqlite3.Connection):
        cursor = database_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()