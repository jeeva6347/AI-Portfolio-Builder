from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, UsageMetrics, PaymentTransaction


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "price", "portfolio_limit", "premium_themes_enabled", "ai_usage_limit", "github_publish_limit")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "current_period_start", "current_period_end", "cancel_at_period_end")
    list_filter = ("plan", "status", "cancel_at_period_end")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)


@admin.register(UsageMetrics)
class UsageMetricsAdmin(admin.ModelAdmin):
    list_display = ("user", "portfolios_count", "ai_uploads_count", "github_publishes_count", "storage_used_bytes", "updated_at")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("portfolios_count", "ai_uploads_count", "github_publishes_count", "storage_used_bytes")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "user", "plan", "amount", "currency", "status", "created_at")
    list_filter = ("status", "plan", "currency")
    search_fields = ("transaction_id", "user__username", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
