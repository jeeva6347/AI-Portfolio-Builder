from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("summary/", views.AnalyticsDashboardView.as_view(), name="dashboard"),
    path("seo/<int:pk>/", views.PortfolioSEOConfigView.as_view(), name="seo_config"),
    path("performance/<int:pk>/", views.PortfolioPerformanceView.as_view(), name="performance_config"),
    
    path("sitemap.xml", views.SitemapView.as_view(), name="sitemap"),
    path("robots.txt", views.RobotsTxtView.as_view(), name="robots_txt"),
]
