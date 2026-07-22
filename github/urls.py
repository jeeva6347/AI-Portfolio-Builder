from django.urls import path
from . import views

app_name = "github"

urlpatterns = [
    path("", views.GitHubIndexView.as_view(), name="index"),
    path("connect/", views.GitHubConnectView.as_view(), name="connect"),
    path("disconnect/", views.GitHubDisconnectView.as_view(), name="disconnect"),
    path("theme/<int:pk>/", views.ThemeDeployView.as_view(), name="theme_deploy"),
]
