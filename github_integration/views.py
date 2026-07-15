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

                # Fetch real-time GitHub Pages build status if repo config is linked
                repo_config = ctx.get("repo_config")
                if repo_config:
                    try:
                        pages_info = get_github_pages_info(token, repo_config.repository_owner, repo_config.repo_name)
                        if pages_info.get("pages_enabled"):
                            ctx["live_pages_status"] = pages_info.get("status")  # "built", "building", or "errored"
                        else:
                            ctx["live_pages_status"] = "not_configured"
                    except Exception:
                        ctx["live_pages_status"] = "unknown"
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


class AutoDeployView(LoginRequiredMixin, View):
    """
    Automatically creates a repository with a name based on the portfolio,
    links the repository mapping, and immediately publishes the website.
    """
    def post(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        token = get_github_token(request.user)
        if not token:
            messages.error(request, "GitHub authentication token is missing. Please connect account first.")
            return redirect("github:dashboard", pk=portfolio.pk)

        import re
        base_name = portfolio.name or "my-portfolio"
        repo_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '-', base_name.lower())
        repo_name = re.sub(r'-+', '-', repo_name).strip('-')
        if not repo_name:
            repo_name = f"portfolio-{portfolio.pk}"

        try:
            owner = get_authenticated_username(token)
            if not owner:
                raise Exception("Failed to identify GitHub user details.")

            success = False
            suffix = 0
            current_repo_name = repo_name
            while not success and suffix < 10:
                try:
                    create_repository(token, current_repo_name)
                    success = True
                    repo_name = current_repo_name
                except Exception:
                    suffix += 1
                    current_repo_name = f"{repo_name}-{suffix}"
            
            if not success:
                raise Exception("Could not create a unique repository name. Please configure manually.")

            # Create or update local config
            config, _ = GitHubRepoConfig.objects.get_or_create(portfolio=portfolio)
            config.repo_name = repo_name
            config.repository_owner = owner
            config.branch_name = "main"
            config.save()

            # Trigger publishing immediately
            deployment = publish_portfolio_to_github(portfolio, token, commit_message="Auto-deployed via AI Portfolio Builder")
            
            if deployment.status == GitHubDeployment.Status.SUCCESS:
                messages.success(
                    request,
                    f"Repository '{owner}/{repo_name}' created and portfolio deployed successfully! Live URL: {deployment.published_url}"
                )
            else:
                messages.warning(
                    request,
                    f"Repository '{owner}/{repo_name}' created, but publishing failed: {deployment.error_message}. You can manually retry from the panel."
                )
        except Exception as e:
            messages.error(request, f"Auto-deployment failed: {str(e)}")

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
