# Smart Classroom Attendance System

AI-Based Smart Classroom Attendance and Analytics System Using Dynamic Class Codes and Face Recognition.

## Academic Project

- Course: B.Tech CSE (AI & ML)
- Semester: III
- University: AKTU
- Project type: College mini-project prototype
- Application type: Local Flask web application

## Current Development Status

### Phase 1 — Project Setup

Completed:

- Flask project structure
- Virtual environment
- Local development server
- Homepage
- Health-check route
- Initial configuration
- Git repository setup

### Phase 2 — Database Design

Completed:

- Flask-SQLAlchemy configuration
- Local SQLite database
- Foreign-key enforcement
- 13 relational database tables
- Student and teacher profiles
- Classes and subjects
- Teaching assignments
- Student enrolments
- Timetable
- Class sessions
- Face-data metadata
- Attendance records
- Manual-review requests
- Audit logs
- Small demonstration dataset
- Database verification scripts
- ER diagram and schema documentation

## Technology Stack

- Python 3.12
- Flask
- Flask-SQLAlchemy
- SQLAlchemy
- SQLite
- HTML
- CSS
- JavaScript
- Bootstrap
- Chart.js
- OpenCV Contrib

## Free and Open-Source Requirement

The project uses only free or open-source technologies.

It does not require:

- Paid APIs
- Paid AI services
- Cloud deployment
- API keys
- Subscription services
- Credit cards
- Special biometric hardware

## Database

The local database is:

```text
instance/attendance.db
### Phase 3 — Authentication and Role-Based Access

Completed:

- Local username and password authentication
- Password-hash verification
- Flask-Login session management
- Flask-WTF CSRF protection
- Admin, teacher and student login
- Role-based dashboard redirection
- Protected Admin Panel
- Protected Teacher Panel
- Protected Student Panel
- Secure POST logout
- Inactive-account validation
- Invalid-login protection
- Unauthenticated-user redirection
- 403 access-denied page
- 404 page-not-found page
- Five automated authentication tests

Verified demonstration accounts:

- Admin: `admin`
- Teacher: `teacher1`
- Student: `student1`

Authentication tests completed:

- Admin login and authorization — Passed
- Teacher login and authorization — Passed
- Student login and authorization — Passed
- Incorrect-password rejection — Passed
- Logged-out-user redirection — Passed