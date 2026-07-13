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
    path("admin/<slug:slug>/", views.ThemeDetailAdminView.as_view(), name="theme_detail_admin"),

    # ── Public views ────────────────────────────────────────────────────────────
    path("marketplace/", views.MarketplaceView.as_view(), name="marketplace"),
    path("preview/<slug:slug>/", views.ThemePreviewView.as_view(), name="theme_preview"),
]
