from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse

from themes.models import Theme
from github.models import GitHubRepoConfig, GitHubDeployment

from .services.oauth_service import (
    is_github_connected,
    get_github_token,
    get_github_username,
    disconnect_github,
)
from .services.repository_service import list_repositories
from .services.deployment_service import publish_theme_to_github
from .services.pages_service import get_github_pages_info


def _base_context(request):
    return {
        "active_tab": "github",
    }


class GitHubConnectView(LoginRequiredMixin, View):
    """Redirects to allauth OAuth connect pipeline for GitHub."""
    def get(self, request):
        theme_pk = request.GET.get("theme_pk")
        if theme_pk:
            next_url = reverse("github:theme_deploy", kwargs={"pk": theme_pk})
        else:
            next_url = reverse("github:index")
        return redirect(f"/accounts/social/github/login/?process=connect&next={next_url}")


class GitHubDisconnectView(LoginRequiredMixin, View):
    """Revokes the GitHub social account connection."""
    def post(self, request):
        disconnect_github(request.user)
        messages.success(request, "GitHub account disconnected successfully.")
        return redirect("github:index")


class GitHubIndexView(LoginRequiredMixin, View):
    """
    Main GitHub Settings & Publishing Overview page.
    """
    template_name = "github/index.html"

    def get(self, request):
        connected = is_github_connected(request.user)
        github_user = get_github_username(request.user) if connected else ""

        user_themes = Theme.objects.filter(uploaded_by=request.user)
        deployments = GitHubDeployment.objects.filter(user=request.user)

        ctx = _base_context(request)
        ctx.update({
            "is_connected": connected,
            "github_username": github_user,
            "user_themes": user_themes,
            "deployments": deployments,
            "latest_deployment": deployments.first(),
        })

        if connected:
            token = get_github_token(request.user)
            if token:
                try:
                    ctx["repos_list"] = list_repositories(token)
                except Exception as e:
                    messages.error(request, f"Failed to retrieve GitHub repositories: {str(e)}")

        return render(request, self.template_name, ctx)


class ThemeDeployView(LoginRequiredMixin, View):
    """
    Handles publishing a specific theme to GitHub Pages.
    """
    template_name = "github/deploy.html"

    def get(self, request, pk):
        theme = get_object_or_404(Theme, pk=pk)
        connected = is_github_connected(request.user)

        repo_config = GitHubRepoConfig.objects.filter(user=request.user, theme=theme).first()
        deployments = GitHubDeployment.objects.filter(user=request.user, theme=theme)

        ctx = _base_context(request)
        ctx.update({
            "theme": theme,
            "is_connected": connected,
            "github_username": get_github_username(request.user) if connected else "",
            "repo_config": repo_config,
            "deployments": deployments,
            "latest_deployment": deployments.first(),
        })

        if connected:
            token = get_github_token(request.user)
            if token and repo_config:
                try:
                    pages_info = get_github_pages_info(token, repo_config.repository_owner, repo_config.repo_name)
                    ctx["live_pages_status"] = pages_info.get("status") if pages_info.get("pages_enabled") else "not_configured"
                except Exception:
                    ctx["live_pages_status"] = "unknown"

        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        theme = get_object_or_404(Theme, pk=pk)
        if not is_github_connected(request.user):
            messages.error(request, "Please connect your GitHub account first.")
            return redirect(f"/github/connect/?theme_pk={theme.pk}")

        token = get_github_token(request.user)
        if not token:
            messages.error(request, "GitHub access token missing. Please reconnect your account.")
            return redirect("github:connect")

        # Get or update repo name preference from post form
        repo_name = request.POST.get("repo_name", "").strip() or f"{theme.slug}-portfolio"
        owner = get_github_username(request.user) or request.user.username

        repo_config, _ = GitHubRepoConfig.objects.get_or_create(
            user=request.user,
            theme=theme,
            defaults={"repo_name": repo_name, "repository_owner": owner}
        )
        if repo_name != repo_config.repo_name:
            repo_config.repo_name = repo_name
            repo_config.save()

        try:
            deployment = publish_theme_to_github(
                user=request.user,
                theme=theme,
                token=token,
                commit_message=f"Deploy {theme.name} portfolio to GitHub Pages"
            )

            if deployment.status == GitHubDeployment.Status.SUCCESS:
                messages.success(request, f"Theme '{theme.name}' successfully published to GitHub Pages! URL: {deployment.published_url}")
            else:
                messages.error(request, f"Publishing failed: {deployment.error_message}")

        except Exception as e:
            messages.error(request, f"Deployment failed: {str(e)}")

        return redirect("github:theme_deploy", pk=theme.pk)
