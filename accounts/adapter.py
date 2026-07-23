import sys
import traceback
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.urls import reverse
from django.conf import settings
from allauth.account.utils import get_next_redirect_url
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Overrides allauth social account adapter to:
    1. Direct users to /dashboard/ on login.
    2. Auto-connect existing user accounts when email matches.
    3. Safely retrieve or provision SocialApp and Site records in production.
    4. Log authentication errors to stderr for production debugging.
    """
    def get_connect_redirect_url(self, request, socialaccount):
        next_url = get_next_redirect_url(request)
        if next_url:
            return next_url
        return reverse("dashboard:home")

    def get_login_redirect_url(self, request):
        return reverse("dashboard:home")

    def pre_social_login(self, request, sociallogin):
        """
        Auto-connect social account to an existing user if a user with the same email exists.
        """
        if sociallogin.is_existing:
            return
        if not sociallogin.email_addresses:
            return
        email = sociallogin.email_addresses[0].email
        if not email:
            return
        try:
            user = User.objects.get(email__iexact=email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        sys.stderr.write(f"[SOCIAL AUTH ERROR] Provider: {provider}, Error: {error}, Exception: {exception}\n")
        if exception:
            sys.stderr.write(f"Traceback:\n{''.join(traceback.format_tb(exception.__traceback__))}\n")
        super().on_authentication_error(request, provider, error=error, exception=exception, extra_context=extra_context)

    def get_app(self, request, provider, client_id=None):
        """
        Safely retrieves or provisions the database SocialApp record linked to Site 1.
        """
        try:
            return super().get_app(request, provider, client_id=client_id)
        except Exception as exc:
            sys.stderr.write(f"[GET_APP FALLBACK] Exception fetching SocialApp for {provider}: {exc}\n")
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
