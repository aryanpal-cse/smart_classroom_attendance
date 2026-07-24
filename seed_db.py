from datetime import time

from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
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


def seed_database() -> None:
    """Insert a small demonstration dataset into the local database."""
    app = create_app()

    with app.app_context():
        db.create_all()

        # Prevent accidental duplicate seed records.
        if User.query.first() is not None:
            print("Seed data was not added.")
            print("Reason: The database already contains user records.")
            return

        try:
            admin_user = User(
                username="admin",
                password_hash=generate_password_hash("Admin@123"),
                role="admin",
            )

            class_section = ClassSection(
                name="CSE-AIML",
                section="A",
                semester=3,
                academic_year="2026-27",
            )

            subjects = [
                Subject(
                    name="Data Structures",
                    code="DS301",
                    semester=3,
                ),
                Subject(
                    name="Python Programming",
                    code="PY302",
                    semester=3,
                ),
                Subject(
                    name="Database Management Systems",
                    code="DB303",
                    semester=3,
                ),
            ]

            teacher_users = [
                User(
                    username="teacher1",
                    password_hash=generate_password_hash("Teacher@123"),
                    role="teacher",
                ),
                User(
                    username="teacher2",
                    password_hash=generate_password_hash("Teacher@123"),
                    role="teacher",
                ),
            ]

            teachers = [
                Teacher(
                    user=teacher_users[0],
                    employee_id="TCH-001",
                    full_name="Demo Teacher One",
                    email="teacher1@example.local",
                ),
                Teacher(
                    user=teacher_users[1],
                    employee_id="TCH-002",
                    full_name="Demo Teacher Two",
                    email="teacher2@example.local",
                ),
            ]

            student_users = []
            students = []

            for number in range(1, 11):
                student_user = User(
                    username=f"student{number}",
                    password_hash=generate_password_hash("Student@123"),
                    role="student",
                )

                student = Student(
                    user=student_user,
                    class_section=class_section,
                    roll_number=f"AIML-{number:03d}",
                    full_name=f"Demo Student {number}",
                    email=f"student{number}@example.local",
                )

                student_users.append(student_user)
                students.append(student)

            db.session.add(admin_user)
            db.session.add(class_section)
            db.session.add_all(subjects)
            db.session.add_all(teacher_users)
            db.session.add_all(teachers)
            db.session.add_all(student_users)
            db.session.add_all(students)

            # Flush assigns database IDs without committing yet.
            db.session.flush()

            assignments = [
                TeachingAssignment(
                    teacher=teachers[0],
                    subject=subjects[0],
                    class_section=class_section,
                ),
                TeachingAssignment(
                    teacher=teachers[0],
                    subject=subjects[1],
                    class_section=class_section,
                ),
                TeachingAssignment(
                    teacher=teachers[1],
                    subject=subjects[2],
                    class_section=class_section,
                ),
            ]

            db.session.add_all(assignments)
            db.session.flush()

            timetable_entries = [
                Timetable(
                    assignment=assignments[0],
                    day_of_week="Monday",
                    start_time=time(10, 0),
                    end_time=time(11, 0),
                    room_number="Lab 1",
                ),
                Timetable(
                    assignment=assignments[1],
                    day_of_week="Tuesday",
                    start_time=time(11, 0),
                    end_time=time(12, 0),
                    room_number="Lab 2",
                ),
                Timetable(
                    assignment=assignments[2],
                    day_of_week="Wednesday",
                    start_time=time(12, 0),
                    end_time=time(13, 0),
                    room_number="Room 203",
                ),
            ]

            db.session.add_all(timetable_entries)

            enrollments = []

            for student in students:
                for subject in subjects:
                    enrollments.append(
                        Enrollment(
                            student=student,
                            class_section=class_section,
                            subject=subject,
                        )
                    )

            db.session.add_all(enrollments)
            db.session.commit()

            print("\nSAMPLE DATA CREATED")
            print("=" * 40)
            print(f"Administrators: {User.query.filter_by(role='admin').count()}")
            print(f"Teachers: {Teacher.query.count()}")
            print(f"Students: {Student.query.count()}")
            print(f"Classes: {ClassSection.query.count()}")
            print(f"Subjects: {Subject.query.count()}")
            print(f"Assignments: {TeachingAssignment.query.count()}")
            print(f"Timetable entries: {Timetable.query.count()}")
            print(f"Enrollments: {Enrollment.query.count()}")
            print("Status: SEEDING COMPLETED")

        except Exception as error:
            db.session.rollback()
            print("Seed data creation failed.")
            print(f"Error: {error}")
            raise


if __name__ == "__main__":
    seed_database()