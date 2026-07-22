import os
import shutil
import zipfile
import io
from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Theme, ThemeCategory, ThemeAsset
from .services import process_theme_upload

User = get_user_model()


class ThemeSystemTestCase(TestCase):
    """
    Test suite for Theme Upload, Extraction, Gallery, and Preview features.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="user@example.com",
            password="password123"
        )
        self.category = ThemeCategory.objects.create(
            name="Developer",
            description="Tech portfolio themes",
            icon="bi-code-slash"
        )

        self.sample_html = """<!DOCTYPE html>
<html>
<head><title>Test Theme</title></head>
<body>
    <h1>Hello World</h1>
    <p>Test portfolio page</p>
</body>
</html>"""

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", self.sample_html)
            zf.writestr("style.css", "body { color: red; }")

        zip_buffer.seek(0)
        self.uploaded_zip = SimpleUploadedFile("theme.zip", zip_buffer.read(), content_type="application/zip")

        self.theme = Theme.objects.create(
            name="Test Theme",
            category=self.category,
            uploaded_by=self.user,
            zip_file=self.uploaded_zip,
            status=Theme.Status.APPROVED
        )
        process_theme_upload(self.theme, self.theme.zip_file)

    def tearDown(self):
        if self.theme.extracted_path:
            dest_dir = os.path.join(settings.MEDIA_ROOT, self.theme.extracted_path)
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir, ignore_errors=True)

    def test_theme_upload_and_extraction(self):
        """Verify ZIP file extraction and asset classification."""
        self.assertEqual(self.theme.assets.count(), 2)
        self.assertTrue(ThemeAsset.objects.filter(theme=self.theme, asset_type=ThemeAsset.AssetType.HTML).exists())
        self.assertTrue(ThemeAsset.objects.filter(theme=self.theme, asset_type=ThemeAsset.AssetType.CSS).exists())

    def test_theme_gallery_view(self):
        """Verify logged-in user can access theme gallery."""
        self.client.login(username="testuser", password="password123")
        res = self.client.get(reverse("themes:gallery"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Test Theme")

    def test_theme_preview_view(self):
        """Verify theme preview serves extracted index.html."""
        res = self.client.get(reverse("themes:preview", kwargs={"pk": self.theme.pk}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Hello World")
