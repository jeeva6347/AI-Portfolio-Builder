import os
import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse


class ThemeCategory(models.Model):
    """Taxonomy for organizing themes (Developer, Minimal, Creative, etc.)."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
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


class Theme(models.Model):
    """
    A portfolio theme package uploaded as a .zip archive (containing index.html & assets).
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
        default=Status.APPROVED,
        db_index=True,
    )
    rejection_reason = models.TextField(blank=True, default="")
    css_variables = models.JSONField(default=dict, blank=True)
    custom_css = models.TextField(blank=True, default="")
    html_structure = models.TextField(blank=True, default="")
    is_featured = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.PositiveIntegerField(default=0)
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        help_text="Price in USD. 0 = free.",
    )

    # Engine Specs & Customization Flags
    template_directory = models.CharField(max_length=255, blank=True)
    configuration_file = models.CharField(max_length=255, default="manifest.json")
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
        help_text="Auto-generated or uploaded preview image.",
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
        help_text="Comma-separated tags, e.g. 'dark, bootstrap, tailwind, portfolio'.",
    )
    version = models.CharField(max_length=20, default="1.0.0")
    downloads = models.PositiveIntegerField(default=0)

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

    @property
    def tag_list(self):
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
