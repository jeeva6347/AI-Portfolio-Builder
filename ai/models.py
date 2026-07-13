from django.db import models
from django.conf import settings


class ResumeUpload(models.Model):
    """
    Stores secure history of user uploaded resumes for AI parsing.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resume_uploads"
    )
    file = models.FileField(upload_to="resumes/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.file.name}"
