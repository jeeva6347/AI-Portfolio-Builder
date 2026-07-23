from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings


class Command(BaseCommand):
    help = "Initializes default Site domain and SocialApp records for production deployment."

    def handle(self, *args, **options):
        # 1. Ensure Site object exists for site_id=1
        try:
            site = Site.objects.get(id=settings.SITE_ID)
            site.domain = settings.SITE_DOMAIN
            site.name = settings.SITE_NAME
            site.save()
            self.stdout.write(self.style.SUCCESS(f"Updated Site domain: {site.domain}"))
        except Site.DoesNotExist:
            site = Site.objects.create(
                id=settings.SITE_ID,
                domain=settings.SITE_DOMAIN,
                name=settings.SITE_NAME,
            )
            self.stdout.write(self.style.SUCCESS(f"Created Site domain: {site.domain}"))

        # 2. Ensure SocialApp records exist for Google and GitHub
        for provider in ["google", "github"]:
            prov_config = settings.SOCIALACCOUNT_PROVIDERS.get(provider, {}).get("APP", {})
            client_id = prov_config.get("client_id", "")
            secret = prov_config.get("secret", "")

            if not client_id or not secret:
                self.stdout.write(self.style.WARNING(
                    f"Skipping {provider.title()} SocialApp: credentials are not configured."
                ))
                continue

            app, created = SocialApp.objects.get_or_create(
                provider=provider,
                defaults={
                    "name": provider.title(),
                    "client_id": client_id,
                    "secret": secret,
                }
            )
            if not created:
                if client_id and not client_id.startswith("dummy-"):
                    app.client_id = client_id
                if secret and not secret.startswith("dummy-"):
                    app.secret = secret
                app.save()

            if not app.sites.filter(id=site.id).exists():
                app.sites.add(site)

            status_str = "Created" if created else "Updated/Exists"
            self.stdout.write(self.style.SUCCESS(f"SocialApp '{provider}' ({status_str}) linked to Site {site.id}"))
