from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for AI Portfolio Builder.

    Extends Django's AbstractUser to support the three platform roles
    defined in the SRS: Super Admin, Admin, and User.
    """

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
    github_username = models.CharField(max_length=150, blank=True)
    email_verified = models.BooleanField(default=False)
    
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
