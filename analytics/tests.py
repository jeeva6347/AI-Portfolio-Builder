import xml.etree.ElementTree as ET
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from portfolio.models import Portfolio
from themes.models import Theme, ThemeCategory, ThemeAsset
from payments.models import SubscriptionPlan
from analytics.models import PortfolioMetric, PortfolioSEO, PortfolioVisit
from analytics.services.tracking_service import track_visit
from analytics.services.seo_service import calculate_seo_score, inject_seo_metadata
from analytics.services.performance_service import analyze_performance

User = get_user_model()


class PortfolioAnalyticsTestCase(TestCase):
    """
    Automated unit tests verifying traffic logging, HTML tags injection filters,
    XML sitemaps, robots.txt endpoints, and premium role gates.
    """
    def setUp(self):
        # Setup plans
        self.free_plan = SubscriptionPlan.objects.get(slug="free")
        self.premium_plan = SubscriptionPlan.objects.get(slug="premium")

        # Create user
        self.user = User.objects.create_user(
            username="analyst",
            email="analyst@example.com",
            password="pwd"
        )
        self.user.save()

        # Create theme and category
        self.category, _ = ThemeCategory.objects.get_or_create(name="Minimalist", defaults={"slug": "minimalist"})
        self.theme = Theme.objects.create(
            name="Alpha Speed",
            slug="alpha-speed",
            category=self.category,
            status=Theme.Status.APPROVED,
            extracted_path="themes/alpha/"
        )

        # Create sample HTML and CSS assets to test performance sizes
        self.html_asset = ThemeAsset.objects.create(
            theme=self.theme,
            file_path="index.html",
            file_name="index.html",
            file_size=2048, # 2KB
            asset_type=ThemeAsset.AssetType.HTML
        )
        self.css_asset = ThemeAsset.objects.create(
            theme=self.theme,
            file_path="css/style.css",
            file_name="style.css",
            file_size=10240, # 10KB
            asset_type=ThemeAsset.AssetType.CSS
        )

        # Create portfolio
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="My Masterpiece",
            selected_theme=self.theme
        )

    def test_analytics_profiles_auto_provision_via_signals(self):
        """Verify metric and seo records are auto-created when a portfolio is saved."""
        self.assertTrue(hasattr(self.portfolio, "metric"))
        self.assertTrue(hasattr(self.portfolio, "seo"))

    def test_visitor_tracking_logs_records_accurately(self):
        """Verify tracking services record browser agent, device type, referrer, and countries."""
        # Setup session request
        session = self.client.session
        session.save()
        
        # Construct mock request variables
        class MockRequest:
            def __init__(self):
                self.META = {
                    "HTTP_USER_AGENT": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                    "HTTP_REFERER": "https://google.com/search?q=jeeva",
                    "HTTP_CF_IPCOUNTRY": "Germany",
                    "REMOTE_ADDR": "192.168.1.1"
                }
                self.GET = {"page": "projects"}
                self.session = session
                # Anonymous or other user
                self.user = User.objects.create_user(username="visitor", email="v@ex.com", password="pwd")

        req = MockRequest()
        visit = track_visit(req, self.portfolio)

        self.assertIsNotNone(visit)
        self.assertEqual(visit.device_type, "Mobile")
        self.assertEqual(visit.browser, "Safari")
        self.assertEqual(visit.referrer, "google.com")
        self.assertEqual(visit.country, "Germany")
        self.assertEqual(visit.path, "projects")

        # Check aggregate metric counter update
        self.portfolio.metric.refresh_from_db()
        self.assertEqual(self.portfolio.metric.total_visits, 1)
        self.assertEqual(self.portfolio.metric.unique_visitors, 1)

    def test_seo_metadata_injects_into_html(self):
        """Verify BeautifulSoup parser inserts tags and favicons correctly."""
        seo = self.portfolio.seo
        seo.seo_title = "Creative Designer Portfolio"
        seo.meta_description = "Check out my awesome projects and skills listing."
        seo.keywords = "design, code, portfolio"
        seo.canonical_url = "https://masterpiece.com/live"
        seo.favicon = SimpleUploadedFile("favicon.ico", b"dummyicon", content_type="image/x-icon")
        seo.save()

        # Re-calculate SEO Score
        score = calculate_seo_score(self.portfolio)
        self.assertTrue(score > 50)

        # Inject into mock compiled template HTML
        html = "<html><head><title>Original Title</title></head><body></body></html>"
        injected = inject_seo_metadata(html, self.portfolio)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(injected, "html.parser")
        self.assertEqual(soup.title.string, "Creative Designer Portfolio")
        self.assertEqual(soup.find("meta", attrs={"name": "description"})["content"], "Check out my awesome projects and skills listing.")
        self.assertEqual(soup.find("meta", attrs={"name": "keywords"})["content"], "design, code, portfolio")
        self.assertEqual(soup.find("link", attrs={"rel": "canonical"})["href"], "https://masterpiece.com/live")
        favicon_url = soup.find("link", attrs={"rel": "icon"})["href"]
        self.assertTrue(favicon_url.startswith("/media/seo/favicons/favicon"))
        self.assertTrue(favicon_url.endswith(".ico"))

    def test_performance_analyzer_aggregates_sizes_and_suggestions(self):
        """Verify analyzer aggregates assets sizes and provides warnings."""
        perf = analyze_performance(self.portfolio)
        
        self.assertEqual(perf["portfolio_size"], 12288) # 2KB + 10KB = 12KB
        self.assertEqual(perf["css_size"], 10240)
        self.assertEqual(perf["html_size"], 2048)
        self.assertEqual(perf["performance_score"], 90) # Deduct 10 for missing favicon
        self.assertIn("Browser favicon is missing.", perf["suggestions"][0])

    def test_sitemap_generation_outputs_valid_xml(self):
        """Verify sitemap.xml returns published portfolio loc tags."""
        # Set status to PUBLISHED
        self.portfolio.status = Portfolio.Status.PUBLISHED
        self.portfolio.save()

        res = self.client.get(reverse("analytics:sitemap"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/xml")

        # Parse XML response
        root = ET.fromstring(res.content)
        urls = [loc.text for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        
        self.assertEqual(len(urls), 3)
        self.assertTrue(any(f"/portfolio/preview/{self.portfolio.pk}/" in u for u in urls))

    def test_robots_txt_routing_provides_plain_text(self):
        """Verify robots.txt serves crawler mapping directives."""
        res = self.client.get(reverse("analytics:robots_txt"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "text/plain")
        self.assertIn("User-agent: *", res.content.decode("utf-8"))
        self.assertIn("Sitemap:", res.content.decode("utf-8"))

    def test_analytics_dashboard_gated_by_premium_subscription(self):
        """Verify free subscribers are redirected to upgrade while premium users are allowed."""
        # 1. Unauthenticated gets redirected to login page
        res_anon = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(res_anon.status_code, 302)

        # Login
        self.client.login(username="analyst", password="pwd")

        # 2. Free subscriber redirected to billing dashboard
        res_free = self.client.get(reverse("analytics:dashboard"))
        self.assertRedirects(res_free, reverse("payments:billing"))

        # Upgrade User subscription to premium
        self.user.subscription.plan = self.premium_plan
        self.user.subscription.save()

        # 3. Premium subscriber gains access successfully
        res_premium = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(res_premium.status_code, 200)
