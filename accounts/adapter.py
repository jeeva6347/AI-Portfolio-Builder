from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from django.urls import reverse
from django.conf import settings
from allauth.account.utils import get_next_redirect_url


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Overrides get_connect_redirect_url and get_app to ensure SocialApp
    lookup never raises SocialApp.DoesNotExist.
    """
    def get_connect_redirect_url(self, request, socialaccount):
        next_url = get_next_redirect_url(request)
        if next_url:
            return next_url
        return reverse("dashboard:home")

    def get_app(self, request, provider, client_id=None):
        """
        Safely returns SocialApp instance from DB or settings fallback.
        """
        try:
            return super().get_app(request, provider, client_id=client_id)
        except Exception:
            prov_config = settings.SOCIALACCOUNT_PROVIDERS.get(provider, {}).get("APP", {})
            app = SocialApp(
                provider=provider,
                name=provider.title(),
                client_id=prov_config.get("client_id", f"dummy-{provider}-client-id"),
                secret=prov_config.get("secret", f"dummy-{provider}-secret"),
            )
            return app
