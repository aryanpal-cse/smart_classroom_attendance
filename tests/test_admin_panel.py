import unittest

from app import create_app
from extensions import db
from models import ClassSection, Student, Subject, Teacher


class AdminPanelTestCase(unittest.TestCase):
    """Test Admin Panel pages and access protection."""

    def setUp(self) -> None:
        """Create the Flask test client and load existing record IDs."""
        self.app = create_app()

        self.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
        )

        self.client = self.app.test_client()

        with self.app.app_context():
            student = Student.query.order_by(Student.id).first()
            teacher = Teacher.query.order_by(Teacher.id).first()
            subject = Subject.query.order_by(Subject.id).first()
            class_section = ClassSection.query.order_by(
                ClassSection.id
            ).first()

            self.student_id = student.id if student else None
            self.teacher_id = teacher.id if teacher else None
            self.subject_id = subject.id if subject else None
            self.class_id = (
                class_section.id
                if class_section
                else None
            )

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

    def login_as_admin(self) -> None:
        """Log in with the administrator demonstration account."""
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

    def test_admin_dashboard_opens(self) -> None:
        """The administrator dashboard should open."""
        self.login_as_admin()

        response = self.client.get(
            "/admin/dashboard",
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
            b"Class Sections",
            response.data,
        )

        self.assertIn(
            b"/admin/classes",
            response.data,
        )

    def test_student_management_pages_open(self) -> None:
        """Student list, add and edit pages should open."""
        self.login_as_admin()

        list_response = self.client.get(
            "/admin/students",
        )

        self.assertEqual(
            list_response.status_code,
            200,
        )

        self.assertIn(
            b"Student Management",
            list_response.data,
        )

        add_response = self.client.get(
            "/admin/students/add",
        )

        self.assertEqual(
            add_response.status_code,
            200,
        )

        self.assertIn(
            b"Add Student",
            add_response.data,
        )

        self.assertIsNotNone(
            self.student_id,
            "No student record is available for the edit-page test.",
        )

        edit_response = self.client.get(
            f"/admin/students/{self.student_id}/edit",
        )

        self.assertEqual(
            edit_response.status_code,
            200,
        )

        self.assertIn(
            b"Edit Student",
            edit_response.data,
        )

    def test_teacher_management_pages_open(self) -> None:
        """Teacher list, add and edit pages should open."""
        self.login_as_admin()

        list_response = self.client.get(
            "/admin/teachers",
        )

        self.assertEqual(
            list_response.status_code,
            200,
        )

        self.assertIn(
            b"Teacher Management",
            list_response.data,
        )

        add_response = self.client.get(
            "/admin/teachers/add",
        )

        self.assertEqual(
            add_response.status_code,
            200,
        )

        self.assertIn(
            b"Add Teacher",
            add_response.data,
        )

        self.assertIsNotNone(
            self.teacher_id,
            "No teacher record is available for the edit-page test.",
        )

        edit_response = self.client.get(
            f"/admin/teachers/{self.teacher_id}/edit",
        )

        self.assertEqual(
            edit_response.status_code,
            200,
        )

        self.assertIn(
            b"Edit Teacher",
            edit_response.data,
        )

    def test_subject_management_pages_open(self) -> None:
        """Subject list, add and edit pages should open."""
        self.login_as_admin()

        list_response = self.client.get(
            "/admin/subjects",
        )

        self.assertEqual(
            list_response.status_code,
            200,
        )

        self.assertIn(
            b"Subject Management",
            list_response.data,
        )

        add_response = self.client.get(
            "/admin/subjects/add",
        )

        self.assertEqual(
            add_response.status_code,
            200,
        )

        self.assertIn(
            b"Add Subject",
            add_response.data,
        )

        self.assertIsNotNone(
            self.subject_id,
            "No subject record is available for the edit-page test.",
        )

        edit_response = self.client.get(
            f"/admin/subjects/{self.subject_id}/edit",
        )

        self.assertEqual(
            edit_response.status_code,
            200,
        )

        self.assertIn(
            b"Edit Subject",
            edit_response.data,
        )

    def test_class_management_pages_open(self) -> None:
        """Class-section list, add and edit pages should open."""
        self.login_as_admin()

        list_response = self.client.get(
            "/admin/classes",
        )

        self.assertEqual(
            list_response.status_code,
            200,
        )

        self.assertIn(
            b"Class Section Management",
            list_response.data,
        )

        add_response = self.client.get(
            "/admin/classes/add",
        )

        self.assertEqual(
            add_response.status_code,
            200,
        )

        self.assertIn(
            b"Add Class Section",
            add_response.data,
        )

        self.assertIsNotNone(
            self.class_id,
            "No class-section record is available for the edit-page test.",
        )

        edit_response = self.client.get(
            f"/admin/classes/{self.class_id}/edit",
        )

        self.assertEqual(
            edit_response.status_code,
            200,
        )

        self.assertIn(
            b"Edit Class Section",
            edit_response.data,
        )

    def test_student_cannot_access_admin_panel(self) -> None:
        """A student should receive a forbidden response."""
        login_response = self.login(
            username="student1",
            password="Student@123",
        )

        self.assertEqual(
            login_response.status_code,
            200,
        )

        self.assertEqual(
            login_response.request.path,
            "/student/dashboard",
        )

        admin_response = self.client.get(
            "/admin/dashboard",
        )

        self.assertEqual(
            admin_response.status_code,
            403,
        )

    def test_logged_out_user_is_redirected(self) -> None:
        """A logged-out user should be redirected to login."""
        response = self.client.get(
            "/admin/dashboard",
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

    def test_invalid_admin_page_returns_404(self) -> None:
        """An invalid administrator URL should return 404."""
        self.login_as_admin()

        response = self.client.get(
            "/admin/not-a-real-page",
        )

        self.assertEqual(
            response.status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)