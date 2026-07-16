from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import AccessMixin

from .models import UsageMetrics, UserSubscription


def get_user_plan_benefits(user):
    """
    Returns the SubscriptionPlan limits configuration for a given user.
    """
    sub = getattr(user, "subscription", None)
    if sub and sub.is_active:
        return sub.plan
    # Default fallback to first plan or free limits
    from .models import SubscriptionPlan
    free_plan = SubscriptionPlan.objects.filter(slug="free").first()
    return free_plan


# ═══════════════════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

def portfolio_limit_required(view_func):
    """Checks if the user has reached the maximum allowed portfolios under their plan."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            # Sync usage metrics first to be accurate
            metrics, _ = UsageMetrics.objects.get_or_create(user=user)
            metrics.sync_metrics()
            
            plan = get_user_plan_benefits(user)
            if metrics.portfolios_count >= plan.portfolio_limit:
                messages.warning(
                    request,
                    f"Portfolio creation limit of {plan.portfolio_limit} reached on your current plan. Please upgrade to create more."
                )
                return redirect("payments:billing")
        return view_func(request, *args, **kwargs)
    return _wrapped


def ai_limit_required(view_func):
    """Enforces resume uploads and parsing limits."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            metrics, _ = UsageMetrics.objects.get_or_create(user=user)
            metrics.sync_metrics()
            
            plan = get_user_plan_benefits(user)
            # If on a paid plan, bypass limits to allow unlimited parsing
            if plan.slug != "free":
                return view_func(request, *args, **kwargs)
                
            if metrics.ai_uploads_count >= plan.ai_usage_limit:
                messages.warning(
                    request,
                    f"You have reached your limit of {plan.ai_usage_limit} AI resume parses. Upgrade to unlock more imports."
                )
                return redirect("payments:billing")
        return view_func(request, *args, **kwargs)
    return _wrapped


def github_publish_limit_required(view_func):
    """Restricts portfolio auto publishing based on subscriber tier limits."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            metrics, _ = UsageMetrics.objects.get_or_create(user=user)
            metrics.sync_metrics()
            
            plan = get_user_plan_benefits(user)
            if metrics.github_publishes_count >= plan.github_publish_limit:
                messages.warning(
                    request,
                    f"GitHub Pages publishing is capped at {plan.github_publish_limit} updates on your current tier. Please upgrade."
                )
                return redirect("payments:billing")
        return view_func(request, *args, **kwargs)
    return _wrapped


# ═══════════════════════════════════════════════════════════════════════════════
# CLASS MIXINS FOR CBV
# ═══════════════════════════════════════════════════════════════════════════════

class PortfolioLimitMixin(AccessMixin):
    """CBV Mixin to block portfolio creation if limit reached."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            metrics, _ = UsageMetrics.objects.get_or_create(user=request.user)
            metrics.sync_metrics()
            
            plan = get_user_plan_benefits(request.user)
            if metrics.portfolios_count >= plan.portfolio_limit:
                messages.warning(
                    request,
                    f"Portfolio creation limit of {plan.portfolio_limit} reached. Upgrade your plan."
                )
                return redirect("payments:billing")
        return super().dispatch(request, *args, **kwargs)


class AILimitMixin(AccessMixin):
    """CBV Mixin to restrict AI resume uploads."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            metrics, _ = UsageMetrics.objects.get_or_create(user=request.user)
            metrics.sync_metrics()
            
            plan = get_user_plan_benefits(request.user)
            # If on a paid plan, bypass limits to allow unlimited parsing
            if plan.slug != "free":
                return super().dispatch(request, *args, **kwargs)
                
            if metrics.ai_uploads_count >= plan.ai_usage_limit:
                messages.warning(
                    request,
                    f"AI parses limit of {plan.ai_usage_limit} reached. Upgrade your plan."
                )
                return redirect("payments:billing")
        return super().dispatch(request, *args, **kwargs)


class GitHubPublishLimitMixin(AccessMixin):
    """CBV Mixin to enforce GitHub auto-publish count limits."""
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            metrics, _ = UsageMetrics.objects.get_or_create(user=request.user)
            metrics.sync_metrics()
            
            plan = get_user_plan_benefits(request.user)
            if metrics.github_publishes_count >= plan.github_publish_limit:
                messages.warning(
                    request,
                    f"GitHub Page updates limit of {plan.github_publish_limit} reached. Upgrade your plan."
                )
                return redirect("payments:billing")
        return super().dispatch(request, *args, **kwargs)
