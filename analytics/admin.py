from django.contrib import admin
from .models import PortfolioMetric, PortfolioVisit, PortfolioSEO


@admin.register(PortfolioMetric)
class PortfolioMetricAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "total_visits", "unique_visitors", "seo_score", "performance_score", "updated_at")
    search_fields = ("portfolio__name", "portfolio__user__username")
    list_filter = ("seo_score", "performance_score")


@admin.register(PortfolioVisit)
class PortfolioVisitAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "timestamp", "session_id", "device_type", "browser", "country", "referrer", "path")
    search_fields = ("portfolio__name", "session_id", "ip_address", "country", "referrer")
    list_filter = ("device_type", "browser", "country", "timestamp")
    date_hierarchy = "timestamp"


@admin.register(PortfolioSEO)
class PortfolioSEOAdmin(admin.ModelAdmin):
    list_display = ("portfolio", "seo_title", "keywords", "canonical_url")
    search_fields = ("portfolio__name", "seo_title", "meta_description")
