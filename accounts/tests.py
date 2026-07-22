from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class AuthenticationTestCase(TestCase):
    """
    Unit tests verifying User model and authentication workflow.
    """
    def test_create_user(self):
        user = User.objects.create_user(
            username="freebie",
            email="freebie@example.com",
            password="pwd"
        )
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="chief",
            email="chief@example.com",
            password="pwd"
        )
        self.assertEqual(admin.role, User.Role.SUPER_ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_login_page_renders_successfully(self):
        res = self.client.get(reverse("account_login"))
        self.assertEqual(res.status_code, 200)

    def test_dashboard_redirect(self):
        user = User.objects.create_user(username="testuser", email="test@example.com", password="pwd")
        self.client.login(username="testuser", password="pwd")
        res = self.client.get(reverse("accounts:dashboard_redirect"))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse("dashboard:home"))
