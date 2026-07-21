"""
subscriptions/models.py — Models for Admin-controlled Subscriptions & Plans (Phase 10.0 MVP)

Provides:
  - SubscriptionPlan: Admin-manageable plans (Free, Starter, Professional, Enterprise).
  - PlanFeature: Features controllable by plan (e.g. AI Portfolio Generation, Resume Import).
  - PlanFeatureAccess: Rules mapping plans to features with enabled flags & usage limits.
  - UserSubscription: Relationship mapping users to their active/expired subscriptions.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """Admin-controlled Subscription Plans."""
    class BillingCycle(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"
        LIFETIME = "LIFETIME", "Lifetime"

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "price", "id"]

    def __str__(self):
        return f"{self.name} ({self.get_billing_cycle_display()}) - ${self.price}"


class PlanFeature(models.Model):
    """Features that can be enabled or limited per plan."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class PlanFeatureAccess(models.Model):
    """Maps SubscriptionPlan to PlanFeature with access control & usage limits."""
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="feature_accesses"
    )
    feature = models.ForeignKey(
        PlanFeature,
        on_delete=models.CASCADE,
        related_name="plan_accesses"
    )
    enabled = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Usage limit (integer). Null means Unlimited."
    )

    class Meta:
        unique_together = ("plan", "feature")
        ordering = ["plan", "feature"]

    def __str__(self):
        limit_str = f"Limit: {self.usage_limit}" if self.usage_limit is not None else "Unlimited"
        status_str = "Enabled" if self.enabled else "Disabled"
        return f"{self.plan.name} -> {self.feature.name} ({status_str}, {limit_str})"


class UserSubscription(models.Model):
    """User membership to a SubscriptionPlan."""
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="user_subscriptions"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.user} - {self.plan.name} ({self.status})"


class FeatureUsage(models.Model):
    """Tracks feature consumption per user/subscription period with atomic increments."""
    class ResetType(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"
        LIFETIME = "LIFETIME", "Lifetime"
        CUSTOM = "CUSTOM", "Custom"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feature_usages"
    )
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usages"
    )
    feature = models.ForeignKey(
        PlanFeature,
        on_delete=models.CASCADE,
        related_name="usages"
    )
    used_count = models.PositiveIntegerField(default=0)
    reset_type = models.CharField(
        max_length=20,
        choices=ResetType.choices,
        default=ResetType.MONTHLY
    )
    period_start = models.DateTimeField(default=timezone.now)
    period_end = models.DateTimeField(null=True, blank=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_used", "-id"]

    def __str__(self):
        return f"{self.user} - {self.feature.name}: {self.used_count} ({self.get_reset_type_display()})"
