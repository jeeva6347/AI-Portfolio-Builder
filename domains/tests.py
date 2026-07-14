"""
Module 13: Custom Domains — tests.py

Unit and integration tests for Custom Domain models, service layer,
permissions, DNS checkers, and management view gates.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from payments.models import SubscriptionPlan, UserSubscription
from portfolio.models import Portfolio
from themes.models import Theme, ThemeCategory
from domains.models import CustomDomain, DomainVerificationLog
from domains.services.domain_service import (
    create_custom_domain,
    run_verification,
    delete_domain,
    get_domain_limit,
    get_portfolio_primary_url,
)

User = get_user_model()


class CustomDomainTestCase(TestCase):
    """
    Test suite verifying CustomDomain model constraints, permission limits,
    mock DNS verification logic, and view route gates.
    """

    def setUp(self):
        # 1. Get or Create Subscription Plans
        self.free_plan, _ = SubscriptionPlan.objects.get_or_create(
            slug="free",
            defaults={
                "name": "Free Plan",
                "price": 0.00,
                "portfolio_limit": 1,
                "premium_themes_enabled": False,
                "ai_usage_limit": 3,
                "github_publish_limit": 3,
            }
        )
        self.premium_plan, _ = SubscriptionPlan.objects.get_or_create(
            slug="premium",
            defaults={
                "name": "Premium Plan",
                "price": 19.99,
                "portfolio_limit": 5,
                "premium_themes_enabled": True,
                "ai_usage_limit": 20,
                "github_publish_limit": 20,
            }
        )

        # 2. Create Users
        self.free_user = User.objects.create_user(
            username="free_guy",
            email="free@guy.com",
            password="pwd",
        )
        # Force plan assignments
        self.free_user.subscription.plan = self.free_plan
        self.free_user.subscription.save()

        self.premium_user = User.objects.create_user(
            username="premium_guy",
            email="premium@guy.com",
            password="pwd",
            role=User.Role.PREMIUM_USER,
        )
        self.premium_user.subscription.plan = self.premium_plan
        self.premium_user.subscription.save()

        # 3. Create Portfolios
        self.theme_cat = ThemeCategory.objects.create(name="Modern", slug="modern")
        self.theme = Theme.objects.create(
            name="Classic Minimal",
            slug="classic-minimal",
            category=self.theme_cat,
            status=Theme.Status.APPROVED,
        )

        self.portfolio_free = Portfolio.objects.create(
            user=self.free_user,
            name="Free Portfolio",
            selected_theme=self.theme,
            status=Portfolio.Status.PUBLISHED,
        )
        self.portfolio_premium = Portfolio.objects.create(
            user=self.premium_user,
            name="Premium Portfolio",
            selected_theme=self.theme,
            status=Portfolio.Status.PUBLISHED,
        )

    def test_domain_validation_and_creation(self):
        """Verify CustomDomain can be successfully created and token is generated."""
        domain, created, error = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="johndoe.com",
            subdomain="www",
            verification_method="txt",
        )
        self.assertTrue(created)
        self.assertEqual(error, "")
        self.assertEqual(domain.domain_name, "johndoe.com")
        self.assertEqual(domain.subdomain, "www")
        self.assertEqual(domain.full_domain, "www.johndoe.com")
        self.assertEqual(domain.status, CustomDomain.Status.PENDING)
        self.assertIsNotNone(domain.verification_token)
        self.assertEqual(len(domain.verification_token), 64)  # Hex token length

    def test_invalid_domain_name_rejected(self):
        """Verify invalid domain structures are rejected during registration."""
        domain, created, error = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="invalid_domain_here",
        )
        self.assertFalse(created)
        self.assertIn("must contain at least one dot", error)

        domain2, created2, error2 = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="bad-label.-name.com",
        )
        self.assertFalse(created2)

    def test_domain_plan_limits(self):
        """Verify domain limit evaluation matches subscription tier specifications."""
        self.assertEqual(get_domain_limit(self.free_user), 0)
        self.assertEqual(get_domain_limit(self.premium_user), 5)

        # Admin user
        admin = User.objects.create_user(
            username="admin_user",
            email="admin@site.com",
            password="pwd",
            role=User.Role.SUPER_ADMIN,
        )
        self.assertEqual(get_domain_limit(admin), 999)

    def test_txt_verification_workflow(self):
        """Verify successful and failed TXT verification updates states and logs."""
        domain, _, _ = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="mycustomdomain.com",
            verification_method="txt",
        )
        
        # Test success path (mock DNS returns success in dev)
        success, detail = run_verification(domain)
        self.assertTrue(success)
        self.assertEqual(domain.status, CustomDomain.Status.ACTIVE)
        self.assertTrue(domain.dns_verified)
        self.assertEqual(domain.ssl_status, CustomDomain.SSLStatus.ISSUED)
        self.assertTrue(domain.ssl_enabled)
        
        # Verify log entry creation
        log = DomainVerificationLog.objects.filter(domain=domain).first()
        self.assertIsNotNone(log)
        self.assertTrue(log.success)
        self.assertEqual(log.method, "txt")

    def test_cname_verification_workflow(self):
        """Verify CNAME verification workflow runs successfully."""
        domain, _, _ = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="portfolio.myname.org",
            verification_method="cname",
        )
        success, detail = run_verification(domain)
        self.assertTrue(success)
        self.assertEqual(domain.status, CustomDomain.Status.ACTIVE)
        self.assertEqual(domain.ssl_status, CustomDomain.SSLStatus.ISSUED)

    def test_primary_domain_switching(self):
        """Verify that making a domain primary clears primary status from others on the same portfolio."""
        dom1, _, _ = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="domain1.com",
        )
        dom2, _, _ = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="domain2.com",
        )

        dom1.mark_verified()
        dom2.mark_verified()

        dom1.set_primary()
        dom1.refresh_from_db()
        self.assertTrue(dom1.is_primary)

        # Set second as primary
        dom2.set_primary()
        dom1.refresh_from_db()
        dom2.refresh_from_db()

        self.assertFalse(dom1.is_primary)
        self.assertTrue(dom2.is_primary)

    def test_primary_promotion_on_deletion(self):
        """Verify deleting a primary domain promotes the next active domain to primary."""
        dom1, _, _ = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="first.com",
        )
        dom2, _, _ = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="second.com",
        )

        dom1.mark_verified()
        dom2.mark_verified()

        dom1.set_primary()
        self.assertTrue(dom1.is_primary)

        # Delete first
        delete_domain(dom1)
        dom2.refresh_from_db()
        self.assertTrue(dom2.is_primary)

    def test_get_portfolio_primary_url(self):
        """Verify url priority chain: Custom Domain > GitHub Pages > Platform URL."""
        # 1. Fallback (Platform URL)
        fallback_url = get_portfolio_primary_url(self.portfolio_premium)
        self.assertEqual(fallback_url, reverse("portfolio:preview", kwargs={"pk": self.portfolio_premium.pk}))

        # 2. Add CNAME custom domain and verify
        dom, _, _ = create_custom_domain(
            user=self.premium_user,
            portfolio=self.portfolio_premium,
            domain_name="mypage.net",
        )
        run_verification(dom)
        dom.set_primary()

        # Should use custom domain now
        custom_url = get_portfolio_primary_url(self.portfolio_premium)
        # In mock, SSL check auto issues SSL → https
        self.assertEqual(custom_url, "https://mypage.net")

    def test_anonymous_redirect_on_dashboard(self):
        """Verify anonymous requests to domains dashboard redirect to login."""
        res = self.client.get(reverse("domains:list"))
        self.assertEqual(res.status_code, 302)
        self.assertIn("login", res.url)

    def test_free_user_gated_billing(self):
        """Verify free user attempting to add domain redirects to billing with warning."""
        self.client.login(username="free_guy", password="pwd")
        res = self.client.get(reverse("domains:add"))
        self.assertEqual(res.status_code, 302)
        self.assertIn("billing", res.url)

    def test_premium_user_access_dashboard(self):
        """Verify premium user can render domains list and add forms."""
        self.client.login(username="premium_guy", password="pwd")
        res = self.client.get(reverse("domains:list"))
        self.assertEqual(res.status_code, 200)

        res_add = self.client.get(reverse("domains:add"))
        self.assertEqual(res_add.status_code, 200)
