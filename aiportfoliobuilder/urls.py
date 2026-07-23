from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

from accounts.views import EmailLoginView, SignupView, LogoutView
from core.views import LandingPageView

urlpatterns = [
    path("", LandingPageView.as_view(), name="root"),

    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/social/", include("allauth.urls")),

    # Allauth compatibility URL aliases
    path("accounts/login/compat/", EmailLoginView.as_view(), name="account_login"),
    path("accounts/signup/compat/", SignupView.as_view(), name="account_signup"),
    path("accounts/logout/compat/", LogoutView.as_view(), name="account_logout"),

    path("dashboard/", include("dashboard.urls")),
    path("themes/", include("themes.urls")),
    path("github/", include("github.urls")),

    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

handler403 = 'dashboard.views.custom_permission_denied_view'
handler404 = 'dashboard.views.custom_page_not_found_view'
handler500 = 'dashboard.views.custom_server_error_view'
