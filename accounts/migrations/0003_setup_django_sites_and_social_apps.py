from django.db import migrations
from decouple import config

def setup_sites_and_apps(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    SocialApp = apps.get_model('socialaccount', 'SocialApp')

    # Configure SITE_ID = 1
    site, created = Site.objects.get_or_create(id=1)
    site.domain = 'ai-portfolio-builder-icmv.onrender.com'
    site.name = 'AI Portfolio Builder'
    site.save()

    # Configure Google SocialApp
    google_client_id = config('GOOGLE_OAUTH_CLIENT_ID', default='dummy-google-client-id')
    google_secret = config('GOOGLE_OAUTH_CLIENT_SECRET', default='dummy-google-client-secret')

    if not google_client_id:
        google_client_id = 'dummy-google-client-id'
    if not google_secret:
        google_secret = 'dummy-google-client-secret'

    google_app, created = SocialApp.objects.get_or_create(
        provider='google',
        defaults={
            'name': 'Google OAuth',
            'client_id': google_client_id,
            'secret': google_secret,
        }
    )
    if not created:
        google_app.client_id = google_client_id
        google_app.secret = google_secret
        google_app.save()
    google_app.sites.add(site)

    # Configure GitHub SocialApp
    github_client_id = config('GITHUB_OAUTH_CLIENT_ID', default='dummy-github-client-id')
    github_secret = config('GITHUB_OAUTH_CLIENT_SECRET', default='dummy-github-client-secret')

    if not github_client_id:
        github_client_id = 'dummy-github-client-id'
    if not github_secret:
        github_secret = 'dummy-github-client-secret'

    github_app, created = SocialApp.objects.get_or_create(
        provider='github',
        defaults={
            'name': 'GitHub OAuth',
            'client_id': github_client_id,
            'secret': github_secret,
        }
    )
    if not created:
        github_app.client_id = github_client_id
        github_app.secret = github_secret
        github_app.save()
    github_app.sites.add(site)

def remove_sites_and_apps(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_theme_preference'),
        ('sites', '0001_initial'),
        ('socialaccount', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(setup_sites_and_apps, remove_sites_and_apps),
    ]
