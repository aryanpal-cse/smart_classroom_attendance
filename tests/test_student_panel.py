import unittest

from app import create_app
from extensions import db


class StudentPanelTestCase(unittest.TestCase):
    """Test Student Panel pages and role protection."""

    def setUp(self) -> None:
        """Create a Flask test client before every test."""
        self.app = create_app()

        self.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
        )

        self.client = self.app.test_client()

    def tearDown(self) -> None:
        """Remove the database session after every test."""
        with self.app.app_context():
            db.session.remove()

    def login(
        self,
        username: str,
        password: str,
    ):
        """Submit the local login form."""
        return self.client.post(
            "/auth/login",
            data={
                "username": username,
                "password": password,
                "remember_me": False,
            },
            follow_redirects=True,
        )

    def login_as_student(self) -> None:
        """Log in using the demonstration student account."""
        response = self.login(
            username="student1",
            password="Student@123",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.request.path,
            "/student/dashboard",
        )

    def test_student_dashboard_opens(self) -> None:
        """The student dashboard should open after login."""
        self.login_as_student()

        response = self.client.get(
            "/student/dashboard",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.request.path,
            "/student/dashboard",
        )

        self.assertIn(
            b"Student Dashboard",
            response.data,
        )

        self.assertIn(
            b"/student/subjects",
            response.data,
        )

    def test_student_subjects_page_opens(self) -> None:
        """The student's subject page should open."""
        self.login_as_student()

        response = self.client.get(
            "/student/subjects",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.request.path,
            "/student/subjects",
        )

        self.assertIn(
            b"My Subjects",
            response.data,
        )

        self.assertIn(
            b"Enrolled Subjects",
            response.data,
        )

    def test_face_recognition_center_opens(self) -> None:
        """The student should see a dedicated face-recognition section."""
        self.login_as_student()
        response = self.client.get("/student/face-recognition")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Face Recognition Center", response.data)
        self.assertIn(b"Register or Update Face", response.data)

    def test_admin_cannot_access_student_panel(self) -> None:
        """An administrator should not access student-only pages."""
        login_response = self.login(
            username="admin",
            password="Admin@123",
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        response = self.client.get(
            "/student/dashboard",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_teacher_cannot_access_student_panel(self) -> None:
        """A teacher should not access student-only pages."""
        login_response = self.login(
            username="teacher1",
            password="Teacher@123",
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        response = self.client.get(
            "/student/dashboard",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_logged_out_user_is_redirected(self) -> None:
        """A logged-out visitor should be redirected to login."""
        response = self.client.get(
            "/student/dashboard",
            follow_redirects=False,
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        location = response.headers.get(
            "Location",
            "",
        )

        self.assertIn(
            "/auth/login",
            location,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)