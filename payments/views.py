from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta

from dashboard.mixins import AdminRequiredMixin
from dashboard.navigation import get_sidebar_navigation
from .models import SubscriptionPlan, UserSubscription, UsageMetrics, PaymentTransaction
from .services.mock_provider import MockPaymentProvider


def _base_context(request, active_tab="billing"):
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "active_tab": active_tab,
    }


class BillingDashboardView(LoginRequiredMixin, View):
    """
    User-facing billing portal displaying active plan tier, limits usage,
    pricing upgrade options, and invoice logs.
    """
    template_name = "payments/billing.html"

    def get(self, request):
        user = request.user
        
        # Ensure user usage stats are updated
        metrics, _ = UsageMetrics.objects.get_or_create(user=user)
        metrics.sync_metrics()

        subscription = getattr(user, "subscription", None)
        active_plan = subscription.plan if subscription else None
        
        # Calculate usage percentages for rendering progress bars
        portfolio_pct = 0
        ai_pct = 0
        github_pct = 0
        
        if active_plan:
            if active_plan.portfolio_limit > 0:
                portfolio_pct = min(round((metrics.portfolios_count / active_plan.portfolio_limit) * 100), 100)
            if active_plan.ai_usage_limit > 0:
                ai_pct = min(round((metrics.ai_uploads_count / active_plan.ai_usage_limit) * 100), 100)
            if active_plan.github_publish_limit > 0:
                github_pct = min(round((metrics.github_publishes_count / active_plan.github_publish_limit) * 100), 100)

        # Convert storage to Megabytes for display
        storage_mb = round(metrics.storage_used_bytes / (1024 * 1024), 2)

        ctx = _base_context(request)
        ctx.update({
            "subscription": subscription,
            "metrics": metrics,
            "active_plan": active_plan,
            "available_plans": SubscriptionPlan.objects.all().order_by("price"),
            "transactions": PaymentTransaction.objects.filter(user=user).order_by("-created_at"),
            "portfolio_pct": portfolio_pct,
            "ai_pct": ai_pct,
            "github_pct": github_pct,
            "storage_mb": storage_mb,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Billing & Subscriptions", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)


class CheckoutSessionView(LoginRequiredMixin, View):
    """
    Initiates payment provider checkout session flows.
    """
    def post(self, request):
        plan_slug = request.POST.get("plan_slug")
        plan = get_object_or_404(SubscriptionPlan, slug=plan_slug)

        # Basic guard: prevent buying Free plan
        if plan.slug == "free":
            messages.error(request, "Free plan cannot be checked out.")
            return redirect("payments:billing")

        provider = MockPaymentProvider()
        return_url = request.build_absolute_uri(reverse("payments:success"))
        
        try:
            checkout_url = provider.create_checkout_session(request.user, plan, return_url)
            return redirect(checkout_url)
        except Exception as e:
            messages.error(request, f"Failed to initiate checkout session: {str(e)}")
            return redirect("payments:billing")


class MockCheckoutView(LoginRequiredMixin, View):
    """
    Simulated checkout platform. Shows pricing and mock payment options.
    """
    template_name = "payments/checkout_mock.html"

    def get(self, request):
        session_id = request.GET.get("session_id")
        plan_slug = request.GET.get("plan_slug")
        
        transaction = get_object_or_404(PaymentTransaction, transaction_id=session_id, user=request.user)
        plan = get_object_or_404(SubscriptionPlan, slug=plan_slug)
        
        ctx = {
            "transaction": transaction,
            "plan": plan,
            "session_id": session_id,
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        session_id = request.POST.get("session_id")
        action = request.POST.get("action", "success")
        
        transaction = get_object_or_404(PaymentTransaction, transaction_id=session_id, user=request.user)
        plan = transaction.plan

        if action == "success":
            transaction.status = PaymentTransaction.Status.SUCCESS
            transaction.save()

            # Activate UserSubscription
            subscription, _ = UserSubscription.objects.get_or_create(user=request.user)
            subscription.plan = plan
            subscription.status = UserSubscription.Status.ACTIVE
            subscription.current_period_start = timezone.now()
            subscription.current_period_end = timezone.now() + timedelta(days=30)
            subscription.cancel_at_period_end = False
            subscription.save()

            # Align custom User Model role limits
            user = request.user
            if plan.slug == "premium":
                user.role = user.Role.PREMIUM_USER
            elif plan.slug == "enterprise":
                user.role = user.Role.PREMIUM_USER # fallback standard role
            user.save(update_fields=["role", "updated_at"])

            messages.success(request, f"Subscription to {plan.name} activated successfully!")
            return redirect("payments:success")
        else:
            transaction.status = PaymentTransaction.Status.FAILED
            transaction.save()
            messages.error(request, "Subscription payment transaction declined.")
            return redirect("payments:failure")


class PaymentSuccessView(LoginRequiredMixin, View):
    """Successful checkout landing."""
    def get(self, request):
        return render(request, "payments/success.html", _base_context(request))


class PaymentFailureView(LoginRequiredMixin, View):
    """Declined checkout landing."""
    def get(self, request):
        return render(request, "payments/failure.html", _base_context(request))


class CancelSubscriptionView(LoginRequiredMixin, View):
    """
    Updates the auto-renew schedule toggle to cancel at end of period.
    """
    def post(self, request):
        subscription = get_object_or_404(UserSubscription, user=request.user)
        if subscription.plan.slug == "free":
            messages.error(request, "Cannot cancel a Free subscription.")
            return redirect("payments:billing")

        subscription.cancel_at_period_end = True
        subscription.save()
        
        messages.success(request, "Subscription renewal successfully canceled. Benefits remain active until the end of your billing cycle.")
        return redirect("payments:billing")


class AdminBillingDashboardView(AdminRequiredMixin, View):
    """
    Aggregates central SaaS business summaries, total revenues,
    active user distributions, and transaction logs.
    """
    template_name = "payments/admin_billing.html"

    def get(self, request):
        # 1. Base counts
        total_subscribers = UserSubscription.objects.exclude(plan__slug="free").count()
        premium_count = UserSubscription.objects.filter(plan__slug="premium", status="active").count()
        enterprise_count = UserSubscription.objects.filter(plan__slug="enterprise", status="active").count()
        
        # 2. Cumulative revenues
        revenue_sum = PaymentTransaction.objects.filter(
            status=PaymentTransaction.Status.SUCCESS
        ).aggregate(total=Sum("amount"))["total"] or 0.00
        
        ctx = _base_context(request, "admin_billing")
        ctx.update({
            "total_subscribers": total_subscribers,
            "premium_count": premium_count,
            "enterprise_count": enterprise_count,
            "total_revenue": revenue_sum,
            "recent_transactions": PaymentTransaction.objects.all().order_by("-created_at")[:15],
            "breadcrumbs": [
                {"title": "Admin Console", "url": "#"},
                {"title": "Revenues & Subscriptions Dashboard", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)
