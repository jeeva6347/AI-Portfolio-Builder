from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from .mixins import SuperAdminRequiredMixin, AdminRequiredMixin
from .navigation import get_sidebar_navigation

User = get_user_model()

# Lazy import to avoid circular dependency at module load time
def _get_theme_model():
    from themes.models import Theme
    return Theme

class DashboardBaseView(TemplateView):
    """Base view for dashboards to inject common context."""
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_nav'] = get_sidebar_navigation(self.request.user)
        return context

class SuperAdminDashboardView(SuperAdminRequiredMixin, DashboardBaseView):
    template_name = "dashboard/super_admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        Theme = _get_theme_model()
        # Real statistics
        context['total_users'] = User.objects.count()
        context['premium_users'] = User.objects.filter(role=User.Role.PREMIUM_USER).count()
        context['free_users'] = User.objects.filter(role=User.Role.FREE_USER).count()
        context['admin_users'] = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]).count()

        # Recent users table
        context['recent_users'] = User.objects.order_by('-created_at')[:5]

        # Real theme stats
        context['total_themes'] = Theme.objects.count()
        context['premium_themes'] = Theme.objects.filter(is_premium=True, status=Theme.Status.APPROVED).count()
        context['published_portfolios'] = 0
        context['monthly_revenue'] = "$0.00"
        context['github_connections'] = User.objects.exclude(github_username="").count()

        context['breadcrumbs'] = [{'title': 'Dashboard', 'url': '#'}]
        return context


class AdminDashboardView(AdminRequiredMixin, DashboardBaseView):
    template_name = "dashboard/admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_users'] = User.objects.count()
        context['managed_themes'] = 0
        context['pending_themes'] = 0
        context['published_themes'] = 0
        
        context['breadcrumbs'] = [{'title': 'Admin Dashboard', 'url': '#'}]
        return context

class UserDashboardView(LoginRequiredMixin, DashboardBaseView):
    template_name = "dashboard/user.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['my_portfolios'] = 0
        context['drafts'] = 0
        context['published'] = 0
        context['github_projects'] = 0
        
        context['breadcrumbs'] = [{'title': 'My Dashboard', 'url': '#'}]
        return context

class PlaceholderView(LoginRequiredMixin, DashboardBaseView):
    template_name = "dashboard/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        title = self.kwargs.get('title', 'Coming Soon')
        context['page_title'] = title
        context['breadcrumbs'] = [
            {'title': 'Dashboard', 'url': '#'},
            {'title': title, 'url': '#'},
        ]
        return context

def custom_permission_denied_view(request, exception=None):
    """Custom 403 error handler."""
    context = {}
    if request.user.is_authenticated:
        context['sidebar_nav'] = get_sidebar_navigation(request.user)
    
    return render(request, "403.html", context, status=403)
