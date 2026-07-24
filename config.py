from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration for the local academic prototype."""

    SECRET_KEY = "development-only-change-later"
    SQLALCHEMY_DATABASE_URI = (
        f"sqlite:///{BASE_DIR / 'instance' / 'attendance.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ATTENDANCE_THRESHOLD = 75