import os
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class SubscriptionPlan(models.Model):
    """
    SaaS Subscription Plans detailing limits and feature privileges.
    Allows administrators to dynamically edit limits from the Django admin.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Monthly price in USD.")
    
    # Portfolio limit
    portfolio_limit = models.PositiveIntegerField(default=1, help_text="Maximum portfolios allowed.")
    
    # Premium theme access
    premium_themes_enabled = models.BooleanField(default=False, help_text="Allow selecting premium themes.")
    
    # AI resume uploads limit
    ai_usage_limit = models.PositiveIntegerField(default=3, help_text="Maximum resume uploads/parses allowed.")
    
    # GitHub publishes limit
    github_publish_limit = models.PositiveIntegerField(default=3, help_text="Maximum GitHub Pages publications allowed.")
    
    # Custom branding removal
    custom_branding_removal = models.BooleanField(default=False, help_text="Allow disabling 'Powered by AI Portfolio Builder'.")
    
    # Enterprise features
    team_access = models.BooleanField(default=False, help_text="Enable team and organization features.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["price", "id"]

    def __str__(self):
        return f"{self.name} (${self.price}/mo)"


class UserSubscription(models.Model):
    """
    Tracks the active plan, status, and periods of a user's subscription.
    """
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.get_status_display()})"

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE and (
            self.current_period_end is None or self.current_period_end > timezone.now()
        )


class UsageMetrics(models.Model):
    """
    Aggregates user SaaS usage stats (Portfolios, AI parse credits, Publishes, Storage).
    Cached metrics to keep pages extremely responsive.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_metrics"
    )
    portfolios_count = models.PositiveIntegerField(default=0)
    ai_uploads_count = models.PositiveIntegerField(default=0)
    github_publishes_count = models.PositiveIntegerField(default=0)
    storage_used_bytes = models.PositiveIntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Usage Metrics"
        verbose_name_plural = "Usage Metrics Summary"

    def __str__(self):
        return f"{self.user.username} Usage Summary"

    def sync_metrics(self):
        """Calculates actual usage metrics from related tables and updates self."""
        user = self.user
        
        # Portfolios
        self.portfolios_count = user.portfolios.count()
        
        # AI Uploads
        self.ai_uploads_count = user.resume_uploads.count()
        
        # GitHub Successful Publishes
        # Avoid import loop by local import
        from github_integration.models import GitHubDeployment
        self.github_publishes_count = GitHubDeployment.objects.filter(
            portfolio__user=user,
            status=GitHubDeployment.Status.SUCCESS
        ).count()
        
        # Storage usage bytes calculation
        total_storage = 0
        
        # Resume uploads storage
        for resume in user.resume_uploads.all():
            try:
                if resume.file and os.path.exists(resume.file.path):
                    total_storage += os.path.getsize(resume.file.path)
            except Exception:
                pass
                
        # Portfolio photos/covers storage
        for pf in user.portfolios.all():
            try:
                if pf.photo and os.path.exists(pf.photo.path):
                    total_storage += os.path.getsize(pf.photo.path)
                if pf.cover and os.path.exists(pf.cover.path):
                    total_storage += os.path.getsize(pf.cover.path)
            except Exception:
                pass

        self.storage_used_bytes = total_storage
        self.save()


class PaymentTransaction(models.Model):
    """
    Audit log record of invoices, charges, and refunds.
    """
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        PENDING = "pending", "Pending"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    transaction_id = models.CharField(max_length=100, unique=True)
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        related_name="transactions"
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Tx: {self.transaction_id} - {self.user.username} (${self.amount})"


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def initialize_user_saas_profile(sender, instance, created, **kwargs):
    """
    Ensures that every user has a default subscription (Free Plan)
    and an associated UsageMetrics profile on creation.
    """
    # Create default plan if it doesn't exist (e.g. during migrations/tests run)
    free_plan, _ = SubscriptionPlan.objects.get_or_create(
        slug="free",
        defaults={
            "name": "Free Plan",
            "price": 0.00,
            "portfolio_limit": 1,
            "premium_themes_enabled": False,
            "ai_usage_limit": 3,
            "github_publish_limit": 3,
            "custom_branding_removal": False,
            "team_access": False,
        }
    )
    
    # Auto-initialize subscription
    if not hasattr(instance, "subscription"):
        UserSubscription.objects.create(
            user=instance,
            plan=free_plan,
            status=UserSubscription.Status.ACTIVE
        )
        
    # Auto-initialize metrics
    if not hasattr(instance, "usage_metrics"):
        UsageMetrics.objects.create(user=instance)
