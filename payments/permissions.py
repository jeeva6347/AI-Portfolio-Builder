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
    """ALL FEATURES FREE: Portfolio limit check bypassed — all users have unlimited portfolios."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped


def ai_limit_required(view_func):
    """ALL FEATURES FREE: AI usage limit check bypassed — all users have unlimited AI features."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped


def github_publish_limit_required(view_func):
    """ALL FEATURES FREE: GitHub publish limit check bypassed — all users have unlimited publishes."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped


# ═══════════════════════════════════════════════════════════════════════════════
# CLASS MIXINS FOR CBV
# ═══════════════════════════════════════════════════════════════════════════════

class PortfolioLimitMixin(AccessMixin):
    """ALL FEATURES FREE: Portfolio limit bypassed — no user is ever blocked."""
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class AILimitMixin(AccessMixin):
    """ALL FEATURES FREE: AI limit bypassed — no user is ever blocked."""
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class GitHubPublishLimitMixin(AccessMixin):
    """ALL FEATURES FREE: GitHub publish limit bypassed — no user is ever blocked."""
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
