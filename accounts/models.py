from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "SUPER_ADMIN")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model for AI Portfolio Builder.

    Extends Django's AbstractUser to support the three platform roles
    defined in the SRS: Super Admin, Admin, and User.
    """
    objects = UserManager()

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Admin"
        PREMIUM_USER = "PREMIUM_USER", "Premium User"
        FREE_USER = "FREE_USER", "Free User"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FREE_USER,
        help_text="Determines dashboard access and permission scope.",
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    github_username = models.CharField(max_length=150, blank=True, default="")
    email_verified = models.BooleanField(default=False)

    # Legacy Compatibility Fields for Existing PostgreSQL Schema
    bio = models.TextField(blank=True, default="")
    company = models.CharField(max_length=100, blank=True, default="")
    location = models.CharField(max_length=100, blank=True, default="")
    website = models.CharField(max_length=200, blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")
    timezone = models.CharField(max_length=50, blank=True, default="UTC")
    
    # Theme Preference for future synchronization
    class ThemePref(models.TextChoices):
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"
        SYSTEM = "system", "System"
        
    theme_preference = models.CharField(
        max_length=10, 
        choices=ThemePref.choices, 
        default=ThemePref.SYSTEM
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email or self.username

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_platform_admin(self):
        return self.role in (self.Role.SUPER_ADMIN, self.Role.ADMIN)

    @property
    def is_premium(self):
        return self.role == self.Role.PREMIUM_USER

    def upgrade_to_premium(self):
        """Called by the payments module (future phase) on successful subscription."""
        if self.role == self.Role.FREE_USER:
            self.role = self.Role.PREMIUM_USER
            self.save(update_fields=["role", "updated_at"])

    def downgrade_to_free(self):
        """Called by the payments module (future phase) on cancellation/expiry."""
        if self.role == self.Role.PREMIUM_USER:
            self.role = self.Role.FREE_USER
            self.save(update_fields=["role", "updated_at"])
