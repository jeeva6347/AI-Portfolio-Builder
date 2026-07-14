"""
Module 13: Custom Domains — urls.py
"""
from django.urls import path
from . import views

app_name = "domains"

urlpatterns = [
    path("", views.DomainListView.as_view(), name="list"),
    path("add/", views.DomainAddView.as_view(), name="add"),
    path("<int:pk>/instructions/", views.DomainInstructionsView.as_view(), name="instructions"),
    path("<int:pk>/verify/", views.DomainVerifyView.as_view(), name="verify"),
    path("<int:pk>/set-primary/", views.DomainSetPrimaryView.as_view(), name="set_primary"),
    path("<int:pk>/delete/", views.DomainDeleteView.as_view(), name="delete"),
    path("<int:pk>/ssl-refresh/", views.DomainSSLRefreshView.as_view(), name="ssl_refresh"),
]
