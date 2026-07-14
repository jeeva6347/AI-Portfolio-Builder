from django.conf import settings

def analytics_context(request):
    """Inject analytics variables into templates conditionally in production."""
    return {
        "GOOGLE_ANALYTICS_ID": getattr(settings, "GOOGLE_ANALYTICS_ID", ""),
        "MICROSOFT_CLARITY_ID": getattr(settings, "MICROSOFT_CLARITY_ID", ""),
        "IS_PRODUCTION": not settings.DEBUG,
    }
