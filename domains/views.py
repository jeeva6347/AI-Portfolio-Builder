"""
Module 13: Custom Domains — views.py

Class-Based Views for domain management dashboard:
- DomainListView       — list all user domains
- DomainAddView        — add a new domain for a portfolio
- DomainDeleteView     — delete a domain
- DomainVerifyView     — trigger DNS verification check
- DomainSetPrimaryView — mark a domain as primary
- DomainInstructionsView — show DNS setup instructions

All views require login. Domain add/verify are gated behind the Premium plan.
"""
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponseForbidden
from django.urls import reverse

from dashboard.navigation import get_sidebar_navigation
from portfolio.models import Portfolio

from .models import CustomDomain
from .forms import CustomDomainForm
from .services.domain_service import (
    create_custom_domain,
    run_verification,
    delete_domain,
    get_domain_limit,
    refresh_ssl_status,
)

logger = logging.getLogger(__name__)


def _base_context(request, active_tab: str = "domains") -> dict:
    """Shared context injected into every domains view."""
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "active_tab": active_tab,
    }


# ── DOMAIN LIST ───────────────────────────────────────────────────────────────

class DomainListView(LoginRequiredMixin, View):
    """
    Lists all custom domains registered by the authenticated user,
    grouped by portfolio.
    """
    template_name = "domains/list.html"

    def get(self, request):
        domains = (
            CustomDomain.objects
            .filter(user=request.user)
            .select_related("portfolio", "portfolio__selected_theme")
            .order_by("portfolio__name", "-is_primary", "-created_at")
        )
        portfolios = (
            Portfolio.objects
            .filter(user=request.user)
            .select_related("selected_theme")
        )
        domain_limit = get_domain_limit(request.user)
        used = domains.count()

        ctx = _base_context(request)
        ctx.update({
            "domains": domains,
            "portfolios": portfolios,
            "domain_limit": domain_limit,
            "domains_used": used,
            "can_add_domain": used < domain_limit,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Custom Domains", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)


# ── DOMAIN ADD ────────────────────────────────────────────────────────────────

class DomainAddView(LoginRequiredMixin, View):
    """
    Renders a form for adding a new custom domain and processes its submission.
    Gated: Free users are redirected to billing.
    """
    template_name = "domains/add.html"

    def _check_limit(self, request) -> bool:
        """Returns True if the user is within their domain quota."""
        limit = get_domain_limit(request.user)
        if limit == 0:
            messages.warning(
                request,
                "Custom Domains are a Premium feature. Please upgrade your plan to add a custom domain.",
            )
            return False
        used = CustomDomain.objects.filter(user=request.user).exclude(
            status=CustomDomain.Status.FAILED
        ).count()
        if used >= limit:
            messages.warning(
                request,
                f"You have reached your limit of {limit} custom domain(s). Upgrade your plan for more.",
            )
            return False
        return True

    def get(self, request):
        if not self._check_limit(request):
            return redirect("payments:billing")

        portfolios = Portfolio.objects.filter(user=request.user).order_by("name")
        form = CustomDomainForm()
        ctx = _base_context(request)
        ctx.update({
            "form": form,
            "portfolios": portfolios,
            "domain_limit": get_domain_limit(request.user),
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Custom Domains", "url": reverse("domains:list")},
                {"title": "Add Domain", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)

    def post(self, request):
        if not self._check_limit(request):
            return redirect("payments:billing")

        form = CustomDomainForm(request.POST)
        portfolio_pk = request.POST.get("portfolio_pk")
        portfolio = get_object_or_404(Portfolio, pk=portfolio_pk, user=request.user)

        if form.is_valid():
            domain_name = form.cleaned_data["domain_name"]
            subdomain = form.cleaned_data["subdomain"]
            provider = form.cleaned_data["provider"]
            method = form.cleaned_data["verification_method"]

            domain, created, error = create_custom_domain(
                user=request.user,
                portfolio=portfolio,
                domain_name=domain_name,
                subdomain=subdomain,
                provider=provider,
                verification_method=method,
            )

            if not created:
                messages.error(request, f"Could not add domain: {error}")
            else:
                messages.success(
                    request,
                    f"Domain '{domain.full_domain}' added. Complete the DNS setup below to verify ownership.",
                )
                return redirect("domains:instructions", pk=domain.pk)

        portfolios = Portfolio.objects.filter(user=request.user).order_by("name")
        ctx = _base_context(request)
        ctx.update({
            "form": form,
            "portfolios": portfolios,
            "selected_portfolio": portfolio,
            "domain_limit": get_domain_limit(request.user),
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Custom Domains", "url": reverse("domains:list")},
                {"title": "Add Domain", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)


# ── DNS INSTRUCTIONS ──────────────────────────────────────────────────────────

class DomainInstructionsView(LoginRequiredMixin, View):
    """
    Displays step-by-step DNS configuration instructions for the domain,
    including the verification token / CNAME record to set.
    """
    template_name = "domains/instructions.html"

    def get(self, request, pk: int):
        domain = get_object_or_404(CustomDomain, pk=pk, user=request.user)
        ctx = _base_context(request)
        ctx.update({
            "domain": domain,
            "txt_record_name": f"_aiportfolio-verify.{domain.domain_name}",
            "txt_record_value": f"aiportfolio-verify={domain.verification_token}",
            "cname_record_name": domain.full_domain,
            "cname_record_value": "platform.aiportfoliobuilder.com",
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Custom Domains", "url": reverse("domains:list")},
                {"title": f"Setup: {domain.full_domain}", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)


# ── DOMAIN VERIFY ─────────────────────────────────────────────────────────────

class DomainVerifyView(LoginRequiredMixin, View):
    """
    Triggers a DNS verification check for the domain and redirects back
    with a success or failure message.
    """
    def post(self, request, pk: int):
        domain = get_object_or_404(CustomDomain, pk=pk, user=request.user)
        success, detail = run_verification(domain)

        if success:
            messages.success(
                request,
                f"✅ Domain '{domain.full_domain}' verified successfully! SSL is being provisioned.",
            )
        else:
            messages.error(
                request,
                f"❌ Verification failed for '{domain.full_domain}'. {detail} — Check your DNS settings and try again.",
            )

        return redirect("domains:instructions", pk=domain.pk)


# ── SET PRIMARY ───────────────────────────────────────────────────────────────

class DomainSetPrimaryView(LoginRequiredMixin, View):
    """
    Marks a verified domain as the primary domain for its portfolio.
    Only ACTIVE domains can be set as primary.
    """
    def post(self, request, pk: int):
        domain = get_object_or_404(CustomDomain, pk=pk, user=request.user)
        if domain.status != CustomDomain.Status.ACTIVE:
            messages.error(request, "Only verified active domains can be set as primary.")
        else:
            domain.set_primary()
            messages.success(
                request,
                f"'{domain.full_domain}' is now the primary domain for '{domain.portfolio.name}'.",
            )
        return redirect("domains:list")


# ── DOMAIN DELETE ─────────────────────────────────────────────────────────────

class DomainDeleteView(LoginRequiredMixin, View):
    """
    Deletes a custom domain after ownership confirmation.
    Automatically promotes another active domain to primary if the deleted one was primary.
    """
    def post(self, request, pk: int):
        domain = get_object_or_404(CustomDomain, pk=pk, user=request.user)
        full_domain = domain.full_domain
        delete_domain(domain)
        messages.success(request, f"Domain '{full_domain}' has been removed.")
        return redirect("domains:list")


# ── SSL REFRESH ───────────────────────────────────────────────────────────────

class DomainSSLRefreshView(LoginRequiredMixin, View):
    """
    Triggers an SSL status refresh for an active domain.
    """
    def post(self, request, pk: int):
        domain = get_object_or_404(CustomDomain, pk=pk, user=request.user)
        ssl_status, detail = refresh_ssl_status(domain)
        if ssl_status == "issued":
            messages.success(request, f"SSL certificate for '{domain.full_domain}' is active.")
        else:
            messages.warning(request, f"SSL status for '{domain.full_domain}': {detail}")
        return redirect("domains:list")
