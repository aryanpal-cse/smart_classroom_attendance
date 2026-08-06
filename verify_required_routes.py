from app import create_app

REQUIRED_ROUTES = {
    "/admin/dashboard",
    "/admin/management/teachers",
    "/admin/management/teachers/department",
    "/admin/management/teachers/timetables",
    "/admin/management/teachers/attendance",
    "/admin/management/teachers/attendance/add",
    "/admin/management/students",
    "/admin/management/students/face-recognition",
    "/admin/management/students/branches",
    "/admin/management/students/years",
    "/admin/management/students/groups",
    "/admin/management/students/sections",
    "/admin/assignments",
    "/admin/assignments/add",
    "/admin/attendance",
    "/admin/attendance/analytics",
    "/admin/attendance/export.csv",
    "/admin/audit-logs",
    "/teacher/dashboard",
    "/teacher/profile",
    "/teacher/classes",
    "/teacher/programs",
    "/teacher/timetable",
    "/teacher/attendance",
    "/teacher/sessions",
    "/teacher/history",
    "/student/dashboard",
    "/student/profile",
    "/student/course",
    "/student/subjects",
    "/student/timetable",
    "/student/attendance",
    "/student/join",
    "/student/face-recognition",
    "/student/face/register",
    "/student/face/verify",
    "/student/manual-review",
}

app = create_app()
registered = {rule.rule for rule in app.url_map.iter_rules()}
missing = sorted(REQUIRED_ROUTES - registered)

print("Required routes:", len(REQUIRED_ROUTES))
print("Registered routes:", len(registered))

if missing:
    print("FAILED: missing routes")
    for path in missing:
        print(" -", path)
    raise SystemExit(1)

print("PASSED: all required routes are registered.")
