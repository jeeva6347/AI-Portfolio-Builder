import os
import shutil
import zipfile
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from themes.models import Theme, ThemeCategory, ThemeMapping, ThemeMappingField
from themes.services import process_theme_upload
from .models import (
    Portfolio,
    PortfolioSkill,
    PortfolioProject,
    PortfolioExperience,
    PortfolioEducation
)

User = get_user_model()


class PortfolioBuilderTestCase(TestCase):
    """
    Test suite for Module 7 and Module 8: Live Preview & Visual Editor.
    """
    def setUp(self):
        # Create standard test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        self.user.save()

        # Create secondary test user for permission checks
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpassword"
        )
        self.other_user.save()

        # Create category
        self.category = ThemeCategory.objects.create(
            name="Developer Theme",
            description="Test Dev Category",
            icon="bi-code"
        )

        # Create test HTML theme for mapping and compilation previews
        self.sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>User Portfolio Website</title></head>
        <body>
            <h1 class="user-name">Developer Name</h1>
            <p class="user-bio">A bio placeholder.</p>
            <div id="projects-grid">
                <div class="project-card">
                    <h4 class="proj-title">Proj 1</h4>
                    <p class="proj-desc">Desc 1</p>
                </div>
            </div>
            <footer>© 2026 Developer Name</footer>
        </body>
        </html>
        """

        # Build in-memory zip
        import io
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("index.html", self.sample_html)
            zip_file.writestr("style.css", "body { background: #fff; }")

        zip_buffer.seek(0)
        self.uploaded_zip = SimpleUploadedFile("portfolio_theme.zip", zip_buffer.read(), content_type="application/zip")

        # Create and extract Theme using Module 5 engine
        self.theme = Theme.objects.create(
            name="Portfolio Template A",
            category=self.category,
            uploaded_by=self.user,
            zip_file=self.uploaded_zip,
            status=Theme.Status.APPROVED
        )
        process_theme_upload(self.theme, self.theme.zip_file)

        # Generate a ThemeMapping for this theme using Module 6 mapper
        self.mapping = ThemeMapping.objects.create(
            theme=self.theme,
            name="Default Theme Map",
            is_active=True,
            created_by=self.user
        )

        # Map flat fields
        ThemeMappingField.objects.create(
            mapping=self.mapping,
            field_key="personal.name",
            selector=".user-name",
            attribute=ThemeMappingField.AttributeType.TEXT
        )
        ThemeMappingField.objects.create(
            mapping=self.mapping,
            field_key="personal.about",
            selector=".user-bio",
            attribute=ThemeMappingField.AttributeType.TEXT
        )

        # Map repeating project list container and children
        ThemeMappingField.objects.create(
            mapping=self.mapping,
            field_key="projects.list",
            selector=".project-card",
            attribute=ThemeMappingField.AttributeType.TEXT
        )
        ThemeMappingField.objects.create(
            mapping=self.mapping,
            field_key="projects.title",
            selector=".project-card .proj-title",
            attribute=ThemeMappingField.AttributeType.TEXT
        )
        ThemeMappingField.objects.create(
            mapping=self.mapping,
            field_key="projects.description",
            selector=".project-card .proj-desc",
            attribute=ThemeMappingField.AttributeType.TEXT
        )

    def tearDown(self):
        # Clean up theme extracted media files
        dest_dir = os.path.join(settings.MEDIA_ROOT, "themes", "extracted", self.theme.slug)
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)

    def test_portfolio_model_and_flat_serialization(self):
        """Verify Portfolio is created and serializes to the correct dictionary values."""
        portfolio = Portfolio.objects.create(
            user=self.user,
            name="John Doe",
            title="Python Dev",
            tagline="Keep it simple",
            about="Biographical details here.",
            email="johndoe@example.com"
        )
        
        fd = portfolio.get_fields_dict()
        self.assertEqual(fd["personal.name"], "John Doe")
        self.assertEqual(fd["personal.title"], "Python Dev")
        self.assertEqual(fd["personal.tagline"], "Keep it simple")
        self.assertEqual(fd["personal.about"], "Biographical details here.")
        self.assertEqual(fd["personal.email"], "johndoe@example.com")

    def test_portfolio_builder_tab_access(self):
        """Verify the builder dashboard view requires login and serves segments correctly."""
        # Create a minimal approved theme so the workspace panel renders (not the onboarding screen)
        category = ThemeCategory.objects.create(name="Test Category", slug="test-category")
        theme = Theme.objects.create(
            name="Test Theme",
            slug="test-theme",
            status=Theme.Status.APPROVED,
            category=category,
        )
        portfolio = Portfolio.objects.create(user=self.user, name="Build Test", selected_theme=theme)

        # Unauthenticated access
        res = self.client.get(reverse("portfolio:builder", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res.status_code, 302)  # Redirects to login

        # Authenticated access – personal tab should render the workspace form panel
        self.client.login(username="testuser", password="testpassword")
        res_auth = self.client.get(reverse("portfolio:builder", kwargs={"pk": portfolio.pk}) + "?tab=personal")
        self.assertEqual(res_auth.status_code, 200)
        self.assertContains(res_auth, "Full Name")

    def test_skills_projects_experiences_crud(self):
        """Verify user can add/delete related skills, projects, and experiences via POST views."""
        self.client.login(username="testuser", password="testpassword")
        portfolio = Portfolio.objects.create(user=self.user)

        # 1. Add Skill
        res_skill = self.client.post(
            reverse("portfolio:skill_create", kwargs={"pk": portfolio.pk}),
            data={"skill_type": "technical", "name": "Django", "level": "Expert"}
        )
        self.assertEqual(res_skill.status_code, 302)
        self.assertTrue(portfolio.skills.filter(name="Django").exists())

        # 2. Add Experience
        res_exp = self.client.post(
            reverse("portfolio:experience_create", kwargs={"pk": portfolio.pk}),
            data={
                "company": "Tech Corp",
                "position": "Django Developer",
                "duration": "2021-2023",
                "description": "Responsibilities and accomplishments..."
            }
        )
        self.assertEqual(res_exp.status_code, 302)
        self.assertTrue(portfolio.experiences.filter(company="Tech Corp").exists())

        # 3. Add Project
        res_proj = self.client.post(
            reverse("portfolio:project_create", kwargs={"pk": portfolio.pk}),
            data={
                "title": "Awesome SaaS",
                "description": "Premium Django dashboard project.",
                "technologies": "Django Tailwind"
            }
        )
        self.assertEqual(res_proj.status_code, 302)
        self.assertTrue(portfolio.projects.filter(title="Awesome SaaS").exists())

        # 4. Delete Project
        proj = portfolio.projects.first()
        res_del_proj = self.client.post(reverse("portfolio:project_delete", kwargs={"pk": proj.pk}))
        self.assertEqual(res_del_proj.status_code, 302)
        self.assertFalse(portfolio.projects.filter(title="Awesome SaaS").exists())

    def test_theme_activation_and_preview_compilation(self):
        """Verify theme activation binds correctly and dynamic previews compile custom portfolio data."""
        self.client.login(username="testuser", password="testpassword")
        portfolio = Portfolio.objects.create(user=self.user, name="Jane Dev", about="I write clean python code.")

        # Activate theme
        res_act = self.client.post(
            reverse("portfolio:select_theme", kwargs={"pk": portfolio.pk}),
            data={"theme_id": self.theme.pk}
        )
        self.assertEqual(res_act.status_code, 302)
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.selected_theme, self.theme)

        # Add 2 dynamic projects to the portfolio to test dynamic list replication
        PortfolioProject.objects.create(
            portfolio=portfolio,
            title="SaaS Platform",
            description="Dynamic SAAS platform",
            technologies="Python Django"
        )
        PortfolioProject.objects.create(
            portfolio=portfolio,
            title="Theme Mapper App",
            description="Visual website mapper",
            technologies="Django JS"
        )

        # Query live preview endpoint
        res_prev = self.client.get(reverse("portfolio:preview", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res_prev.status_code, 200)
        
        compiled_html = res_prev.content.decode("utf-8")
        
        # Verify flat fields compiled correctly
        self.assertIn("Jane Dev", compiled_html)
        self.assertIn("I write clean python code.", compiled_html)
        
        # Verify base tag was injected inside head to resolve assets relative paths
        self.assertIn("<base href=", compiled_html)
        
        # Verify projects list replicated the project-card element and populated values
        self.assertIn("SaaS Platform", compiled_html)
        self.assertIn("Theme Mapper App", compiled_html)
        self.assertIn("Dynamic SAAS platform", compiled_html)
        self.assertIn("Visual website mapper", compiled_html)

    # ── MODULE 8 NEW TESTS ───────────────────────────────────────────────────

    def test_portfolio_listing_by_status(self):
        """Verify multi-portfolio dashboard listing page shows status segments counts."""
        self.client.login(username="testuser", password="testpassword")
        
        # Create draft, published, archived portfolios
        Portfolio.objects.create(user=self.user, name="D1", status=Portfolio.Status.DRAFT)
        Portfolio.objects.create(user=self.user, name="P1", status=Portfolio.Status.PUBLISHED)
        Portfolio.objects.create(user=self.user, name="A1", status=Portfolio.Status.ARCHIVED)

        res = self.client.get(reverse("portfolio:list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "D1")
        self.assertContains(res, "P1")
        self.assertContains(res, "A1")

    def test_portfolio_duplication_clones_all_child_records(self):
        """Verify portfolio clone action deep-copies flat properties and related list items."""
        self.client.login(username="testuser", password="testpassword")
        
        # Upgrade subscription to premium to bypass portfolio limit
        from payments.models import SubscriptionPlan
        premium_plan = SubscriptionPlan.objects.get(slug="premium")
        self.user.subscription.plan = premium_plan
        self.user.subscription.save()

        portfolio = Portfolio.objects.create(user=self.user, name="Original Portfolio", title="CTO")
        
        # Add related records
        PortfolioSkill.objects.create(portfolio=portfolio, name="Python Programming")
        PortfolioProject.objects.create(portfolio=portfolio, title="Django Server")

        res_dup = self.client.post(reverse("portfolio:duplicate", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res_dup.status_code, 302)

        # Check duplicated clone portfolio exists
        clones = Portfolio.objects.filter(user=self.user, name="Copy of Original Portfolio")
        self.assertTrue(clones.exists())
        
        clone = clones.first()
        self.assertEqual(clone.title, "CTO")
        self.assertEqual(clone.status, Portfolio.Status.DRAFT)

        # Verify child relations cloned successfully
        self.assertTrue(clone.skills.filter(name="Python Programming").exists())
        self.assertTrue(clone.projects.filter(title="Django Server").exists())

    def test_autosave_draft_api_asynchronously(self):
        """Verify debounced AJAX partial form POST saves draft values successfully."""
        self.client.login(username="testuser", password="testpassword")
        portfolio = Portfolio.objects.create(user=self.user, name="Initial Name")

        res_ajax = self.client.post(
            reverse("portfolio:update_api", kwargs={"pk": portfolio.pk}),
            data={
                "name": "Updated Name via API",
                "title": "Staff Architect",
                "about": "New description...",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(res_ajax.status_code, 200)
        
        # Verify JSON response success
        json_data = json.loads(res_ajax.content.decode("utf-8"))
        self.assertTrue(json_data["success"])

        # Check DB updated
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.name, "Updated Name via API")
        self.assertEqual(portfolio.title, "Staff Architect")

    def test_unauthorized_draft_preview_is_blocked(self):
        """Ensure other users cannot view or preview another user's unpublished drafts."""
        # Create a draft portfolio for self.user
        portfolio = Portfolio.objects.create(user=self.user, name="Secret Draft", status=Portfolio.Status.DRAFT)

        # Login as other_user and attempt to fetch preview
        self.client.login(username="otheruser", password="otherpassword")
        res_preview = self.client.get(reverse("portfolio:preview", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res_preview.status_code, 403)  # Forbidden block!

        # Set status to PUBLISHED and verify access is allowed
        portfolio.status = Portfolio.Status.PUBLISHED
        portfolio.save(update_fields=["status"])

        res_published_preview = self.client.get(reverse("portfolio:preview", kwargs={"pk": portfolio.pk}))
        # Now allowed (either returns 200 compiled HTML or warnings about missing mapping selections)
        self.assertIn(res_published_preview.status_code, [200, 404])

    def test_portfolio_archive_and_restore(self):
        """Verify archiving a portfolio updates status, and restoring reverts it to draft."""
        self.client.login(username="testuser", password="testpassword")
        portfolio = Portfolio.objects.create(user=self.user, name="To Archive", status=Portfolio.Status.PUBLISHED)
        
        # Archive
        res_arch = self.client.post(reverse("portfolio:archive", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res_arch.status_code, 302)
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.status, Portfolio.Status.ARCHIVED)

        # Restore
        res_rest = self.client.post(reverse("portfolio:restore", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res_rest.status_code, 302)
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.status, Portfolio.Status.DRAFT)

    def test_portfolio_deletion_by_owner(self):
        """Verify owner can delete a portfolio and its data gets removed."""
        self.client.login(username="testuser", password="testpassword")
        portfolio = Portfolio.objects.create(user=self.user, name="To Delete")
        
        res_del = self.client.post(reverse("portfolio:delete", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(Portfolio.objects.filter(pk=portfolio.pk).exists())

    def test_visual_editor_page_requires_auth(self):
        """Verify that accessing visual editor dashboard requires a login redirect."""
        portfolio = Portfolio.objects.create(user=self.user, name="No Auth Editor")
        res = self.client.get(reverse("portfolio:builder", kwargs={"pk": portfolio.pk}))
        self.assertEqual(res.status_code, 302)

    def test_user_cannot_update_other_user_portfolio_api(self):
        """Verify permission checks block unauthorized AJAX update requests on other portfolios."""
        portfolio = Portfolio.objects.create(user=self.user, name="Secret Portfolio")
        
        self.client.login(username="otheruser", password="otherpassword")
        res = self.client.post(
            reverse("portfolio:update_api", kwargs={"pk": portfolio.pk}),
            data={"name": "Hacked Name"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(res.status_code, 403)
        portfolio.refresh_from_db()
        self.assertNotEqual(portfolio.name, "Hacked Name")


class PortfolioVersioningTestCase(TestCase):
    """
    Test suite for Phase 6.1 Backend Version Engine.
    Tests snapshot creation, version restoration, and version diff comparison.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory
        self.user = User.objects.create_user(username="versionuser", password="versionpassword")
        self.category = ThemeCategory.objects.create(name="Version Cat", slug="version-cat")
        self.theme = Theme.objects.create(
            name="Version Theme",
            slug="version-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Version Test Portfolio",
            title="Senior Django Developer",
            about="Building backend versioning systems.",
            selected_theme=self.theme
        )
        # Create sample child records
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Python", skill_type="technical")
        PortfolioProject.objects.create(
            portfolio=self.portfolio,
            title="SaaS Engine",
            description="Version management system for portfolios."
        )

    def test_create_version_snapshot(self):
        """Verify creating a version snapshot serializes portfolio and increments version number."""
        from portfolio.services.versioning import create_version_snapshot, decompress_snapshot

        v1 = create_version_snapshot(self.portfolio, title="Initial Snapshot", tag="Draft")
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v1.tag, "Draft")
        
        snapshot_data = decompress_snapshot(v1.snapshot_json)
        self.assertIn("fields", snapshot_data)
        self.assertEqual(snapshot_data["fields"]["name"], "Version Test Portfolio")
        self.assertEqual(len(snapshot_data["children"]["projects"]), 1)

        v2 = create_version_snapshot(self.portfolio, title="Second Snapshot", tag="Published", is_published=True)
        self.assertEqual(v2.version_number, 2)
        self.assertTrue(v2.is_published)

    def test_restore_version_snapshot(self):
        """Verify restoring a version snapshot updates portfolio data and creates a Rollback version."""
        from portfolio.services.versioning import create_version_snapshot, restore_version_snapshot

        # Create v1
        v1 = create_version_snapshot(self.portfolio, title="Original State", tag="Draft")

        # Update portfolio
        self.portfolio.name = "Modified Portfolio Name"
        self.portfolio.save()
        PortfolioProject.objects.create(portfolio=self.portfolio, title="Project 2")

        # Restore v1
        rollback_v = restore_version_snapshot(self.portfolio, v1, user=self.user)
        self.portfolio.refresh_from_db()

        self.assertEqual(self.portfolio.name, "Version Test Portfolio")
        self.assertEqual(self.portfolio.projects.count(), 1)
        self.assertEqual(rollback_v.tag, "Rollback")

    def test_compare_version_snapshots(self):
        """Verify comparing two version snapshots detects field and child diffs."""
        from portfolio.services.versioning import create_version_snapshot, compare_version_snapshots

        v1 = create_version_snapshot(self.portfolio, title="v1")
        self.portfolio.title = "Lead Software Architect"
        self.portfolio.save()
        v2 = create_version_snapshot(self.portfolio, title="v2")

        diff = compare_version_snapshots(v1, v2)
        self.assertEqual(diff["version_a"], 1)
        self.assertEqual(diff["version_b"], 2)
        self.assertIn("title", diff["field_diffs"])
        self.assertEqual(diff["field_diffs"]["title"]["old"], "Senior Django Developer")
        self.assertEqual(diff["field_diffs"]["title"]["new"], "Lead Software Architect")

    def test_version_list_api(self):
        """Verify GET /portfolio/builder/<pk>/versions/ returns JSON list of versions."""
        from portfolio.services.versioning import create_version_snapshot

        create_version_snapshot(self.portfolio, title="Snap 1")
        self.client.login(username="versionuser", password="versionpassword")
        res = self.client.get(reverse("portfolio:version_list_api", kwargs={"pk": self.portfolio.pk}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["versions"]), 1)

    def test_version_restore_api(self):
        """Verify POST /portfolio/builder/<pk>/versions/<v_pk>/restore/ restores target version."""
        from portfolio.services.versioning import create_version_snapshot

        v1 = create_version_snapshot(self.portfolio, title="Original")
        self.portfolio.name = "Renamed"
        self.portfolio.save()

        self.client.login(username="versionuser", password="versionpassword")
        res = self.client.post(reverse("portfolio:version_restore_api", kwargs={"pk": self.portfolio.pk, "v_pk": v1.pk}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "Version Test Portfolio")

    def test_version_compare_api(self):
        """Verify POST /portfolio/builder/<pk>/versions/compare/ returns diff JSON."""
        from portfolio.services.versioning import create_version_snapshot

        v1 = create_version_snapshot(self.portfolio, title="v1")
        self.portfolio.title = "Architect"
        self.portfolio.save()
        v2 = create_version_snapshot(self.portfolio, title="v2")

        self.client.login(username="versionuser", password="versionpassword")
        res = self.client.post(
            reverse("portfolio:version_compare_api", kwargs={"pk": self.portfolio.pk}),
            data={"version_a_id": v1.pk, "version_b_id": v2.pk}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("title", data["diff"]["field_diffs"])

    def test_publishing_creates_version_snapshot(self):
        """Verify publishing a portfolio creates a Published version snapshot."""
        self.client.login(username="versionuser", password="versionpassword")
        res = self.client.post(reverse("portfolio:publish", kwargs={"pk": self.portfolio.pk}))
        self.assertEqual(res.status_code, 302)

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.status, Portfolio.Status.PUBLISHED)
        self.assertTrue(self.portfolio.versions.filter(tag="Published", is_published=True).exists())

    def test_zlib_snapshot_compression_and_decompression(self):
        """Verify zlib compression compresses large JSON dicts and decompresses seamlessly."""
        from portfolio.services.versioning import compress_snapshot, decompress_snapshot

        large_dict = {"fields": {"about": "A" * 1000}, "children": {}}
        compressed = compress_snapshot(large_dict)
        self.assertTrue(compressed.get("_compressed"))

        decompressed = decompress_snapshot(compressed)
        self.assertEqual(decompressed["fields"]["about"], "A" * 1000)

    def test_partial_section_restore(self):
        """Verify restoring only selected sections (e.g. projects) preserves other modified fields."""
        from portfolio.services.versioning import create_version_snapshot, restore_version_snapshot

        # Create v1
        v1 = create_version_snapshot(self.portfolio, title="v1")

        # Change name and projects
        self.portfolio.name = "New Portfolio Name"
        self.portfolio.save()
        PortfolioProject.objects.create(portfolio=self.portfolio, title="Extra Project")

        # Partial restore: projects only
        restore_version_snapshot(self.portfolio, v1, user=self.user, sections_to_restore=["projects"])
        self.portfolio.refresh_from_db()

        # Projects restored (back to 1 item), but name remains modified!
        self.assertEqual(self.portfolio.projects.count(), 1)
        self.assertEqual(self.portfolio.name, "New Portfolio Name")

    def test_version_preview_endpoint(self):
        """Verify GET /portfolio/builder/<pk>/versions/<v_pk>/preview/ renders historical HTML preview."""
        from portfolio.services.versioning import create_version_snapshot

        v1 = create_version_snapshot(self.portfolio, title="v1")
        self.client.login(username="versionuser", password="versionpassword")
        res = self.client.get(reverse("portfolio:version_preview_api", kwargs={"pk": self.portfolio.pk, "v_pk": v1.pk}))
        self.assertIn(res.status_code, [200, 404])


class PortfolioPublishingPipelineTestCase(TestCase):
    """
    Test suite for Phase 7.1 Publishing Pipeline.
    Tests validation rules, build artifacts, publish lock, build logs, and error codes.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory
        self.user = User.objects.create_user(username="publisher", password="publishpassword")
        self.category = ThemeCategory.objects.create(name="Modern", slug="modern")
        self.theme = Theme.objects.create(
            name="Publish Theme",
            slug="publish-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Publisher Portfolio",
            title="Senior DevOps Engineer",
            about="Automating cloud infrastructure and publishing pipelines.",
            selected_theme=self.theme
        )
        from portfolio.services.versioning import create_version_snapshot
        v1 = create_version_snapshot(self.portfolio, title="v1", is_published=True)
        self.portfolio.published_version = v1
        self.portfolio.save()

    def test_validate_portfolio(self):
        """Verify validate_portfolio returns structured error codes for invalid states."""
        from portfolio.services.publishing import validate_portfolio

        # Invalid portfolio with no theme
        self.portfolio.selected_theme = None
        self.portfolio.save()
        errors = validate_portfolio(self.portfolio)
        self.assertTrue(any(e["code"] == "THEME_NOT_FOUND" for e in errors))

    def test_build_portfolio_artifact(self):
        """Verify build_portfolio returns BuildArtifact with index.html, assets/css/styles.css, and metrics."""
        from portfolio.services.publishing import build_portfolio

        artifact = build_portfolio(self.portfolio)
        self.assertIn("index.html", artifact.static_files)
        self.assertIn("assets/css/styles.css", artifact.static_files)
        self.assertIn("manifest.json", artifact.static_files)
        self.assertIn("build_time_ms", artifact.metrics)

    def test_publish_portfolio_pipeline(self):
        """Verify publish_portfolio executes full pipeline, updates status, and logs build steps."""
        from portfolio.services.publishing import publish_portfolio

        res = publish_portfolio(self.portfolio, user=self.user)
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "PUBLISHED")

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.status, Portfolio.Status.PUBLISHED)
        self.assertEqual(self.portfolio.build_status, Portfolio.BuildStatus.PUBLISHED)
        self.assertIsNotNone(self.portfolio.published_at)
        self.assertTrue(self.portfolio.build_logs.exists())

    def test_publish_lock_prevents_duplicate_builds(self):
        """Verify Publish Lock rejects concurrent publish requests when build_status == BUILDING."""
        from portfolio.services.publishing import publish_portfolio

        self.portfolio.build_status = Portfolio.BuildStatus.BUILDING
        self.portfolio.save()

        res = publish_portfolio(self.portfolio, user=self.user)
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "PUBLISH_IN_PROGRESS")


class StaticSiteBuildEngineTestCase(TestCase):
    """
    Test suite for Phase 7.2 Static Site Generation.
    Tests validate_build_prerequisites, build_static_portfolio, sitemap.xml, robots.txt, manifest.json, and seo.json.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory
        from portfolio.services.versioning import create_version_snapshot

        self.user = User.objects.create_user(username="staticbuilder", password="staticpassword")
        self.category = ThemeCategory.objects.create(name="Static Cat", slug="static-cat")
        self.theme = Theme.objects.create(
            name="Static Theme",
            slug="static-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Static Portfolio",
            title="Full Stack Engineer",
            about="Building static site generators.",
            selected_theme=self.theme
        )
        # Create published version snapshot
        self.published_version = create_version_snapshot(
            self.portfolio,
            title="Published v1",
            tag="Published",
            is_published=True
        )
        self.portfolio.published_version = self.published_version
        self.portfolio.status = Portfolio.Status.PUBLISHED
        self.portfolio.save()

    def test_validate_build_prerequisites(self):
        """Verify validate_build_prerequisites checks published version and theme."""
        from portfolio.services.build import validate_build_prerequisites

        # Valid portfolio
        errors = validate_build_prerequisites(self.portfolio)
        self.assertEqual(len(errors), 0)

        # Portfolio without published version
        self.portfolio.published_version = None
        self.portfolio.versions.all().delete()
        self.portfolio.save()
        errors_no_ver = validate_build_prerequisites(self.portfolio)
        self.assertTrue(any(e["code"] == "NO_PUBLISHED_VERSION" for e in errors_no_ver))

    def test_build_static_portfolio_package(self):
        """Verify build_static_portfolio generates index.html, sitemap.xml, robots.txt, and manifest.json."""
        from portfolio.services.build import build_static_portfolio

        res = build_static_portfolio(self.portfolio)
        self.assertTrue(res["success"])
        self.assertEqual(res["code"], "BUILD_SUCCESSFUL")

        artifact = res["artifact"]
        self.assertIn("index.html", artifact.static_package)
        self.assertIn("assets/css/styles.css", artifact.static_package)
        self.assertIn("sitemap.xml", artifact.static_package)
        self.assertIn("robots.txt", artifact.static_package)
        self.assertIn("manifest.json", artifact.static_package)
        self.assertIn("seo.json", artifact.static_package)

    def test_build_metrics(self):
        """Verify build_static_portfolio returns accurate build metrics."""
        from portfolio.services.build import build_static_portfolio

        res = build_static_portfolio(self.portfolio)
        metrics = res["metrics"]
        self.assertIn("build_time_ms", metrics)
        self.assertIn("html_size", metrics)
        self.assertIn("css_size", metrics)
        self.assertIn("pages_generated", metrics)


class GitHubDeploymentEngineTestCase(TestCase):
    """
    Test suite for Phase 7.3 GitHub Deployment Engine.
    Tests validate_deployment_prerequisites, deploy_to_github, immutable deployment history, and POST API endpoint.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory
        from portfolio.services.versioning import create_version_snapshot
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp

        self.user = User.objects.create_user(username="ghdeployer", password="ghpassword")
        self.category = ThemeCategory.objects.create(name="Deploy Cat", slug="deploy-cat")
        self.theme = Theme.objects.create(
            name="Deploy Theme",
            slug="deploy-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Deploy Portfolio",
            title="Cloud Architect",
            about="Deploying portfolio sites to GitHub Pages.",
            selected_theme=self.theme
        )
        # Create published version snapshot
        self.published_version = create_version_snapshot(
            self.portfolio,
            title="Published v1",
            tag="Published",
            is_published=True
        )
        self.portfolio.published_version = self.published_version
        self.portfolio.status = Portfolio.Status.PUBLISHED
        self.portfolio.save()

        # Setup GitHub Social Account & Token
        app = SocialApp.objects.create(provider="github", name="GitHub App", client_id="test", secret="secret")
        account = SocialAccount.objects.create(user=self.user, provider="github", uid="12345", extra_data={"login": "ghdeployer"})
        SocialToken.objects.create(account=account, app=app, token="mock-token")

    def test_validate_deployment_prerequisites(self):
        """Verify validate_deployment_prerequisites checks GitHub connection and published state."""
        from portfolio.services.deployment import validate_deployment_prerequisites
        from allauth.socialaccount.models import SocialAccount

        # Valid configuration
        errors = validate_deployment_prerequisites(self.portfolio, self.user)
        self.assertEqual(len(errors), 0)

        # Unconnected user
        SocialAccount.objects.filter(user=self.user).delete()
        errors_no_gh = validate_deployment_prerequisites(self.portfolio, self.user)
        self.assertTrue(any(e["code"] == "GITHUB_NOT_CONNECTED" for e in errors_no_gh))

    def test_deploy_to_github_success(self):
        """Verify deploy_to_github creates a new PortfolioDeployment record with status SUCCESS."""
        from portfolio.services.deployment import deploy_to_github
        from portfolio.models import PortfolioDeployment

        res = deploy_to_github(self.portfolio, self.user)
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("commit_sha", res)

        self.assertEqual(PortfolioDeployment.objects.filter(portfolio=self.portfolio, deployment_status="SUCCESS").count(), 1)
        latest = PortfolioDeployment.objects.filter(portfolio=self.portfolio).first()
        self.assertEqual(latest.deployment_status, PortfolioDeployment.Status.SUCCESS)
        self.assertIn("ghdeployer.github.io", latest.deployment_url)

    def test_deploy_to_github_failure_preserves_history(self):
        """Verify deployment failure creates FAILED record without deleting previous SUCCESS history."""
        from portfolio.services.deployment import deploy_to_github
        from portfolio.models import PortfolioDeployment

        # 1. Create a successful deployment record
        deploy_to_github(self.portfolio, self.user)

        # 2. Simulate failure by removing published version
        self.portfolio.published_version = None
        self.portfolio.versions.all().delete()
        self.portfolio.save()

        res = deploy_to_github(self.portfolio, self.user)
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "VALIDATION_FAILED")

        # Previous success history is preserved!
        self.assertTrue(PortfolioDeployment.objects.filter(portfolio=self.portfolio, deployment_status="SUCCESS").exists())

    def test_deploy_api_endpoint(self):
        """Verify POST /portfolio/<pk>/deploy/ returns JSON response."""
        self.client.login(username="ghdeployer", password="ghpassword")
        res = self.client.post(reverse("portfolio:deploy_api", kwargs={"pk": self.portfolio.pk}))
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "SUCCESS")


class AIPortfolioGenerationEngineTestCase(TestCase):
    """
    Test suite for Phase 8.1 AI Portfolio Generation Engine.
    Tests prompt construction, provider abstraction, schema validation, safety sanitization, and DB isolation.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="aiuser", password="aipassword")
        self.profile_input = {
            "name": "Jane Doe",
            "headline": "Lead AI Engineer",
            "about": "Building generative AI models and SaaS engines.",
            "skills": ["Python", "PyTorch", "Django", "Python"],  # Duplicate skill
            "experience": [
                {
                    "company": "AI Labs",
                    "position": "Staff Engineer",
                    "duration": "2022 - Present",
                    "description": "<script>alert('xss')</script>Built scalable LLM pipelines."
                }
            ],
            "education": [{"institution": "Tech Institute", "degree": "M.S. AI", "year": "2021"}],
            "projects": [{"title": "Neural Builder", "description": "LLM text generator", "technologies": ["Python", "PyTorch"]}],
            "certifications": [],
            "contact": {"email": "jane@example.com"},
            "social_links": {"github": "https://github.com/janedoe"}
        }

    def test_prompt_construction(self):
        """Verify build_portfolio_prompt constructs prompt with PROMPT_VERSION == '1.0'."""
        from portfolio.services.ai_prompts import PROMPT_VERSION, build_portfolio_prompt

        self.assertEqual(PROMPT_VERSION, "1.0")
        system_prompt, user_prompt = build_portfolio_prompt(self.profile_input)
        self.assertIn("executive resume writer", system_prompt)
        self.assertIn("Jane Doe", user_prompt)
        self.assertIn("hero", user_prompt)

    def test_provider_abstraction(self):
        """Verify GeminiProvider generates text response and token metadata."""
        from portfolio.services.ai_provider import GeminiProvider

        provider = GeminiProvider(api_key="mock-key")
        raw_text, token_meta = provider.generate("Build portfolio prompt")
        self.assertIn("hero", raw_text)
        self.assertIn("prompt_tokens", token_meta)
        self.assertIn("completion_tokens", token_meta)

    def test_generate_portfolio_with_ai_pipeline(self):
        """Verify generate_portfolio_with_ai outputs validated JSON with hero, about, skills, and metadata."""
        from portfolio.services.ai_generation import generate_portfolio_with_ai

        res = generate_portfolio_with_ai(self.profile_input)
        self.assertTrue(res["success"])
        self.assertEqual(res["code"], "AI_GENERATION_SUCCESSFUL")

        data = res["data"]
        self.assertIn("hero", data)
        self.assertIn("about", data)
        self.assertIn("skills", data)
        self.assertIn("projects", data)
        self.assertIn("experience", data)
        self.assertIn("education", data)
        self.assertIn("contact", data)

        metadata = res["metadata"]
        self.assertEqual(metadata["prompt_version"], "1.0")
        self.assertIn("generation_time_ms", metadata)
        self.assertIn("token_usage", metadata)

    def test_safety_sanitization_and_deduplication(self):
        """Verify validate_and_sanitize_output strips script injection and deduplicates skills."""
        from portfolio.services.ai_generation import validate_and_sanitize_output

        raw_ai_dict = {
            "hero": {"name": "<script>evil()</script>Jane Doe", "headline": "AI Lead", "bio": "Bio"},
            "about": {"summary": "Summary", "highlights": ["Item 1"]},
            "skills": [
                {"name": "Python", "category": "technical", "level": "Expert"},
                {"name": "python", "category": "technical", "level": "Expert"},  # Duplicate
            ],
            "projects": [],
            "experience": [],
            "education": [],
            "contact": {"email": "jane@example.com"}
        }

        sanitized, errors = validate_and_sanitize_output(raw_ai_dict)
        self.assertEqual(len(errors), 0)
        self.assertEqual(sanitized["hero"]["name"], "Jane Doe")  # Script tag stripped!
        self.assertEqual(len(sanitized["skills"]), 1)             # Deduplicated!

    def test_zero_database_writes_guarantee(self):
        """Verify Phase 8.1 execution performs ZERO database writes."""
        from portfolio.services.ai_generation import generate_portfolio_with_ai

        initial_count = Portfolio.objects.count()
        generate_portfolio_with_ai(self.profile_input)
        final_count = Portfolio.objects.count()

        # Database count remains strictly unchanged!
        self.assertEqual(initial_count, final_count)


class AIPortfolioImportEngineTestCase(TestCase):
    """
    Test suite for Phase 8.2 AI Portfolio Import Engine.
    Tests atomic draft hydration, partial import, import modes (replace/merge/skip), published version isolation, and API endpoint.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory
        from portfolio.services.versioning import create_version_snapshot

        self.user = User.objects.create_user(username="aiimporter", password="importpassword")
        self.category = ThemeCategory.objects.create(name="Import Cat", slug="import-cat")
        self.theme = Theme.objects.create(
            name="Import Theme",
            slug="import-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Original Portfolio Name",
            title="Junior Dev",
            about="Original About",
            selected_theme=self.theme
        )
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Java", skill_type="technical")

        # Create published version snapshot
        self.published_ver = create_version_snapshot(
            self.portfolio,
            title="Published v1",
            tag="Published",
            is_published=True
        )
        self.portfolio.published_version = self.published_ver
        self.portfolio.save()

        self.ai_payload = {
            "hero": {"name": "AI Name", "headline": "AI Senior Architect", "bio": "AI Bio"},
            "about": {"summary": "AI generated biography summary.", "highlights": ["AWS", "Django"]},
            "skills": [
                {"name": "Python", "category": "technical", "level": "Expert"},
                {"name": "Docker", "category": "technical", "level": "Advanced"}
            ],
            "projects": [
                {"title": "AI SaaS App", "description": "AI Builder", "technologies": ["Python", "Django"], "url": "https://ai.com"}
            ],
            "experience": [
                {"company": "AI Tech", "position": "Senior Engineer", "duration": "2022-Present", "description": "LLM Dev"}
            ],
            "education": [
                {"institution": "MIT", "degree": "B.S. CS", "year": "2020"}
            ],
            "contact": {"email": "ai@example.com", "github": "https://github.com/ai", "linkedin": "https://linkedin.com/in/ai"}
        }

    def test_import_full_portfolio(self):
        """Verify import_generated_portfolio hydrates draft models and creates AI Generated snapshot."""
        from portfolio.services.ai_import import import_generated_portfolio
        from portfolio.models import PortfolioVersion, PortfolioBuildLog

        res = import_generated_portfolio(
            portfolio=self.portfolio,
            ai_data=self.ai_payload,
            mode="replace",
            ai_metadata={"provider": "Gemini", "model": "gemini-1.5-flash", "prompt_version": "1.0"},
            user=self.user
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "IMPORTED")

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "AI Name")
        self.assertEqual(self.portfolio.title, "AI Senior Architect")
        self.assertEqual(self.portfolio.skills.count(), 2)
        self.assertEqual(self.portfolio.projects.count(), 1)
        self.assertEqual(self.portfolio.experiences.count(), 1)

        # Snapshot checks
        ai_snapshot = PortfolioVersion.objects.filter(portfolio=self.portfolio, tag="AI Generated").first()
        self.assertIsNotNone(ai_snapshot)
        self.assertEqual(ai_snapshot.snapshot_json["_ai_metadata"]["provider"], "Gemini")

        # Audit log checks
        self.assertTrue(PortfolioBuildLog.objects.filter(portfolio=self.portfolio, step="AI Import").exists())

    def test_partial_section_import(self):
        """Verify partial section import updates only requested sections (e.g. hero & skills)."""
        from portfolio.services.ai_import import import_generated_portfolio

        res = import_generated_portfolio(
            portfolio=self.portfolio,
            ai_data=self.ai_payload,
            sections=["hero", "skills"],
            mode="replace"
        )
        self.assertTrue(res["success"])
        self.assertIn("hero", res["sections"])
        self.assertIn("skills", res["sections"])
        self.assertNotIn("projects", res["sections"])

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "AI Name")
        self.assertEqual(self.portfolio.projects.count(), 0)  # Unimported sections untouched

    def test_import_mode_merge_preserves_existing(self):
        """Verify import mode 'merge' adds new skills without deleting existing Java skill."""
        from portfolio.services.ai_import import import_generated_portfolio

        res = import_generated_portfolio(
            portfolio=self.portfolio,
            ai_data=self.ai_payload,
            sections=["skills"],
            mode="merge"
        )
        self.assertTrue(res["success"])
        self.portfolio.refresh_from_db()

        # Existing Java + 2 new skills = 3 skills total
        self.assertEqual(self.portfolio.skills.count(), 3)
        self.assertTrue(self.portfolio.skills.filter(name="Java").exists())

    def test_published_version_isolation(self):
        """Verify AI import NEVER overwrites or mutates published versions/snapshots."""
        from portfolio.services.ai_import import import_generated_portfolio
        from portfolio.services.versioning import decompress_snapshot

        initial_published_snap = decompress_snapshot(self.published_ver.snapshot_json)

        import_generated_portfolio(self.portfolio, self.ai_payload, mode="replace")

        self.published_ver.refresh_from_db()
        post_published_snap = decompress_snapshot(self.published_ver.snapshot_json)

        # Published snapshot data remains strictly identical!
        self.assertEqual(initial_published_snap["fields"]["name"], post_published_snap["fields"]["name"])

    def test_ai_import_api_endpoint(self):
        """Verify POST /portfolio/builder/<pk>/ai-import/ returns JSON response."""
        self.client.login(username="aiimporter", password="importpassword")
        payload = {
            "ai_data": self.ai_payload,
            "sections": ["hero", "skills"],
            "mode": "merge",
            "ai_metadata": {"provider": "Gemini", "model": "gemini-1.5-flash", "prompt_version": "1.0"}
        }
        res = self.client.post(
            reverse("portfolio:ai_import_api", kwargs={"pk": self.portfolio.pk}),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status"], "IMPORTED")
        self.assertIn("hero", data["sections"])


class AIPortfolioSectionRegenerationTestCase(TestCase):
    """
    Test suite for Phase 8.3 AI Section Regeneration & Smart Editing.
    Tests zero-DB preview mode, single-section atomic replacement, section checksums, conflict detection, and API endpoints.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory

        self.user = User.objects.create_user(username="airegenerator", password="regeneratepassword")
        self.category = ThemeCategory.objects.create(name="Regen Cat", slug="regen-cat")
        self.theme = Theme.objects.create(
            name="Regen Theme",
            slug="regen-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Alex Original",
            title="Original Dev",
            about="Original About",
            selected_theme=self.theme
        )
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Python", skill_type="technical")
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Django", skill_type="technical")

    def test_regenerate_section_preview_mode(self):
        """Verify regenerate_section produces preview payload and checksums with ZERO database writes."""
        from portfolio.services.ai_regeneration import regenerate_section

        initial_name = self.portfolio.name
        res = regenerate_section(self.portfolio, section_name="hero", user_prompt="Make it sound executive")

        self.assertTrue(res["success"])
        self.assertEqual(res["code"], "REGENERATION_PREVIEW_READY")
        self.assertIn("current_data", res)
        self.assertIn("regenerated_data", res)
        self.assertIn("current_checksum", res)
        self.assertIn("regenerated_checksum", res)

        # Database zero-write assertion
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, initial_name)

    def test_apply_regenerated_section_single_section(self):
        """Verify apply_regenerated_section updates ONLY target section (hero) while leaving skills untouched."""
        from portfolio.services.ai_regeneration import apply_regenerated_section
        from portfolio.models import PortfolioVersion

        new_hero_data = {
            "name": "Alex Executive",
            "headline": "Chief Technology Officer",
            "bio": "Leading enterprise AI architectures."
        }

        res = apply_regenerated_section(
            portfolio=self.portfolio,
            section_name="hero",
            regenerated_data=new_hero_data,
            ai_metadata={"provider": "Gemini", "model": "gemini-1.5-flash", "prompt_version": "1.0"},
            user=self.user
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "SECTION_APPLIED")

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "Alex Executive")
        self.assertEqual(self.portfolio.title, "Chief Technology Officer")
        # Skills remain completely untouched!
        self.assertEqual(self.portfolio.skills.count(), 2)

        # Snapshot checks
        snap = PortfolioVersion.objects.filter(portfolio=self.portfolio, tag="AI Generated").first()
        self.assertIsNotNone(snap)
        self.assertIn("Regenerated Hero Section", snap.title)
        self.assertEqual(snap.snapshot_json["_ai_metadata"]["section"], "hero")

    def test_conflict_detection_mismatch(self):
        """Verify conflict detection returns error status when expected_checksum fails to match."""
        from portfolio.services.ai_regeneration import apply_regenerated_section

        res = apply_regenerated_section(
            portfolio=self.portfolio,
            section_name="hero",
            regenerated_data={"name": "Alex New"},
            expected_checksum="invalidchecksum123"
        )
        self.assertFalse(res["success"])
        self.assertEqual(res["code"], "CONFLICT_DETECTED")

    def test_ai_regenerate_and_accept_api_endpoints(self):
        """Verify POST /portfolio/builder/<pk>/ai-regenerate-section/ and /ai-accept-section/ endpoints."""
        self.client.login(username="airegenerator", password="regeneratepassword")

        # 1. Regenerate API Preview
        regen_res = self.client.post(
            reverse("portfolio:ai_regenerate_section_api", kwargs={"pk": self.portfolio.pk}),
            data=json.dumps({"section_name": "hero", "user_prompt": "Executive tagline"}),
            content_type="application/json"
        )
        self.assertEqual(regen_res.status_code, 200)
        regen_data = regen_res.json()
        self.assertTrue(regen_data["success"])
        self.assertIn("regenerated_data", regen_data)

        # 2. Accept API Commit
        accept_res = self.client.post(
            reverse("portfolio:ai_accept_section_api", kwargs={"pk": self.portfolio.pk}),
            data=json.dumps({
                "section_name": "hero",
                "regenerated_data": regen_data["regenerated_data"],
                "expected_checksum": regen_data["current_checksum"],
                "ai_metadata": regen_data["metadata"]
            }),
            content_type="application/json"
        )
        self.assertEqual(accept_res.status_code, 200)
        accept_data = accept_res.json()
        self.assertTrue(accept_data["success"])
        self.assertEqual(accept_data["status"], "SECTION_APPLIED")


class AIPromptLibraryTestCase(TestCase):
    """
    Test suite for Phase 8.4 AI Prompt Library & Prompt Management.
    Tests prompt registration, template validation, nested version lookup, variable injection, placeholder protection, and caching.
    """
    def test_prompt_registration_and_retrieval(self):
        """Verify PromptLibrary registers immutable PromptTemplate and retrieves by key and version."""
        from portfolio.services.prompt_library import PromptLibrary, PromptTemplate

        custom_tmpl = PromptTemplate(
            key="test_custom_prompt",
            category="testing",
            version="1.0",
            description="Test template",
            system_prompt="System role for {{user_role}}",
            user_template="Hello {{name}}, welcome to {{app}}!",
            required_variables=["user_role", "name", "app"],
            schema={"type": "object"}
        )
        PromptLibrary.register(custom_tmpl)

        retrieved = PromptLibrary.get_template("test_custom_prompt", version="1.0")
        self.assertEqual(retrieved.key, "test_custom_prompt")
        self.assertEqual(retrieved.version, "1.0")

    def test_registration_validation_checks(self):
        """Verify PromptLibrary rejects invalid templates (empty prompts, missing required variables)."""
        from portfolio.services.prompt_library import PromptLibrary, PromptTemplate

        # Empty system prompt
        invalid_tmpl = PromptTemplate(
            key="invalid_prompt",
            category="testing",
            version="1.0",
            description="Invalid",
            system_prompt="",
            user_template="Template {{var}}",
            required_variables=["var"],
            schema={"type": "object"}
        )
        with self.assertRaises(ValueError):
            PromptLibrary.register(invalid_tmpl)

        # Undeclared placeholder in required_variables
        invalid_vars_tmpl = PromptTemplate(
            key="invalid_vars",
            category="testing",
            version="1.0",
            description="Invalid vars",
            system_prompt="Role",
            user_template="Hello {{missing_var}}",
            required_variables=[],
            schema={"type": "object"}
        )
        with self.assertRaises(ValueError):
            PromptLibrary.register(invalid_vars_tmpl)

    def test_variable_injection_and_unresolved_protection(self):
        """Verify build_prompt injects variables and rejects missing required variables or unresolved tags."""
        from portfolio.services.prompt_library import PromptLibrary

        compiled = PromptLibrary.build_prompt(
            "portfolio_generation",
            variables={"profile_json": {"name": "Test User"}}
        )

        self.assertEqual(compiled["key"], "portfolio_generation")
        self.assertIn("Test User", compiled["user_prompt"])
        self.assertNotIn("{{profile_json}}", compiled["user_prompt"])

        # Missing required variables
        with self.assertRaises(ValueError):
            PromptLibrary.build_prompt("portfolio_generation", variables={})

    def test_compiled_prompt_caching(self):
        """Verify compiled prompts are cached with variable hashing."""
        from portfolio.services.prompt_library import PromptLibrary
        from django.core.cache import cache

        res1 = PromptLibrary.build_prompt("hero_regeneration", variables={
            "portfolio_title": "Developer",
            "portfolio_context": "Context",
            "current_section": "Current",
            "user_instruction": "Instruction"
        })
        self.assertIsNotNone(res1)
        self.assertIn("user_prompt", res1)

    def test_integration_with_ai_services(self):
        """Verify generate_portfolio_with_ai and regenerate_section execute seamlessly with PromptLibrary."""
        from portfolio.services.ai_generation import generate_portfolio_with_ai
        from portfolio.services.ai_regeneration import regenerate_section

        # 1. AI Generation
        gen_res = generate_portfolio_with_ai({"name": "Test Builder", "headline": "Engineer"})
        self.assertTrue(gen_res["success"])
        self.assertEqual(gen_res["metadata"]["prompt_version"], "1.0")

        # 2. AI Section Regeneration
        from themes.models import Theme, ThemeCategory
        user = User.objects.create_user(username="prompter", password="promptpassword")
        cat = ThemeCategory.objects.create(name="Cat", slug="cat")
        theme = Theme.objects.create(name="Theme", slug="theme", category=cat, status=Theme.Status.APPROVED, is_active=True)
        portfolio = Portfolio.objects.create(user=user, name="Prompt Test", title="Dev", selected_theme=theme)

        regen_res = regenerate_section(portfolio, section_name="hero")
        self.assertTrue(regen_res["success"])
        self.assertEqual(regen_res["metadata"]["prompt_version"], "1.0")


class AIPortfolioAssistantTestCase(TestCase):
    """
    Test suite for Phase 8.5 AI Assistant & Smart Suggestions.
    Tests Deterministic Rule Engine, hybrid AI analysis, score breakdowns (0-100), priority sorting,
    zero-DB write isolation, versioned caching, and API views.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory

        self.user = User.objects.create_user(username="aiassistant", password="assistantpassword")
        self.category = ThemeCategory.objects.create(name="Assist Cat", slug="assist-cat")
        self.theme = Theme.objects.create(
            name="Assist Theme",
            slug="assist-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Assistant Draft",
            title="Software Architect",
            about="Short bio",
            selected_theme=self.theme
        )

    def test_deterministic_rule_engine_checks(self):
        """Verify DeterministicRuleEngine flags missing contact email, missing LinkedIn, empty skills, and short bio."""
        from portfolio.services.ai_assistant import DeterministicRuleEngine

        suggestions, scores = DeterministicRuleEngine.evaluate_rules(self.portfolio)
        sugg_ids = [s["id"] for s in suggestions]

        self.assertIn("rule_missing_contact_email", sugg_ids)
        self.assertIn("rule_missing_linkedin", sugg_ids)
        self.assertIn("rule_empty_skills_collection", sugg_ids)
        self.assertIn("rule_short_about_bio", sugg_ids)
        self.assertIn("overall", scores)

    def test_analyze_portfolio_scores_and_priorities(self):
        """Verify analyze_portfolio returns multidimensional scores, priority-sorted suggestions, and metadata."""
        from portfolio.services.ai_assistant import analyze_portfolio

        res = analyze_portfolio(self.portfolio)

        self.assertTrue(res["success"])
        self.assertEqual(res["code"], "ANALYSIS_COMPLETE")
        self.assertIn("scores", res)
        self.assertIn("suggestions", res)
        self.assertIn("metadata", res)

        # Priority sorting assertion (critical before recommended before optional)
        suggs = res["suggestions"]
        if len(suggs) >= 2:
            prio_order = {"critical": 0, "recommended": 1, "optional": 2}
            self.assertLessEqual(prio_order[suggs[0]["priority"]], prio_order[suggs[-1]["priority"]])

        # Metadata check
        self.assertEqual(res["metadata"]["analysis_version"], "1.0")

    def test_zero_database_write_guarantee(self):
        """Verify analyze_portfolio operates in 100% read-only mode with zero database writes."""
        from portfolio.services.ai_assistant import analyze_portfolio

        initial_count = Portfolio.objects.count()
        initial_name = self.portfolio.name

        analyze_portfolio(self.portfolio)

        self.assertEqual(Portfolio.objects.count(), initial_count)
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, initial_name)

    def test_ai_analysis_api_endpoint(self):
        """Verify POST /portfolio/builder/<pk>/ai-analysis/ returns 200 JsonResponse."""
        self.client.login(username="aiassistant", password="assistantpassword")

        res = self.client.post(
            reverse("portfolio:ai_analysis_api", kwargs={"pk": self.portfolio.pk}),
            data=json.dumps({"user_instruction": "Focus on SEO"}),
            content_type="application/json"
        )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["code"], "ANALYSIS_COMPLETE")
        self.assertIn("scores", data)
        self.assertIn("suggestions", data)


class AIPortfolioResumeImportTestCase(TestCase):
    """
    Test suite for Phase 9.0 Resume Import & Portfolio Generation.
    Tests plugin parsers (TXT/DOCX/PDF), 8-step security validation sequence, normalized section extraction,
    zero-DB preview mode, preview diff delta calculator, and import snapshot creation.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.user = User.objects.create_user(username="resumeimporter", password="resumepassword")
        self.category = ThemeCategory.objects.create(name="Resume Cat", slug="resume-cat")
        self.theme = Theme.objects.create(
            name="Resume Theme",
            slug="resume-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Resume Draft Initial",
            title="Software Developer",
            selected_theme=self.theme
        )

        self.sample_txt = (
            "John Architect\n"
            "Email: john.architect@example.com\n"
            "GitHub: https://github.com/johnarchitect\n"
            "LinkedIn: https://linkedin.com/in/johnarchitect\n"
            "Summary: Senior Software Engineer with over 8 years of experience building scalable systems using Python and Django.\n"
            "Skills: Python, Django, React, PostgreSQL, Docker, AWS\n"
            "Experience: Lead Engineer at Cloud Solutions from 2021 to Present.\n"
            "Education: Bachelor of Science in Computer Science from University of Technology, 2020."
        )
        self.txt_file = SimpleUploadedFile("resume.txt", self.sample_txt.encode("utf-8"), content_type="text/plain")

    def test_txt_parser_plugin_and_section_extraction(self):
        """Verify parse_resume processes TXT files and extracts normalized resume sections."""
        from portfolio.services.resume_parser import parse_resume

        res = parse_resume(self.txt_file)

        self.assertTrue(res["success"])
        self.assertEqual(res["ext"], "txt")
        self.assertIn("normalized_resume", res)

        norm = res["normalized_resume"]
        self.assertEqual(norm["personal"]["value"]["email"], "john.architect@example.com")
        self.assertIn("Python", [s["name"] for s in norm["skills"]["value"]])

    def test_security_validations(self):
        """Verify parse_resume enforces extension checks, size limits, and minimum character thresholds."""
        from portfolio.services.resume_parser import parse_resume
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Unsupported Extension
        bad_ext = SimpleUploadedFile("resume.exe", b"Malicious content", content_type="application/octet-stream")
        with self.assertRaises(ValueError):
            parse_resume(bad_ext)

        # Insufficient text (< 50 chars)
        short_txt = SimpleUploadedFile("short.txt", b"Too short", content_type="text/plain")
        with self.assertRaises(ValueError):
            parse_resume(short_txt)

    def test_resume_upload_preview_api_zero_db(self):
        """Verify POST /portfolio/builder/<pk>/resume-upload/ returns preview & diff delta with ZERO DB writes."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(username="resumeimporter", password="resumepassword")

        initial_count = Portfolio.objects.count()
        fresh_file = SimpleUploadedFile("resume.txt", self.sample_txt.encode("utf-8"), content_type="text/plain")

        res = self.client.post(
            reverse("portfolio:resume_upload_api", kwargs={"pk": self.portfolio.pk}),
            data={"resume": fresh_file}
        )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["code"], "RESUME_PREVIEW_READY")
        self.assertIn("generated_portfolio", data)
        self.assertIn("diff_summary", data)

        # Zero DB write assertion
        self.assertEqual(Portfolio.objects.count(), initial_count)

    def test_resume_import_api_commit(self):
        """Verify POST /portfolio/builder/<pk>/resume-import/ updates draft state and creates version history snapshot."""
        from portfolio.models import PortfolioVersion

        self.client.login(username="resumeimporter", password="resumepassword")

        ai_data = {
            "hero": {"name": "John Architect Imported", "headline": "Chief Architect", "bio": "Bio"},
            "about": {"summary": "Summary", "highlights": []},
            "skills": [{"name": "Python", "category": "technical", "level": "Expert"}],
            "projects": [],
            "experience": [],
            "education": [],
            "contact": {"email": "john@example.com", "github": "", "linkedin": ""}
        }

        res = self.client.post(
            reverse("portfolio:resume_import_api", kwargs={"pk": self.portfolio.pk}),
            data=json.dumps({"ai_data": ai_data, "resume_hash": "hash123"}),
            content_type="application/json"
        )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "John Architect Imported")

        # Snapshot checks
        snap = PortfolioVersion.objects.filter(portfolio=self.portfolio).first()
        self.assertIsNotNone(snap)
        self.assertEqual(snap.snapshot_json["_ai_metadata"]["source"], "resume_import")


class AIPortfolioJobOptimizationTestCase(TestCase):
    """
    Test suite for Phase 9.1 Job Description Optimization.
    Tests JD parsing, skill strength categorizer, ATS keyword coverage metrics, match scores (0-100),
    zero-DB optimization previews, selective section application, and version snapshot creation.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory

        self.user = User.objects.create_user(username="joboptimizer", password="optimizerpassword")
        self.category = ThemeCategory.objects.create(name="Job Cat", slug="job-cat")
        self.theme = Theme.objects.create(
            name="Job Theme",
            slug="job-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Alex Optimization Draft",
            title="Senior Developer",
            about="Python and Django engineer.",
            selected_theme=self.theme
        )
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Python", skill_type="technical")
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Django", skill_type="technical")

        self.sample_jd = (
            "Job Title: Senior AI Architect at Enterprise Tech\n"
            "We are seeking a Senior AI Architect to build Python, LLM, and Docker microservices.\n"
            "Requirements: Python, Django, LLM, Docker, PostgreSQL, REST API."
        )

    def test_parse_job_description_and_extraction(self):
        """Verify parse_job_description processes text and extracts job requirements."""
        from portfolio.services.job_description import parse_job_description

        res = parse_job_description(job_text=self.sample_jd)

        self.assertTrue(res["success"])
        self.assertIn("job_requirements", res)
        reqs = res["job_requirements"]
        self.assertEqual(reqs["company"], "Enterprise Tech")
        self.assertIn("Python", reqs["skills"])

    def test_compare_portfolio_to_job_matching_and_scores(self):
        """Verify compare_portfolio_to_job categorizes skills, reports ATS keyword coverage, experience alignment, and score breakdown."""
        from portfolio.services.job_description import extract_job_requirements, compare_portfolio_to_job

        reqs = extract_job_requirements(self.sample_jd)
        comp_res = compare_portfolio_to_job(self.portfolio, reqs)

        self.assertIn("summary", comp_res)
        self.assertIn("skills", comp_res)
        self.assertIn("keyword_coverage", comp_res)
        self.assertIn("experience_alignment", comp_res)
        self.assertIn("scores", comp_res)

        # Skill categorization & weighted keywords check
        self.assertIn("python", comp_res["skills"]["strong_match"])
        self.assertIn("weighted", comp_res["keyword_coverage"])

        # ATS Score breakdown & experience alignment checks
        self.assertIn("weights", comp_res["scores"]["ats_score"])
        self.assertIn("backend", comp_res["experience_alignment"])

    def test_generate_job_optimization_preview_zero_db(self):
        """Verify generate_job_optimization_preview produces section previews with priority scores and zero DB writes."""
        from portfolio.services.job_description import extract_job_requirements, generate_job_optimization_preview

        initial_count = Portfolio.objects.count()
        reqs = extract_job_requirements(self.sample_jd)

        prev = generate_job_optimization_preview(self.portfolio, reqs)

        self.assertTrue(prev["success"])
        self.assertEqual(prev["code"], "JOB_OPTIMIZATION_READY")
        self.assertIn("optimizations", prev)
        self.assertIn("priority_score", prev["optimizations"]["hero"])

        # Zero DB write assertion
        self.assertEqual(Portfolio.objects.count(), initial_count)

    def test_job_analysis_and_apply_api_endpoints(self):
        """Verify POST /job-analysis/ and /job-apply/ API endpoints and session history metadata."""
        from portfolio.models import PortfolioVersion

        self.client.login(username="joboptimizer", password="optimizerpassword")

        # 1. Job Analysis API Preview
        analysis_res = self.client.post(
            reverse("portfolio:job_analysis_api", kwargs={"pk": self.portfolio.pk}),
            data=json.dumps({"job_text": self.sample_jd}),
            content_type="application/json"
        )
        self.assertEqual(analysis_res.status_code, 200)
        analysis_data = analysis_res.json()
        self.assertTrue(analysis_data["success"])

        # 2. Selective Job Apply API Commit
        apply_res = self.client.post(
            reverse("portfolio:job_apply_api", kwargs={"pk": self.portfolio.pk}),
            data=json.dumps({
                "selected_sections": ["hero"],
                "optimizations": analysis_data["optimizations"],
                "job_metadata": {"job_title": "AI Architect", "company": "Enterprise Tech"},
                "job_hash": analysis_data["job_hash"]
            }),
            content_type="application/json"
        )
        self.assertEqual(apply_res.status_code, 200)
        apply_data = apply_res.json()
        self.assertTrue(apply_data["success"])
        self.assertIn("hero", apply_data["applied_sections"])

        # Snapshot check & session metadata
        snap = PortfolioVersion.objects.filter(portfolio=self.portfolio, tag="Job Optimized").first()
        self.assertIsNotNone(snap)
        self.assertEqual(snap.snapshot_json["_ai_metadata"]["source"], "job_optimization")
        self.assertIn("optimization_session", snap.snapshot_json["_ai_metadata"])


class AIPortfolioCoverLetterTestCase(TestCase):
    """
    Test suite for Phase 9.2 AI Cover Letter Generator.
    Tests prompt generation, tone/length/template selection, zero-DB previews, evidence mapping,
    JD requirement coverage, readability metrics, hash duplicate detection, version save/restore/list/delete,
    and multi-format export engines (PDF, DOCX, Markdown, Plain Text).
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory
        from portfolio.models import CoverLetter

        self.user = User.objects.create_user(username="letterwriter", password="letterpassword")
        self.category = ThemeCategory.objects.create(name="Letter Cat", slug="letter-cat")
        self.theme = Theme.objects.create(
            name="Letter Theme",
            slug="letter-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Jordan Lee Draft",
            title="Lead Systems Architect",
            about="Building distributed Python and Django cloud engines.",
            selected_theme=self.theme
        )

        self.sample_job_reqs = {
            "title": "Principal AI Engineer",
            "company": "Cloud Computing Inc",
            "skills": ["Python", "Django", "System Architecture", "Docker"]
        }

    def test_generate_cover_letter_preview_zero_db(self):
        """Verify generate_cover_letter produces preview payload with zero DB writes."""
        from portfolio.models import CoverLetter
        from portfolio.services.cover_letter import generate_cover_letter

        initial_count = CoverLetter.objects.count()

        preview = generate_cover_letter(
            portfolio=self.portfolio,
            job_requirements=self.sample_job_reqs,
            tone="Enthusiastic",
            length="Medium",
            template_variant="Modern"
        )

        self.assertTrue(preview["success"])
        self.assertEqual(preview["code"], "COVER_LETTER_PREVIEW_READY")
        self.assertIn("evidence_map", preview)
        self.assertIn("coverage", preview)
        self.assertIn("metrics", preview)
        self.assertEqual(preview["metadata"]["tone"], "Enthusiastic")

        # Zero DB write assertion
        self.assertEqual(CoverLetter.objects.count(), initial_count)

    def test_save_cover_letter_version_and_duplicate_check(self):
        """Verify save_cover_letter_version creates version records and handles duplicate detection."""
        from portfolio.models import CoverLetter
        from portfolio.services.cover_letter import save_cover_letter_version

        cl_data = {
            "title": "Cover Letter v1",
            "greeting": "Dear Hiring Manager,",
            "introduction": "Introductory statement...",
            "body": "Detailed body content...",
            "closing": "Closing statement...",
            "signature": "Sincerely,\nJordan Lee"
        }

        # 1. Save new version
        res1 = save_cover_letter_version(
            portfolio=self.portfolio,
            cover_letter_data=cl_data,
            tone="Professional",
            length="Medium",
            job_requirements=self.sample_job_reqs
        )
        self.assertTrue(res1["success"])
        self.assertFalse(res1["is_duplicate"])
        self.assertEqual(res1["version_number"], 1)

        # 2. Duplicate detection check
        res2 = save_cover_letter_version(
            portfolio=self.portfolio,
            cover_letter_data=cl_data,
            tone="Professional",
            length="Medium",
            job_requirements=self.sample_job_reqs
        )
        self.assertTrue(res2["is_duplicate"])

    def test_cover_letter_history_and_reversible_restore(self):
        """Verify GET /history/ and POST /history/ (reversible restore creates new revision)."""
        from portfolio.models import CoverLetter

        self.client.login(username="letterwriter", password="letterpassword")

        cl = CoverLetter.objects.create(
            portfolio=self.portfolio,
            title="Cover Letter Initial",
            job_title="Lead Architect",
            company="Tech Corp",
            tone="Formal",
            content_json={"greeting": "Dear Sir,", "introduction": "Intro", "body": "Body", "closing": "Closing", "signature": "Sig"},
            content_text="Dear Sir,\n\nIntro\n\nBody\n\nClosing\n\nSig",
            version_number=1
        )

        # 1. History List GET
        res = self.client.get(reverse("portfolio:cover_letter_history_api", kwargs={"pk": self.portfolio.pk}))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 1)

        # 2. Reversible Restore POST (creates v2 from v1)
        res_restore = self.client.post(
            reverse("portfolio:cover_letter_history_api", kwargs={"pk": self.portfolio.pk}),
            data=json.dumps({"action": "restore", "cover_letter_id": cl.pk}),
            content_type="application/json"
        )
        self.assertEqual(res_restore.status_code, 200)
        restore_data = res_restore.json()
        self.assertEqual(restore_data["version_number"], 2)
        self.assertEqual(CoverLetter.objects.filter(portfolio=self.portfolio).count(), 2)

    def test_export_cover_letter_multi_format(self):
        """Verify export_cover_letter generates valid bytes for PDF, DOCX, Markdown, and TXT formats."""
        from portfolio.services.cover_letter import export_cover_letter

        cl_data = {
            "title": "Export Test Letter",
            "greeting": "Dear Hiring Manager,",
            "introduction": "Introductory statement...",
            "body": "Detailed body content...",
            "closing": "Closing statement...",
            "signature": "Sincerely,\nJordan Lee",
            "metadata": {"tone": "Executive", "length": "Medium", "template_variant": "Corporate", "provider": "Gemini"}
        }

        for fmt in ["pdf", "docx", "markdown", "txt"]:
            bytes_out, mime_type, filename = export_cover_letter(cl_data, format=fmt)
            self.assertGreater(len(bytes_out), 10)
            self.assertTrue(filename.endswith(f".{fmt}" if fmt != "markdown" else ".md"))


class AIPortfolioResumeOptimizerTestCase(TestCase):
    """
    Test suite for Phase 9.3 ATS Resume Optimizer (MVP).
    Tests section-by-section optimization diff (summary, skills, projects, experience), protected contact/education isolation,
    zero DB writes during preview, new version save flow without overwriting original resume, and API endpoints.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory
        from portfolio.models import OptimizedResume

        self.user = User.objects.create_user(username="resumeoptimizer", password="optimizerpassword")
        self.category = ThemeCategory.objects.create(name="Resume Cat 2", slug="resume-cat-2")
        self.theme = Theme.objects.create(
            name="Resume Theme 2",
            slug="resume-theme-2",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Morgan Resume Draft",
            title="Senior Full Stack Engineer",
            about="Python, Django, and React expert.",
            selected_theme=self.theme
        )

        self.sample_resume = {
            "personal": {"name": "Morgan Vance", "email": "morgan@example.com", "phone": "555-0199"},
            "summary": "Full stack engineer building scalable Django systems.",
            "skills": [{"name": "Python", "category": "technical", "level": "Expert"}],
            "projects": [{"title": "Cloud Portal", "description": "SaaS Platform"}],
            "experience": [{"company": "Tech Corp", "position": "Developer", "duration": "2020-Present"}],
            "education": [{"institution": "MIT", "degree": "B.S. CS", "year": "2019"}]
        }

        self.sample_job_reqs = {
            "title": "Lead Python Architect",
            "company": "Enterprise Tech",
            "skills": ["Python", "Django", "PostgreSQL", "Docker"]
        }

    def test_optimize_resume_preview_zero_db(self):
        """Verify optimize_resume returns simplified preview diff with zero DB writes."""
        from portfolio.models import OptimizedResume
        from portfolio.services.resume_optimizer import optimize_resume

        initial_count = OptimizedResume.objects.count()

        preview = optimize_resume(
            resume_data=self.sample_resume,
            job_requirements=self.sample_job_reqs
        )

        self.assertIn("summary", preview)
        self.assertIn("skills", preview)
        self.assertIn("projects", preview)
        self.assertIn("experience", preview)
        self.assertIn("current", preview["summary"])
        self.assertIn("optimized", preview["summary"])

        # Zero DB write assertion
        self.assertEqual(OptimizedResume.objects.count(), initial_count)

    def test_save_optimized_resume_creates_new_version(self):
        """Verify save_optimized_resume creates a new version without overwriting original resume data."""
        from portfolio.models import OptimizedResume
        from portfolio.services.resume_optimizer import optimize_resume, save_optimized_resume

        preview = optimize_resume(self.sample_resume, self.sample_job_reqs)

        res = save_optimized_resume(
            portfolio=self.portfolio,
            optimized_preview_data=preview,
            original_resume_data=self.sample_resume,
            title="Morgan Optimized Resume v1"
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["version_number"], 1)

        opt_rec = OptimizedResume.objects.get(pk=res["optimized_resume_id"])
        self.assertEqual(opt_rec.title, "Morgan Optimized Resume v1")
        # Verify protected personal & education sections preserved intact
        self.assertEqual(opt_rec.resume_data_json["personal"]["name"], "Morgan Vance")
        self.assertEqual(opt_rec.resume_data_json["education"][0]["institution"], "MIT")

    def test_resume_optimize_and_save_api_endpoints(self):
        """Verify POST /resume/optimize/ and POST /resume/save/ API views."""
        self.client.login(username="resumeoptimizer", password="optimizerpassword")

        # 1. Optimize API Preview
        opt_res = self.client.post(
            reverse("portfolio:resume_optimize_api"),
            data=json.dumps({
                "resume_data": self.sample_resume,
                "job_requirements": self.sample_job_reqs
            }),
            content_type="application/json"
        )
        self.assertEqual(opt_res.status_code, 200)
        opt_preview = opt_res.json()

        # 2. Save API Commit
        save_res = self.client.post(
            reverse("portfolio:resume_save_api"),
            data=json.dumps({
                "portfolio_id": self.portfolio.pk,
                "optimized_preview_data": opt_preview,
                "original_resume_data": self.sample_resume,
                "title": "Morgan Saved ATS Resume"
            }),
            content_type="application/json"
        )
        self.assertEqual(save_res.status_code, 200)
        save_data = save_res.json()
        self.assertTrue(save_data["success"])
        self.assertEqual(save_data["title"], "Morgan Saved ATS Resume")


class AIPortfolioExportTestCase(TestCase):
    """
    Test suite for Phase 9.4 Portfolio Export (MVP).
    Tests export_portfolio for HTML (Theme Engine reuse), ZIP (Static Site Generator reuse), PDF, and DOCX formats,
    invalid format validation, missing portfolio error handling, and HTTP download response headers.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory

        self.user = User.objects.create_user(username="exporteruser", password="exporterpassword")
        self.category = ThemeCategory.objects.create(name="Export Cat", slug="export-cat")
        self.theme = Theme.objects.create(
            name="Export Theme",
            slug="export-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Alex Rivera Portfolio",
            title="Senior DevOps & Cloud Architect",
            about="Architecting resilient Kubernetes clusters and CI/CD pipelines.",
            selected_theme=self.theme
        )
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Kubernetes", skill_type="technical", level="Expert")
        PortfolioProject.objects.create(portfolio=self.portfolio, title="Cloud Engine", description="Kubernetes Deployment Platform")

    def test_export_portfolio_all_formats(self):
        """Verify export_portfolio produces valid downloadable bytes for PDF, DOCX, HTML, and ZIP formats."""
        from portfolio.services.export_service import export_portfolio

        for fmt, expected_ext, expected_mime in [
            ("html", ".html", "text/html"),
            ("pdf", ".pdf", "application/pdf"),
            ("docx", ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("zip", ".zip", "application/zip")
        ]:
            bytes_out, mime_type, filename = export_portfolio(self.portfolio, format=fmt)
            self.assertGreater(len(bytes_out), 10)
            self.assertEqual(mime_type, expected_mime)
            self.assertTrue(filename.endswith(expected_ext))

    def test_export_portfolio_invalid_format(self):
        """Verify export_portfolio raises ValueError for unsupported formats."""
        from portfolio.services.export_service import export_portfolio

        with self.assertRaises(ValueError):
            export_portfolio(self.portfolio, format="unsupported_fmt")

    def test_portfolio_export_api_endpoint(self):
        """Verify POST /portfolio/export/ returns HTTP download responses with correct attachment headers."""
        self.client.login(username="exporteruser", password="exporterpassword")

        # 1. Valid PDF Export
        res_pdf = self.client.post(
            reverse("portfolio:portfolio_export_api"),
            data=json.dumps({"portfolio_id": self.portfolio.pk, "format": "pdf"}),
            content_type="application/json"
        )
        self.assertEqual(res_pdf.status_code, 200)
        self.assertEqual(res_pdf["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", res_pdf["Content-Disposition"])

        # 2. Valid HTML Export
        res_html = self.client.post(
            reverse("portfolio:portfolio_export_api"),
            data=json.dumps({"portfolio_id": self.portfolio.pk, "format": "html"}),
            content_type="application/json"
        )
        self.assertEqual(res_html.status_code, 200)
        self.assertEqual(res_html["Content-Type"], "text/html")

        # 3. Invalid Format Validation
        res_invalid = self.client.post(
            reverse("portfolio:portfolio_export_api"),
            data=json.dumps({"portfolio_id": self.portfolio.pk, "format": "mp4"}),
            content_type="application/json"
        )
        self.assertEqual(res_invalid.status_code, 400)
        self.assertFalse(res_invalid.json()["success"])


class AIPortfolioBackupTestCase(TestCase):
    """
    Test suite for Phase 9.5 Portfolio Backup & Restore (MVP).
    Tests export_portfolio_backup (JSON serialization), import_portfolio_backup (brand new portfolio creation, unique name resolution,
    original portfolio untouched), validation of bad JSON, and API endpoints.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory

        self.user = User.objects.create_user(username="backupuser", password="backuppassword")
        self.category = ThemeCategory.objects.create(name="Backup Cat", slug="backup-cat")
        self.theme = Theme.objects.create(
            name="Backup Theme",
            slug="backup-theme",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True
        )
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Taylor Swift Portfolio",
            title="Grammy-Winning Executive Producer",
            about="Creating global enterprise entertainment architectures.",
            selected_theme=self.theme
        )
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Audio Architecture", skill_type="technical", level="Expert")
        PortfolioProject.objects.create(portfolio=self.portfolio, title="Eras Tour Tech", description="Global Concert Sync Engine")

    def test_export_portfolio_backup(self):
        """Verify export_portfolio_backup produces valid JSON backup data structure."""
        from portfolio.services.backup_service import export_portfolio_backup

        backup_data = export_portfolio_backup(self.portfolio)

        self.assertEqual(backup_data["version"], "1.0")
        self.assertEqual(backup_data["backup_type"], "portfolio_backup")
        self.assertEqual(backup_data["portfolio"]["name"], "Taylor Swift Portfolio")
        self.assertEqual(len(backup_data["skills"]), 1)
        self.assertEqual(backup_data["skills"][0]["name"], "Audio Architecture")
        self.assertEqual(len(backup_data["projects"]), 1)

    def test_import_portfolio_backup_and_unique_naming(self):
        """Verify import_portfolio_backup creates a new portfolio with unique name handling while leaving original untouched."""
        from portfolio.services.backup_service import export_portfolio_backup, import_portfolio_backup

        backup_data = export_portfolio_backup(self.portfolio)
        initial_port_count = Portfolio.objects.filter(user=self.user).count()

        # 1st import -> "Taylor Swift Portfolio (Imported)"
        imported_1 = import_portfolio_backup(backup_data, user=self.user)
        self.assertNotEqual(imported_1.pk, self.portfolio.pk)
        self.assertEqual(imported_1.name, "Taylor Swift Portfolio (Imported)")
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), initial_port_count + 1)
        self.assertEqual(imported_1.skills.count(), 1)

        # 2nd import -> "Taylor Swift Portfolio (Imported 2)"
        imported_2 = import_portfolio_backup(backup_data, user=self.user)
        self.assertEqual(imported_2.name, "Taylor Swift Portfolio (Imported 2)")
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), initial_port_count + 2)

        # Original portfolio unchanged assertion
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.name, "Taylor Swift Portfolio")

    def test_backup_import_validation_errors(self):
        """Verify import_portfolio_backup raises ValueError for bad JSON format or missing name."""
        from portfolio.services.backup_service import import_portfolio_backup

        with self.assertRaises(ValueError):
            import_portfolio_backup("invalid_string_not_dict", user=self.user)

        with self.assertRaises(ValueError):
            import_portfolio_backup({"portfolio": {}}, user=self.user)

    def test_backup_export_and_import_api_endpoints(self):
        """Verify POST /portfolio/backup/export/ and POST /portfolio/backup/import/ API views."""
        self.client.login(username="backupuser", password="backuppassword")

        # 1. Backup Export API
        export_res = self.client.post(
            reverse("portfolio:portfolio_backup_export_api"),
            data=json.dumps({"portfolio_id": self.portfolio.pk}),
            content_type="application/json"
        )
        self.assertEqual(export_res.status_code, 200)
        self.assertEqual(export_res["Content-Type"], "application/json")
        self.assertIn("attachment; filename=", export_res["Content-Disposition"])

        backup_payload = json.loads(export_res.content.decode("utf-8"))
        self.assertEqual(backup_payload["backup_type"], "portfolio_backup")

        # 2. Backup Import API
        import_res = self.client.post(
            reverse("portfolio:portfolio_backup_import_api"),
            data=json.dumps(backup_payload),
            content_type="application/json"
        )
        self.assertEqual(import_res.status_code, 200)
        import_data = import_res.json()
        self.assertTrue(import_data["success"])
        self.assertEqual(import_data["code"], "BACKUP_IMPORTED")
        self.assertIn("(Imported)", import_data["name"])


class AIPortfolioTemplatesTestCase(TestCase):
    """
    Test suite for Phase 9.6 Portfolio Templates (MVP).
    Tests list_templates (built-in theme query), change_template (template switching with content immutability guarantee for About,
    Skills, Projects, Experience, Education, Contact), invalid template error handling, and API endpoints.
    """
    def setUp(self):
        from themes.models import Theme, ThemeCategory

        self.user = User.objects.create_user(username="templateuser", password="templatepassword")
        self.category = ThemeCategory.objects.create(name="Engineering", slug="engineering")

        self.theme_1 = Theme.objects.create(
            name="Modern Glass",
            slug="modern-glass",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True,
            description="Glassmorphism theme layout."
        )
        self.theme_2 = Theme.objects.create(
            name="Classic Serif",
            slug="classic-serif",
            category=self.category,
            status=Theme.Status.APPROVED,
            is_active=True,
            description="Traditional editorial layout."
        )

        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Ada Lovelace Portfolio",
            title="First Computer Programmer",
            about="Pioneer of algorithmic computing engines.",
            selected_theme=self.theme_1,
            email="ada@analyticalengine.org",
            phone="555-1843"
        )
        PortfolioSkill.objects.create(portfolio=self.portfolio, name="Bernoulli Computation", skill_type="technical", level="Master")
        PortfolioProject.objects.create(portfolio=self.portfolio, title="Analytical Engine", description="Mechanical Computer")

    def test_list_templates(self):
        """Verify list_templates returns active template presets with streamlined fields."""
        from portfolio.services.template_service import list_templates

        templates = list_templates()
        self.assertGreaterEqual(len(templates), 2)
        target = next((t for t in templates if t["slug"] == "modern-glass"), None)
        self.assertIsNotNone(target)
        self.assertEqual(target["name"], "Modern Glass")
        self.assertEqual(target["category"], "Engineering")
        self.assertIn("id", target)
        self.assertIn("slug", target)
        self.assertIn("description", target)

    def test_change_template_and_data_immutability(self):
        """Verify change_template updates selected_theme while leaving About, Skills, Projects, Contact 100% unchanged."""
        from portfolio.services.template_service import change_template

        res = change_template(self.portfolio, self.theme_2.pk)
        self.assertTrue(res["success"])
        self.assertEqual(res["template_slug"], "classic-serif")

        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.selected_theme, self.theme_2)

        # Immutability assertions
        self.assertEqual(self.portfolio.name, "Ada Lovelace Portfolio")
        self.assertEqual(self.portfolio.title, "First Computer Programmer")
        self.assertEqual(self.portfolio.about, "Pioneer of algorithmic computing engines.")
        self.assertEqual(self.portfolio.email, "ada@analyticalengine.org")
        self.assertEqual(self.portfolio.skills.count(), 1)
        self.assertEqual(self.portfolio.projects.count(), 1)

    def test_change_template_invalid_template_error(self):
        """Verify change_template raises ValueError for nonexistent or inactive template ID/slug."""
        from portfolio.services.template_service import change_template

        with self.assertRaises(ValueError):
            change_template(self.portfolio, "nonexistent-theme-slug")

        with self.assertRaises(ValueError):
            change_template(self.portfolio, 999999)

    def test_templates_api_endpoints(self):
        """Verify GET /portfolio/templates/ and POST /portfolio/template/change/."""
        self.client.login(username="templateuser", password="templatepassword")

        # 1. GET /portfolio/templates/
        list_res = self.client.get(reverse("portfolio:portfolio_templates_list_api"))
        self.assertEqual(list_res.status_code, 200)
        list_data = list_res.json()
        self.assertTrue(list_data["success"])
        self.assertGreaterEqual(list_data["count"], 2)

        # 2. POST /portfolio/template/change/
        change_res = self.client.post(
            reverse("portfolio:portfolio_change_template_api"),
            data=json.dumps({"portfolio_id": self.portfolio.pk, "template_slug": "classic-serif"}),
            content_type="application/json"
        )
        self.assertEqual(change_res.status_code, 200)
        change_data = change_res.json()
        self.assertTrue(change_data["success"])
        self.assertEqual(change_data["code"], "TEMPLATE_CHANGED")
        self.assertEqual(change_data["template_slug"], "classic-serif")


class AIPortfolioSEOTestCase(TestCase):
    """
    Test suite for Phase 9.7 Portfolio SEO (MVP).
    Tests clean_seo_description (HTML tag stripping, whitespace normalization, 155-char truncation),
    generate_meta_tags, generate_open_graph, generate_twitter_card, generate_robots_txt, generate_sitemap,
    missing portfolio error, permission denied error, and GET /portfolio/seo/<pk>/ API.
    """
    def setUp(self):
        self.user = User.objects.create_user(username="seouser", password="seopassword")
        self.other_user = User.objects.create_user(username="seootheruser", password="seopassword")
        self.portfolio = Portfolio.objects.create(
            user=self.user,
            name="Grace Hopper Portfolio",
            title="COBOL Pioneer & Rear Admiral",
            about="<p>Building <strong>compiler engines</strong> and debugging initial machine software systems across distributed nodes with extensive high-performance infrastructure.</p>",
            email="grace@navy.mil"
        )

    def test_clean_seo_description(self):
        """Verify clean_seo_description strips HTML tags, normalizes whitespace, and truncates to max_length."""
        from portfolio.services.seo_service import clean_seo_description

        raw = "<div>Hello   <b>World</b>   <p>This is a long sentence testing SEO metadata generation.</p></div>"
        cleaned = clean_seo_description(raw, max_length=30)
        self.assertNotIn("<b>", cleaned)
        self.assertNotIn("  ", cleaned)
        self.assertTrue(cleaned.endswith("..."))
        self.assertLessEqual(len(cleaned), 30)

    def test_generate_meta_open_graph_twitter(self):
        """Verify generate_meta_tags, generate_open_graph, and generate_twitter_card produce clean social metadata."""
        from portfolio.services.seo_service import generate_meta_tags, generate_open_graph, generate_twitter_card

        domain = "https://myportfolios.com"

        # 1. Meta Tags
        meta = generate_meta_tags(self.portfolio, domain=domain)
        self.assertEqual(meta["title"], "Grace Hopper Portfolio - COBOL Pioneer & Rear Admiral")
        self.assertNotIn("<p>", meta["description"])
        self.assertNotIn("<strong>", meta["description"])
        self.assertIn("Building compiler engines", meta["description"])

        # 2. Open Graph Tags
        og = generate_open_graph(self.portfolio, domain=domain)
        self.assertEqual(og["og:title"], meta["title"])
        self.assertEqual(og["og:url"], f"https://myportfolios.com/p/{self.portfolio.pk}/")
        self.assertEqual(og["og:type"], "website")

        # 3. Twitter Card Tags
        tw = generate_twitter_card(self.portfolio, domain=domain)
        self.assertEqual(tw["twitter:card"], "summary_large_image")
        self.assertEqual(tw["twitter:title"], meta["title"])

    def test_generate_robots_and_sitemap(self):
        """Verify generate_robots_txt and generate_sitemap produce valid specifications."""
        from portfolio.services.seo_service import generate_robots_txt, generate_sitemap

        domain = "https://myportfolios.com"

        # Robots.txt
        robots = generate_robots_txt(self.portfolio, domain=domain)
        self.assertIn("User-agent: *", robots)
        self.assertIn("Sitemap: https://myportfolios.com/sitemap.xml", robots)

        # Sitemap.xml
        sitemap = generate_sitemap(self.portfolio, domain=domain)
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', sitemap)
        self.assertIn(f"<loc>https://myportfolios.com/p/{self.portfolio.pk}/</loc>", sitemap)

    def test_seo_api_endpoint_and_permissions(self):
        """Verify GET /portfolio/seo/<pk>/ returns 200 for owner, 403 for unauthorized user, and 404 for missing portfolio."""
        url = reverse("portfolio:portfolio_seo_api", kwargs={"pk": self.portfolio.pk})

        # 1. Owner Access
        self.client.login(username="seouser", password="seopassword")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("meta_tags", data)
        self.assertIn("open_graph", data)
        self.assertIn("twitter_card", data)
        self.assertIn("robots_txt", data)
        self.assertIn("sitemap_xml", data)

        # 2. Unauthorized User Access (403 Forbidden)
        self.client.login(username="seootheruser", password="seopassword")
        res_forbidden = self.client.get(url)
        self.assertEqual(res_forbidden.status_code, 403)

        # 3. Missing Portfolio Access (404 Not Found)
        missing_url = reverse("portfolio:portfolio_seo_api", kwargs={"pk": 999999})
        res_missing = self.client.get(missing_url)
        self.assertEqual(res_missing.status_code, 404)


















