"""
subscriptions/admin.py — Jazzmin Admin Integration, Custom Badges, Audit Logging & Subscriptions Summary Dashboard (Phase 10.0 MVP)

Provides:
  - SubscriptionPlanAdmin: Plan configuration with collapsible fieldsets, badges, actions, & prefetch_related optimization.
  - PlanFeatureAdmin: Feature registry with auto slug prepopulate.
  - PlanFeatureAccessInline & Admin: Plan feature rules with select_related optimization.
  - UserSubscriptionAdmin: User subscriptions with color-coded status badges, actions, & select_related optimization.
  - FeatureUsageAdmin: Consumption tracking with remaining usage & usage percentage displays, reset actions, & select_related optimization.
  - Subscriptions Summary Admin Dashboard (admin:subscriptions_summary): Metric cards, Plan Breakdown widget, & Top Used Features widget.
"""

from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count

from subscriptions.models import (
    SubscriptionPlan,
    PlanFeature,
    PlanFeatureAccess,
    UserSubscription,
    FeatureUsage
)
from subscriptions.services import get_remaining_usage, get_usage_limit


def log_admin_action(request, obj, message):
    """Utility helper to log admin actions in Django's LogEntry table for audit trails."""
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=CHANGE,
        change_message=message
    )


class PlanFeatureAccessInline(admin.TabularInline):
    model = PlanFeatureAccess
    extra = 1
    autocomplete_fields = ["feature"]
    fields = ["feature", "enabled", "usage_limit", "unlimited_status"]
    readonly_fields = ["unlimited_status"]

    @admin.display(description="Unlimited?")
    def unlimited_status(self, obj):
        if not obj or obj.usage_limit is None:
            return format_html('<span style="color: #28a745; font-weight: bold;">Yes (Unlimited)</span>')
        return format_html('<span style="color: #6c757d;">No ({})</span>', obj.usage_limit)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "billing_cycle", "active_badge", "featured_badge", "display_order")
    list_filter = ("billing_cycle", "is_active", "is_featured")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("display_order", "price")
    inlines = [PlanFeatureAccessInline]
    actions = ["activate_selected", "deactivate_selected", "mark_featured", "remove_featured"]

    fieldsets = (
        ("Plan General Info", {
            "fields": ("name", "slug", "description", "price", "billing_cycle")
        }),
        ("Visibility & Status", {
            "classes": ("collapse",),
            "fields": ("is_active", "is_featured", "display_order")
        }),
        ("System Metadata", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at")
        }),
    )
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("feature_accesses__feature")

    @admin.display(description="Active", boolean=True)
    def active_badge(self, obj):
        return obj.is_active

    @admin.display(description="Featured", boolean=True)
    def featured_badge(self, obj):
        return obj.is_featured

    @admin.action(description="Activate selected plans")
    def activate_selected(self, request, queryset):
        updated = queryset.update(is_active=True)
        for obj in queryset:
            log_admin_action(request, obj, "Activated SubscriptionPlan")
        self.message_user(request, f"Activated {updated} plan(s).", messages.SUCCESS)

    @admin.action(description="Deactivate selected plans")
    def deactivate_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        for obj in queryset:
            log_admin_action(request, obj, "Deactivated SubscriptionPlan")
        self.message_user(request, f"Deactivated {updated} plan(s).", messages.WARNING)

    @admin.action(description="Mark as featured")
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        for obj in queryset:
            log_admin_action(request, obj, "Marked SubscriptionPlan as featured")
        self.message_user(request, f"Marked {updated} plan(s) as featured.", messages.SUCCESS)

    @admin.action(description="Remove featured tag")
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        for obj in queryset:
            log_admin_action(request, obj, "Removed featured status from SubscriptionPlan")
        self.message_user(request, f"Removed featured status from {updated} plan(s).", messages.INFO)


@admin.register(PlanFeature)
class PlanFeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("created_at",)


@admin.register(PlanFeatureAccess)
class PlanFeatureAccessAdmin(admin.ModelAdmin):
    list_display = ("plan", "feature", "enabled", "usage_limit_display")
    list_filter = ("enabled", "plan", "feature")
    search_fields = ("plan__name", "feature__name", "feature__slug")
    autocomplete_fields = ["plan", "feature"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("plan", "feature")

    @admin.display(description="Usage Limit")
    def usage_limit_display(self, obj):
        if obj.usage_limit is None:
            return format_html('<span style="color: #28a745; font-weight: bold;">Unlimited</span>')
        return obj.usage_limit


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status_badge", "start_date", "end_date")
    list_filter = ("status", "plan", "plan__billing_cycle")
    search_fields = ("user__username", "user__email", "plan__name")
    autocomplete_fields = ["user", "plan"]
    readonly_fields = ("created_at", "updated_at")
    actions = ["activate_subscriptions", "expire_subscriptions", "cancel_subscriptions", "assign_free_plan"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "plan")

    @admin.display(description="Status")
    def status_badge(self, obj):
        if obj.status == UserSubscription.Status.ACTIVE:
            return format_html('<span class="badge badge-success" style="background-color: #28a745; color: white; padding: 4px 8px; border-radius: 4px;">ACTIVE</span>')
        elif obj.status == UserSubscription.Status.EXPIRED:
            return format_html('<span class="badge badge-warning" style="background-color: #ffc107; color: black; padding: 4px 8px; border-radius: 4px;">EXPIRED</span>')
        else:
            return format_html('<span class="badge badge-danger" style="background-color: #dc3545; color: white; padding: 4px 8px; border-radius: 4px;">CANCELLED</span>')

    @admin.action(description="Activate selected subscriptions")
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(status=UserSubscription.Status.ACTIVE)
        for obj in queryset:
            log_admin_action(request, obj, "Activated UserSubscription")
        self.message_user(request, f"Activated {updated} subscription(s).", messages.SUCCESS)

    @admin.action(description="Expire selected subscriptions")
    def expire_subscriptions(self, request, queryset):
        updated = queryset.update(status=UserSubscription.Status.EXPIRED)
        for obj in queryset:
            log_admin_action(request, obj, "Expired UserSubscription")
        self.message_user(request, f"Expired {updated} subscription(s).", messages.WARNING)

    @admin.action(description="Cancel selected subscriptions")
    def cancel_subscriptions(self, request, queryset):
        updated = queryset.update(status=UserSubscription.Status.CANCELLED)
        for obj in queryset:
            log_admin_action(request, obj, "Cancelled UserSubscription")
        self.message_user(request, f"Cancelled {updated} subscription(s).", messages.ERROR)

    @admin.action(description="Assign Free Plan")
    def assign_free_plan(self, request, queryset):
        free_plan = SubscriptionPlan.objects.filter(slug="free").first()
        if not free_plan:
            self.message_user(request, "Free plan not found in database.", messages.ERROR)
            return
        updated = queryset.update(plan=free_plan, status=UserSubscription.Status.ACTIVE)
        for obj in queryset:
            log_admin_action(request, obj, f"Assigned Free plan to {obj.user}")
        self.message_user(request, f"Assigned Free plan to {updated} user subscription(s).", messages.SUCCESS)


@admin.register(FeatureUsage)
class FeatureUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "feature", "used_count", "remaining_display", "usage_percentage_display", "reset_type", "last_used")
    list_filter = ("reset_type", "feature", "subscription__status")
    search_fields = ("user__username", "user__email", "feature__name", "feature__slug")
    autocomplete_fields = ["user", "feature"]
    readonly_fields = ("used_count", "last_used", "remaining_display", "usage_percentage_display")
    actions = ["reset_usage_selected", "reset_selected_users", "reset_selected_feature", "reset_all_monthly_usage"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "feature", "subscription", "subscription__plan")

    @admin.display(description="Remaining")
    def remaining_display(self, obj):
        rem = get_remaining_usage(obj.user, obj.feature.slug)
        if rem is None:
            return format_html('<span style="color: #28a745; font-weight: bold;">Unlimited</span>')
        elif rem == 0:
            return format_html('<span style="color: #dc3545; font-weight: bold;">0 (Depleted)</span>')
        return rem

    @admin.display(description="Usage %")
    def usage_percentage_display(self, obj):
        limit = get_usage_limit(obj.user, obj.feature.slug)
        if limit is None:
            return format_html('<span style="color: #28a745;">Unlimited</span>')
        if limit == 0:
            return format_html('<span style="color: #dc3545;">Disabled</span>')
        pct = min(100, int((obj.used_count / limit) * 100))
        color = "#dc3545" if pct >= 100 else ("#ffc107" if pct >= 80 else "#28a745")
        return format_html('<span style="color: {}; font-weight: bold;">{} / {} ({}%)</span>', color, obj.used_count, limit, pct)

    @admin.action(description="Reset usage for selected records")
    def reset_usage_selected(self, request, queryset):
        updated = queryset.update(used_count=0)
        for obj in queryset:
            log_admin_action(request, obj, "Reset feature usage count to 0")
        self.message_user(request, f"Reset usage for {updated} record(s).", messages.SUCCESS)

    @admin.action(description="Reset usage for selected users")
    def reset_selected_users(self, request, queryset):
        user_ids = queryset.values_list("user_id", flat=True)
        updated = FeatureUsage.objects.filter(user_id__in=user_ids).update(used_count=0)
        self.message_user(request, f"Reset usage for all features of selected users ({updated} records).", messages.SUCCESS)

    @admin.action(description="Reset usage for selected feature")
    def reset_selected_feature(self, request, queryset):
        feature_ids = queryset.values_list("feature_id", flat=True)
        updated = FeatureUsage.objects.filter(feature_id__in=feature_ids).update(used_count=0)
        self.message_user(request, f"Reset usage for all users of selected feature(s) ({updated} records).", messages.SUCCESS)

    @admin.action(description="Reset all monthly usage records")
    def reset_all_monthly_usage(self, request, queryset):
        updated = FeatureUsage.objects.filter(reset_type=FeatureUsage.ResetType.MONTHLY).update(used_count=0)
        self.message_user(request, f"Reset all MONTHLY usage records ({updated} total records).", messages.SUCCESS)


# ---------------------------------------------------------------------------
# Subscriptions Summary Dashboard View (admin:subscriptions_summary)
# ---------------------------------------------------------------------------
@staff_member_required
def subscriptions_summary_view(request):
    """
    Staff-protected custom Jazzmin admin view rendering Subscriptions Summary metrics and widgets.
    """
    total_plans = SubscriptionPlan.objects.count()
    total_features = PlanFeature.objects.count()

    active_subscribers = UserSubscription.objects.filter(status=UserSubscription.Status.ACTIVE).count()
    expired_subscribers = UserSubscription.objects.filter(status=UserSubscription.Status.EXPIRED).count()
    cancelled_subscribers = UserSubscription.objects.filter(status=UserSubscription.Status.CANCELLED).count()

    # Widget 1: Plan Distribution Breakdown
    plan_breakdown = []
    for plan in SubscriptionPlan.objects.all():
        sub_count = UserSubscription.objects.filter(plan=plan, status=UserSubscription.Status.ACTIVE).count()
        plan_breakdown.append({
            "name": plan.name,
            "billing_cycle": plan.get_billing_cycle_display(),
            "price": plan.price,
            "count": sub_count
        })

    # Widget 2: Most Used Features
    top_used_features = list(
        FeatureUsage.objects.values("feature__name", "feature__slug")
        .annotate(total_uses=Sum("used_count"))
        .order_by("-total_uses")[:10]
    )

    context = {
        **admin.site.each_context(request),
        "title": "Subscriptions Summary Dashboard",
        "total_plans": total_plans,
        "total_features": total_features,
        "active_subscribers": active_subscribers,
        "expired_subscribers": expired_subscribers,
        "cancelled_subscribers": cancelled_subscribers,
        "plan_breakdown": plan_breakdown,
        "top_used_features": top_used_features,
    }
    return render(request, "admin/subscriptions/summary.html", context)


# Register custom dashboard URL in Django Admin Site
def get_admin_urls(urls):
    def get_urls():
        custom_urls = [
            path("subscriptions/summary/", subscriptions_summary_view, name="subscriptions_summary"),
        ]
        return custom_urls + urls()
    return get_urls

admin.site.get_urls = get_admin_urls(admin.site.get_urls)
