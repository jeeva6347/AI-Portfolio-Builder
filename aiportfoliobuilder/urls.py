from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Root: redirect unauthenticated → login; authenticated users will
    # be picked up by dashboard_redirect after login completes.
    path("", RedirectView.as_view(url="/accounts/login/", permanent=False), name="root"),

    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/social/", include("allauth.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("themes/", include("themes.urls")),
    path("portfolio/", include("portfolio.urls")),
    path("ai/", include("ai.urls")),
    path("github/", include("github_integration.urls")),
    path("billing/", include("payments.urls")),
    path("analytics/", include("analytics.urls")),
    
    # Root level SEO files
    path("sitemap.xml", RedirectView.as_view(url="/analytics/sitemap.xml", permanent=True)),
    path("robots.txt", RedirectView.as_view(url="/analytics/robots.txt", permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'dashboard.views.custom_permission_denied_view'
