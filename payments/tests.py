import os
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

from themes.models import Theme, ThemeCategory
from portfolio.models import Portfolio
from payments.models import SubscriptionPlan, UserSubscription, UsageMetrics, PaymentTransaction

User = get_user_model()


class SaaSBillingTestCase(TestCase):
    """
    Comprehensive test suite for Module 10: SaaS Subscription & Payments.
    """
    def setUp(self):
        # Retrieve default plans populated during migrations
        self.free_plan = SubscriptionPlan.objects.get(slug="free")
        self.premium_plan = SubscriptionPlan.objects.get(slug="premium")
        self.enterprise_plan = SubscriptionPlan.objects.get(slug="enterprise")

        # Create standard user
        self.user = User.objects.create_user(
            username="freeuser",
            email="free@example.com",
            password="password123"
        )
        self.user.save()

        # Create admin user
        self.admin_user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            password="password123",
            role=User.Role.ADMIN
        )
        self.admin_user.save()

        # Create premium theme for testing theme access
        self.category, _ = ThemeCategory.objects.get_or_create(name="Creative", defaults={"slug": "creative"})
        self.premium_theme, _ = Theme.objects.get_or_create(
            slug="premium-layout",
            defaults={
                "name": "Premium Layout",
                "category": self.category,
                "status": Theme.Status.APPROVED,
                "is_premium": True
            }
        )
        
        # Create normal free theme
        self.free_theme, _ = Theme.objects.get_or_create(
            slug="free-layout",
            defaults={
                "name": "Free Layout",
                "category": self.category,
                "status": Theme.Status.APPROVED,
                "is_premium": False
            }
        )

    def test_signals_initialize_profile_on_creation(self):
        """Verify new users automatically get a default active Free subscription and UsageMetrics."""
        user = User.objects.create_user(username="newuser", email="new@example.com", password="pwd")
        
        self.assertTrue(hasattr(user, "subscription"))
        self.assertEqual(user.subscription.plan, self.free_plan)
        self.assertEqual(user.subscription.status, UserSubscription.Status.ACTIVE)
        
        self.assertTrue(hasattr(user, "usage_metrics"))
        self.assertEqual(user.usage_metrics.portfolios_count, 0)

    def test_portfolio_limits_are_enforced_for_free_users(self):
        """Verify Free user is blocked from creating more than 1 portfolio."""
        self.client.login(username="freeuser", password="password123")
        
        # 1. First portfolio creation should succeed
        res = self.client.post(reverse("portfolio:create"))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), 1)
        
        # 2. Second portfolio creation should be blocked and redirect to billing
        res2 = self.client.post(reverse("portfolio:create"))
        self.assertRedirects(res2, reverse("payments:billing"))
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), 1)

    def test_premium_theme_activation_blocked_for_free_users(self):
        """Verify Free user cannot select/activate premium themes."""
        portfolio = Portfolio.objects.create(user=self.user, name="My Portfolio")
        self.client.login(username="freeuser", password="password123")
        
        # Activate Premium theme
        res = self.client.post(
            reverse("portfolio:select_theme", kwargs={"pk": portfolio.pk}),
            data={"theme_id": self.premium_theme.pk}
        )
        self.assertRedirects(res, reverse("payments:billing"))
        portfolio.refresh_from_db()
        self.assertNotEqual(portfolio.selected_theme, self.premium_theme)

        # Activate Free theme should succeed
        res2 = self.client.post(
            reverse("portfolio:select_theme", kwargs={"pk": portfolio.pk}),
            data={"theme_id": self.free_theme.pk}
        )
        self.assertRedirects(res2, reverse("portfolio:select_theme", kwargs={"pk": portfolio.pk}))
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.selected_theme, self.free_theme)

    def test_checkout_upgrades_user_subscription_and_logs_transaction(self):
        """Verify checkout simulator registers success, upgrades plan, and changes user roles."""
        self.client.login(username="freeuser", password="password123")

        # 1. Initiate checkout session
        res_checkout = self.client.post(reverse("payments:checkout"), data={"plan_slug": "premium"})
        self.assertEqual(res_checkout.status_code, 302)
        self.assertIn("/billing/checkout/mock/", res_checkout.url)

        # Extract session reference
        session_id = res_checkout.url.split("session_id=")[-1].split("&")[0]
        transaction = PaymentTransaction.objects.get(transaction_id=session_id)
        self.assertEqual(transaction.status, PaymentTransaction.Status.PENDING)

        # 2. Simulate payment success callback
        res_mock = self.client.post(reverse("payments:checkout_mock"), data={
            "session_id": session_id,
            "action": "success"
        })
        self.assertRedirects(res_mock, reverse("payments:success"))

        # Verify database logs
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, PaymentTransaction.Status.SUCCESS)

        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription.plan, self.premium_plan)
        self.assertEqual(self.user.role, User.Role.PREMIUM_USER)

    def test_checkout_failure_keeps_free_tier(self):
        """Verify payment decline leaves user on the Free tier."""
        self.client.login(username="freeuser", password="password123")
        
        res_checkout = self.client.post(reverse("payments:checkout"), data={"plan_slug": "premium"})
        session_id = res_checkout.url.split("session_id=")[-1].split("&")[0]

        res_mock = self.client.post(reverse("payments:checkout_mock"), data={
            "session_id": session_id,
            "action": "failure"
        })
        self.assertRedirects(res_mock, reverse("payments:failure"))

        self.user.refresh_from_db()
        self.assertEqual(self.user.subscription.plan, self.free_plan)
        self.assertEqual(self.user.role, User.Role.FREE_USER)

    def test_cancel_subscription_renewal(self):
        """Verify users can set their paid subscription to cancel at period end."""
        self.client.login(username="freeuser", password="password123")
        
        # Manually upgrade user to Paid Premium first
        self.user.subscription.plan = self.premium_plan
        self.user.subscription.save()

        # Submit cancellation POST
        res = self.client.post(reverse("payments:cancel"))
        self.assertRedirects(res, reverse("payments:billing"))
        
        self.user.subscription.refresh_from_db()
        self.assertTrue(self.user.subscription.cancel_at_period_end)

    def test_admin_billing_dashboard_enforces_permissions(self):
        """Verify normal users get 403 on admin summary but administrators can access it."""
        # 1. Free user gets redirected or blocked (Custom handler 403 page is triggered)
        self.client.login(username="freeuser", password="password123")
        res_free = self.client.get(reverse("payments:admin_summary"))
        self.assertEqual(res_free.status_code, 403)

        # 2. Admin user accesses successfully
        self.client.login(username="adminuser", password="password123")
        res_admin = self.client.get(reverse("payments:admin_summary"))
        self.assertEqual(res_admin.status_code, 200)
