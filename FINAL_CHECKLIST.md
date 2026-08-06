# Final Local Test Checklist

Complete these checks before the final Git commit.

## 1. Install and start

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py
python app.py
```

## 2. Automated tests

```powershell
python -m unittest discover -s tests -v
```

Expected: 41 tests pass.

## 3. Admin checks

- Login as `admin`.
- Confirm the dashboard has only Teacher Management and Student Management.
- Open Teacher Management.
- Open a department and teacher record.
- Add/edit a teaching assignment.
- View the teacher weekly timetable.
- Add and edit teacher attendance with a correction reason.
- Open Student Management.
- Navigate Course → Branch → Academic Year → Group → Section.
- Open the section timetable and student roster.
- Open Student Attendance, Analytics, CSV Export and Audit Logs.

## 4. Teacher checks

- Login as `teacher1`.
- Confirm only the logged-in teacher's profile/classes are visible.
- Open the weekly timetable.
- Start a live class and generate a six-character code.
- Open the live roster.
- End the session.
- Resolve pending manual reviews.
- Finalize the session.
- Confirm missing student records become absent.
- Open My Attendance.

## 5. Student and camera checks

- Login as `student1`.
- Confirm only the logged-in student's information is visible.
- Open the weekly timetable.
- Register face samples in good lighting.
- Join a live class using the teacher's temporary code.
- Complete face verification.
- Confirm attendance appears only once.
- Test a failed verification and manual-review request.
- Confirm low-attendance warnings and detailed history.

## 6. Back-button check

Open pages in all three panels and confirm the global Back button is visible
in the header. It should return to the previous same-site page or the role
Dashboard.

## 7. Final Git update

After all local checks pass:

```powershell
git status
git add .
git commit -m "Final version: complete role dashboards and attendance workflow"
git push origin main
```

Do not commit real face samples, `.env`, `venv`, or personal student data.
