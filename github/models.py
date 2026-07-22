from django.db import models
from django.conf import settings
from themes.models import Theme


class GitHubRepoConfig(models.Model):
    """
    Persists the connected GitHub repository settings for a specific theme or user.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="github_configs"
    )
    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name="github_configs",
        null=True,
        blank=True
    )
    repo_name = models.CharField(max_length=200, help_text="e.g. my-glass-portfolio")
    repository_owner = models.CharField(max_length=150, help_text="GitHub username of the owner")
    branch_name = models.CharField(max_length=50, default="main")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "GitHub Repository Config"
        verbose_name_plural = "GitHub Repository Configs"

    def __str__(self):
        theme_str = self.theme.name if self.theme else "General"
        return f"{self.repository_owner}/{self.repo_name} ({theme_str})"


class GitHubDeployment(models.Model):
    """
    Historical records of each theme publishing attempt and Pages deployment status.
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="github_deployments"
    )
    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name="deployments"
    )
    repo_name = models.CharField(max_length=200)
    repository_owner = models.CharField(max_length=150)
    branch_name = models.CharField(max_length=50, default="main")

    deployment_version = models.PositiveIntegerField(default=1)
    deployment_duration = models.FloatField(default=0.0, help_text="Duration in seconds")
    deployment_message = models.CharField(max_length=255, blank=True)
    pages_enabled = models.BooleanField(default=False)

    last_commit_sha = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    published_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "GitHub Deployment Log"
        verbose_name_plural = "GitHub Deployment Logs"

    def __str__(self):
        return f"v{self.deployment_version} for {self.theme.name} on {self.repo_name} ({self.status})"
