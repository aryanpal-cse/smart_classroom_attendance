import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Configuration for the local academic prototype."""

    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "local-development-key-change-before-real-deployment",
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'attendance.db'}",
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    ATTENDANCE_THRESHOLD = int(
        os.getenv("ATTENDANCE_THRESHOLD", "75")
    )

    FACE_DATA_DIR = BASE_DIR / "face_data"
    FACE_MODEL_PATH = FACE_DATA_DIR / "lbph_model.yml"
    FACE_SAMPLE_TARGET = int(
        os.getenv("FACE_SAMPLE_TARGET", "10")
    )
    FACE_RECOGNITION_MAX_DISTANCE = float(
        os.getenv("FACE_RECOGNITION_MAX_DISTANCE", "70.0")
    )

    REPORTS_DIR = BASE_DIR / "reports"
