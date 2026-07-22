from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.urls import reverse
from django.conf import settings
from allauth.account.utils import get_next_redirect_url


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Overrides get_connect_redirect_url and get_app to ensure SocialApp and Site
    lookups never fail in production.
    """
    def get_connect_redirect_url(self, request, socialaccount):
        next_url = get_next_redirect_url(request)
        if next_url:
            return next_url
        return reverse("dashboard:home")

    def get_app(self, request, provider, client_id=None):
        """
        Safely retrieves or provisions the database SocialApp record linked to Site 1.
        """
        try:
            return super().get_app(request, provider, client_id=client_id)
        except Exception:
            try:
                site, _ = Site.objects.get_or_create(
                    id=settings.SITE_ID,
                    defaults={
                        "domain": "ai-portfolio-builder-icmv.onrender.com",
                        "name": "Theme Publisher Platform",
                    }
                )
                prov_config = settings.SOCIALACCOUNT_PROVIDERS.get(provider, {}).get("APP", {})
                client_id_val = prov_config.get("client_id", f"dummy-{provider}-client-id")
                secret_val = prov_config.get("secret", f"dummy-{provider}-secret")

                app, _ = SocialApp.objects.get_or_create(
                    provider=provider,
                    defaults={
                        "name": provider.title(),
                        "client_id": client_id_val,
                        "secret": secret_val,
                    }
                )
                if not app.sites.filter(id=site.id).exists():
                    app.sites.add(site)
                return app
            except Exception:
                # Ultimate fallback
                prov_config = settings.SOCIALACCOUNT_PROVIDERS.get(provider, {}).get("APP", {})
                return SocialApp(
                    provider=provider,
                    name=provider.title(),
                    client_id=prov_config.get("client_id", f"dummy-{provider}-client-id"),
                    secret=prov_config.get("secret", f"dummy-{provider}-secret"),
                )
