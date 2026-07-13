from django.contrib import admin
from .models import ResumeUpload


@admin.register(ResumeUpload)
class ResumeUploadAdmin(admin.ModelAdmin):
    list_display = ("user", "file", "uploaded_at", "is_processed")
    list_filter = ("is_processed", "uploaded_at")
    search_fields = ("user__username", "file")
