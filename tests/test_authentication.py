def test_admin_login_and_access(self) -> None:
    """Admin should log in and access the admin dashboard."""
    response = self.client.post(
        "/auth/login",
        data={
            "username": "admin",
            "password": "Admin@123",
            "remember_me": False,
        },
        follow_redirects=True,
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