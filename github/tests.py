import os
import shutil
import zipfile
import io
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from allauth.socialaccount.models import SocialAccount, SocialToken
from themes.models import Theme, ThemeCategory
from themes.services import process_theme_upload
from github.models import GitHubRepoConfig, GitHubDeployment
from github.services.exporter_service import compile_theme_static_bundle
from github.services.deployment_service import publish_theme_to_github

User = get_user_model()


class GitHubIntegrationTestCase(TestCase):
    """
    Test suite for GitHub integration & Theme Publishing to GitHub Pages.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        self.user.github_username = "testuser"
        self.user.save()

        self.social_account = SocialAccount.objects.create(
            user=self.user,
            provider="github",
            uid="12345",
            extra_data={"login": "testuser"}
        )
        self.social_token = SocialToken.objects.create(
            account=self.social_account,
            token="gho_mock_access_token_12345"
        )

        self.category = ThemeCategory.objects.create(
            name="Developer Theme",
            description="Test Dev Category",
            icon="bi-code"
        )

        self.sample_html = "<!DOCTYPE html><html><body><h1>Theme</h1></body></html>"
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("index.html", self.sample_html)
            zip_file.writestr("style.css", "body { background: #fff; }")

        zip_buffer.seek(0)
        self.uploaded_zip = SimpleUploadedFile("theme.zip", zip_buffer.read(), content_type="application/zip")

        self.theme = Theme.objects.create(
            name="Test Theme Layout",
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

    def test_exporter_packages_theme_bundle(self):
        """Verify exporter packages extracted theme files."""
        bundle = compile_theme_static_bundle(self.theme)
        self.assertIn("index.html", bundle)
        self.assertIn("style.css", bundle)

    @patch("github.services.repository_service.github_api_request")
    def test_publish_theme_to_github(self, mock_api):
        """Verify publish_theme_to_github creates commit and enables Pages."""
        def side_effect(url, token, data=None, method="GET"):
            if "git/blobs" in url:
                return ({"sha": "mock_blob_sha"}, 201)
            if "git/ref" in url and method == "GET":
                return ({"object": {"sha": "parent_commit_sha"}}, 200)
            if "git/commits/parent_commit_sha" in url:
                return ({"tree": {"sha": "parent_tree_sha"}}, 200)
            if "git/trees" in url:
                return ({"sha": "new_tree_sha"}, 201)
            if "git/commits" in url and method == "POST":
                return ({"sha": "new_commit_sha"}, 201)
            if "git/refs/heads" in url and method == "PATCH":
                return ({"object": {"sha": "new_commit_sha"}}, 200)
            if "pages" in url:
                return ({"html_url": "https://testuser.github.io/test-repo/"}, 201)
            return ({"name": "test-repo", "default_branch": "main"}, 200)

        mock_api.side_effect = side_effect

        deployment = publish_theme_to_github(self.user, self.theme, "gho_mock_token")
        if deployment.status != GitHubDeployment.Status.SUCCESS:
            print("DEPLOYMENT ERROR:", deployment.error_message)
        self.assertEqual(deployment.status, GitHubDeployment.Status.SUCCESS)
        self.assertEqual(deployment.last_commit_sha, "new_commit_sha")
        self.assertTrue(deployment.pages_enabled)
