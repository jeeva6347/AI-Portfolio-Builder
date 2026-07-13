import os
import shutil
import zipfile
from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Theme, ThemeCategory, ThemeAsset, ThemeMapping, ThemeMappingField
from .services import process_theme_upload, apply_theme_mapping, sanitize_html_string
from .scanner import scan_html_elements, suggest_mappings, detect_placeholders

User = get_user_model()


class ThemeMapperTestCase(TestCase):
    """
    Test suite for Module 6 Theme Mapper features.
    """
    def setUp(self):
        # Create super admin user
        self.user = User.objects.create_superuser(
            username="superadmin",
            email="admin@example.com",
            password="adminpassword"
        )
        self.user.role = User.Role.SUPER_ADMIN
        self.user.save()

        # Create normal free user for permission checking
        self.free_user = User.objects.create_user(
            username="freeuser",
            email="free@example.com",
            password="userpassword"
        )
        self.free_user.role = User.Role.FREE_USER
        self.free_user.save()

        # Create category
        self.category = ThemeCategory.objects.create(
            name="Developer Test",
            description="Category for testing mapping",
            icon="bi-code"
        )

        # Create sample HTML and zip for processing
        self.sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>My Test Theme</title></head>
        <body>
            <h1 class="hero-name" id="main-name">John Doe</h1>
            <p class="about-text">This is a paragraph about myself.</p>
            <img src="avatar.png" class="profile-photo" alt="My avatar" />
            <a href="https://github.com" class="github-link">GitHub Link</a>
            <footer>© 2026 John Doe</footer>
        </body>
        </html>
        """

        # Build in-memory zip
        import io
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("index.html", self.sample_html)
            zip_file.writestr("style.css", "body { background: #fff; }")
            zip_file.writestr("assets/avatar.png", b"fake-image-bytes")

        zip_buffer.seek(0)
        self.uploaded_zip = SimpleUploadedFile("theme.zip", zip_buffer.read(), content_type="application/zip")

        # Create draft Theme
        self.theme = Theme.objects.create(
            name="Test Theme",
            category=self.category,
            uploaded_by=self.user,
            zip_file=self.uploaded_zip,
            status=Theme.Status.DRAFT
        )

        # Extract files using service
        process_theme_upload(self.theme, self.theme.zip_file)

    def tearDown(self):
        # Clean up theme extracted files
        dest_dir = os.path.join(settings.MEDIA_ROOT, "themes", "extracted", self.theme.slug)
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)

    def test_theme_extraction_and_assets(self):
        """Verify ZIP validation, extraction and Asset scanner worked."""
        self.assertEqual(self.theme.assets.count(), 3)
        self.assertTrue(ThemeAsset.objects.filter(theme=self.theme, asset_type=ThemeAsset.AssetType.HTML).exists())
        self.assertTrue(ThemeAsset.objects.filter(theme=self.theme, asset_type=ThemeAsset.AssetType.CSS).exists())
        self.assertTrue(ThemeAsset.objects.filter(theme=self.theme, asset_type=ThemeAsset.AssetType.IMAGE).exists())

    def test_html_scanner_and_suggestions(self):
        """Verify HTML element scanner and mapping suggestions."""
        elements = scan_html_elements(self.sample_html)
        # Check we scanned major tags
        tags = [el.tag for el in elements]
        self.assertIn("h1", tags)
        self.assertIn("p", tags)
        self.assertIn("img", tags)
        self.assertIn("a", tags)

        # Check suggestions heuristic
        suggestions = suggest_mappings(elements)
        s_keys = [s.field_key for s in suggestions]
        self.assertIn("personal.name", s_keys)
        self.assertIn("social.github", s_keys)

    def test_theme_mapping_profile_duplication_and_activation(self):
        """Verify Mapping profile creation, duplication, and activation constraints."""
        # 1. Create mapping
        mapping = ThemeMapping.objects.create(
            theme=self.theme,
            name="Profile A",
            is_active=True,
            created_by=self.user
        )

        # Add mapping fields
        field_name = ThemeMappingField.objects.create(
            mapping=mapping,
            field_key="personal.name",
            selector="#main-name",
            attribute=ThemeMappingField.AttributeType.TEXT
        )
        field_git = ThemeMappingField.objects.create(
            mapping=mapping,
            field_key="social.github",
            selector=".github-link",
            attribute=ThemeMappingField.AttributeType.HREF
        )

        self.assertEqual(mapping.fields.count(), 2)

        # 2. Test duplication
        cloned = mapping.duplicate(new_name="Profile B")
        self.assertEqual(cloned.name, "Profile B")
        self.assertEqual(cloned.fields.count(), 2)
        self.assertFalse(cloned.is_active)  # Cloned mappings are inactive by default

        # 3. Test activation uniqueness constraint
        cloned.activate()
        mapping.refresh_from_db()
        cloned.refresh_from_db()

        self.assertTrue(cloned.is_active)
        self.assertFalse(mapping.is_active)  # Old mapping was deactivated automatically

    def test_apply_mapping_compilation(self):
        """Verify mapped selectors compile and render correctly with mock data."""
        mapping = ThemeMapping.objects.create(
            theme=self.theme,
            name="Profile A",
            is_active=True,
            created_by=self.user
        )
        ThemeMappingField.objects.create(
            mapping=mapping,
            field_key="personal.name",
            selector="#main-name",
            attribute=ThemeMappingField.AttributeType.TEXT
        )
        ThemeMappingField.objects.create(
            mapping=mapping,
            field_key="social.github",
            selector=".github-link",
            attribute=ThemeMappingField.AttributeType.HREF
        )

        # Apply mapping
        portfolio_data = {"personal.name": "Jane Developer", "social.github": "https://github.com/janedev"}
        compiled_html = apply_theme_mapping(self.sample_html, mapping, portfolio_data)

        self.assertIn("Jane Developer", compiled_html)
        self.assertIn("https://github.com/janedev", compiled_html)
        # Verify original wasn't completely ruined, stylesheet link or tags still exist
        self.assertIn("hero-name", compiled_html)

    def test_xss_protection_and_sanitization(self):
        """Ensure script injection is stripped out during HTML injection/sanitization."""
        dirty_html = "<div>Hello <script>alert('xss')</script><a href='javascript:alert(1)'>click</a></div>"
        clean_html = sanitize_html_string(dirty_html)
        
        self.assertNotIn("script", clean_html)
        self.assertNotIn("javascript:", clean_html)

    def test_permissions_restricted_to_admin(self):
        """Verify normal users cannot access mapping edit or API save views."""
        mapping = ThemeMapping.objects.create(
            theme=self.theme,
            name="Profile A",
            is_active=True,
            created_by=self.user
        )

        # Login as normal user
        self.client.login(username="freeuser", password="userpassword")
        
        # Access edit page
        res_edit = self.client.get(reverse("themes:mapping_edit", kwargs={"pk": mapping.pk}))
        self.assertEqual(res_edit.status_code, 403)  # Forbidden

        # Access JSON save API
        res_save = self.client.post(
            reverse("themes:mapping_save_api", kwargs={"pk": mapping.pk}),
            data='{"fields": []}',
            content_type="application/json"
        )
        self.assertEqual(res_save.status_code, 403)

    def test_mime_type_classification(self):
        """Verify mime-type classification maps extensions to AssetType correctly."""
        self.assertEqual(ThemeAsset.classify("index.html"), ThemeAsset.AssetType.HTML)
        self.assertEqual(ThemeAsset.classify("css/style.CSS"), ThemeAsset.AssetType.CSS)
        self.assertEqual(ThemeAsset.classify("js/app.mjs"), ThemeAsset.AssetType.JS)
        self.assertEqual(ThemeAsset.classify("img/avatar.WEBP"), ThemeAsset.AssetType.IMAGE)
        self.assertEqual(ThemeAsset.classify("font/Inter.woff2"), ThemeAsset.AssetType.FONT)
        self.assertEqual(ThemeAsset.classify("unknown.xyz"), ThemeAsset.AssetType.OTHER)

    def test_theme_download_counter_increment(self):
        """Verify that viewing theme details increments the downloads count."""
        initial_downloads = self.theme.downloads
        self.theme.increment_downloads()
        self.theme.refresh_from_db()
        self.assertEqual(self.theme.downloads, initial_downloads + 1)

    def test_zip_validation_invalid_files(self):
        """Verify that invalid zip uploads are rejected gracefully."""
        from .services import _validate_zip, ThemeUploadError
        import io
        invalid_buffer = io.BytesIO(b"this is plain text not a zip file")
        with self.assertRaises(ThemeUploadError):
            _validate_zip(invalid_buffer)
