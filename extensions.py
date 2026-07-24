import sqlite3

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id: str):
    """Load the logged-in user from the database session."""
    from models import User

    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(
    database_connection,
    connection_record,
) -> None:
    """Enable foreign-key validation for SQLite connections."""
    del connection_record

    if isinstance(database_connection, sqlite3.Connection):
        cursor = database_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()