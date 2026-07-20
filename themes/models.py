"""
Theme Engine models — Module 5.

Three models:
  ThemeCategory  — taxonomy for organising themes (Developer, Minimal, etc.)
  Theme          — the uploaded theme package (zip → extracted files)
  ThemeAsset     — individual file records extracted from the zip
"""

import os
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse


class ThemeCategory(models.Model):
    """Taxonomy for themes (Minimal, Corporate, Developer, etc.)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    # Bootstrap Icons class, e.g. "bi-briefcase-fill"
    icon = models.CharField(max_length=50, default="bi-grid-fill")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Theme Category"
        verbose_name_plural = "Theme Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


import uuid


class Theme(models.Model):
    """
    A portfolio theme uploaded as a .zip archive or registered via theme registry.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    author = models.CharField(max_length=150, blank=True, default="AI Portfolio Team")
    category = models.ForeignKey(
        ThemeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="themes",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_themes",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text="Price in USD. 0 = free.",
    )

    # Engine Specs & Customization Flags
    template_directory = models.CharField(max_length=255, blank=True)
    configuration_file = models.CharField(max_length=255, default="theme.json")
    default_css = models.TextField(blank=True)
    css_variables = models.JSONField(default=dict, blank=True)
    font_family = models.CharField(max_length=100, default="Inter")
    supports_dark_mode = models.BooleanField(default=True)
    supports_custom_colors = models.BooleanField(default=True)
    supports_custom_fonts = models.BooleanField(default=True)
    supports_animation = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    # Storage
    zip_file = models.FileField(upload_to="themes/zips/", null=True, blank=True)
    extracted_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path relative to MEDIA_ROOT where zip was extracted.",
    )
    thumbnail = models.ImageField(
        upload_to="themes/thumbnails/",
        null=True,
        blank=True,
        help_text="Auto-generated or manually uploaded preview image.",
    )
    preview_image = models.ImageField(
        upload_to="themes/previews/",
        null=True,
        blank=True,
        help_text="High-resolution full preview screenshot image.",
    )

    # Metadata
    tags = models.CharField(
        max_length=500,
        blank=True,
        help_text="Comma-separated tags, e.g. 'dark, minimal, portfolio'.",
    )
    version = models.CharField(max_length=20, default="1.0.0")
    downloads = models.PositiveIntegerField(default=0)

    # Rejection reason (set by admin on rejection)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Theme"
        verbose_name_plural = "Themes"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Theme.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("themes:theme_detail_admin", kwargs={"slug": self.slug})

    def increment_downloads(self):
        """Increment the download count for this theme."""
        self.downloads += 1
        self.save(update_fields=["downloads"])

    @property
    def tag_list(self):
        """Return tags as a Python list."""
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def index_html_path(self):
        """Absolute path to the extracted index.html for iframe preview."""
        if self.extracted_path:
            return os.path.join(settings.MEDIA_ROOT, self.extracted_path, "index.html")
        return None

    @property
    def index_html_url(self):
        """Media URL to the extracted index.html for iframe preview."""
        if self.extracted_path:
            return f"{settings.MEDIA_URL}{self.extracted_path}/index.html"
        return None

    @property
    def file_count(self):
        return self.assets.count()

    @property
    def total_size(self):
        """Total size of all assets in bytes."""
        return self.assets.aggregate(total=models.Sum("file_size"))["total"] or 0


class ThemeAsset(models.Model):
    """Individual file extracted from a Theme zip archive."""

    class AssetType(models.TextChoices):
        HTML = "html", "HTML"
        CSS = "css", "CSS"
        JS = "js", "JavaScript"
        IMAGE = "image", "Image"
        FONT = "font", "Font"
        OTHER = "other", "Other"

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="assets")
    asset_type = models.CharField(
        max_length=10, choices=AssetType.choices, default=AssetType.OTHER
    )
    file_path = models.CharField(
        max_length=500, help_text="Path relative to theme extracted_path."
    )
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0, help_text="Size in bytes.")
    mime_type = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["asset_type", "file_name"]
        verbose_name = "Theme Asset"
        verbose_name_plural = "Theme Assets"

    def __str__(self):
        return f"{self.theme.name} / {self.file_path}"

    @staticmethod
    def classify(filename: str) -> str:
        """Map a filename extension to an AssetType choice value."""
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext in {"html", "htm"}:
            return ThemeAsset.AssetType.HTML
        if ext == "css":
            return ThemeAsset.AssetType.CSS
        if ext in {"js", "mjs"}:
            return ThemeAsset.AssetType.JS
        if ext in {"jpg", "jpeg", "png", "gif", "svg", "webp", "ico", "avif"}:
            return ThemeAsset.AssetType.IMAGE
        if ext in {"woff", "woff2", "ttf", "eot", "otf"}:
            return ThemeAsset.AssetType.FONT
        return ThemeAsset.AssetType.OTHER


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 6 — THEME MAPPER
# ═══════════════════════════════════════════════════════════════════════════════

class ThemeMapping(models.Model):
    """
    A named mapping profile that connects a Theme's HTML elements
    to portfolio data fields.

    One Theme can have multiple named mappings (e.g. "v1", "dark-variant").
    Only one mapping is marked `is_active` at a time per theme.

    Workflow:
      Admin creates mapping → adds ThemeMappingField rows → activates
      System uses active mapping to render user portfolio with real data.
    """

    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name="mappings",
    )
    name = models.CharField(
        max_length=100,
        help_text="Human-readable name, e.g. 'v1 Default' or 'Dark Variant'.",
    )
    version = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(
        default=False,
        help_text="Only one mapping per theme should be active at a time.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_mappings",
    )
    notes = models.TextField(blank=True, help_text="Optional admin notes about this mapping.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Theme Mapping"
        verbose_name_plural = "Theme Mappings"
        # Enforce at most one active mapping per theme at the DB level
        constraints = [
            models.UniqueConstraint(
                fields=["theme"],
                condition=models.Q(is_active=True),
                name="unique_active_mapping_per_theme",
            )
        ]

    def __str__(self):
        active = " [ACTIVE]" if self.is_active else ""
        return f"{self.theme.name} — {self.name} v{self.version}{active}"

    def activate(self):
        """
        Deactivate all other mappings for this theme, then activate self.
        Wrapped in a transaction to stay consistent.
        """
        from django.db import transaction
        with transaction.atomic():
            ThemeMapping.objects.filter(theme=self.theme, is_active=True).update(is_active=False)
            self.is_active = True
            self.save(update_fields=["is_active", "updated_at"])

    def duplicate(self, new_name: str = None) -> "ThemeMapping":
        """Clone this mapping and all its fields into a new inactive mapping."""
        new_mapping = ThemeMapping.objects.create(
            theme=self.theme,
            name=new_name or f"{self.name} (copy)",
            version=self.version,
            is_active=False,
            created_by=self.created_by,
            notes=self.notes,
        )
        for field in self.fields.all():
            ThemeMappingField.objects.create(
                mapping=new_mapping,
                field_key=field.field_key,
                selector=field.selector,
                attribute=field.attribute,
                order=field.order,
                is_required=field.is_required,
                notes=field.notes,
            )
        return new_mapping


class ThemeMappingField(models.Model):
    """
    One row = one mapped element.

    e.g.:
      field_key  = "personal.name"
      selector   = "h1.hero-title"
      attribute  = "text"   (inner text) | "src" | "href" | "data-*" | "html"
      order      = 1

    The selector is a CSS selector string; the system applies it to the
    theme's index.html to locate the target element.
    """

    class AttributeType(models.TextChoices):
        TEXT = "text", "Inner Text"
        HTML = "html", "Inner HTML"
        SRC = "src", "src attribute (img)"
        HREF = "href", "href attribute (link)"
        ALT = "alt", "alt attribute (img)"
        PLACEHOLDER = "placeholder", "Placeholder text"
        CUSTOM = "custom", "Custom attribute"

    mapping = models.ForeignKey(
        ThemeMapping,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    # Key from PORTFOLIO_FIELDS registry, e.g. "personal.name", "social.github"
    field_key = models.CharField(max_length=100)
    # CSS selector to locate the element, e.g. "#hero h1" or ".about-text p"
    selector = models.CharField(max_length=500)
    # How to inject the value into the element
    attribute = models.CharField(
        max_length=20,
        choices=AttributeType.choices,
        default=AttributeType.TEXT,
    )
    # For AttributeType.CUSTOM: the attribute name e.g. "data-email"
    custom_attribute = models.CharField(max_length=100, blank=True)
    # Display order in the mapper UI
    order = models.PositiveSmallIntegerField(default=0)
    is_required = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "field_key"]
        verbose_name = "Mapping Field"
        verbose_name_plural = "Mapping Fields"

    def __str__(self):
        return f"{self.field_key} → {self.selector} [{self.attribute}]"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Guard: same field_key cannot appear twice in the same mapping
        if (
            ThemeMappingField.objects
            .filter(mapping=self.mapping, field_key=self.field_key)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                {"field_key": f"Field '{self.field_key}' is already mapped in this profile. Remove the existing mapping first."}
            )

