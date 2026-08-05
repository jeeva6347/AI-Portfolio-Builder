from django.conf import settings
from dashboard.navigation import get_sidebar_navigation


def analytics_context(request):
    """Inject global site variables into templates."""
    canonical_url = request.build_absolute_uri(request.path)
    
    return {
        "IS_PRODUCTION": not settings.DEBUG,
        "SEO_TITLE": "Theme Publisher — Upload & Deploy Themes to GitHub Pages",
        "SEO_DESCRIPTION": "Upload custom themes (HTML5, CSS3, JS, Bootstrap 5, Tailwind CSS), preview live, and publish directly to GitHub Pages.",
        "SEO_KEYWORDS": "theme upload, github pages publisher, bootstrap themes, tailwind themes, theme gallery",
        "CANONICAL_URL": canonical_url,
    }


def sidebar_context(request):
    """Inject sidebar_nav into all template contexts for logged-in users."""
    if hasattr(request, "user") and request.user.is_authenticated:
        return {
            "sidebar_nav": get_sidebar_navigation(request.user)
        }
    return {
        "sidebar_nav": []
    }
