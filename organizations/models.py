"""
Module 14: Team Collaboration & Organization Workspace — models.py

Defines models for Organizations, Organization Memberships,
Member Invitations, and Team Activity Logs.
"""
import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone


class Organization(models.Model):
    """
    Represents a team workspace for collaborative portfolio management.
    """
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_organizations",
    )
    logo = models.ImageField(upload_to="organizations/logos/", null=True, blank=True)
    description = models.TextField(blank=True)
    plan = models.ForeignKey(
        "payments.SubscriptionPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class OrganizationMember(models.Model):
    """
    Represents membership/role of a user inside an organization.
    """
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        EDITOR = "EDITOR", "Editor"
        VIEWER = "VIEWER", "Viewer"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invites_members",
    )
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "user")
        ordering = ["joined_at"]

    def __str__(self) -> str:
        return f"{self.user.username} ({self.get_role_display()}) in {self.organization.name}"


class Invitation(models.Model):
    """
    Represents an invitation sent to a user by email to join an organization.
    """
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    role = models.CharField(
        max_length=20,
        choices=OrganizationMember.Role.choices,
        default=OrganizationMember.Role.VIEWER,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invite for {self.email} to {self.organization.name} ({self.get_status_display()})"

    def generate_token(self) -> str:
        """Generates and sets a fresh cryptographically secure invite token."""
        self.token = secrets.token_urlsafe(32)
        return self.token

    @property
    def is_valid(self) -> bool:
        """Checks if the invitation is pending and has not expired."""
        return self.status == self.Status.PENDING and self.expires_at > timezone.now()


class ActivityLog(models.Model):
    """
    Audit log record tracking collaboration events inside an organization.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="organization_activities",
    )
    action = models.CharField(max_length=255)
    object_type = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        username = self.user.username if self.user else "System"
        return f"{username} {self.action} on {self.object_type} in {self.organization.name}"
