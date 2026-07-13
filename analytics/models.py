from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

from portfolio.models import Portfolio


class PortfolioMetric(models.Model):
    """
    Summarized aggregate metric tracker for a user's portfolio.
    Re-calculated periodically or dynamically upon visits logs.
    """
    portfolio = models.OneToOneField(Portfolio, on_delete=models.CASCADE, related_name="metric")
    total_visits = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)
    returning_visitors = models.PositiveIntegerField(default=0)
    
    # Future-ready slots
    avg_session_duration = models.FloatField(default=0.0, help_text="Average session duration in seconds")
    bounce_rate = models.FloatField(default=0.0, help_text="Bounce rate percentage")
    
    seo_score = models.PositiveIntegerField(default=100)
    performance_score = models.PositiveIntegerField(default=100)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Metrics for {self.portfolio.name} (Visits: {self.total_visits})"


class PortfolioVisit(models.Model):
    """
    Individual visitor log details tracking device, browser, referrer, country,
    and target page path.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="visits")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    session_id = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # User Agent dimensions
    device_type = models.CharField(max_length=50, default="Desktop", db_index=True) # Desktop, Mobile, Tablet
    browser = models.CharField(max_length=100, default="Other", db_index=True) # Chrome, Firefox, Safari, Edge, etc.
    
    # Referrer & Geography
    referrer = models.CharField(max_length=255, default="direct", db_index=True)
    country = models.CharField(max_length=100, default="Unknown", db_index=True)
    
    # Visited section/path (Home, projects, contact, etc.)
    path = models.CharField(max_length=255, default="Home", db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Visit to {self.portfolio.name} from {self.country} on {self.timestamp.strftime('%Y-%m-%d %H:%i')}"


class PortfolioSEO(models.Model):
    """
    Custom metadata header tags config for search engines indexing.
    """
    portfolio = models.OneToOneField(Portfolio, on_delete=models.CASCADE, related_name="seo")
    
    # Meta Info
    seo_title = models.CharField(max_length=200, blank=True, help_text="Custom title tag override")
    meta_description = models.TextField(blank=True, help_text="Search engine meta description snippet")
    keywords = models.CharField(max_length=500, blank=True, help_text="Comma-separated keywords list")
    canonical_url = models.URLField(blank=True, help_text="Canonical URL referencing this index")
    
    # Open Graph Facebook/LinkedIn
    og_title = models.CharField(max_length=200, blank=True, help_text="Open Graph sharing title")
    og_description = models.TextField(blank=True, help_text="Open Graph description snippet")
    og_image = models.ImageField(upload_to="seo/og_images/", null=True, blank=True, help_text="OG Social Share Image")
    
    # Twitter Card elements
    twitter_title = models.CharField(max_length=200, blank=True, help_text="Twitter card title override")
    twitter_description = models.TextField(blank=True, help_text="Twitter card description override")
    
    # Assets overrides
    favicon = models.ImageField(upload_to="seo/favicons/", null=True, blank=True, help_text="Browser window favicon")
    
    # Crawlers indexing
    robots_txt = models.TextField(default="User-agent: *\nAllow: /", help_text="Custom crawlers access rules")

    def __str__(self):
        return f"SEO Settings for {self.portfolio.name}"


# ---------------------------------------------------------------------------
# Signals setup to automatically provision metrics and seo profiles
# ---------------------------------------------------------------------------
@receiver(post_save, sender=Portfolio)
def initialize_analytics_profile(sender, instance, created, **kwargs):
    if created:
        PortfolioMetric.objects.get_or_create(portfolio=instance)
        PortfolioSEO.objects.get_or_create(portfolio=instance)
