from django.contrib import admin
from django.utils.html import format_html
from .models import Theme, ThemeCategory, ThemeAsset


@admin.register(ThemeCategory)
class ThemeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "theme_count", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def theme_count(self, obj):
        return obj.themes.count()
    theme_count.short_description = "Themes"


class ThemeAssetInline(admin.TabularInline):
    model = ThemeAsset
    extra = 0
    readonly_fields = ("asset_type", "file_path", "file_name", "file_size", "mime_type")
    can_delete = False


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "status_badge", "is_premium", "price", "downloads", "uploaded_by", "created_at")
    list_filter = ("status", "is_premium", "category")
    search_fields = ("name", "tags", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("downloads", "created_at", "updated_at", "extracted_path", "file_count_display", "total_size_display")
    inlines = [ThemeAssetInline]
    fieldsets = (
        ("Identity", {"fields": ("name", "slug", "description", "category", "tags", "version")}),
        ("Pricing", {"fields": ("is_premium", "price")}),
        ("Status", {"fields": ("status", "rejection_reason", "uploaded_by")}),
        ("Files", {"fields": ("zip_file", "thumbnail", "extracted_path", "file_count_display", "total_size_display")}),
        ("Stats", {"fields": ("downloads", "created_at", "updated_at")}),
    )

    def status_badge(self, obj):
        colors = {
            "draft": "#6b7280",
            "pending": "#f59e0b",
            "approved": "#10b981",
            "rejected": "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:9999px;font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def file_count_display(self, obj):
        return obj.file_count
    file_count_display.short_description = "File Count"

    def total_size_display(self, obj):
        size = obj.total_size
        if size > 1_048_576:
            return f"{size / 1_048_576:.1f} MB"
        elif size > 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} bytes"
    total_size_display.short_description = "Total Size"


@admin.register(ThemeAsset)
class ThemeAssetAdmin(admin.ModelAdmin):
    list_display = ("file_name", "theme", "asset_type", "file_size", "mime_type")
    list_filter = ("asset_type", "theme")
    search_fields = ("file_name", "file_path", "theme__name")
    readonly_fields = ("theme", "asset_type", "file_path", "file_name", "file_size", "mime_type")
