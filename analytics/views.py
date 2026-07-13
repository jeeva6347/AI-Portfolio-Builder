from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
from django import forms
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta

from dashboard.navigation import get_sidebar_navigation
from portfolio.models import Portfolio
from themes.models import Theme
from github_integration.models import GitHubDeployment
from payments.models import UserSubscription, UsageMetrics
from .models import PortfolioMetric, PortfolioSEO, PortfolioVisit
from .services.performance_service import analyze_performance
from .services.seo_service import calculate_seo_score


class PortfolioSEOForm(forms.ModelForm):
    class Meta:
        model = PortfolioSEO
        fields = [
            "seo_title", "meta_description", "keywords", "canonical_url",
            "og_title", "og_description", "og_image",
            "twitter_title", "twitter_description",
            "favicon", "robots_txt"
        ]
        widgets = {
            "seo_title": forms.TextInput(attrs={"class": "form-control rounded-pill text-xs", "placeholder": "SEO Browser Window Title Override"}),
            "meta_description": forms.Textarea(attrs={"class": "form-control rounded-2xl text-xs", "rows": 3, "placeholder": "Search engine snippet (150-160 characters suggested)..."}),
            "keywords": forms.TextInput(attrs={"class": "form-control rounded-pill text-xs", "placeholder": "e.g. portfolio, developer, python, designer"}),
            "canonical_url": forms.URLInput(attrs={"class": "form-control rounded-pill text-xs", "placeholder": "https://yoursite.com"}),
            "og_title": forms.TextInput(attrs={"class": "form-control rounded-pill text-xs", "placeholder": "Social sharing card title"}),
            "og_description": forms.Textarea(attrs={"class": "form-control rounded-2xl text-xs", "rows": 2, "placeholder": "Social sharing summary description..."}),
            "twitter_title": forms.TextInput(attrs={"class": "form-control rounded-pill text-xs", "placeholder": "Twitter Card title"}),
            "twitter_description": forms.Textarea(attrs={"class": "form-control rounded-2xl text-xs", "rows": 2, "placeholder": "Twitter Card summary description..."}),
            "robots_txt": forms.Textarea(attrs={"class": "form-control rounded-2xl text-xs", "rows": 3}),
        }


def _base_context(request, active_tab="analytics"):
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "active_tab": active_tab,
    }


class AnalyticsDashboardView(LoginRequiredMixin, View):
    """
    Core Analytics page visualizing visits charts, referrers, and geography.
    Gated to PREMIUM_USER and SUPER_ADMIN roles.
    """
    template_name = "analytics/dashboard.html"

    def get(self, request):
        # Premium subscription tier limits validation check
        from payments.permissions import get_user_plan_benefits
        plan = get_user_plan_benefits(request.user)
        is_admin = request.user.role in [request.user.Role.SUPER_ADMIN, request.user.Role.ADMIN]
        if not (plan.premium_themes_enabled or is_admin):
            messages.warning(request, "Portfolio Traffic Analytics is a Premium feature. Please upgrade your subscription plan.")
            return redirect("payments:billing")

        user = request.user
        portfolios = Portfolio.objects.filter(user=user)
        
        # Calculate totals across all user portfolios
        total_views = 0
        total_uniques = 0
        total_returning = 0
        
        portfolio_stats = []
        recent_visits = PortfolioVisit.objects.filter(portfolio__user=user).order_by("-timestamp")[:10]

        for p in portfolios:
            metric, _ = PortfolioMetric.objects.get_or_create(portfolio=p)
            total_views += metric.total_visits
            total_uniques += metric.unique_visitors
            total_returning += metric.returning_visitors
            portfolio_stats.append({
                "portfolio": p,
                "metric": metric,
            })

        # Calculate daily traffic data over past 30 days for Chart.js
        today = timezone.now().date()
        date_list = [today - timedelta(days=x) for x in range(30)]
        date_list.reverse()
        
        chart_labels = [d.strftime("%b %d") for d in date_list]
        chart_data = []
        
        all_user_visits = PortfolioVisit.objects.filter(portfolio__user=user, timestamp__date__gte=today - timedelta(days=30))
        visits_by_date = {}
        for v in all_user_visits:
            v_date = v.timestamp.date()
            visits_by_date[v_date] = visits_by_date.get(v_date, 0) + 1
            
        for d in date_list:
            chart_data.append(visits_by_date.get(d, 0))

        # Device Types breakdown splits
        device_counts = all_user_visits.values("device_type").annotate(count=Count("id"))
        device_labels = [x["device_type"] for x in device_counts]
        device_data = [x["count"] for x in device_counts]

        # Browser breakdown splits
        browser_counts = all_user_visits.values("browser").annotate(count=Count("id"))
        browser_labels = [x["browser"] for x in browser_counts]
        browser_data = [x["count"] for x in browser_counts]

        # Referrers splits
        referrer_stats = all_user_visits.values("referrer").annotate(count=Count("id")).order_by("-count")[:5]
        
        # Geography splits
        country_stats = all_user_visits.values("country").annotate(count=Count("id")).order_by("-count")[:5]

        # Most Viewed Pages path splits
        page_stats = all_user_visits.values("path", "portfolio__name").annotate(count=Count("id")).order_by("-count")[:5]

        # -----------------------------------------------------------------------
        # ADMIN ANALYTICS PANELS (Only rendered if admin)
        # -----------------------------------------------------------------------
        admin_context = {}
        if is_admin:
            admin_context.update({
                "admin_total_views": PortfolioVisit.objects.count(),
                "admin_published_portfolios": Portfolio.objects.filter(status=Portfolio.Status.PUBLISHED).count(),
                "admin_premium_subs": UserSubscription.objects.exclude(plan__slug="free").count(),
                "admin_total_deployments": GitHubDeployment.objects.count(),
                "admin_ai_uploads": UsageMetrics.objects.aggregate(total=Sum("ai_uploads_count"))["total"] or 0,
                "admin_popular_themes": Theme.objects.filter(status=Theme.Status.APPROVED).order_by("-downloads")[:5],
                "admin_subscription_distribution": UserSubscription.objects.values("plan__name").annotate(count=Count("id")),
            })

        ctx = _base_context(request)
        ctx.update({
            "portfolios": portfolios,
            "portfolio_stats": portfolio_stats,
            "total_views": total_views,
            "total_uniques": total_uniques,
            "total_returning": total_returning,
            "recent_visits": recent_visits,
            "chart_labels": chart_labels,
            "chart_data": chart_data,
            "device_labels": device_labels,
            "device_data": device_data,
            "browser_labels": browser_labels,
            "browser_data": browser_data,
            "referrer_stats": referrer_stats,
            "country_stats": country_stats,
            "page_stats": page_stats,
            "is_admin_user": is_admin,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Traffic & SEO Analytics Portal", "url": "#"},
            ],
        })
        ctx.update(admin_context)
        return render(request, self.template_name, ctx)


class PortfolioSEOConfigView(LoginRequiredMixin, View):
    """
    Form view managing portfolio search metadata parameters.
    """
    template_name = "analytics/seo_config.html"

    def get(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk)
        if portfolio.user != request.user:
            raise PermissionDenied("You do not own this portfolio.")

        seo, _ = PortfolioSEO.objects.get_or_create(portfolio=portfolio)
        form = PortfolioSEOForm(instance=seo)

        ctx = _base_context(request)
        ctx.update({
            "portfolio": portfolio,
            "seo": seo,
            "form": form,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Portfolios", "url": reverse("portfolio:list")},
                {"title": f"SEO Settings: {portfolio.name}", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk)
        if portfolio.user != request.user:
            raise PermissionDenied("You do not own this portfolio.")

        seo, _ = PortfolioSEO.objects.get_or_create(portfolio=portfolio)
        form = PortfolioSEOForm(request.POST, request.FILES, instance=seo)
        
        if form.is_valid():
            form.save()
            
            # Recalculate SEO Score
            calculate_seo_score(portfolio)
            
            messages.success(request, f"SEO Meta Config for '{portfolio.name}' updated successfully.")
            return redirect("analytics:seo_config", pk=portfolio.pk)

        ctx = _base_context(request)
        ctx.update({
            "portfolio": portfolio,
            "seo": seo,
            "form": form,
        })
        return render(request, self.template_name, ctx)


class PortfolioPerformanceView(LoginRequiredMixin, View):
    """
    Speed Diagnostics dashboard calculating file sizes and suggestions.
    """
    template_name = "analytics/performance.html"

    def get(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk)
        if portfolio.user != request.user:
            raise PermissionDenied("You do not own this portfolio.")

        # Trigger dynamic performance evaluation
        perf_data = analyze_performance(portfolio)

        ctx = _base_context(request)
        ctx.update({
            "portfolio": portfolio,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Portfolios", "url": reverse("portfolio:list")},
                {"title": f"Performance Diagnostic: {portfolio.name}", "url": "#"},
            ],
        })
        ctx.update(perf_data)
        return render(request, self.template_name, ctx)


class SitemapView(View):
    """
    Dynamic sitemap.xml generator listing all public portfolios.
    """
    def get(self, request):
        portfolios = Portfolio.objects.filter(status=Portfolio.Status.PUBLISHED).select_related("user")
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]
        
        for p in portfolios:
            url = request.build_absolute_uri(reverse("portfolio:preview", kwargs={"pk": p.pk}))
            xml_lines.append("  <url>")
            xml_lines.append(f"    <loc>{url}</loc>")
            xml_lines.append(f"    <lastmod>{p.updated_at.strftime('%Y-%m-%d')}</lastmod>")
            xml_lines.append("    <changefreq>weekly</changefreq>")
            xml_lines.append("    <priority>0.8</priority>")
            xml_lines.append("  </url>")
            
        xml_lines.append("</urlset>")
        return HttpResponse("\n".join(xml_lines), content_type="application/xml")


class RobotsTxtView(View):
    """
    Dynamic robots.txt builder routing crawlers and pointing indexes.
    """
    def get(self, request):
        sitemap_url = request.build_absolute_uri(reverse("analytics:sitemap"))
        content = f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /billing/\n\nSitemap: {sitemap_url}"
        return HttpResponse(content, content_type="text/plain")
