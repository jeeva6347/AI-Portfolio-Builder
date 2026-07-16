from django.conf import settings
from decouple import config

def analytics_context(request):
    """Inject analytics and global SEO variables into templates conditionally in production."""
    # Build absolute canonical URL safely
    canonical_url = request.build_absolute_uri(request.path)
    # Build fallback share image absolute URL
    og_default_image = request.build_absolute_uri("/static/img/og_default_share_card.png")
    
    return {
        "GOOGLE_ANALYTICS_ID": getattr(settings, "GOOGLE_ANALYTICS_ID", ""),
        "MICROSOFT_CLARITY_ID": getattr(settings, "MICROSOFT_CLARITY_ID", ""),
        "IS_PRODUCTION": not settings.DEBUG,
        
        # Site verification meta tags
        "GOOGLE_SITE_VERIFICATION": config("GOOGLE_SITE_VERIFICATION", default=""),
        "BING_SITE_VERIFICATION": config("BING_SITE_VERIFICATION", default=""),
        
        # Reusable global SEO configuration
        "SEO_TITLE": "AI Portfolio Builder — Create Professional Portfolios in Seconds",
        "SEO_DESCRIPTION": "Convert your resume PDF or Word file into a stunning, responsive public portfolio hosted on GitHub Pages or custom domains using Gemini AI mapping.",
        "SEO_KEYWORDS": "portfolio builder, resume parser, AI resume import, developer portfolio, github pages, designer resume, custom domains",
        "CANONICAL_URL": canonical_url,
        "OG_DEFAULT_IMAGE": og_default_image,
        "THEME_COLOR": "#0b0f19",
    }
