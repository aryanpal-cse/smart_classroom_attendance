import unittest

from app import create_app


class AuthenticationTestCase(unittest.TestCase):
    """Test login, logout and role-based dashboard protection."""

    def setUp(self) -> None:
        self.app = create_app()

        self.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
        )

        self.client = self.app.test_client()

    def login(self, username: str, password: str):
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

    def logout(self):
        """Log out the current test user."""
        return self.client.post(
            "/auth/logout",
            follow_redirects=True,
        )

    def test_admin_login_and_access(self) -> None:
        response = self.login("admin", "Admin@123")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Admin Dashboard", response.data)

        forbidden_response = self.client.get(
            "/teacher/dashboard",
        )

        self.assertEqual(forbidden_response.status_code, 403)

        self.logout()

    def test_teacher_login_and_access(self) -> None:
        response = self.login(
            "teacher1",
            "Teacher@123",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Teacher Dashboard", response.data)

        forbidden_response = self.client.get(
            "/admin/dashboard",
        )

        self.assertEqual(forbidden_response.status_code, 403)

        self.logout()

    def test_student_login_and_access(self) -> None:
        response = self.login(
            "student1",
            "Student@123",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Dashboard", response.data)

        forbidden_response = self.client.get(
            "/admin/dashboard",
        )

        self.assertEqual(forbidden_response.status_code, 403)

        self.logout()

    def test_invalid_password_is_rejected(self) -> None:
        response = self.login(
            "student1",
            "WrongPassword",
        )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            b"Invalid username or password.",
            response.data,
        )

        self.assertNotIn(
            b"Student Dashboard",
            response.data,
        )

    def test_logged_out_user_is_redirected(self) -> None:
        response = self.client.get(
            "/admin/dashboard",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.location)


if __name__ == "__main__":
    unittest.main(verbosity=2)