from django.urls import path
from . import views

app_name = "github"

urlpatterns = [
    path("connect/", views.GitHubConnectView.as_view(), name="connect"),
    path("disconnect/", views.GitHubDisconnectView.as_view(), name="disconnect"),
    
    path("portfolio/<int:pk>/", views.DeploymentDashboardView.as_view(), name="dashboard"),
    path("portfolio/<int:pk>/configure/", views.ConfigureRepositoryView.as_view(), name="configure"),
    path("portfolio/<int:pk>/auto-deploy/", views.AutoDeployView.as_view(), name="auto_deploy"),
    path("portfolio/<int:pk>/publish/", views.PublishPortfolioView.as_view(), name="publish"),
    path("portfolio/<int:pk>/clear/", views.ClearConnectionView.as_view(), name="clear"),
]
