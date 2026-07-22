from django.apps import AppConfig


class GithubConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "github"
    label = "github_app"
    verbose_name = "GitHub Deployment & Integration"
