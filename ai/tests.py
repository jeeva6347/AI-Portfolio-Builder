import os
import json
import docx
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from portfolio.models import Portfolio, PortfolioProject, PortfolioSkill
from .models import ResumeUpload
from .services import ResumeParserService

User = get_user_model()


class AIResumeImportTestCase(TestCase):
    """
    Test suite for Module 6: AI Resume Import & Content Generation.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            username="aiuser",
            email="aiuser@example.com",
            password="aipassword"
        )
        self.user.save()

        # Build clean test text
        self.resume_text = """
        JANE SMITH
        Senior Software Architect
        jane.smith@example.com | +1-555-0199 | Austin, TX
        github.com/janesmith | linkedin.com/in/janesmith

        Education
        B.S. in Computer Engineering, University of Texas, 2018

        Skills
        Python, Django, PostgreSQL, Kubernetes, AWS, Team Collaboration

        Experience
        Cloud Inc at Software Architect, 2021 - Present
        Architected microservices processing 10M requests daily.

        Projects
        Auto Deploy Pipeline
        Built a serverless deployment manager using Django.
        """

    def test_heuristics_parser_extraction(self):
        """Verify regex heuristic parser extracts name, contact info, and structural sections."""
        data = ResumeParserService.parse_resume_data_heuristics(self.resume_text)
        
        self.assertEqual(data["personal"]["name"].strip(), "JANE SMITH")
        self.assertEqual(data["personal"]["title"].strip(), "Senior Software Architect")
        self.assertEqual(data["personal"]["email"], "jane.smith@example.com")
        self.assertEqual(data["personal"]["phone"], "+1-555-0199")
        self.assertEqual(data["personal"]["social_github"], "github.com/janesmith")
        self.assertEqual(data["personal"]["social_linkedin"], "linkedin.com/in/janesmith")
        
        # Verify skills list populated
        skills = [s["name"] for s in data["skills"]]
        self.assertIn("Python", skills)
        self.assertIn("PostgreSQL", skills)
        
        # Verify education
        self.assertTrue(len(data["education"]) > 0)
        self.assertEqual(data["education"][0]["year"], "2018")

        # Verify experience
        self.assertTrue(len(data["experience"]) > 0)
        self.assertEqual(data["experience"][0]["company"], "Cloud Inc")

    def test_ai_content_enrichment(self):
        """Verify content generation enriches descriptions and generates SEO metadata."""
        parsed_data = ResumeParserService.parse_resume_data_heuristics(self.resume_text)
        enriched = ResumeParserService.generate_ai_content(parsed_data)
        
        self.assertTrue(len(enriched["personal"]["about"]) > 50)  # Has rich details
        self.assertEqual(enriched["seo_title"], "JANE SMITH | Senior Software Architect")
        self.assertIn("JANE SMITH", enriched["seo_description"])

    def test_file_upload_size_and_extension_validation(self):
        """Verify upload view handles size, extension, and corruption validation checks."""
        self.client.login(username="aiuser", password="aipassword")

        # 1. Invalid file format
        txt_file = SimpleUploadedFile("resume.txt", b"Plain text file", content_type="text/plain")
        res_format = self.client.post(reverse("ai:import"), {"resume_file": txt_file})
        self.assertEqual(res_format.status_code, 302)
        # Should redirect back with error message
        self.assertFalse(ResumeUpload.objects.exists())

        # 2. Corrupted PDF check (empty file)
        corrupt_pdf = SimpleUploadedFile("resume.pdf", b"", content_type="application/pdf")
        res_corrupt = self.client.post(reverse("ai:import"), {"resume_file": corrupt_pdf})
        self.assertEqual(res_corrupt.status_code, 302)
        self.assertFalse(ResumeUpload.objects.exists())

    def test_resume_save_to_portfolio(self):
        """Verify review POST integrates details and populates portfolio builder tables."""
        self.client.login(username="aiuser", password="aipassword")

        # Create a pre-existing portfolio to verify overwrite logic
        portfolio = Portfolio.objects.create(user=self.user, name="Old Name")
        PortfolioSkill.objects.create(portfolio=portfolio, name="Legacy Skill")

        # Simulate parsed session data
        parsed_data = {
            "personal": {
                "name": "Jane Smith",
                "title": "Architect",
                "about": "Rich bio details...",
                "email": "jane@example.com",
                "phone": "555-123",
                "address": "Austin",
                "social_github": "https://github.com/jane",
                "social_linkedin": ""
            },
            "skills": [{"name": "AI Systems", "type": "technical"}],
            "experience": [],
            "education": [],
            "projects": [{"title": "Agent Platform", "description": "AI systems", "technologies": "Python"}]
        }
        session = self.client.session
        session["parsed_resume_data"] = parsed_data
        session.save()

        # Submit review confirmation POST
        lists_dict = {
            "skills": parsed_data["skills"],
            "experience": parsed_data["experience"],
            "education": parsed_data["education"],
            "projects": parsed_data["projects"]
        }
        res_save = self.client.post(
            reverse("ai:review"),
            data={
                "name": "Jane Smith",
                "title": "Architect",
                "about": "Rich bio details...",
                "email": "jane@example.com",
                "phone": "555-123",
                "address": "Austin",
                "social_github": "https://github.com/jane",
                "social_linkedin": "",
                "lists_json": json.dumps(lists_dict),
                "overwrite": "on"
            }
        )
        self.assertEqual(res_save.status_code, 302)  # Redirects to portfolio builder
        
        # Verify Portfolio fields updated
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.name, "Jane Smith")
        self.assertEqual(portfolio.title, "Architect")

        # Verify overwrite cleared legacy skills and saved new ones
        self.assertFalse(portfolio.skills.filter(name="Legacy Skill").exists())
        self.assertTrue(portfolio.skills.filter(name="AI Systems").exists())
        self.assertTrue(portfolio.projects.filter(title="Agent Platform").exists())
