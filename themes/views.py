"""
themes/views.py — Module 5: Theme Engine

Views are split into two groups:
  Admin views  — require Admin or Super Admin role
  Public views — require login only (Marketplace, Preview)

All views reuse the existing dashboard layout (dashboard/layouts/base.html)
and dashboard components (breadcrumb, stat_card, table_card, etc.).
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models as db_models
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, TemplateView

from dashboard.mixins import AdminRequiredMixin, SuperAdminRequiredMixin
from dashboard.navigation import get_sidebar_navigation
from .forms import CategoryForm, MarketplaceFilterForm, ThemeRejectForm, ThemeUploadForm
from .models import Theme, ThemeAsset, ThemeCategory
from .services import ThemeUploadError, process_theme_upload


# ── Shared context helper ──────────────────────────────────────────────────────

def _base_context(request, breadcrumbs=None):
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "breadcrumbs": breadcrumbs or [],
    }


def _suggested_icons():
    """Return a curated list of Bootstrap Icons for category icon picker."""
    return [
        "bi-briefcase-fill", "bi-person-fill", "bi-code-slash",
        "bi-palette-fill", "bi-building-fill", "bi-lightbulb-fill",
        "bi-star-fill", "bi-grid-fill", "bi-rocket-takeoff-fill",
        "bi-laptop-fill", "bi-brush-fill", "bi-camera-fill",
        "bi-chat-dots-fill", "bi-globe", "bi-moon-stars-fill",
        "bi-sun-fill", "bi-file-earmark-text-fill", "bi-shop-fill",
    ]


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN VIEWS
# ══════════════════════════════════════════════════════════════════════════════

class ThemeListAdminView(AdminRequiredMixin, View):
    """
    Admin: paginated list of all themes with status filter.
    GET /themes/admin/
    """
    template_name = "themes/admin/theme_list.html"

    def get(self, request):
        status_filter = request.GET.get("status", "")
        themes = Theme.objects.select_related("category", "uploaded_by").order_by("-created_at")
        if status_filter:
            themes = themes.filter(status=status_filter)

        # Stats for the page header cards
        stats = {
            "total": Theme.objects.count(),
            "draft": Theme.objects.filter(status=Theme.Status.DRAFT).count(),
            "pending": Theme.objects.filter(status=Theme.Status.PENDING).count(),
            "approved": Theme.objects.filter(status=Theme.Status.APPROVED).count(),
            "rejected": Theme.objects.filter(status=Theme.Status.REJECTED).count(),
        }

        ctx = _base_context(request, [
            {"title": "Dashboard", "url": "#"},
            {"title": "Theme Management", "url": "#"},
        ])
        ctx.update({
            "themes": themes,
            "stats": stats,
            "current_status": status_filter,
            "status_choices": Theme.Status.choices,
        })
        return render(request, self.template_name, ctx)


class ThemeUploadView(AdminRequiredMixin, View):
    """
    Admin: upload a new theme zip.
    GET  /themes/admin/upload/  → render upload form
    POST /themes/admin/upload/  → process zip, create Theme
    """
    template_name = "themes/admin/theme_upload.html"

    def get(self, request):
        form = ThemeUploadForm()
        ctx = _base_context(request, [
            {"title": "Dashboard", "url": "#"},
            {"title": "Theme Management", "url": reverse_lazy("themes:theme_list_admin")},
            {"title": "Upload Theme", "url": "#"},
        ])
        ctx["form"] = form
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = ThemeUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            ctx = _base_context(request, [
                {"title": "Dashboard", "url": "#"},
                {"title": "Theme Management", "url": reverse_lazy("themes:theme_list_admin")},
                {"title": "Upload Theme", "url": "#"},
            ])
            ctx["form"] = form
            return render(request, self.template_name, ctx)

        # Create the Theme record first (status=draft)
        theme = form.save(commit=False)
        theme.uploaded_by = request.user
        theme.status = Theme.Status.DRAFT
        theme.zip_file = request.FILES["zip_file"]
        theme.save()

        # Run the upload pipeline
        try:
            process_theme_upload(theme, request.FILES["zip_file"])
            messages.success(
                request,
                f"✅ Theme '{theme.name}' uploaded successfully! "
                f"{theme.file_count} assets extracted. Status: Draft.",
            )
            return redirect("themes:theme_detail_admin", slug=theme.slug)
        except ThemeUploadError as e:
            # Pipeline failed — delete the Theme record we just created
            theme.delete()
            form.add_error("zip_file", str(e))
            ctx = _base_context(request, [
                {"title": "Dashboard", "url": "#"},
                {"title": "Theme Management", "url": reverse_lazy("themes:theme_list_admin")},
                {"title": "Upload Theme", "url": "#"},
            ])
            ctx["form"] = form
            return render(request, self.template_name, ctx)


class ThemeDetailAdminView(AdminRequiredMixin, View):
    """
    Admin: view / manage a single theme.
    GET /themes/admin/<slug>/
    """
    template_name = "themes/admin/theme_detail.html"

    def get(self, request, slug):
        theme = get_object_or_404(Theme, slug=slug)
        assets_by_type = {}
        for asset in theme.assets.order_by("asset_type", "file_name"):
            assets_by_type.setdefault(asset.get_asset_type_display(), []).append(asset)

        ctx = _base_context(request, [
            {"title": "Dashboard", "url": "#"},
            {"title": "Theme Management", "url": reverse_lazy("themes:theme_list_admin")},
            {"title": theme.name, "url": "#"},
        ])
        ctx.update({
            "theme": theme,
            "assets_by_type": assets_by_type,
            "reject_form": ThemeRejectForm(),
        })
        return render(request, self.template_name, ctx)


class ThemeApproveView(AdminRequiredMixin, View):
    """POST /themes/admin/<slug>/approve/ — approve a theme."""

    def post(self, request, slug):
        theme = get_object_or_404(Theme, slug=slug)
        theme.status = Theme.Status.APPROVED
        theme.rejection_reason = ""
        theme.save(update_fields=["status", "rejection_reason", "updated_at"])
        messages.success(request, f"✅ Theme '{theme.name}' has been approved and is now live in the Marketplace.")
        return redirect("themes:theme_detail_admin", slug=theme.slug)


class ThemeRejectView(AdminRequiredMixin, View):
    """POST /themes/admin/<slug>/reject/ — reject a theme with reason."""

    def post(self, request, slug):
        theme = get_object_or_404(Theme, slug=slug)
        form = ThemeRejectForm(request.POST)
        if form.is_valid():
            theme.status = Theme.Status.REJECTED
            theme.rejection_reason = form.cleaned_data["reason"]
            theme.save(update_fields=["status", "rejection_reason", "updated_at"])
            messages.warning(request, f"⚠️ Theme '{theme.name}' has been rejected.")
        else:
            messages.error(request, "Please provide a rejection reason.")
        return redirect("themes:theme_detail_admin", slug=theme.slug)


class ThemeSetPendingView(AdminRequiredMixin, View):
    """POST /themes/admin/<slug>/submit/ — move draft → pending review."""

    def post(self, request, slug):
        theme = get_object_or_404(Theme, slug=slug)
        if theme.status == Theme.Status.DRAFT:
            theme.status = Theme.Status.PENDING
            theme.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Theme '{theme.name}' submitted for review.")
        return redirect("themes:theme_detail_admin", slug=theme.slug)


class ThemeDeleteView(AdminRequiredMixin, View):
    """POST /themes/admin/<slug>/delete/ — permanently delete a theme."""

    def post(self, request, slug):
        theme = get_object_or_404(Theme, slug=slug)
        name = theme.name
        # Cleanup extracted files
        import os, shutil
        from django.conf import settings
        if theme.extracted_path:
            abs_path = os.path.join(settings.MEDIA_ROOT, theme.extracted_path)
            if os.path.exists(abs_path):
                shutil.rmtree(abs_path, ignore_errors=True)
        theme.delete()
        messages.success(request, f"🗑️ Theme '{name}' has been permanently deleted.")
        return redirect("themes:theme_list_admin")


class CategoryListView(AdminRequiredMixin, View):
    """
    Admin: list + create theme categories.
    GET  /themes/admin/categories/
    POST /themes/admin/categories/  → create new category
    """
    template_name = "themes/admin/category_list.html"

    def get(self, request):
        ctx = _base_context(request, [
            {"title": "Dashboard", "url": "#"},
            {"title": "Theme Management", "url": reverse_lazy("themes:theme_list_admin")},
            {"title": "Categories", "url": "#"},
        ])
        ctx.update({
            "categories": ThemeCategory.objects.annotate(theme_count=db_models.Count("themes")),
            "form": CategoryForm(),
            "suggested_icons": _suggested_icons(),
        })
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{form.cleaned_data['name']}' created.")
            return redirect("themes:category_list")
        ctx = _base_context(request, [
            {"title": "Dashboard", "url": "#"},
            {"title": "Theme Management", "url": reverse_lazy("themes:theme_list_admin")},
            {"title": "Categories", "url": "#"},
        ])
        ctx.update({
            "categories": ThemeCategory.objects.annotate(theme_count=db_models.Count("themes")),
            "form": form,
            "suggested_icons": _suggested_icons(),
        })
        return render(request, self.template_name, ctx)


class CategoryDeleteView(AdminRequiredMixin, View):
    """POST /themes/admin/categories/<slug>/delete/"""

    def post(self, request, slug):
        cat = get_object_or_404(ThemeCategory, slug=slug)
        name = cat.name
        cat.delete()
        messages.success(request, f"Category '{name}' deleted.")
        return redirect("themes:category_list")


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC VIEWS (login required)
# ══════════════════════════════════════════════════════════════════════════════

class MarketplaceView(LoginRequiredMixin, View):
    """
    Public marketplace: browse approved themes.
    GET /themes/marketplace/
    """
    template_name = "themes/marketplace.html"
    login_url = "/accounts/login/"

    def get(self, request):
        form = MarketplaceFilterForm(request.GET or None)
        themes = Theme.objects.filter(status=Theme.Status.APPROVED).select_related("category")

        # Apply filters
        if form.is_valid():
            if q := form.cleaned_data.get("q"):
                themes = themes.filter(
                    db_models.Q(name__icontains=q) |
                    db_models.Q(description__icontains=q) |
                    db_models.Q(tags__icontains=q)
                )
            if cat := form.cleaned_data.get("category"):
                themes = themes.filter(category=cat)
            if pricing := form.cleaned_data.get("pricing"):
                if pricing == "free":
                    themes = themes.filter(is_premium=False)
                elif pricing == "premium":
                    themes = themes.filter(is_premium=True)
            sort = form.cleaned_data.get("sort") or "-created_at"
            themes = themes.order_by(sort)
        else:
            themes = themes.order_by("-created_at")

        categories = ThemeCategory.objects.all()
        ctx = _base_context(request, [
            {"title": "Dashboard", "url": "#"},
            {"title": "Marketplace", "url": "#"},
        ])
        ctx.update({
            "themes": themes,
            "form": form,
            "categories": categories,
            "total_themes": themes.count(),
        })
        return render(request, self.template_name, ctx)


class ThemePreviewView(LoginRequiredMixin, View):
    """
    iframe preview of an approved theme's index.html.
    GET /themes/preview/<slug>/
    """
    template_name = "themes/preview.html"
    login_url = "/accounts/login/"

    def get(self, request, slug):
        theme = get_object_or_404(Theme, slug=slug, status=Theme.Status.APPROVED)
        ctx = _base_context(request, [
            {"title": "Dashboard", "url": "#"},
            {"title": "Marketplace", "url": reverse_lazy("themes:marketplace")},
            {"title": f"Preview: {theme.name}", "url": "#"},
        ])
        ctx["theme"] = theme
        return render(request, self.template_name, ctx)
