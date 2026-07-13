import os
import shutil
import zipfile
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from allauth.socialaccount.models import SocialAccount, SocialToken
from themes.models import Theme, ThemeCategory, ThemeMapping, ThemeMappingField
from themes.services import process_theme_upload
from portfolio.models import Portfolio, PortfolioProject
from github_integration.models import GitHubRepoConfig, GitHubDeployment

from github_integration.services.exporter_service import compile_portfolio_static_bundle
from github_integration.services.deployment_service import publish_portfolio_to_github

User = get_user_model()


class GitHubIntegrationTestCase(TestCase):
    """
    Test suite for Module 9: GitHub Auto Publish & GitHub Pages Deployment.
    """
    def setUp(self):
        # Create standard user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        self.user.save()

        # Create secondary user for permission validation
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpassword"
        )
        self.other_user.save()

        # Link social account & token
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

        # Create test theme category
        self.category = ThemeCategory.objects.create(
            name="Developer Theme",
            description="Test Dev Category",
            icon="bi-code"
        )

        # Create mock theme structure
        self.sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Static Site</title></head>
        <body>
            <h1 class="name">Name</h1>
            <img src="/media/portfolios/photos/avatar.jpg" class="avatar">
        </body>
        </html>
        """

        import io
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

        # Create mapping profile
        self.mapping = ThemeMapping.objects.create(
            theme=self.theme,
            name="Default Theme Map",
            is_active=True,
            created_by=self.user
        )
        ThemeMappingField.objects.create(
            mapping=self.mapping,
            field_key="personal.name",
            selector=".name",
            attribute=ThemeMappingField.AttributeType.TEXT
        )

        # Create portfolio mapping
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Jane Developer",
            selected_theme=self.theme
        )

    def tearDown(self):
        # Clean up theme extracted media files
        dest_dir = os.path.join(settings.MEDIA_ROOT, "themes", "extracted", self.theme.slug)
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)

    def test_exporter_packages_bundle_and_rewrites_paths(self):
        """Verify the exporter service packages HTML/CSS and converts media paths to relative."""
        # Create a dummy media file to test packaging
        media_sub_dir = os.path.join(settings.BASE_DIR, "media", "portfolios", "photos")
        os.makedirs(media_sub_dir, exist_ok=True)
        dummy_file = os.path.join(media_sub_dir, "avatar.jpg")
        with open(dummy_file, "wb") as f:
            f.write(b"dummy_image_data")

        try:
            bundle = compile_portfolio_static_bundle(self.portfolio)
            
            # Verify index.html exists in bundle
            self.assertIn("index.html", bundle)
            self.assertIn("style.css", bundle)
            
            # Verify dummy image was packaged under its relative media folder key
            self.assertIn("media/portfolios/photos/avatar.jpg", bundle)
            self.assertEqual(bundle["media/portfolios/photos/avatar.jpg"], b"dummy_image_data")

            # Verify HTML was parsed and the src attribute is rewritten to be relative
            compiled_html = bundle["index.html"].decode("utf-8")
            self.assertIn('src="media/portfolios/photos/avatar.jpg"', compiled_html)
            self.assertNotIn('src="/media/portfolios/photos/avatar.jpg"', compiled_html)
        finally:
            if os.path.exists(dummy_file):
                os.remove(dummy_file)

    @patch("github_integration.services.repository_service.github_api_request")
    def test_configure_and_clear_connection_views(self, mock_api):
        """Verify user can link and clear repository config connections."""
        self.client.login(username="testuser", password="testpassword")
        
        # Mock user and list api responses
        mock_api.side_effect = [
            ({"login": "testuser"}, 200), # get_authenticated_username
        ]

        # Configure repository mapping
        res = self.client.post(
            reverse("github:configure", kwargs={"pk": self.portfolio.pk}),
            data={"repo_choice": "existing", "existing_repo": "my-portfolio"}
        )
        self.assertEqual(res.status_code, 302)
        
        # Verify local database config created
        config = GitHubRepoConfig.objects.filter(portfolio=self.portfolio).first()
        self.assertIsNotNone(config)
        self.assertEqual(config.repo_name, "my-portfolio")
        self.assertEqual(config.repository_owner, "testuser")

        # Clear configuration mapping view
        res_clear = self.client.post(reverse("github:clear", kwargs={"pk": self.portfolio.pk}))
        self.assertEqual(res_clear.status_code, 302)
        self.assertFalse(GitHubRepoConfig.objects.filter(portfolio=self.portfolio).exists())

    @patch("github_integration.services.repository_service.github_api_request")
    def test_publish_workflow_integrates_github_git_apis(self, mock_api):
        """Verify the publishing workflow calls Git Data and Pages REST APIs successfully."""
        config = GitHubRepoConfig.objects.create(
            portfolio=self.portfolio,
            repo_name="deploy-repo",
            repository_owner="testuser"
        )

        # Mock Git Data API step returns
        mock_api.side_effect = [
            ({"object": {"sha": "latest_ref_commit_sha"}}, 200),  # heads/main ref
            ({"tree": {"sha": "base_tree_sha"}}, 200),            # commit detail
            ({"sha": "new_tree_sha"}, 201),                       # create tree
            ({"sha": "new_commit_sha"}, 201),                     # create commit
            ({"object": {"sha": "new_commit_sha"}}, 200),         # patch ref
            ({"html_url": "https://testuser.github.io/deploy-repo/"}, 201), # enable pages
        ]

        deployment = publish_portfolio_to_github(self.portfolio, "gho_mock_token")
        self.assertEqual(deployment.status, GitHubDeployment.Status.SUCCESS)
        self.assertEqual(deployment.last_commit_sha, "new_commit_sha")
        self.assertEqual(deployment.published_url, "https://testuser.github.io/deploy-repo/")
        self.assertTrue(deployment.pages_enabled)

    def test_unauthorized_user_is_forbidden_to_publish(self):
        """Verify users cannot view or trigger deployments on portfolios they do not own."""
        # Setup repository config for portfolio
        GitHubRepoConfig.objects.create(
            portfolio=self.portfolio,
            repo_name="private-repo",
            repository_owner="testuser"
        )

        # Login as other_user
        self.client.login(username="otheruser", password="otherpassword")
        
        # 1. Attempt to view dashboard
        res_dash = self.client.get(reverse("github:dashboard", kwargs={"pk": self.portfolio.pk}))
        self.assertEqual(res_dash.status_code, 404)  # Blocked by user filter query!

        # 2. Attempt to publish
        res_pub = self.client.post(reverse("github:publish", kwargs={"pk": self.portfolio.pk}))
        self.assertEqual(res_pub.status_code, 404)
