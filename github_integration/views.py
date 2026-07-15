from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseForbidden

from dashboard.navigation import get_sidebar_navigation
from portfolio.models import Portfolio
from github_integration.models import GitHubRepoConfig, GitHubDeployment

from .services.oauth_service import (
    is_github_connected,
    get_github_token,
    get_github_username,
    disconnect_github,
)
from .services.repository_service import (
    list_repositories,
    create_repository,
    get_authenticated_username,
)
from .services.deployment_service import publish_portfolio_to_github


def _base_context(request):
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "active_tab": "github",
    }


class GitHubConnectView(LoginRequiredMixin, View):
    """Redirects to allauth OAuth connect pipeline for GitHub."""
    def get(self, request):
        portfolio_pk = request.GET.get("portfolio_pk")
        if portfolio_pk:
            next_url = reverse("github:dashboard", kwargs={"pk": portfolio_pk})
        else:
            next_url = reverse("portfolio:list")
        return redirect(f"/accounts/social/github/login/?process=connect&next={next_url}")


class GitHubDisconnectView(LoginRequiredMixin, View):
    """Revokes the GitHub social account connection."""
    def post(self, request):
        disconnect_github(request.user)
        messages.success(request, "GitHub account disconnected successfully.")
        return redirect("portfolio:list")


class DeploymentDashboardView(LoginRequiredMixin, View):
    """
    Shows deployment information, linked repository configuration,
    and history of commits/Pages publications.
    """
    template_name = "github/dashboard.html"

    def get(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        connected = is_github_connected(request.user)
        
        ctx = _base_context(request)
        ctx.update({
            "portfolio": portfolio,
            "is_connected": connected,
            "github_username": get_github_username(request.user) if connected else "",
            "repo_config": getattr(portfolio, "github_config", None),
            "deployments": portfolio.deployments.all(),
            "latest_deployment": portfolio.deployments.first(),
            "breadcrumbs": [
                {"title": "My Portfolios", "url": reverse("portfolio:list")},
                {"title": f"Deploy: {portfolio.name}", "url": "#"},
            ],
        })

        if connected:
            token = get_github_token(request.user)
            if token:
                try:
                    ctx["repos_list"] = list_repositories(token)
                except Exception as e:
                    messages.error(request, f"Failed to retrieve repositories: {str(e)}")
            else:
                # Token might have expired or been revoked
                messages.warning(request, "GitHub access token not found. Please reconnect your account.")
                ctx["is_connected"] = False

        return render(request, self.template_name, ctx)


class ConfigureRepositoryView(LoginRequiredMixin, View):
    """
    Links a portfolio to a repository name. Handles creating new
    repositories or selecting existing ones.
    """
    def post(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        token = get_github_token(request.user)
        if not token:
            messages.error(request, "GitHub authentication token is missing. Please connect account first.")
            return redirect("github:dashboard", pk=portfolio.pk)

        repo_choice = request.POST.get("repo_choice", "existing")
        
        try:
            owner = get_authenticated_username(token)
            if not owner:
                raise Exception("Failed to identify GitHub user details.")

            if repo_choice == "new":
                new_repo_name = request.POST.get("new_repo").strip()
                if not new_repo_name:
                    raise Exception("Repository name cannot be blank.")
                # Create repository on GitHub
                create_repository(token, new_repo_name)
                repo_name = new_repo_name
            else:
                repo_name = request.POST.get("existing_repo")
                if not repo_name:
                    raise Exception("Please select a repository.")

            # Create or update local config
            config, _ = GitHubRepoConfig.objects.get_or_create(portfolio=portfolio)
            config.repo_name = repo_name
            config.repository_owner = owner
            config.branch_name = "main"
            config.save()

            messages.success(request, f"Portfolio connected to repository '{owner}/{repo_name}' successfully!")
        except Exception as e:
            messages.error(request, f"Configuration failed: {str(e)}")

        return redirect("github:dashboard", pk=portfolio.pk)


from payments.permissions import GitHubPublishLimitMixin


class PublishPortfolioView(GitHubPublishLimitMixin, LoginRequiredMixin, View):
    """
    Triggers the static export packaging compile and pushes changes
    directly via Git Data API commits.
    """
    def post(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        token = get_github_token(request.user)
        if not token:
            messages.error(request, "GitHub authentication token is missing.")
            return redirect("github:dashboard", pk=portfolio.pk)

        commit_msg = request.POST.get("commit_message", "Publish portfolio updates via AI Portfolio Builder").strip()
        if not commit_msg:
            commit_msg = "Publish portfolio updates via AI Portfolio Builder"

        try:
            deployment = publish_portfolio_to_github(portfolio, token, commit_message=commit_msg)
            if deployment.status == GitHubDeployment.Status.SUCCESS:
                messages.success(
                    request,
                    f"Portfolio published successfully! Live website URL: {deployment.published_url}"
                )
            else:
                messages.error(
                    request,
                    f"Publishing failed: {deployment.error_message}. Check deployment logs."
                )
        except Exception as e:
            messages.error(request, f"Deployment failed: {str(e)}")

        return redirect("github:dashboard", pk=portfolio.pk)


class ClearConnectionView(LoginRequiredMixin, View):
    """
    Removes the linked repository connection config locally,
    preserving all files committed to the GitHub repository itself.
    """
    def post(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        config = getattr(portfolio, "github_config", None)
        if config:
            repo = config.repo_name
            config.delete()
            messages.success(request, f"Removed repository connection config to '{repo}'.")
        return redirect("github:dashboard", pk=portfolio.pk)
