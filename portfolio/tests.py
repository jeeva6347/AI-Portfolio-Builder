import os
import shutil
import zipfile
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from themes.models import Theme, ThemeCategory, ThemeMapping, ThemeMappingField
from themes.services import process_theme_upload
from .models import Portfolio, PortfolioSkill, PortfolioProject, PortfolioExperience

User = get_user_model()


class PortfolioBuilderTestCase(TestCase):
    """
    Test suite for Module 7 Portfolio Builder.
    """
    def setUp(self):
        # Create standard test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword"
        )
        self.user.save()

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
            attribute=ThemeMappingField.AttributeType.TEXT  # mapped container tag
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
        # Unauthenticated access
        res = self.client.get(reverse("portfolio:builder"))
        self.assertEqual(res.status_code, 302)  # Redirects to login

        # Authenticated access
        self.client.login(username="testuser", password="testpassword")
        res_auth = self.client.get(reverse("portfolio:builder") + "?tab=personal")
        self.assertEqual(res_auth.status_code, 200)
        self.assertContains(res_auth, "Personal details")

    def test_skills_projects_experiences_crud(self):
        """Verify user can add/delete related skills, projects, and experiences via POST views."""
        self.client.login(username="testuser", password="testpassword")
        portfolio = Portfolio.objects.create(user=self.user)

        # 1. Add Skill
        res_skill = self.client.post(
            reverse("portfolio:skill_create"),
            data={"skill_type": "technical", "name": "Django", "level": "Expert"}
        )
        self.assertEqual(res_skill.status_code, 302)
        self.assertTrue(portfolio.skills.filter(name="Django").exists())

        # 2. Add Experience
        res_exp = self.client.post(
            reverse("portfolio:experience_create"),
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
            reverse("portfolio:project_create"),
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
            reverse("portfolio:select_theme"),
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
        res_prev = self.client.get(reverse("portfolio:preview"))
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
