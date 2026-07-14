"""
Module 13: Custom Domains — services/dns_service.py

DNS verification service layer.
Provides TXT and CNAME lookup utilities designed for easy swap to real DNS
providers (dnspython, Cloudflare API, etc.) in production.

In development mode (DOMAIN_DNS_MOCK=True) all lookups return success to allow
full UI/flow testing without an actual DNS resolver.
"""
import logging
import socket
from typing import Tuple

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Toggle via settings or .env: DOMAIN_DNS_MOCK=True (default in dev)
MOCK_DNS = getattr(settings, "DOMAIN_DNS_MOCK", True)


def _mock_txt_lookup(domain: str, token: str) -> Tuple[bool, str]:
    """Simulated TXT lookup for development environments."""
    logger.info("[MOCK DNS] TXT lookup for %s — token %s → success", domain, token[:8])
    return True, f"Mock TXT record found: aiportfolio-verify={token}"


def _mock_cname_lookup(domain: str, target: str) -> Tuple[bool, str]:
    """Simulated CNAME lookup for development environments."""
    logger.info("[MOCK DNS] CNAME lookup for %s → %s — success", domain, target)
    return True, f"Mock CNAME: {domain} → {target}"


def lookup_txt_record(domain: str, token: str) -> Tuple[bool, str]:
    """
    Checks whether the expected TXT verification record exists for the given domain.

    Args:
        domain: The fully-qualified domain name to query.
        token:  The verification token expected in the TXT value.

    Returns:
        (success: bool, detail: str) — success=True when the token is found.
    """
    if MOCK_DNS:
        return _mock_txt_lookup(domain, token)

    # Real DNS lookup via socket / dnspython (production integration point)
    try:
        # Try to resolve - in production replace with dnspython dns.resolver.resolve()
        # For now, fall back to socket for basic hostname validation
        socket.getaddrinfo(domain, None)
        return False, "TXT record not found — real DNS resolver not configured."
    except socket.gaierror as exc:
        detail = f"DNS resolution error for {domain}: {exc}"
        logger.warning(detail)
        return False, detail
    except Exception as exc:
        detail = f"Unexpected DNS error: {exc}"
        logger.error(detail)
        return False, detail


def lookup_cname_record(domain: str, expected_target: str) -> Tuple[bool, str]:
    """
    Checks whether the domain has a CNAME pointing to the expected target.

    Args:
        domain:          The CNAME source domain to query.
        expected_target: The CNAME destination value to match.

    Returns:
        (success: bool, detail: str)
    """
    if MOCK_DNS:
        return _mock_cname_lookup(domain, expected_target)

    try:
        socket.getaddrinfo(domain, None)
        return False, "CNAME validation requires dnspython — configure DNS resolver."
    except socket.gaierror as exc:
        detail = f"DNS resolution error for {domain}: {exc}"
        logger.warning(detail)
        return False, detail
    except Exception as exc:
        detail = f"Unexpected DNS error: {exc}"
        logger.error(detail)
        return False, detail


def validate_domain_name(domain: str) -> Tuple[bool, str]:
    """
    Validates that a domain string is structurally well-formed.

    Rules:
    - Must contain at least one dot
    - Each label must be 1–63 characters
    - Only letters, digits, and hyphens allowed in labels
    - Cannot start or end with a hyphen
    - Total length ≤ 253 characters

    Returns:
        (valid: bool, error_message: str)
    """
    domain = domain.strip().lower()
    if len(domain) > 253:
        return False, "Domain name exceeds 253 characters."
    if "." not in domain:
        return False, "Domain must contain at least one dot (e.g. example.com)."

    labels = domain.split(".")
    for label in labels:
        if not label:
            return False, "Domain contains empty label (double-dot or leading/trailing dot)."
        if len(label) > 63:
            return False, f"Label '{label}' exceeds 63 characters."
        if not all(c.isalnum() or c == "-" for c in label):
            return False, f"Label '{label}' contains invalid characters."
        if label.startswith("-") or label.endswith("-"):
            return False, f"Label '{label}' cannot start or end with a hyphen."

    return True, ""


def check_ssl_status(domain: str) -> Tuple[str, str]:
    """
    Returns the SSL certificate status for the domain.

    In development mock mode always returns 'issued'.
    Production integration point for Let's Encrypt / Certbot / acme.sh.

    Returns:
        (ssl_status: str, detail: str) — ssl_status is one of 'pending'/'issued'/'failed'
    """
    if MOCK_DNS:
        logger.info("[MOCK SSL] SSL check for %s → issued", domain)
        return "issued", f"Mock SSL certificate issued for {domain}"

    # Production: integrate with certbot or Let's Encrypt ACME client here
    return "pending", "SSL automation not configured — manual certificate required."
