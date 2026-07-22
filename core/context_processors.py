from django.conf import settings


def analytics_context(request):
    """Inject global site variables into templates."""
    canonical_url = request.build_absolute_uri(request.path)
    
    return {
        "IS_PRODUCTION": not settings.DEBUG,
        "SEO_TITLE": "Portfolio Theme Publisher — Upload & Deploy Themes to GitHub Pages",
        "SEO_DESCRIPTION": "Upload custom portfolio themes (HTML5, CSS3, JS, Bootstrap 5, Tailwind CSS), preview live, and publish directly to GitHub Pages.",
        "SEO_KEYWORDS": "portfolio theme upload, github pages publisher, bootstrap themes, tailwind themes, theme gallery",
        "CANONICAL_URL": canonical_url,
    }
