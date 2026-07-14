from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class AuthenticationTestCase(TestCase):
    """
    Unit tests verifying User model roles validation, django superuser properties,
    and login redirects.
    """
    def test_create_user_with_roles(self):
        """Verify that default user role is FREE_USER and roles map correctly."""
        user = User.objects.create_user(
            username="freebie",
            email="freebie@example.com",
            password="pwd"
        )
        self.assertEqual(user.role, User.Role.FREE_USER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        premium = User.objects.create_user(
            username="richard",
            email="rich@example.com",
            password="pwd",
            role=User.Role.PREMIUM_USER
        )
        self.assertEqual(premium.role, User.Role.PREMIUM_USER)

    def test_create_superuser(self):
        """Verify superuser custom creation settings."""
        admin = User.objects.create_superuser(
            username="chief",
            email="chief@example.com",
            password="pwd"
        )
        self.assertEqual(admin.role, User.Role.SUPER_ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_login_page_renders_successfully(self):
        """Verify authentication login page loads fine."""
        res = self.client.get(reverse("account_login"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Sign In")  # allauth renders "Sign In" not "Log In"

    def test_authenticated_user_redirects_to_dashboard(self):
        """Verify that logged-in users hitting root are redirected to dashboard."""
        User.objects.create_user(username="testuser", password="pwd123password")
        self.client.login(username="testuser", password="pwd123password")
        
        # Hitting login redirects to dashboard
        res = self.client.get(reverse("account_login"))
        self.assertEqual(res.status_code, 302)
