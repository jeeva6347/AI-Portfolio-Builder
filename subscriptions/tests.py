"""
subscriptions/tests.py — Comprehensive Test Suite for Subscription & Plan Management System (Phase 10.0 MVP)
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.management import call_command

from subscriptions.models import (
    SubscriptionPlan,
    PlanFeature,
    PlanFeatureAccess,
    UserSubscription
)
from subscriptions.services import (
    get_user_subscription,
    get_user_plan,
    get_available_features,
    has_feature,
    get_usage_limit
)

User = get_user_model()


class SubscriptionSystemTestCase(TestCase):
    """
    Test suite verifying SubscriptionPlan, PlanFeature, PlanFeatureAccess, UserSubscription,
    subscription_service functions, and management command data seeding.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="subuser", password="subpassword")

        # 1. Create Free & Pro Plans
        self.free_plan = SubscriptionPlan.objects.create(
            name="Free Plan",
            slug="free",
            price="0.00",
            billing_cycle=SubscriptionPlan.BillingCycle.MONTHLY,
            is_active=True,
            display_order=1
        )
        self.pro_plan = SubscriptionPlan.objects.create(
            name="Pro Plan",
            slug="pro",
            price="19.99",
            billing_cycle=SubscriptionPlan.BillingCycle.MONTHLY,
            is_active=True,
            is_featured=True,
            display_order=2
        )

        # 2. Create Features
        self.feat_gen = PlanFeature.objects.create(name="AI Generation", slug="ai-portfolio-generation")
        self.feat_export = PlanFeature.objects.create(name="Portfolio Export", slug="portfolio-export")
        self.feat_github = PlanFeature.objects.create(name="GitHub Deployment", slug="github-deployment")

        # 3. Configure Feature Access
        # Free Plan
        PlanFeatureAccess.objects.create(plan=self.free_plan, feature=self.feat_gen, enabled=True, usage_limit=1)
        PlanFeatureAccess.objects.create(plan=self.free_plan, feature=self.feat_export, enabled=True, usage_limit=2)
        PlanFeatureAccess.objects.create(plan=self.free_plan, feature=self.feat_github, enabled=False, usage_limit=0)

        # Pro Plan
        PlanFeatureAccess.objects.create(plan=self.pro_plan, feature=self.feat_gen, enabled=True, usage_limit=None)
        PlanFeatureAccess.objects.create(plan=self.pro_plan, feature=self.feat_export, enabled=True, usage_limit=None)
        PlanFeatureAccess.objects.create(plan=self.pro_plan, feature=self.feat_github, enabled=True, usage_limit=None)

    def test_default_free_plan_fallback(self):
        """Verify user without explicit subscription receives default Free plan and free feature limits."""
        plan = get_user_plan(self.user)
        self.assertEqual(plan, self.free_plan)

        self.assertTrue(has_feature(self.user, "ai-portfolio-generation"))
        self.assertEqual(get_usage_limit(self.user, "ai-portfolio-generation"), 1)

        self.assertFalse(has_feature(self.user, "github-deployment"))
        self.assertEqual(get_usage_limit(self.user, "github-deployment"), 0)

    def test_active_user_subscription(self):
        """Verify active UserSubscription grants Pro plan features and unlimited usage limits."""
        UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status=UserSubscription.Status.ACTIVE
        )

        plan = get_user_plan(self.user)
        self.assertEqual(plan, self.pro_plan)

        self.assertTrue(has_feature(self.user, "github-deployment"))
        self.assertIsNone(get_usage_limit(self.user, "github-deployment"))  # None = Unlimited

        available = get_available_features(self.user)
        self.assertEqual(len(available), 3)

    def test_expired_and_cancelled_subscription_fallback(self):
        """Verify expired or cancelled subscriptions fall back safely to Free plan."""
        # 1. Expired date
        sub_expired = UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status=UserSubscription.Status.ACTIVE,
            end_date=timezone.now() - timedelta(days=1)
        )

        plan = get_user_plan(self.user)
        self.assertEqual(plan, self.free_plan)
        sub_expired.refresh_from_db()
        self.assertEqual(sub_expired.status, UserSubscription.Status.EXPIRED)

        # 2. Cancelled status
        UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status=UserSubscription.Status.CANCELLED
        )
        plan_cancelled = get_user_plan(self.user)
        self.assertEqual(plan_cancelled, self.free_plan)

    def test_seed_subscription_data_command(self):
        """Verify seed_subscription_data management command runs cleanly and creates default plans and features."""
        call_command("seed_subscription_data")

        self.assertTrue(SubscriptionPlan.objects.filter(slug="starter").exists())
        self.assertTrue(SubscriptionPlan.objects.filter(slug="professional").exists())
        self.assertTrue(PlanFeature.objects.filter(slug="cover-letter-generator").exists())
        self.assertTrue(PlanFeature.objects.filter(slug="ats-resume-optimizer").exists())

    def test_feature_usage_tracking_and_limit_enforcement(self):
        """Verify usage tracking, atomic F() increments, can_use_feature enforcement, and get_remaining_usage calculation."""
        from subscriptions.services import can_use_feature, get_remaining_usage, increment_feature_usage, get_usage_count

        slug = "ai-portfolio-generation"

        # Initially 0 used, limit = 1
        self.assertEqual(get_usage_count(self.user, slug), 0)
        self.assertTrue(can_use_feature(self.user, slug))
        self.assertEqual(get_remaining_usage(self.user, slug), 1)

        # Increment usage by 1
        usage = increment_feature_usage(self.user, slug)
        self.assertIsNotNone(usage)
        self.assertEqual(usage.used_count, 1)

        # Limit reached (1/1): can_use_feature returns False, remaining usage returns 0
        self.assertFalse(can_use_feature(self.user, slug))
        self.assertEqual(get_remaining_usage(self.user, slug), 0)

    def test_unlimited_usage_for_pro_plan(self):
        """Verify Pro plan with usage_limit=None grants unlimited remaining usage and allows repeated consumption."""
        from subscriptions.services import can_use_feature, get_remaining_usage, increment_feature_usage

        UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status=UserSubscription.Status.ACTIVE
        )

        slug = "ai-portfolio-generation"
        self.assertIsNone(get_remaining_usage(self.user, slug))  # None = Unlimited
        self.assertTrue(can_use_feature(self.user, slug))

        # Perform 10 increments
        for _ in range(10):
            increment_feature_usage(self.user, slug)

        self.assertTrue(can_use_feature(self.user, slug))
        self.assertIsNone(get_remaining_usage(self.user, slug))

    def test_admin_subscriptions_summary_dashboard_view(self):
        """Verify staff member access to admin:subscriptions_summary dashboard view."""
        from django.urls import reverse

        staff_user = User.objects.create_user(username="adminstaff", password="adminpassword", is_staff=True)

        # 1. Non-staff user is redirected
        self.client.login(username="subuser", password="subpassword")
        response_non_staff = self.client.get(reverse("admin:subscriptions_summary"))
        self.assertEqual(response_non_staff.status_code, 302)  # Redirects to admin login

        # 2. Staff user can access dashboard
        self.client.login(username="adminstaff", password="adminpassword")
        response_staff = self.client.get(reverse("admin:subscriptions_summary"))
        self.assertEqual(response_staff.status_code, 200)
        self.assertIn("total_plans", response_staff.context)
        self.assertIn("total_features", response_staff.context)
        self.assertIn("plan_breakdown", response_staff.context)
        self.assertIn("top_used_features", response_staff.context)

    def test_admin_actions_and_audit_logging(self):
        """Verify custom admin actions update models and record LogEntry audit trail records."""
        from subscriptions.admin import SubscriptionPlanAdmin, UserSubscriptionAdmin, FeatureUsageAdmin
        from subscriptions.models import FeatureUsage
        from subscriptions.services import increment_feature_usage
        from django.contrib.admin.models import LogEntry
        from django.test import RequestFactory
        from django.contrib.messages.storage.cookie import CookieStorage

        staff_user = User.objects.create_superuser(username="adminuser", password="adminpassword")
        factory = RequestFactory()

        # 1. Test SubscriptionPlanAdmin activate_selected action
        plan_admin = SubscriptionPlanAdmin(SubscriptionPlan, None)
        request = factory.post("/admin/subscriptions/subscriptionplan/")
        request.user = staff_user
        setattr(request, '_messages', CookieStorage(request))

        plan_admin.activate_selected(request, SubscriptionPlan.objects.filter(pk=self.free_plan.pk))
        self.assertTrue(SubscriptionPlan.objects.get(pk=self.free_plan.pk).is_active)
        self.assertTrue(LogEntry.objects.filter(user=staff_user).exists())

        # 2. Test FeatureUsageAdmin reset_usage_selected action
        increment_feature_usage(self.user, "ai-portfolio-generation")
        usage_admin = FeatureUsageAdmin(FeatureUsage, None)
        usage_qs = FeatureUsage.objects.filter(user=self.user)
        usage_admin.reset_usage_selected(request, usage_qs)
        self.assertEqual(usage_qs.first().used_count, 0)
