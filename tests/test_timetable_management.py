import unittest

from app import create_app
from extensions import db
from models import Timetable


class TimetableManagementTestCase(unittest.TestCase):
    """Test Admin timetable pages and role protection."""

    def setUp(self) -> None:
        self.app = create_app()

        self.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
        )

        self.client = self.app.test_client()

        with self.app.app_context():
            timetable_entry = Timetable.query.order_by(
                Timetable.id.asc()
            ).first()

            self.timetable_id = (
                timetable_entry.id
                if timetable_entry
                else None
            )

    def tearDown(self) -> None:
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

    def login_as_admin(self) -> None:
        """Log in using the administrator account."""
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

    def test_timetable_list_page_opens(self) -> None:
        """The timetable management page should open."""
        self.login_as_admin()

        response = self.client.get(
            "/admin/timetable",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            b"Timetable Management",
            response.data,
        )

        self.assertIn(
            b"/admin/timetable/add",
            response.data,
        )

    def test_add_timetable_page_opens(self) -> None:
        """The Add Timetable Entry page should open."""
        self.login_as_admin()

        response = self.client.get(
            "/admin/timetable/add",
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            b"Add Timetable Entry",
            response.data,
        )

        self.assertIn(
            b"teaching_assignment_id",
            response.data,
        )

        self.assertIn(
            b"day_of_week",
            response.data,
        )

        self.assertIn(
            b"start_time",
            response.data,
        )

        self.assertIn(
            b"end_time",
            response.data,
        )

    def test_edit_timetable_page_opens(self) -> None:
        """The Edit Timetable Entry page should open."""
        self.login_as_admin()

        self.assertIsNotNone(
            self.timetable_id,
            "At least one timetable entry is required.",
        )

        response = self.client.get(
            (
                f"/admin/timetable/"
                f"{self.timetable_id}/edit"
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            b"Edit Timetable Entry",
            response.data,
        )

    def test_invalid_timetable_entry_returns_404(self) -> None:
        """An unknown timetable ID should return 404."""
        self.login_as_admin()

        response = self.client.get(
            "/admin/timetable/999999/edit",
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_teacher_cannot_access_timetable_management(
        self,
    ) -> None:
        """A teacher should not access Admin timetable pages."""
        login_response = self.login(
            username="teacher1",
            password="Teacher@123",
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        response = self.client.get(
            "/admin/timetable",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_student_cannot_access_timetable_management(
        self,
    ) -> None:
        """A student should not access Admin timetable pages."""
        login_response = self.login(
            username="student1",
            password="Student@123",
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        response = self.client.get(
            "/admin/timetable/add",
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_logged_out_user_is_redirected(self) -> None:
        """A logged-out visitor should be redirected to login."""
        response = self.client.get(
            "/admin/timetable",
            follow_redirects=False,
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            "/auth/login",
            response.headers.get("Location", ""),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)