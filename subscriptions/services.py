"""
subscriptions/services.py — Subscription & Feature Access Evaluation Service (Phase 10.0 MVP)

Provides:
  - get_user_subscription(): Resolves user's active UserSubscription record.
  - get_user_plan(): Resolves user's active SubscriptionPlan or falls back to Free plan.
  - get_available_features(): Retrieves list of enabled feature accesses for user's plan.
  - has_feature(): Evaluates whether a user has access to a specific feature slug based on DB rules.
  - get_usage_limit(): Evaluates usage limit for a feature (None = Unlimited, 0 = Disabled, N = limit).
  - get_usage_count(): Retrieves current feature usage count for active period.
  - can_use_feature(): Evaluates if user can consume feature (has_feature and used_count < usage_limit).
  - get_remaining_usage(): Exposes remaining usage (None = Unlimited, 0 = Depleted, N = remaining).
  - increment_feature_usage(): Atomically increments used_count via Django F() expressions.
"""

from typing import Optional, List, Dict, Any
from django.utils import timezone
from django.db import models, transaction
from django.db.models import F

from subscriptions.models import (
    SubscriptionPlan,
    PlanFeature,
    PlanFeatureAccess,
    UserSubscription,
    FeatureUsage
)


def get_user_subscription(user) -> Optional[UserSubscription]:
    """
    Returns user's active UserSubscription.
    Auto-expires subscriptions whose end_date has passed.
    """
    if not user or not user.is_authenticated:
        return None

    subscription = UserSubscription.objects.filter(
        user=user,
        status=UserSubscription.Status.ACTIVE
    ).select_related("plan").order_by("-start_date", "-id").first()

    if subscription and subscription.end_date:
        if subscription.end_date < timezone.now():
            subscription.status = UserSubscription.Status.EXPIRED
            subscription.save(update_fields=["status", "updated_at"])
            return None

    return subscription


def get_user_plan(user) -> SubscriptionPlan:
    """
    Returns user's active SubscriptionPlan.
    If no active subscription exists, returns the default active 'Free' plan.
    """
    subscription = get_user_subscription(user)
    if subscription and subscription.plan and subscription.plan.is_active:
        return subscription.plan

    # Fallback to Free Plan
    free_plan = SubscriptionPlan.objects.filter(
        slug="free",
        is_active=True
    ).first()

    if not free_plan:
        free_plan = SubscriptionPlan.objects.filter(
            is_active=True
        ).order_by("price", "display_order").first()

    return free_plan


def get_available_features(user) -> List[PlanFeatureAccess]:
    """
    Returns all enabled PlanFeatureAccess records for the user's active plan.
    """
    plan = get_user_plan(user)
    if not plan:
        return []

    return list(
        PlanFeatureAccess.objects.filter(
            plan=plan,
            enabled=True,
            feature__isnull=False
        ).select_related("feature")
    )


def has_feature(user, feature_slug: str) -> bool:
    """
    Dynamically checks if a feature_slug is enabled for user's current subscription plan.
    Everything is database-driven and manageable via Django Admin.
    """
    if not feature_slug or not user or not user.is_authenticated:
        return False

    plan = get_user_plan(user)
    if not plan:
        return False

    return PlanFeatureAccess.objects.filter(
        plan=plan,
        feature__slug=feature_slug,
        enabled=True
    ).exists()


def get_usage_limit(user, feature_slug: str) -> Optional[int]:
    """
    Returns usage limit for feature_slug:
      - None: Unlimited usage
      - 0: Feature is disabled or plan not found
      - Positive Integer: Usage count limit
    """
    if not feature_slug or not user or not user.is_authenticated:
        return 0

    plan = get_user_plan(user)
    if not plan:
        return 0

    access = PlanFeatureAccess.objects.filter(
        plan=plan,
        feature__slug=feature_slug
    ).first()

    if not access or not access.enabled:
        return 0

    return access.usage_limit


def get_usage_record(user, feature_slug: str) -> Optional[FeatureUsage]:
    """
    Helper that finds or creates the current active FeatureUsage record for user & feature.
    """
    if not feature_slug or not user or not user.is_authenticated:
        return None

    feature = PlanFeature.objects.filter(slug=feature_slug).first()
    if not feature:
        return None

    subscription = get_user_subscription(user)

    usage, _ = FeatureUsage.objects.get_or_create(
        user=user,
        feature=feature,
        defaults={
            "subscription": subscription,
            "reset_type": FeatureUsage.ResetType.MONTHLY
        }
    )
    return usage


def get_usage_count(user, feature_slug: str) -> int:
    """
    Returns the current feature usage count for the user in their current billing period.
    """
    usage = get_usage_record(user, feature_slug)
    return usage.used_count if usage else 0


def can_use_feature(user, feature_slug: str) -> bool:
    """
    Evaluates if user can consume feature:
      - Returns False if has_feature is False
      - Returns True if usage limit is None (Unlimited)
      - Returns True if used_count < usage_limit
      - Returns False if usage limit reached or exceeded
    """
    if not has_feature(user, feature_slug):
        return False

    limit = get_usage_limit(user, feature_slug)
    if limit is None:
        return True

    used = get_usage_count(user, feature_slug)
    return used < limit


def get_remaining_usage(user, feature_slug: str) -> Optional[int]:
    """
    Returns remaining usage for a feature:
      - None: Unlimited usage
      - 0: Feature is disabled or limit reached
      - Positive Integer: Remaining available uses (e.g. 2 for 2/5 remaining)
    """
    if not has_feature(user, feature_slug):
        return 0

    limit = get_usage_limit(user, feature_slug)
    if limit is None:
        return None

    used = get_usage_count(user, feature_slug)
    return max(0, limit - used)


def increment_feature_usage(user, feature_slug: str, count: int = 1) -> Optional[FeatureUsage]:
    """
    Atomically increments used_count via Django F() expressions to prevent concurrency race conditions.
    """
    usage = get_usage_record(user, feature_slug)
    if not usage:
        return None

    FeatureUsage.objects.filter(pk=usage.pk).update(
        used_count=F("used_count") + count,
        last_used=timezone.now()
    )
    usage.refresh_from_db()
    return usage
