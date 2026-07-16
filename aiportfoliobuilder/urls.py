from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from analytics.views import SitemapView, RobotsTxtView

from core.views import LandingPageView

urlpatterns = [
    path("", LandingPageView.as_view(), name="root"),

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
    path("domains/", include("domains.urls")),
    path("organizations/", include("organizations.urls")),
    
    # Root level SEO files
    path("sitemap.xml", SitemapView.as_view(), name="sitemap"),
    path("robots.txt", RobotsTxtView.as_view(), name="robots_txt"),
    path("favicon.ico", RedirectView.as_view(url=staticfiles_storage.url("favicon.ico")), name="favicon"),
    path("apple-touch-icon.png", RedirectView.as_view(url=staticfiles_storage.url("apple-touch-icon.png")), name="apple_touch_icon"),
    path("site.webmanifest", RedirectView.as_view(url=staticfiles_storage.url("site.webmanifest")), name="site_webmanifest"),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

handler403 = 'dashboard.views.custom_permission_denied_view'
handler404 = 'dashboard.views.custom_page_not_found_view'
handler500 = 'dashboard.views.custom_server_error_view'
