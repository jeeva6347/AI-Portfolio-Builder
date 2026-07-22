from django.views.generic import TemplateView
from themes.models import Theme


class LandingPageView(TemplateView):
    """
    Renders the public landing page showcasing theme upload & GitHub Pages publishing features.
    """
    template_name = "core/landing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["themes"] = Theme.objects.filter(is_active=True).order_by("-created_at")[:6]
        return ctx
