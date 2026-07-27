import unittest

from app import create_app
from extensions import db


class AuthenticationTestCase(unittest.TestCase):
    """Test login, logout and role-based dashboard access."""

    def setUp(self) -> None:
        """Create a new Flask test client before each test."""
        self.app = create_app()

        self.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
        )

        self.client = self.app.test_client()

    def tearDown(self) -> None:
        """Remove the database session after each test."""
        with self.app.app_context():
            db.session.remove()

    def login(
        self,
        username: str,
        password: str,
    ):
        """Submit the login form."""
        return self.client.post(
            "/auth/login",
            data={
                "username": username,
                "password": password,
                "remember_me": False,
            },
            follow_redirects=True,
        )

    def test_admin_login_and_access(self) -> None:
        """Admin should log in and open the admin dashboard."""
        response = self.login(
            username="admin",
            password="Admin@123",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.request.path,
            "/admin/dashboard",
        )

        self.assertIn(
            b"/admin/classes",
            response.data,
        )

    def test_teacher_login_and_access(self) -> None:
        """Teacher should log in and open the teacher dashboard."""
        response = self.login(
            username="teacher1",
            password="Teacher@123",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.request.path,
            "/teacher/dashboard",
        )

        self.assertIn(
            b"Teacher Dashboard",
            response.data,
        )

    def test_student_login_and_access(self) -> None:
        """Student should log in and open the student dashboard."""
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

    def test_invalid_login_is_rejected(self) -> None:
        """An incorrect password should not create a login session."""
        response = self.login(
            username="admin",
            password="WrongPassword123",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.request.path,
            "/auth/login",
        )

        protected_response = self.client.get(
            "/admin/dashboard",
            follow_redirects=False,
        )

        self.assertEqual(
            protected_response.status_code,
            302,
        )

    def test_logged_out_user_is_redirected(self) -> None:
        """A logged-out user should be redirected to login."""
        response = self.client.get(
            "/teacher/dashboard",
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