from django.urls import path
from . import views

app_name = "ai"

urlpatterns = [
    path("import/", views.ResumeImportView.as_view(), name="import"),
    path("review/", views.ResumeReviewView.as_view(), name="review"),
]
