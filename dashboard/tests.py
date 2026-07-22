from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class DashboardTestCase(TestCase):
    """
    Unit tests verifying dashboard access and profile management.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

    def test_dashboard_home_requires_login(self):
        res = self.client.get(reverse("dashboard:home"))
        self.assertEqual(res.status_code, 302)
        self.assertIn("login", res.url)

    def test_dashboard_home_accessible_logged_in(self):
        self.client.login(username="testuser", password="password123")
        res = self.client.get(reverse("dashboard:home"))
        self.assertEqual(res.status_code, 200)

    def test_profile_view_post(self):
        self.client.login(username="testuser", password="password123")
        res = self.client.post(
            reverse("dashboard:profile"),
            data={"first_name": "John", "last_name": "Doe", "github_username": "johndoe"}
        )
        self.assertEqual(res.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "John")
        self.assertEqual(self.user.github_username, "johndoe")
