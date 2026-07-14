"""
Version 2.0: core views.py

Renders the modern, dynamic SaaS landing page displaying real database themes
and pricing plans.
"""
from django.views.generic import TemplateView
from themes.models import Theme
from payments.models import SubscriptionPlan


class LandingPageView(TemplateView):
    """
    Renders the public landing page with Hero, features, AI demo,
    real marketplace themes, pricing tiers, and FAQ.
    """
    template_name = "core/landing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Get active/approved themes
        ctx["themes"] = Theme.objects.filter(status=Theme.Status.APPROVED)[:6]
        # Get SaaS pricing plans
        ctx["plans"] = SubscriptionPlan.objects.all().order_by("price")
        return ctx
