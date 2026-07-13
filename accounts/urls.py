from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("sessions/", views.sessions_view, name="sessions"),

    # Forgot / reset password
    path("password-reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path(
        "password-reset/confirm/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("password-reset/complete/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
