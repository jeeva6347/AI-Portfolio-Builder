from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "premium_badge",
        "email_verified",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "email_verified", "is_active")
    search_fields = ("username", "email", "github_username")
    ordering = ("-created_at",)

    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Platform Info",
            {
                "fields": (
                    "role",
                    "avatar",
                    "github_username",
                    "email_verified",
                )
            },
        ),
    )

    @admin.display(description="Premium", boolean=True)
    def premium_badge(self, obj):
        return obj.is_premium
