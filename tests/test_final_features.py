import unittest

from app import create_app
from extensions import db


class FinalFeatureTestCase(unittest.TestCase):
    """Smoke tests for the final academic-prototype pages."""

    def setUp(self) -> None:
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        with self.app.app_context():
            db.session.remove()

    def login(self, username: str, password: str):
        return self.client.post(
            "/auth/login",
            data={
                "username": username,
                "password": password,
                "remember_me": False,
            },
            follow_redirects=True,
        )

    def test_global_back_button_is_available(self) -> None:
        self.login("admin", "Admin@123")
        response = self.client.get("/admin/management/teachers")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"header-back-link", response.data)
        self.assertIn(b"Back", response.data)

    def test_admin_final_management_pages_open(self) -> None:
        self.login("admin", "Admin@123")

        for path in [
            "/admin/assignments",
            "/admin/assignments/add",
            "/admin/attendance",
            "/admin/attendance/analytics",
            "/admin/audit-logs",
            "/admin/management/teachers/1",
            "/admin/management/teachers/attendance",
            "/admin/management/teachers/attendance/add",
            "/admin/management/teachers/timetables",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_student_hierarchy_reaches_section_level(self) -> None:
        self.login("admin", "Admin@123")

        paths = [
            "/admin/management/students",
            "/admin/management/students/branches?course=B.Tech",
            (
                "/admin/management/students/years"
                "?course=B.Tech&branch=CSE-AIML"
            ),
            (
                "/admin/management/students/groups"
                "?course=B.Tech&branch=CSE-AIML&year=2026-27"
            ),
            (
                "/admin/management/students/sections"
                "?course=B.Tech&branch=CSE-AIML&year=2026-27"
                "&group=General&semester=3"
            ),
            "/admin/management/students/sections/1",
        ]

        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_teacher_final_pages_open(self) -> None:
        self.login("teacher1", "Teacher@123")

        for path in [
            "/teacher/dashboard",
            "/teacher/timetable",
            "/teacher/sessions",
            "/teacher/history",
            "/teacher/attendance",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_student_face_and_attendance_pages_open(self) -> None:
        self.login("student1", "Student@123")

        for path in [
            "/student/dashboard",
            "/student/timetable",
            "/student/join",
            "/student/face/register",
            "/student/attendance",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_admin_csv_export_is_available(self) -> None:
        self.login("admin", "Admin@123")
        response = self.client.get("/admin/attendance/export.csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.content_type)
        self.assertIn(
            "attachment",
            response.headers.get("Content-Disposition", ""),
        )

    def test_cross_role_final_pages_are_blocked(self) -> None:
        self.login("student1", "Student@123")

        self.assertEqual(
            self.client.get("/admin/attendance").status_code,
            403,
        )
        self.assertEqual(
            self.client.get("/teacher/sessions").status_code,
            403,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
