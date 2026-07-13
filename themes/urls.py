from django.urls import path
from . import views

app_name = "themes"

urlpatterns = [
    # ── Admin views ────────────────────────────────────────────────────────────
    path("admin/", views.ThemeListAdminView.as_view(), name="theme_list_admin"),
    path("admin/upload/", views.ThemeUploadView.as_view(), name="theme_upload"),
    path("admin/categories/", views.CategoryListView.as_view(), name="category_list"),
    path("admin/categories/<slug:slug>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    # Theme-specific admin actions (order matters: specific paths before <slug>/)
    path("admin/<slug:slug>/approve/", views.ThemeApproveView.as_view(), name="theme_approve"),
    path("admin/<slug:slug>/reject/", views.ThemeRejectView.as_view(), name="theme_reject"),
    path("admin/<slug:slug>/submit/", views.ThemeSetPendingView.as_view(), name="theme_submit"),
    path("admin/<slug:slug>/delete/", views.ThemeDeleteView.as_view(), name="theme_delete"),
    
    # ── Module 6 Mapper URL patterns ──────────────────────────────────────────
    path("admin/<slug:slug>/mappings/", views.MappingListView.as_view(), name="mapping_list"),
    path("admin/<slug:slug>/mappings/create/", views.MappingCreateView.as_view(), name="mapping_create"),
    path("admin/<slug:slug>/scan/", views.ThemeScannerAPI.as_view(), name="theme_scan_api"),
    path("admin/mappings/<int:pk>/edit/", views.MappingEditView.as_view(), name="mapping_edit"),
    path("admin/mappings/<int:pk>/delete/", views.MappingDeleteView.as_view(), name="mapping_delete"),
    path("admin/mappings/<int:pk>/duplicate/", views.MappingDuplicateView.as_view(), name="mapping_duplicate"),
    path("admin/mappings/<int:pk>/toggle-active/", views.MappingToggleActiveView.as_view(), name="mapping_toggle_active"),
    path("admin/mappings/<int:pk>/preview/", views.MappingPreviewView.as_view(), name="mapping_preview"),
    path("admin/mappings/<int:pk>/preview/compiled/", views.MappingPreviewCompiledView.as_view(), name="mapping_preview_compiled"),
    path("admin/mappings/<int:pk>/save-api/", views.MappingSaveAPI.as_view(), name="mapping_save_api"),
    
    path("admin/<slug:slug>/", views.ThemeDetailAdminView.as_view(), name="theme_detail_admin"),

    # ── Public views ────────────────────────────────────────────────────────────
    path("marketplace/", views.MarketplaceView.as_view(), name="marketplace"),
    path("preview/<slug:slug>/", views.ThemePreviewView.as_view(), name="theme_preview"),
]
