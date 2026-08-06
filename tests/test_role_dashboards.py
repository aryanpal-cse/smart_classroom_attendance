import unittest

from app import create_app
from extensions import db


class RoleDashboardTestCase(unittest.TestCase):
    """Test the role-specific profile, class and timetable pages."""

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

    def test_teacher_personal_pages_and_weekly_timetable(self) -> None:
        self.login("teacher1", "Teacher@123")

        for path in [
            "/teacher/profile",
            "/teacher/classes",
            "/teacher/programs",
            "/teacher/timetable",
            "/teacher/attendance",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(b"Demo Teacher One", response.data)

        timetable_response = self.client.get("/teacher/timetable")
        self.assertIn(b"Data Structures", timetable_response.data)
        self.assertIn(b"Monday", timetable_response.data)

    def test_student_personal_pages_and_weekly_timetable(self) -> None:
        self.login("student1", "Student@123")

        for path in [
            "/student/profile",
            "/student/course",
            "/student/subjects",
            "/student/timetable",
            "/student/attendance",
            "/student/face-recognition",
        ]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(b"Demo Student 1", response.data)

        timetable_response = self.client.get("/student/timetable")
        self.assertIn(b"Data Structures", timetable_response.data)
        self.assertIn(b"Demo Teacher One", timetable_response.data)
        self.assertIn(b"Monday", timetable_response.data)

    def test_admin_teacher_and_student_management_flows(self) -> None:
        self.login("admin", "Admin@123")

        teacher_home = self.client.get("/admin/management/teachers")
        self.assertEqual(teacher_home.status_code, 200)
        self.assertIn(b"Select Department", teacher_home.data)

        student_home = self.client.get("/admin/management/students")
        self.assertEqual(student_home.status_code, 200)
        self.assertIn(b"Select Course", student_home.data)

        branches = self.client.get(
            "/admin/management/students/branches?course=B.Tech"
        )
        self.assertEqual(branches.status_code, 200)
        self.assertIn(b"CSE-AIML", branches.data)

    def test_admin_face_recognition_status_page(self) -> None:
        self.login("admin", "Admin@123")
        response = self.client.get(
            "/admin/management/students/face-recognition"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Face Recognition Status", response.data)

    def test_teacher_attendance_pages_are_role_protected(self) -> None:
        self.login("teacher1", "Teacher@123")
        response = self.client.get("/admin/management/teachers/attendance")
        self.assertEqual(response.status_code, 403)

        own_response = self.client.get("/teacher/attendance")
        self.assertEqual(own_response.status_code, 200)
        self.assertIn(b"My Attendance", own_response.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
