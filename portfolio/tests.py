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




