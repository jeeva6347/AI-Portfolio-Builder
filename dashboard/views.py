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
        # Real portfolio stats
        from portfolio.models import Portfolio
        from payments.models import PaymentTransaction
        from django.db.models import Sum
        
        context['published_portfolios'] = Portfolio.objects.filter(status=Portfolio.Status.PUBLISHED).count()
        total_revenue = PaymentTransaction.objects.filter(status="success").aggregate(total=Sum("amount"))["total"] or 0.00
        context['monthly_revenue'] = f"${total_revenue:.2f}"
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
        from portfolio.models import Portfolio
        # Use select_related + prefetch to avoid N+1 queries
        portfolios = list(
            Portfolio.objects.filter(user=self.request.user)
            .select_related("selected_theme")
            .prefetch_related("metric")
        )
        primary_portfolio = sorted(portfolios, key=lambda p: p.updated_at or p.created_at, reverse=True)[0] if portfolios else None

        context['my_portfolios'] = len(portfolios)
        context['selected_theme_name'] = primary_portfolio.selected_theme.name if primary_portfolio and primary_portfolio.selected_theme else "None"

        context['drafts'] = sum(1 for p in portfolios if p.status == Portfolio.Status.DRAFT)
        context['published'] = sum(1 for p in portfolios if p.status == Portfolio.Status.PUBLISHED)
        context['archived'] = sum(1 for p in portfolios if p.status == Portfolio.Status.ARCHIVED)
        context['github_projects'] = primary_portfolio.projects.exclude(github_url="").count() if primary_portfolio else 0

        # Traffic aggregates — use annotation to avoid N+1 per portfolio
        from analytics.models import PortfolioMetric, PortfolioVisit
        from django.db.models import Sum as DbSum, Avg
        metrics_qs = PortfolioMetric.objects.filter(portfolio__user=self.request.user)

        totals = metrics_qs.aggregate(
            total_visits=DbSum("total_visits"),
            avg_seo=Avg("seo_score"),
            avg_perf=Avg("performance_score"),
        )
        total_views = totals["total_visits"] or 0
        avg_seo = round(totals["avg_seo"] or 100)
        avg_perf = round(totals["avg_perf"] or 100)

        context['total_views'] = total_views
        context['avg_seo'] = avg_seo
        context['avg_perf'] = avg_perf

        # 30 days Chart.js trend parameters
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.now().date()
        date_list = [today - timedelta(days=x) for x in range(30)]
        date_list.reverse()

        context['chart_labels'] = [d.strftime("%b %d") for d in date_list]
        all_user_visits = PortfolioVisit.objects.filter(
            portfolio__user=self.request.user,
            timestamp__date__gte=today - timedelta(days=30)
        )
        visits_by_date = {}
        for v in all_user_visits:
            v_date = v.timestamp.date()
            visits_by_date[v_date] = visits_by_date.get(v_date, 0) + 1

        context['chart_data'] = [visits_by_date.get(d, 0) for d in date_list]

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

def custom_page_not_found_view(request, exception=None):
    """Custom 404 error handler."""
    context = {}
    if request.user.is_authenticated:
        context['sidebar_nav'] = get_sidebar_navigation(request.user)
    return render(request, "404.html", context, status=404)

def custom_server_error_view(request):
    """Custom 500 error handler."""
    context = {}
    return render(request, "500.html", context, status=500)

def custom_csrf_failure_view(request, reason=""):
    """Custom CSRF failure handler."""
    context = {'reason': reason}
    return render(request, "csrf_failure.html", context, status=403)
