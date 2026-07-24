from werkzeug.security import check_password_hash

from app import create_app
from models import (
    ClassSection,
    Enrollment,
    Student,
    Subject,
    Teacher,
    TeachingAssignment,
    Timetable,
    User,
)


def verify_seed_data() -> None:
    """Verify the sample records and important relationships."""
    app = create_app()

    with app.app_context():
        print("\nSAMPLE DATA VERIFICATION")
        print("=" * 45)

        checks = {
            "Admin users": User.query.filter_by(role="admin").count() == 1,
            "Teacher profiles": Teacher.query.count() == 2,
            "Student profiles": Student.query.count() == 10,
            "Class sections": ClassSection.query.count() == 1,
            "Subjects": Subject.query.count() == 3,
            "Teaching assignments": TeachingAssignment.query.count() == 3,
            "Timetable entries": Timetable.query.count() == 3,
            "Student enrollments": Enrollment.query.count() == 30,
        }

        all_passed = True

        for check_name, passed in checks.items():
            status = "PASSED" if passed else "FAILED"
            print(f"{check_name}: {status}")

            if not passed:
                all_passed = False

        print("\nRELATIONSHIP CHECKS")
        print("-" * 45)

        first_student = Student.query.order_by(Student.id).first()
        first_teacher = Teacher.query.order_by(Teacher.id).first()
        first_assignment = TeachingAssignment.query.order_by(
            TeachingAssignment.id
        ).first()
        first_timetable = Timetable.query.order_by(Timetable.id).first()

        if first_student:
            print(
                "First student:",
                first_student.roll_number,
                "-",
                first_student.full_name,
            )
            print(
                "Student class:",
                first_student.class_section.name,
                first_student.class_section.section,
            )
            print(
                "Student subject enrollments:",
                len(first_student.enrollments),
            )
        else:
            print("First student: NOT FOUND")
            all_passed = False

        if first_teacher:
            print(
                "First teacher:",
                first_teacher.employee_id,
                "-",
                first_teacher.full_name,
            )
        else:
            print("First teacher: NOT FOUND")
            all_passed = False

        if first_assignment:
            print(
                "First assignment:",
                first_assignment.teacher.full_name,
                "teaches",
                first_assignment.subject.name,
                "to",
                first_assignment.class_section.name,
                first_assignment.class_section.section,
            )
        else:
            print("First assignment: NOT FOUND")
            all_passed = False

        if first_timetable:
            print(
                "First timetable:",
                first_timetable.day_of_week,
                first_timetable.start_time,
                "-",
                first_timetable.end_time,
            )
        else:
            print("First timetable: NOT FOUND")
            all_passed = False

        print("\nPASSWORD HASH CHECK")
        print("-" * 45)

        admin_user = User.query.filter_by(username="admin").first()

        if admin_user and check_password_hash(
            admin_user.password_hash,
            "Admin@123",
        ):
            print("Admin password hash: PASSED")
        else:
            print("Admin password hash: FAILED")
            all_passed = False

        print("\nFINAL RESULT")
        print("=" * 45)

        if all_passed:
            print("Status: SAMPLE DATABASE READY")
        else:
            print("Status: VERIFICATION FAILED")


if __name__ == "__main__":
    verify_seed_data()