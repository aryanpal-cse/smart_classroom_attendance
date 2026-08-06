import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import current_app

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    cv2 = None
    np = None


class FaceRecognitionUnavailable(RuntimeError):
    """Raised when the local OpenCV face module is unavailable."""


class FaceImageError(ValueError):
    """Raised when the submitted camera frame cannot be processed."""


@dataclass
class FaceVerificationResult:
    """Result returned by the local LBPH verification service."""

    matched: bool
    predicted_student_id: int | None
    distance: float | None
    similarity_score: float | None
    reason: str


def _require_opencv() -> None:
    if cv2 is None or np is None:
        raise FaceRecognitionUnavailable(
            "OpenCV and NumPy are not installed. Run: "
            "pip install opencv-contrib-python numpy"
        )

    if not hasattr(cv2, "face"):
        raise FaceRecognitionUnavailable(
            "The OpenCV face module is unavailable. Install "
            "opencv-contrib-python, not opencv-python."
        )


def _decode_data_url(image_data: str):
    """Decode a browser canvas data URL into an OpenCV image."""
    _require_opencv()

    if not image_data or "," not in image_data:
        raise FaceImageError("No valid camera image was submitted.")

    _, encoded = image_data.split(",", 1)

    try:
        raw_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise FaceImageError("The captured image could not be decoded.") from error

    image_array = np.frombuffer(raw_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise FaceImageError("The captured image could not be opened.")

    return image


def _extract_largest_face(image):
    """Detect and normalize the largest visible face."""
    _require_opencv()

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))

    faces = detector.detectMultiScale(
        grayscale,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    # A second, slightly more tolerant pass helps ordinary laptop webcams
    # without accepting frames that contain no detectable face at all.
    if len(faces) == 0:
        faces = detector.detectMultiScale(
            grayscale,
            scaleFactor=1.05,
            minNeighbors=3,
            minSize=(60, 60),
        )

    if len(faces) == 0:
        raise FaceImageError(
            "No clear face was detected. Move closer, face the camera, "
            "and use even front lighting."
        )

    x, y, width, height = max(faces, key=lambda box: box[2] * box[3])
    face = grayscale[y : y + height, x : x + width]
    return cv2.resize(face, (200, 200))


def _student_face_directory(student_id: int) -> Path:
    root = Path(current_app.config["FACE_DATA_DIR"])
    return root / f"student_{student_id}"


def save_face_sample(student_id: int, image_data: str) -> tuple[str, int]:
    """Save one detected face sample and return its path and total count."""
    image = _decode_data_url(image_data)
    face = _extract_largest_face(image)

    directory = _student_face_directory(student_id)
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    sample_path = directory / f"sample_{timestamp}.jpg"

    if not cv2.imwrite(str(sample_path), face):
        raise FaceImageError("The local face sample could not be saved.")

    sample_count = len(list(directory.glob("*.jpg")))
    return str(sample_path), sample_count


def train_lbph_model() -> tuple[int, int]:
    """Train one local LBPH model from all registered student samples."""
    _require_opencv()

    root = Path(current_app.config["FACE_DATA_DIR"])
    images: list[Any] = []
    labels: list[int] = []
    registered_students: set[int] = set()

    for directory in sorted(root.glob("student_*")):
        if not directory.is_dir():
            continue

        try:
            student_id = int(directory.name.split("_", 1)[1])
        except (IndexError, ValueError):
            continue

        for sample_path in sorted(directory.glob("*.jpg")):
            image = cv2.imread(str(sample_path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                continue

            images.append(cv2.resize(image, (200, 200)))
            labels.append(student_id)
            registered_students.add(student_id)

    if not images:
        raise FaceImageError(
            "No face samples are available. Register at least one student first."
        )

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(images, np.array(labels, dtype=np.int32))

    model_path = Path(current_app.config["FACE_MODEL_PATH"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    recognizer.write(str(model_path))

    return len(images), len(registered_students)


def verify_student_face(
    expected_student_id: int,
    image_data: str,
) -> FaceVerificationResult:
    """Verify whether the captured face matches the logged-in student."""
    image = _decode_data_url(image_data)
    face = _extract_largest_face(image)

    model_path = Path(current_app.config["FACE_MODEL_PATH"])
    if not model_path.exists():
        raise FaceRecognitionUnavailable(
            "The local face model has not been trained yet."
        )

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(model_path))

    predicted_label, distance = recognizer.predict(face)
    max_distance = float(
        current_app.config["FACE_RECOGNITION_MAX_DISTANCE"]
    )

    # LBPH returns a distance: lower values indicate a closer match.
    similarity_score = round(max(0.0, min(100.0, 100.0 - distance)), 1)
    matched = (
        predicted_label == expected_student_id
        and distance <= max_distance
    )

    if matched:
        reason = "The captured face matched the logged-in student."
    elif predicted_label != expected_student_id:
        reason = "The detected face belongs to a different registered label."
    else:
        reason = "The face similarity was below the configured threshold."

    return FaceVerificationResult(
        matched=matched,
        predicted_student_id=int(predicted_label),
        distance=round(float(distance), 2),
        similarity_score=similarity_score,
        reason=reason,
    )
