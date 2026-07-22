from django.urls import path
from . import views

app_name = "themes"

urlpatterns = [
    path("", views.ThemeGalleryView.as_view(), name="gallery"),
    path("upload/", views.ThemeUploadView.as_view(), name="upload"),
    path("<int:pk>/preview/", views.ThemePreviewView.as_view(), name="preview"),
    path("<int:pk>/edit/", views.ThemeEditView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ThemeDeleteView.as_view(), name="delete"),
]
