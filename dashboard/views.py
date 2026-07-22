from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.contrib import messages

from .navigation import get_sidebar_navigation
from themes.models import Theme
from github.models import GitHubDeployment, GitHubRepoConfig
from github.services.oauth_service import is_github_connected, get_github_username

User = get_user_model()


class DashboardBaseView(TemplateView):
    """Base view for dashboard views to inject common context."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_nav'] = get_sidebar_navigation(self.request.user)
        return context


class DashboardHomeView(LoginRequiredMixin, DashboardBaseView):
    """
    Main User Dashboard view: overview of uploaded themes, GitHub status, deployments.
    """
    template_name = "dashboard/home.html"
    login_url = "/accounts/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if not user or not user.is_authenticated:
            return context

        user_themes = Theme.objects.filter(uploaded_by=user).order_by("-created_at")
        all_themes = Theme.objects.filter(is_active=True)
        deployments = GitHubDeployment.objects.filter(user=user)
        is_connected = is_github_connected(user)

        context.update({
            "user_themes": user_themes,
            "user_themes_count": user_themes.count(),
            "total_themes_count": all_themes.count(),
            "is_github_connected": is_connected,
            "github_username": get_github_username(user) if is_connected else "",
            "deployments": deployments[:5],
            "successful_deployments_count": deployments.filter(status=GitHubDeployment.Status.SUCCESS).count(),
        })
        return context


class ProfileView(LoginRequiredMixin, DashboardBaseView):
    """
    User Profile & Account Settings view.
    """
    template_name = "dashboard/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        context["is_github_connected"] = is_github_connected(self.request.user)
        context["github_username"] = get_github_username(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        github_username = request.POST.get("github_username", "").strip()
        avatar = request.FILES.get("avatar")

        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if github_username:
            user.github_username = github_username
        if avatar:
            user.avatar = avatar

        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("dashboard:profile")


# Error views
def custom_permission_denied_view(request, exception=None):
    return render(request, "403.html", status=403)

def custom_page_not_found_view(request, exception=None):
    return render(request, "404.html", status=404)

def custom_server_error_view(request):
    return render(request, "500.html", status=500)

def custom_csrf_failure_view(request, reason=""):
    return render(request, "403.html", {"reason": reason}, status=403)
