"""
Module 13: Custom Domains — services/domain_service.py

High-level domain management service.
Orchestrates verification flows, status transitions, SSL checks,
and primary domain switching.
"""
import logging
from typing import Tuple

from django.db import transaction
from django.utils import timezone

from domains.models import CustomDomain, DomainVerificationLog
from domains.services.dns_service import (
    lookup_txt_record,
    lookup_cname_record,
    check_ssl_status,
    validate_domain_name,
)

logger = logging.getLogger(__name__)


def create_custom_domain(
    user,
    portfolio,
    domain_name: str,
    subdomain: str = "",
    provider: str = "custom",
    verification_method: str = "txt",
) -> Tuple["CustomDomain", bool, str]:
    """
    Creates a new CustomDomain record for the given user/portfolio.

    Validates the domain format, generates a verification token,
    and returns the created instance.

    Returns:
        (domain: CustomDomain, created: bool, error: str)
        On failure, domain is None and error contains the reason.
    """
    # Validate domain format
    full = f"{subdomain}.{domain_name}" if subdomain else domain_name
    valid, error = validate_domain_name(full)
    if not valid:
        return None, False, error

    # Prevent duplicate domain registrations across the platform
    if CustomDomain.objects.filter(domain_name=domain_name, subdomain=subdomain).exclude(
        status=CustomDomain.Status.FAILED
    ).exists():
        return None, False, f"Domain '{full}' is already registered on this platform."

    with transaction.atomic():
        domain = CustomDomain.objects.create(
            user=user,
            portfolio=portfolio,
            domain_name=domain_name.lower().strip(),
            subdomain=subdomain.lower().strip(),
            provider=provider,
            verification_method=verification_method,
            status=CustomDomain.Status.PENDING,
        )
        domain.generate_verification_token()

    logger.info(
        "CustomDomain created: pk=%d domain=%s user=%s",
        domain.pk,
        domain.full_domain,
        user.username,
    )
    return domain, True, ""


def run_verification(domain: "CustomDomain") -> Tuple[bool, str]:
    """
    Executes a DNS verification check for the given domain.

    Updates domain status and logs the attempt to DomainVerificationLog.

    Returns:
        (success: bool, detail: str)
    """
    domain.status = CustomDomain.Status.VERIFYING
    domain.last_checked = timezone.now()
    domain.save(update_fields=["status", "last_checked"])

    method = domain.verification_method

    if method == CustomDomain.VerificationMethod.TXT:
        success, detail = lookup_txt_record(domain.full_domain, domain.verification_token)
    elif method == CustomDomain.VerificationMethod.CNAME:
        # CNAME should point to platform domain
        platform_target = "platform.aiportfoliobuilder.com"
        success, detail = lookup_cname_record(domain.full_domain, platform_target)
    else:
        success, detail = False, f"Unknown verification method: {method}"

    # Log the attempt
    DomainVerificationLog.objects.create(
        domain=domain,
        success=success,
        method=method,
        detail=detail,
    )

    if success:
        domain.mark_verified()
        # Trigger SSL check immediately after DNS verification
        _update_ssl_status(domain)
        logger.info("Domain verified: %s", domain.full_domain)
    else:
        domain.mark_failed()
        logger.warning("Domain verification failed: %s — %s", domain.full_domain, detail)

    return success, detail


def _update_ssl_status(domain: "CustomDomain") -> None:
    """Internal helper: refreshes SSL status after verification."""
    ssl_status, detail = check_ssl_status(domain.full_domain)
    domain.ssl_status = ssl_status
    if ssl_status == CustomDomain.SSLStatus.ISSUED:
        domain.ssl_enabled = True
    domain.save(update_fields=["ssl_status", "ssl_enabled"])


def refresh_ssl_status(domain: "CustomDomain") -> Tuple[str, str]:
    """
    Refreshes and persists the SSL certificate status for an active domain.

    Returns:
        (ssl_status: str, detail: str)
    """
    if domain.status != CustomDomain.Status.ACTIVE:
        return domain.ssl_status, "Domain must be active before SSL can be checked."

    ssl_status, detail = check_ssl_status(domain.full_domain)
    domain.ssl_status = ssl_status
    domain.ssl_enabled = ssl_status == CustomDomain.SSLStatus.ISSUED
    domain.save(update_fields=["ssl_status", "ssl_enabled"])
    return ssl_status, detail


def delete_domain(domain: "CustomDomain") -> None:
    """
    Deletes a custom domain record and clears its primary flag if set.
    If this was the primary domain, the oldest remaining active domain
    is promoted to primary automatically.
    """
    portfolio = domain.portfolio
    was_primary = domain.is_primary
    domain.delete()
    logger.info("CustomDomain deleted: %s", domain.full_domain)

    if was_primary:
        # Auto-promote next active domain as primary
        next_domain = (
            CustomDomain.objects.filter(portfolio=portfolio, status=CustomDomain.Status.ACTIVE)
            .order_by("created_at")
            .first()
        )
        if next_domain:
            next_domain.set_primary()


def get_portfolio_primary_url(portfolio) -> str:
    """
    Returns the best available public URL for a portfolio using the priority chain:
    1. Primary active custom domain (with SSL if available)
    2. GitHub Pages URL (from GitHubRepoConfig)
    3. Platform preview URL

    Args:
        portfolio: Portfolio instance

    Returns:
        str: Public-facing URL for the portfolio.
    """
    from django.urls import reverse

    # 1. Primary custom domain
    primary = (
        CustomDomain.objects.filter(
            portfolio=portfolio,
            is_primary=True,
            status=CustomDomain.Status.ACTIVE,
        )
        .first()
    )
    if primary:
        scheme = "https" if primary.ssl_enabled else "http"
        return f"{scheme}://{primary.full_domain}"

    # 2. GitHub Pages URL
    try:
        from github_integration.models import GitHubRepoConfig
        github_config = GitHubRepoConfig.objects.filter(portfolio=portfolio).first()
        if github_config and github_config.pages_url:
            return github_config.pages_url
    except Exception:
        pass

    # 3. Platform URL (fallback)
    return reverse("portfolio:preview", kwargs={"pk": portfolio.pk})


def get_domain_limit(user) -> int:
    """
    Returns the maximum custom domain count allowed for the user's plan.

    - Free users: 0
    - Premium users: 5
    - Super Admin / Enterprise: unlimited (999)
    """
    from payments.permissions import get_user_plan_benefits

    if user.role in ["SUPER_ADMIN", "ADMIN"]:
        return 999

    plan = get_user_plan_benefits(user)
    if plan and plan.team_access:
        return 999  # Enterprise
    if plan and plan.premium_themes_enabled:
        return 5  # Premium
    return 0  # Free
