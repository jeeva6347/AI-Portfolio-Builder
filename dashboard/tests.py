from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class DashboardTestCase(TestCase):
    """
    Unit tests verifying dashboard view gates, role checking access, and dynamic sidebar configs.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username="freeuser",
            email="free@example.com",
            password="pwd"
        )
        self.admin = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="pwd",
            role=User.Role.SUPER_ADMIN
        )

    def test_user_dashboard_access_requires_login(self):
        """Verify anonymous user gets redirected to accounts/login/ page."""
        res = self.client.get(reverse("dashboard:user"))
        self.assertEqual(res.status_code, 302)
        self.assertIn("login", res.url)

    def test_user_dashboard_allows_logged_in_user(self):
        """Verify logged-in user can access the user dashboard."""
        self.client.login(username="freeuser", password="pwd")
        res = self.client.get(reverse("dashboard:user"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "My Dashboard")

    def test_super_admin_dashboard_gate_blocks_regular_user(self):
        """Verify that non-admin receives 403 Forbidden on admin dashboard."""
        self.client.login(username="freeuser", password="pwd")
        res = self.client.get(reverse("dashboard:super_admin"))
        self.assertEqual(res.status_code, 403)

    def test_super_admin_dashboard_allows_super_admin(self):
        """Verify that SUPER_ADMIN can view the super admin dashboard page."""
        self.client.login(username="adminuser", password="pwd")
        res = self.client.get(reverse("dashboard:super_admin"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Super Admin Dashboard")  # page title text
