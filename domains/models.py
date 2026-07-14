"""
Module 13: Custom Domains — models.py

Implements CustomDomain model for mapping user-owned domain names
to published portfolio websites, with TXT/CNAME verification and SSL tracking.
"""
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone


class CustomDomain(models.Model):
    """
    Represents a user-owned custom domain or subdomain mapped to a portfolio.

    Supports TXT and CNAME verification flows, SSL status tracking,
    and a primary domain designation for URL resolution priority.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFYING = "verifying", "Verifying"
        ACTIVE = "active", "Active"
        FAILED = "failed", "Failed"

    class SSLStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ISSUED = "issued", "Issued"
        FAILED = "failed", "Failed"

    class VerificationMethod(models.TextChoices):
        TXT = "txt", "TXT Record"
        CNAME = "cname", "CNAME Record"

    class Provider(models.TextChoices):
        CUSTOM = "custom", "Custom / Other"
        NAMECHEAP = "namecheap", "Namecheap"
        GODADDY = "godaddy", "GoDaddy"
        CLOUDFLARE = "cloudflare", "Cloudflare"
        GOOGLE = "google", "Google Domains"
        AWS_ROUTE53 = "aws_route53", "AWS Route 53"

    # Ownership relations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="custom_domains",
    )
    portfolio = models.ForeignKey(
        "portfolio.Portfolio",
        on_delete=models.CASCADE,
        related_name="custom_domains",
    )

    # Domain identification
    domain_name = models.CharField(
        max_length=253,
        help_text="The root or www domain, e.g. myportfolio.com",
    )
    subdomain = models.CharField(
        max_length=63,
        blank=True,
        help_text="Optional subdomain prefix, e.g. 'www' or 'portfolio'",
    )
    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
        default=Provider.CUSTOM,
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    ssl_status = models.CharField(
        max_length=20,
        choices=SSLStatus.choices,
        default=SSLStatus.PENDING,
    )

    # Verification
    verification_token = models.CharField(
        max_length=64,
        blank=True,
        help_text="Unique token placed in DNS TXT record for ownership proof.",
    )
    verification_method = models.CharField(
        max_length=10,
        choices=VerificationMethod.choices,
        default=VerificationMethod.TXT,
    )
    dns_verified = models.BooleanField(default=False)
    ssl_enabled = models.BooleanField(default=False)

    # Priority flag
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary domain used in public portfolio URL resolution.",
        db_index=True,
    )

    # Audit
    last_checked = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]
        verbose_name = "Custom Domain"
        verbose_name_plural = "Custom Domains"

    def __str__(self) -> str:
        return f"{self.full_domain} → {self.portfolio.name} ({self.get_status_display()})"

    @property
    def full_domain(self) -> str:
        """Returns the fully-qualified domain name including optional subdomain."""
        if self.subdomain:
            return f"{self.subdomain}.{self.domain_name}"
        return self.domain_name

    def generate_verification_token(self) -> str:
        """Generates and saves a fresh cryptographically-secure 32-byte hex token."""
        self.verification_token = secrets.token_hex(32)
        self.save(update_fields=["verification_token"])
        return self.verification_token

    def mark_verified(self) -> None:
        """Transitions domain to ACTIVE status after DNS verification succeeds."""
        self.dns_verified = True
        self.status = self.Status.ACTIVE
        self.last_checked = timezone.now()
        self.save(update_fields=["dns_verified", "status", "last_checked"])

    def mark_failed(self) -> None:
        """Transitions domain to FAILED status after verification error."""
        self.dns_verified = False
        self.status = self.Status.FAILED
        self.last_checked = timezone.now()
        self.save(update_fields=["dns_verified", "status", "last_checked"])

    def set_primary(self) -> None:
        """
        Sets this domain as the primary domain for its portfolio.
        Clears the is_primary flag on all other domains belonging to the same portfolio.
        """
        CustomDomain.objects.filter(
            portfolio=self.portfolio,
            is_primary=True,
        ).exclude(pk=self.pk).update(is_primary=False)
        self.is_primary = True
        self.save(update_fields=["is_primary"])


class DomainVerificationLog(models.Model):
    """
    Audit trail of all verification check attempts for a custom domain.
    Stores the outcome, error details, and timestamp for each check.
    """
    domain = models.ForeignKey(
        CustomDomain,
        on_delete=models.CASCADE,
        related_name="verification_logs",
    )
    checked_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    method = models.CharField(max_length=10)
    detail = models.TextField(blank=True, help_text="DNS response or error detail.")

    class Meta:
        ordering = ["-checked_at"]

    def __str__(self) -> str:
        result = "✓" if self.success else "✗"
        return f"{result} {self.domain.full_domain} @ {self.checked_at:%Y-%m-%d %H:%M}"
