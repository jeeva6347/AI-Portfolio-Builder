from django.contrib import admin
from .models import GitHubRepoConfig, GitHubDeployment


@admin.register(GitHubRepoConfig)
class GitHubRepoConfigAdmin(admin.ModelAdmin):
    list_display = ("repository_owner", "repo_name", "user", "theme", "created_at")
    search_fields = ("repository_owner", "repo_name", "user__username")
    list_filter = ("branch_name", "created_at")


@admin.register(GitHubDeployment)
class GitHubDeploymentAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "repo_name", "deployment_version", "status", "published_url", "created_at")
    list_filter = ("status", "pages_enabled", "created_at")
    search_fields = ("repo_name", "repository_owner", "user__username", "theme__name")
    readonly_fields = ("created_at", "updated_at")
