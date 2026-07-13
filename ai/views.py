import os
import json
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.core.exceptions import ValidationError

from pypdf import PdfReader
from docx import Document

from dashboard.navigation import get_sidebar_navigation
from portfolio.models import (
    Portfolio,
    PortfolioSkill,
    PortfolioProject,
    PortfolioExperience,
    PortfolioEducation
)
from .models import ResumeUpload
from .services import ResumeParserService


def _base_context(request):
    """Helper to return consistent navigation context for AI views."""
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "breadcrumbs": [
            {"title": "Dashboard", "url": "#"},
            {"title": "AI Resume Import", "url": "#"},
        ],
    }


class ResumeImportView(LoginRequiredMixin, View):
    """
    Handles secure resume upload (PDF/DOCX), runs validation (size, format, corruption),
    and initiates AI information extraction & content enrichment.
    """
    template_name = "ai/import.html"

    def get(self, request):
        ctx = _base_context(request)
        return render(request, self.template_name, ctx)

    def post(self, request):
        uploaded_file = request.FILES.get("resume_file")
        if not uploaded_file:
            messages.error(request, "No file uploaded.")
            return redirect("ai:import")

        # 1. Size Validation (Max 10 MB)
        if uploaded_file.size > 10 * 1024 * 1024:
            messages.error(request, "File size exceeds 10MB limit.")
            return redirect("ai:import")

        # 2. Extension Validation
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in [".pdf", ".docx"]:
            messages.error(request, "Unsupported file format. Please upload PDF or DOCX.")
            return redirect("ai:import")

        # 3. Secure File Saving
        upload_record = ResumeUpload.objects.create(
            user=request.user,
            file=uploaded_file
        )

        file_path = upload_record.file.path

        # 4. Corrupted File Check
        try:
            if ext == ".pdf":
                # Attempt to open and read pages
                reader = PdfReader(file_path)
                if len(reader.pages) == 0:
                    raise Exception("Zero pages in PDF.")
            elif ext == ".docx":
                # Attempt to parse document structure
                Document(file_path)
        except Exception as e:
            # Delete corrupted file record
            if os.path.exists(file_path):
                os.remove(file_path)
            upload_record.delete()
            
            messages.error(request, "Uploaded file appears to be corrupted or invalid.")
            return redirect("ai:import")

        # 5. Extract Text and Run AI Content Generation
        try:
            raw_text = ResumeParserService.extract_text_from_file(file_path)
            if not raw_text.strip():
                raise Exception("Extracted text is empty. File might contain only scanned images.")

            parsed_data = ResumeParserService.parse_resume_data(raw_text)
            enriched_data = ResumeParserService.generate_ai_content(parsed_data)

            # Store the resulting dictionary in the session for Review & Edit step
            request.session["parsed_resume_data"] = enriched_data
            
            # Mark upload as processed
            upload_record.is_processed = True
            upload_record.save(update_fields=["is_processed"])

            messages.success(request, "Resume parsed successfully. Please review the details below.")
            return redirect("ai:review")

        except Exception as e:
            # Delete record on processing failure
            if os.path.exists(file_path):
                os.remove(file_path)
            upload_record.delete()

            messages.error(request, f"Failed to parse resume: {str(e)}")
            return redirect("ai:import")


class ResumeReviewView(LoginRequiredMixin, View):
    """
    Renders structured review panel displaying extracted and generated data.
    Allows user to edit and save details directly into their Portfolio Builder.
    """
    template_name = "ai/review.html"

    def get(self, request):
        parsed_data = request.session.get("parsed_resume_data")
        if not parsed_data:
            messages.warning(request, "Please upload a resume first.")
            return redirect("ai:import")

        # Format lists (Skills, Experience, Education, Projects) as pretty JSON string for edit
        lists_dict = {
            "skills": parsed_data.get("skills", []),
            "experience": parsed_data.get("experience", []),
            "education": parsed_data.get("education", []),
            "projects": parsed_data.get("projects", [])
        }
        
        ctx = _base_context(request)
        ctx.update({
            "personal": parsed_data.get("personal", {}),
            "lists_json": json.dumps(lists_dict, indent=2),
        })
        return render(request, self.template_name, ctx)

    def post(self, request):
        parsed_data = request.session.get("parsed_resume_data")
        if not parsed_data:
            messages.warning(request, "Please upload a resume first.")
            return redirect("ai:import")

        # Extract editable details from form
        name = request.POST.get("name")
        title = request.POST.get("title")
        about = request.POST.get("about")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        social_github = request.POST.get("social_github")
        social_linkedin = request.POST.get("social_linkedin")
        lists_json_str = request.POST.get("lists_json")
        overwrite = request.POST.get("overwrite") == "on"

        try:
            lists_data = json.loads(lists_json_str)
        except Exception:
            messages.error(request, "Invalid JSON format inside lists editor.")
            return redirect("ai:review")

        # Create or update user portfolio
        portfolio, _ = Portfolio.objects.get_or_create(user=request.user)

        # Update flat characteristics
        portfolio.name = name
        portfolio.title = title
        portfolio.about = about
        portfolio.email = email
        portfolio.phone = phone
        portfolio.address = address
        portfolio.social_github = social_github
        portfolio.social_linkedin = social_linkedin
        portfolio.save()

        # Handle Overwrite vs Merge logic
        if overwrite:
            portfolio.skills.all().delete()
            portfolio.projects.all().delete()
            portfolio.experiences.all().delete()
            portfolio.education.all().delete()

        # Insert Skills
        skills_list = lists_data.get("skills", [])
        for idx, s in enumerate(skills_list):
            if isinstance(s, dict) and s.get("name"):
                PortfolioSkill.objects.create(
                    portfolio=portfolio,
                    skill_type=s.get("type", "technical"),
                    name=s.get("name"),
                    level=s.get("level", "")
                )

        # Insert Experiences
        exp_list = lists_data.get("experience", [])
        for idx, exp in enumerate(exp_list):
            if isinstance(exp, dict) and exp.get("company") and exp.get("position"):
                PortfolioExperience.objects.create(
                    portfolio=portfolio,
                    company=exp.get("company"),
                    position=exp.get("position"),
                    duration=exp.get("duration", "Present"),
                    description=exp.get("description", ""),
                    order=idx
                )

        # Insert Educations
        edu_list = lists_data.get("education", [])
        for idx, edu in enumerate(edu_list):
            if isinstance(edu, dict) and edu.get("degree") and edu.get("college"):
                PortfolioEducation.objects.create(
                    portfolio=portfolio,
                    degree=edu.get("degree"),
                    college=edu.get("college"),
                    university=edu.get("university", ""),
                    year=edu.get("year", ""),
                    order=idx
                )

        # Insert Projects
        proj_list = lists_data.get("projects", [])
        for idx, proj in enumerate(proj_list):
            if isinstance(proj, dict) and proj.get("title"):
                PortfolioProject.objects.create(
                    portfolio=portfolio,
                    title=proj.get("title"),
                    description=proj.get("description", ""),
                    technologies=proj.get("technologies", ""),
                    order=idx
                )

        # Clean session
        if "parsed_resume_data" in request.session:
            del request.session["parsed_resume_data"]

        messages.success(request, "AI resume details integrated into your portfolio builder workspace!")
        return redirect("portfolio:builder")
