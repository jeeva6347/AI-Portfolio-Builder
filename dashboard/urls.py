from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Dashboards
    path("super-admin/", views.SuperAdminDashboardView.as_view(), name="super_admin"),
    path("admin/", views.AdminDashboardView.as_view(), name="admin"),
    path("user/", views.UserDashboardView.as_view(), name="user"),
    
    # Placeholders for future modules
    path("themes/", views.PlaceholderView.as_view(), {'title': 'Themes'}, name="themes_placeholder"),
    path("portfolio/", views.PlaceholderView.as_view(), {'title': 'Portfolio'}, name="portfolio_placeholder"),
    path("marketplace/", views.PlaceholderView.as_view(), {'title': 'Marketplace'}, name="marketplace_placeholder"),
    path("github/", views.PlaceholderView.as_view(), {'title': 'GitHub Integration'}, name="github_placeholder"),
    path("ai/", views.PlaceholderView.as_view(), {'title': 'AI Content Generator'}, name="ai_placeholder"),
    path("analytics/", views.PlaceholderView.as_view(), {'title': 'Analytics'}, name="analytics_placeholder"),
    path("payments/", views.PlaceholderView.as_view(), {'title': 'Payments'}, name="payments_placeholder"),
    path("settings/", views.PlaceholderView.as_view(), {'title': 'Settings'}, name="settings_placeholder"),
]
