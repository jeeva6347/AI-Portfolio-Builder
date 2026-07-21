import os
import time
import json
import copy
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.core.cache import cache

from dashboard.navigation import get_sidebar_navigation
from themes.models import Theme
from themes.services import apply_theme_mapping

from .models import (
    Portfolio,
    PortfolioSkill,
    PortfolioProject,
    PortfolioExperience,
    PortfolioEducation,
    PortfolioCertificate,
    PortfolioService,
    PortfolioTestimonial,
)
from .forms import (
    PortfolioForm,
    PortfolioSkillForm,
    PortfolioProjectForm,
    PortfolioExperienceForm,
    PortfolioEducationForm,
    PortfolioCertificateForm,
    PortfolioServiceForm,
    PortfolioTestimonialForm,
)


from django.core.exceptions import PermissionDenied

def get_portfolio_for_user(pk, user, required_role="VIEWER"):
    """
    Retrieves a portfolio by PK and verifies the user has the required permission role.
    If the portfolio is personal, the user must be the owner.
    If the portfolio belongs to an organization, the user must be a member with
    at least the required role (OWNER, ADMIN, EDITOR, VIEWER).
    """
    portfolio = get_object_or_404(Portfolio, pk=pk)
    if not portfolio.organization:
        if portfolio.user == user:
            return portfolio
        raise PermissionDenied("You do not have permission to access this portfolio.")
    
    try:
        from organizations.services.org_service import check_portfolio_collaboration_permission as check_perm
        has_perm = check_perm(portfolio, user, required_role)
    except Exception:
        has_perm = (portfolio.user == user)
        
    if has_perm:
        return portfolio
    raise PermissionDenied("You do not have permission to perform this action on this shared portfolio.")


def _base_context(request, active_tab="personal"):
    """Helper to return consistent navigation context for portfolio views."""
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "active_tab": active_tab,
    }


# ── PORTFOLIO LIST VIEW ──────────────────────────────────────────────────────

class PortfolioListView(LoginRequiredMixin, View):
    """
    Dashboard list view showing all user portfolios partitioned by status.
    """
    template_name = "portfolio/list.html"

    def get(self, request):
        from django.db.models import Q
        try:
            from organizations.models import OrganizationMember
            org_ids = OrganizationMember.objects.filter(user=request.user, active=True).values_list('organization_id', flat=True)
        except Exception:
            org_ids = []

        portfolios = list(
            Portfolio.objects.filter(
                Q(user=request.user) | Q(organization_id__in=org_ids)
            )
            .select_related("selected_theme", "organization")
            .order_by("-updated_at")
        )
        ctx = _base_context(request, "list")
        ctx.update({
            "portfolios": portfolios,
            "drafts": [p for p in portfolios if p.status == Portfolio.Status.DRAFT],
            "published": [p for p in portfolios if p.status == Portfolio.Status.PUBLISHED],
            "archived": [p for p in portfolios if p.status == Portfolio.Status.ARCHIVED],
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "My Portfolios", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)


from payments.permissions import PortfolioLimitMixin


# ── PORTFOLIO LIST VIEW ──────────────────────────────────────────────────────
# ...
class PortfolioCreateView(PortfolioLimitMixin, LoginRequiredMixin, View):
    """Creates a new draft portfolio and redirects to its visual editor."""
    def post(self, request):
        # Create a default draft portfolio
        count = Portfolio.objects.filter(user=request.user).count()
        portfolio = Portfolio.objects.create(
            user=request.user,
            name=f"My Portfolio {count + 1}",
            title="Software Engineer",
            status=Portfolio.Status.DRAFT
        )
        messages.success(request, f"New draft portfolio '{portfolio.name}' created.")
        return redirect("portfolio:builder", pk=portfolio.pk)


class PortfolioDeleteView(LoginRequiredMixin, View):
    """Deletes a portfolio record."""
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "ADMIN")
        name = portfolio.name
        portfolio.delete()
        messages.success(request, f"Deleted portfolio '{name}'.")
        return redirect("portfolio:list")


class PortfolioDuplicateView(PortfolioLimitMixin, LoginRequiredMixin, View):
    """
    Clones a portfolio record along with all related skills, projects,
    experience, education, and testimonials.
    """
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        
        # 1. Duplicate top-level model
        clone = copy.copy(portfolio)
        clone.id = None
        clone.pk = None
        clone.name = f"Copy of {portfolio.name}"
        clone.status = Portfolio.Status.DRAFT
        clone.save()

        # 2. Duplicate child relations
        for item in portfolio.skills.all():
            skill_clone = copy.copy(item)
            skill_clone.id = None
            skill_clone.pk = None
            skill_clone.portfolio = clone
            skill_clone.save()

        for item in portfolio.projects.all():
            proj_clone = copy.copy(item)
            proj_clone.id = None
            proj_clone.pk = None
            proj_clone.portfolio = clone
            proj_clone.save()

        for item in portfolio.experiences.all():
            exp_clone = copy.copy(item)
            exp_clone.id = None
            exp_clone.pk = None
            exp_clone.portfolio = clone
            exp_clone.save()

        for item in portfolio.education.all():
            edu_clone = copy.copy(item)
            edu_clone.id = None
            edu_clone.pk = None
            edu_clone.portfolio = clone
            edu_clone.save()

        for item in portfolio.certificates.all():
            cert_clone = copy.copy(item)
            cert_clone.id = None
            cert_clone.pk = None
            cert_clone.portfolio = clone
            cert_clone.save()

        for item in portfolio.services.all():
            serv_clone = copy.copy(item)
            serv_clone.id = None
            serv_clone.pk = None
            serv_clone.portfolio = clone
            serv_clone.save()

        for item in portfolio.testimonials.all():
            test_clone = copy.copy(item)
            test_clone.id = None
            test_clone.pk = None
            test_clone.portfolio = clone
            test_clone.save()

        messages.success(request, f"Duplicated portfolio into '{clone.name}'.")
        return redirect("portfolio:list")


# ── STATUS MUTATION ACTIONS ──────────────────────────────────────────────────

class PortfolioPublishView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")

        from portfolio.services.publishing import publish_portfolio
        res = publish_portfolio(portfolio, user=request.user)

        # Handle AJAX/JSON requests
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.content_type == "application/json":
            status_code = 200 if res.get("success") else (400 if res.get("code") == "VALIDATION_FAILED" else 409)
            return JsonResponse(res, status=status_code)

        if res.get("success"):
            messages.success(request, f"Published portfolio '{portfolio.name}' successfully!")
        else:
            first_err = res.get("errors", [{}])[0].get("message", "Publishing failed.")
            messages.error(request, f"Publishing failed: {first_err}")

        return redirect("portfolio:list")


class PortfolioDeployView(LoginRequiredMixin, View):
    """
    POST /portfolio/<int:pk>/deploy/
    Triggers GitHub deployment pipeline for the portfolio.
    Returns JSON response with deployment status, commit_sha, duration_ms, and deployment_url.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        from portfolio.services.deployment import deploy_to_github
        res = deploy_to_github(portfolio, user=request.user)

        status_code = 200 if res.get("success") else 400
        return JsonResponse(res, status=status_code)


class PortfolioAIImportAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/ai-import/
    Imports validated AI JSON payload into portfolio draft state.
    Supports partial sections, import modes ('replace', 'merge', 'skip_existing'), and AI metadata versioning.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        body = {}
        if request.body:
            try:
                body = json.loads(request.body.decode("utf-8"))
            except Exception:
                pass

        if not body and request.POST:
            body = request.POST.dict()

        ai_data = body.get("ai_data", body)
        if isinstance(ai_data, str):
            try:
                ai_data = json.loads(ai_data)
            except Exception:
                ai_data = {}

        sections = body.get("sections")
        mode = body.get("mode", "replace")
        ai_metadata = body.get("ai_metadata")

        from portfolio.services.ai_import import import_generated_portfolio
        res = import_generated_portfolio(
            portfolio=portfolio,
            ai_data=ai_data,
            sections=sections,
            mode=mode,
            ai_metadata=ai_metadata,
            user=request.user
        )

        status_code = 200 if res.get("success") else 400
        return JsonResponse(res, status=status_code)


class PortfolioAIRegenerateSectionAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/ai-regenerate-section/
    Generates preview payload for a single portfolio section using AI (Zero DB Writes).
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        section_name = body.get("section_name", "")
        user_prompt = body.get("user_prompt", "")

        from portfolio.services.ai_regeneration import regenerate_section
        res = regenerate_section(portfolio, section_name=section_name, user_prompt=user_prompt)

        status_code = 200 if res.get("success") else 400
        return JsonResponse(res, status=status_code)


class PortfolioAIAcceptSectionAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/ai-accept-section/
    Atomically commits an accepted regenerated section into draft state & version history.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        section_name = body.get("section_name", "")
        regenerated_data = body.get("regenerated_data", {})
        ai_metadata = body.get("ai_metadata")
        expected_checksum = body.get("expected_checksum")

        from portfolio.services.ai_regeneration import apply_regenerated_section
        res = apply_regenerated_section(
            portfolio=portfolio,
            section_name=section_name,
            regenerated_data=regenerated_data,
            ai_metadata=ai_metadata,
            expected_checksum=expected_checksum,
            user=request.user
        )

        status_code = 200 if res.get("success") else 400
        return JsonResponse(res, status=status_code)


class PortfolioAIAssistantAnalysisAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/ai-analysis/
    Executes hybrid AI Assistant analysis pipeline (Deterministic Rule Engine + Gemini AI Analysis).
    Returns multidimensional scores (0-100), priority-sorted recommendations, explainability reasons,
    confidence metrics, and AI metadata with zero database write isolation.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        user_instruction = body.get("user_instruction")
        target_role = body.get("target_role")
        industry = body.get("industry")
        seniority = body.get("seniority")

        from portfolio.services.ai_assistant import analyze_portfolio
        res = analyze_portfolio(
            portfolio=portfolio,
            user_instruction=user_instruction,
            target_role=target_role,
            industry=industry,
            seniority=seniority
        )

        status_code = 200 if res.get("success") else 400
        return JsonResponse(res, status=status_code)


class PortfolioResumeUploadAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/resume-upload/
    Accepts resume file upload (PDF/DOCX/TXT), executes 8-step security validation sequence,
    parses & normalizes sections, invokes Phase 8.1 AI generation engine, and returns zero-DB preview + diff delta summary.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        if "resume" not in request.FILES:
            return JsonResponse({"success": False, "code": "NO_FILE", "message": "No resume file uploaded."}, status=400)

        uploaded_file = request.FILES["resume"]

        try:
            from portfolio.services.resume_parser import parse_resume, compute_preview_diff
            from portfolio.services.ai_generation import generate_portfolio_with_ai

            # 1. Parse Resume & Normalize Sections
            parse_result = parse_resume(uploaded_file, max_size_mb=5)
            norm = parse_result["normalized_resume"]

            # Format raw profile data for Phase 8.1 AI Generation Engine
            profile_data = {
                "name": norm["personal"]["value"]["name"],
                "headline": norm["personal"]["value"]["headline"],
                "about": norm["summary"]["value"],
                "contact_email": norm["personal"]["value"]["email"],
                "social_github": norm["personal"]["value"]["github"],
                "social_linkedin": norm["personal"]["value"]["linkedin"],
                "skills": [s["name"] for s in norm["skills"]["value"]],
                "projects": [p["title"] for p in norm["projects"]["value"]],
                "experience": [f"{e['position']} at {e['company']}" for e in norm["experience"]["value"]],
                "education": [ed["degree"] for ed in norm["education"]["value"]]
            }

            # 2. Invoke Phase 8.1 AI Generation Engine (Zero DB Write)
            gen_res = generate_portfolio_with_ai(profile_data)
            if not gen_res.get("success"):
                return JsonResponse(gen_res, status=400)

            generated_portfolio = gen_res.get("data", gen_res.get("portfolio", {}))

            # 3. Calculate Difference Delta Summary
            diff_summary = compute_preview_diff(portfolio, generated_portfolio)

            # 4. Return Preview Payload
            return JsonResponse({
                "success": True,
                "code": "RESUME_PREVIEW_READY",
                "filename": parse_result["filename"],
                "resume_hash": parse_result["resume_hash"],
                "statistics": parse_result["statistics"],
                "normalized_resume": norm,
                "generated_portfolio": generated_portfolio,
                "diff_summary": diff_summary,
                "ai_metadata": gen_res.get("metadata", {})
            })

        except ValueError as val_err:
            return JsonResponse({"success": False, "code": "VALIDATION_FAILED", "message": str(val_err)}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "code": "RESUME_PARSING_FAILED", "message": f"Resume processing failed: {str(e)}"}, status=400)


class PortfolioResumeImportAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/resume-import/
    Commits an accepted resume-generated portfolio preview into draft state via Phase 8.2 import engine,
    and creates a PortfolioVersion snapshot tagged "Resume Import".
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        ai_data = body.get("ai_data", {})
        resume_hash = body.get("resume_hash", "")
        ai_metadata = body.get("ai_metadata", {})

        if not isinstance(ai_metadata, dict):
            ai_metadata = {}

        ai_metadata.update({
            "source": "resume_import",
            "resume_hash": resume_hash,
            "parser_version": "1.0",
            "generated_from_resume": True,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

        from portfolio.services.ai_import import import_generated_portfolio
        res = import_generated_portfolio(
            portfolio=portfolio,
            ai_data=ai_data,
            mode="replace",
            ai_metadata=ai_metadata,
            user=request.user
        )

        status_code = 200 if res.get("success") else 400
        return JsonResponse(res, status=status_code)


class PortfolioJobAnalysisAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/job-analysis/
    Accepts pasted job description text or uploaded file (PDF/DOCX/TXT), parses requirements,
    compares against current portfolio draft, calculates ATS match scores (0-100), and generates
    section-by-section optimization preview with zero database writes.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        job_text = None
        uploaded_file = None

        if "job_file" in request.FILES:
            uploaded_file = request.FILES["job_file"]

        if not uploaded_file:
            try:
                body = json.loads(request.body.decode("utf-8")) if request.body else {}
                job_text = body.get("job_text") or body.get("job_description")
                user_instruction = body.get("user_instruction")
            except Exception:
                job_text = request.POST.get("job_text")
                user_instruction = request.POST.get("user_instruction")
        else:
            user_instruction = request.POST.get("user_instruction")

        if not job_text and not uploaded_file:
            return JsonResponse({"success": False, "code": "MISSING_JOB_DESCRIPTION", "message": "Please provide job description text or upload a document."}, status=400)

        try:
            from portfolio.services.job_description import parse_job_description, generate_job_optimization_preview

            # 1. Parse Job Description
            parse_res = parse_job_description(job_text=job_text, uploaded_file=uploaded_file, max_size_mb=5)
            job_reqs = parse_res["job_requirements"]

            # 2. Generate Optimization Preview (Zero DB Writes)
            preview_res = generate_job_optimization_preview(
                portfolio=portfolio,
                job_requirements=job_reqs,
                user_instruction=user_instruction
            )

            status_code = 200 if preview_res.get("success") else 400
            return JsonResponse(preview_res, status=status_code)

        except ValueError as val_err:
            return JsonResponse({"success": False, "code": "VALIDATION_FAILED", "message": str(val_err)}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "code": "JOB_ANALYSIS_FAILED", "message": f"Job analysis failed: {str(e)}"}, status=400)


class PortfolioJobApplyAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/job-apply/
    Selectively commits approved section optimizations (e.g. hero, skills) into draft state via Phase 8.3 section regeneration engine,
    and creates a PortfolioVersion snapshot tagged "Job Optimized".
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        selected_sections = body.get("selected_sections", [])
        optimizations = body.get("optimizations", {})
        job_metadata = body.get("job_metadata", {})
        job_hash = body.get("job_hash", "")

        if not selected_sections or not isinstance(selected_sections, list):
            return JsonResponse({"success": False, "code": "NO_SECTIONS_SELECTED", "message": "No target sections selected for application."}, status=400)

        from portfolio.services.ai_regeneration import apply_regenerated_section
        from portfolio.models import PortfolioVersion
        from portfolio.services.versioning import create_version_snapshot
        from django.db import transaction
        from portfolio.services.prompt_library import PROMPT_VERSION

        applied_report = {}
        all_warnings = []

        try:
            with transaction.atomic():
                for sec_name in selected_sections:
                    sec_key = sec_name.lower()
                    opt_item = optimizations.get(sec_key, optimizations.get(sec_name, {}))
                    opt_data = opt_item.get("optimized_data", opt_item) if isinstance(opt_item, dict) else opt_item

                    if not opt_data:
                        continue

                    apply_res = apply_regenerated_section(
                        portfolio=portfolio,
                        section_name=sec_key,
                        regenerated_data=opt_data,
                        user=request.user
                    )

                    if apply_res.get("success"):
                        applied_report[sec_key] = "applied"
                    else:
                        applied_report[sec_key] = "failed"
                        all_warnings.extend(apply_res.get("errors", []))

                # Create PortfolioVersion Snapshot Tagged "Job Optimized"
                job_title = job_metadata.get("job_title", "Target Job")
                version_title = f"Job Optimized Portfolio - {job_title}"

                snapshot = create_version_snapshot(
                    portfolio=portfolio,
                    title=version_title,
                    tag="Job Optimized",
                    description=f"Applied targeted optimizations for {job_title}.",
                    is_published=False,
                    is_manual_save=True,
                    created_by=request.user
                )

                meta_payload = {
                    "source": "job_optimization",
                    "job_hash": job_hash,
                    "job_title": job_title,
                    "company": job_metadata.get("company", ""),
                    "optimization_version": "1.0",
                    "provider": "Gemini",
                    "prompt_version": PROMPT_VERSION,
                    "applied_sections": list(applied_report.keys()),
                    "optimization_session": {
                        "job_hash": job_hash,
                        "applied_sections": list(applied_report.keys()),
                        "applied_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                }

                snap_json = snapshot.snapshot_json
                snap_json["_ai_metadata"] = meta_payload
                snapshot.snapshot_json = snap_json
                snapshot.save(update_fields=["snapshot_json"])

                cache.delete(f"builder_draft_{portfolio.pk}")
                cache.delete_pattern(f"job_opt_{portfolio.pk}_*") if hasattr(cache, "delete_pattern") else None

                return JsonResponse({
                    "success": True,
                    "status": "JOB_OPTIMIZATIONS_APPLIED",
                    "version_number": snapshot.version_number,
                    "applied_sections": applied_report,
                    "warnings": all_warnings,
                    "errors": []
                })

        except Exception as e:
            return JsonResponse({"success": False, "code": "JOB_APPLY_FAILED", "message": f"Failed to apply optimizations: {str(e)}"}, status=400)


class CoverLetterGenerateView(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/cover-letter/generate/
    Generates a structured cover letter preview in 100% read-only mode (Zero Database Writes).
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        resume_data = body.get("resume_data", {})
        job_requirements = body.get("job_requirements", {})
        tone = body.get("tone", "Professional")
        length = body.get("length", "Medium")
        template_variant = body.get("template_variant", "Modern")
        user_instruction = body.get("user_instruction")

        from portfolio.services.cover_letter import generate_cover_letter
        res = generate_cover_letter(
            portfolio=portfolio,
            resume_data=resume_data,
            job_requirements=job_requirements,
            tone=tone,
            length=length,
            template_variant=template_variant,
            user_instruction=user_instruction
        )

        status_code = 200 if res.get("success") else 400
        return JsonResponse(res, status=status_code)


class CoverLetterSaveView(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/cover-letter/save/
    Saves or restores a cover letter version record in DB with duplicate detection.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        cover_letter_data = body.get("cover_letter_data", {})
        tone = body.get("tone", "Professional")
        length = body.get("length", "Medium")
        template_variant = body.get("template_variant", "Modern")
        job_requirements = body.get("job_requirements", {})
        replace_version_id = body.get("replace_version_id")

        if not cover_letter_data:
            return JsonResponse({"success": False, "code": "MISSING_DATA", "message": "Cover letter content data is required."}, status=400)

        from portfolio.services.cover_letter import save_cover_letter_version
        res = save_cover_letter_version(
            portfolio=portfolio,
            cover_letter_data=cover_letter_data,
            tone=tone,
            length=length,
            template_variant=template_variant,
            job_requirements=job_requirements,
            replace_version_id=replace_version_id,
            user=request.user
        )

        status_code = 200 if res.get("success") else 400
        return JsonResponse(res, status=status_code)


class CoverLetterHistoryView(LoginRequiredMixin, View):
    """
    GET & POST /portfolio/builder/<int:pk>/cover-letter/history/
    Lists saved cover letter versions with restore (creates new revision safely), duplicate, and delete operations.
    """
    def get(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "VIEWER")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        from portfolio.models import CoverLetter
        versions = CoverLetter.objects.filter(portfolio=portfolio).order_by("-version_number")

        history_list = []
        for v in versions:
            history_list.append({
                "id": v.pk,
                "version_number": v.version_number,
                "title": v.title,
                "job_title": v.job_title,
                "company": v.company,
                "tone": v.tone,
                "length": v.length,
                "template_variant": v.template_variant,
                "created_at": v.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "content_json": v.content_json,
                "metadata": v.metadata_json
            })

        return JsonResponse({"success": True, "count": len(history_list), "history": history_list})

    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        action = body.get("action", "").lower()
        cover_letter_id = body.get("cover_letter_id")

        from portfolio.models import CoverLetter
        from portfolio.services.cover_letter import save_cover_letter_version

        try:
            cl = CoverLetter.objects.get(pk=cover_letter_id, portfolio=portfolio)
        except CoverLetter.DoesNotExist:
            return JsonResponse({"success": False, "code": "NOT_FOUND", "message": "Cover letter version not found."}, status=404)

        if action == "restore":
            # Reversible restore — creates a NEW revision from the historical version
            res = save_cover_letter_version(
                portfolio=portfolio,
                cover_letter_data=cl.content_json,
                tone=cl.tone,
                length=cl.length,
                template_variant=cl.template_variant,
                job_requirements={"title": cl.job_title, "company": cl.company},
                user=request.user
            )
            res["action"] = "restored_as_new_version"
            return JsonResponse(res)

        elif action == "duplicate":
            res = save_cover_letter_version(
                portfolio=portfolio,
                cover_letter_data=cl.content_json,
                tone=cl.tone,
                length=cl.length,
                template_variant=cl.template_variant,
                job_requirements={"title": cl.job_title, "company": cl.company},
                user=request.user
            )
            res["action"] = "duplicated"
            return JsonResponse(res)

        elif action == "delete":
            v_num = cl.version_number
            cl.delete()
            return JsonResponse({"success": True, "action": "deleted", "message": f"Deleted cover letter v{v_num}."})

        else:
            return JsonResponse({"success": False, "code": "INVALID_ACTION", "message": "Invalid action. Supported: restore, duplicate, delete."}, status=400)


class CoverLetterExportView(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<int:pk>/cover-letter/export/
    Generates downloadable cover letter files in PDF, DOCX, Markdown, or Plain Text format.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "VIEWER")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        export_format = body.get("format", "pdf")
        cover_letter_data = body.get("cover_letter_data")
        cover_letter_id = body.get("cover_letter_id")

        from portfolio.models import CoverLetter
        from portfolio.services.cover_letter import export_cover_letter

        if not cover_letter_data and cover_letter_id:
            try:
                cl = CoverLetter.objects.get(pk=cover_letter_id, portfolio=portfolio)
                cover_letter_data = {
                    "title": cl.title,
                    "greeting": cl.content_json.get("greeting", ""),
                    "introduction": cl.content_json.get("introduction", ""),
                    "body": cl.content_json.get("body", ""),
                    "closing": cl.content_json.get("closing", ""),
                    "signature": cl.content_json.get("signature", ""),
                    "metadata": cl.metadata_json
                }
            except CoverLetter.DoesNotExist:
                return JsonResponse({"success": False, "code": "NOT_FOUND", "message": "Cover letter record not found."}, status=404)

        if not cover_letter_data:
            return JsonResponse({"success": False, "code": "MISSING_DATA", "message": "Cover letter content required for export."}, status=400)

        file_bytes, mime_type, filename = export_cover_letter(cover_letter_data, format=export_format)

        response = HttpResponse(file_bytes, content_type=mime_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ResumeOptimizeView(LoginRequiredMixin, View):
    """
    POST /resume/optimize/
    Generates a simplified zero-DB-write preview diff optimizing Summary, Skills, Projects, and Experience.
    """
    def post(self, request):
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        resume_data = body.get("resume_data", {})
        job_requirements = body.get("job_requirements", {})
        user_instruction = body.get("user_instruction")

        if not resume_data:
            return JsonResponse({"success": False, "code": "MISSING_RESUME_DATA", "message": "Resume data is required for optimization."}, status=400)
        if not job_requirements:
            return JsonResponse({"success": False, "code": "MISSING_JOB_REQUIREMENTS", "message": "Job description requirements are required for optimization."}, status=400)

        try:
            from portfolio.services.resume_optimizer import optimize_resume
            preview_res = optimize_resume(
                resume_data=resume_data,
                job_requirements=job_requirements,
                user_instruction=user_instruction
            )
            return JsonResponse(preview_res, status=200)

        except ValueError as val_err:
            return JsonResponse({"success": False, "code": "VALIDATION_FAILED", "message": str(val_err)}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "code": "RESUME_OPTIMIZATION_FAILED", "message": f"Resume optimization failed: {str(e)}"}, status=400)


class ResumeSaveView(LoginRequiredMixin, View):
    """
    POST /resume/save/
    Saves a new OptimizedResume version in DB without overwriting original resume data.
    """
    def post(self, request):
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        portfolio_id = body.get("portfolio_id")
        optimized_preview_data = body.get("optimized_preview_data", {})
        original_resume_data = body.get("original_resume_data", {})
        title = body.get("title")

        if not portfolio_id:
            return JsonResponse({"success": False, "code": "MISSING_PORTFOLIO_ID", "message": "Portfolio ID is required."}, status=400)
        if not optimized_preview_data:
            return JsonResponse({"success": False, "code": "MISSING_PREVIEW_DATA", "message": "Optimized preview data is required for saving."}, status=400)

        try:
            portfolio = get_portfolio_for_user(portfolio_id, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)
        except Exception:
            return JsonResponse({"success": False, "code": "PORTFOLIO_NOT_FOUND", "message": "Portfolio not found."}, status=404)

        try:
            from portfolio.services.resume_optimizer import save_optimized_resume
            res = save_optimized_resume(
                portfolio=portfolio,
                optimized_preview_data=optimized_preview_data,
                original_resume_data=original_resume_data,
                title=title,
                user=request.user
            )
            return JsonResponse(res, status=200)

        except Exception as e:
            return JsonResponse({"success": False, "code": "RESUME_SAVE_FAILED", "message": f"Failed to save optimized resume: {str(e)}"}, status=400)


class PortfolioExportView(LoginRequiredMixin, View):
    """
    POST /portfolio/export/
    Exports a portfolio into PDF, DOCX, HTML (Theme Engine reuse), or ZIP (Static Site Builder reuse).
    Returns file download attachment response.
    """
    def post(self, request, pk=None):
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        portfolio_id = pk or body.get("portfolio_id") or body.get("pk") or request.POST.get("portfolio_id") or request.POST.get("pk") or request.GET.get("portfolio_id") or request.GET.get("pk")
        export_format = body.get("format") or request.POST.get("format", "pdf")

        if not portfolio_id:
            return JsonResponse({"success": False, "code": "MISSING_PORTFOLIO_ID", "message": "Portfolio ID is required for export."}, status=400)

        try:
            portfolio = get_portfolio_for_user(portfolio_id, request.user, "VIEWER")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)
        except Exception:
            return JsonResponse({"success": False, "code": "PORTFOLIO_NOT_FOUND", "message": "Portfolio not found."}, status=404)

        try:
            from portfolio.services.export_service import export_portfolio
            file_bytes, mime_type, filename = export_portfolio(portfolio, format=export_format)

            response = HttpResponse(file_bytes, content_type=mime_type)
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        except ValueError as val_err:
            return JsonResponse({"success": False, "code": "INVALID_EXPORT_FORMAT", "message": str(val_err)}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "code": "EXPORT_FAILED", "message": f"Export failed: {str(e)}"}, status=400)


class PortfolioBackupExportView(LoginRequiredMixin, View):
    """
    POST /portfolio/backup/export/
    Generates and downloads a complete JSON portfolio backup snapshot.
    """
    def post(self, request, pk=None):
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        portfolio_id = pk or body.get("portfolio_id") or body.get("pk") or request.POST.get("portfolio_id") or request.POST.get("pk") or request.GET.get("portfolio_id") or request.GET.get("pk")

        if not portfolio_id:
            return JsonResponse({"success": False, "code": "MISSING_PORTFOLIO_ID", "message": "Portfolio ID is required for backup export."}, status=400)

        try:
            portfolio = get_portfolio_for_user(portfolio_id, request.user, "VIEWER")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)
        except Exception:
            return JsonResponse({"success": False, "code": "PORTFOLIO_NOT_FOUND", "message": "Portfolio not found."}, status=404)

        try:
            from portfolio.services.backup_service import export_portfolio_backup
            backup_data = export_portfolio_backup(portfolio)

            json_bytes = json.dumps(backup_data, indent=2).encode("utf-8")
            clean_name = re.sub(r"[^\w\-_]", "_", portfolio.name or "Portfolio")

            response = HttpResponse(json_bytes, content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="{clean_name}_backup.json"'
            return response

        except Exception as e:
            return JsonResponse({"success": False, "code": "BACKUP_EXPORT_FAILED", "message": f"Backup export failed: {str(e)}"}, status=400)


class PortfolioBackupImportView(LoginRequiredMixin, View):
    """
    POST /portfolio/backup/import/
    Imports a JSON backup snapshot and reconstructs a brand new portfolio. Never overwrites existing portfolios!
    """
    def post(self, request):
        backup_file = request.FILES.get("backup_file")
        backup_data = None

        if backup_file:
            try:
                raw_bytes = backup_file.read()
                backup_data = json.loads(raw_bytes.decode("utf-8"))
            except Exception:
                return JsonResponse({"success": False, "code": "INVALID_JSON_FILE", "message": "Uploaded file is not a valid JSON backup document."}, status=400)
        else:
            try:
                backup_data = json.loads(request.body.decode("utf-8")) if request.body else {}
            except Exception:
                return JsonResponse({"success": False, "code": "INVALID_JSON_BODY", "message": "Invalid JSON body format."}, status=400)

        if not backup_data:
            return JsonResponse({"success": False, "code": "MISSING_BACKUP_DATA", "message": "Backup payload or file is required."}, status=400)

        try:
            from portfolio.services.backup_service import import_portfolio_backup
            new_portfolio = import_portfolio_backup(backup_data, user=request.user)

            return JsonResponse({
                "success": True,
                "code": "BACKUP_IMPORTED",
                "message": f"Successfully imported portfolio '{new_portfolio.name}'.",
                "portfolio_id": new_portfolio.pk,
                "name": new_portfolio.name
            }, status=200)

        except ValueError as val_err:
            return JsonResponse({"success": False, "code": "VALIDATION_FAILED", "message": str(val_err)}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "code": "BACKUP_IMPORT_FAILED", "message": f"Backup import failed: {str(e)}"}, status=400)


class PortfolioTemplatesListView(LoginRequiredMixin, View):
    """
    GET /portfolio/templates/
    Returns active built-in portfolio template presets.
    """
    def get(self, request):
        try:
            from portfolio.services.template_service import list_templates
            templates = list_templates()
            return JsonResponse({"success": True, "count": len(templates), "templates": templates}, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "code": "LIST_TEMPLATES_FAILED", "message": f"Failed to list templates: {str(e)}"}, status=400)


class PortfolioChangeTemplateView(LoginRequiredMixin, View):
    """
    POST /portfolio/template/change/
    Switches a portfolio's visual template layout while preserving user data.
    """
    def post(self, request, pk=None):
        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            body = {}

        portfolio_id = pk or body.get("portfolio_id") or body.get("pk") or request.POST.get("portfolio_id") or request.POST.get("pk") or request.GET.get("portfolio_id")
        template_identifier = body.get("template_id") or body.get("template_slug") or body.get("theme_id") or body.get("theme_slug") or request.POST.get("template_id") or request.POST.get("template_slug")

        if not portfolio_id:
            return JsonResponse({"success": False, "code": "MISSING_PORTFOLIO_ID", "message": "Portfolio ID is required."}, status=400)

        if not template_identifier:
            return JsonResponse({"success": False, "code": "MISSING_TEMPLATE_IDENTIFIER", "message": "Template ID or slug is required."}, status=400)

        try:
            portfolio = get_portfolio_for_user(portfolio_id, request.user, "EDITOR")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)
        except Exception:
            return JsonResponse({"success": False, "code": "PORTFOLIO_NOT_FOUND", "message": "Portfolio not found."}, status=404)

        try:
            from portfolio.services.template_service import change_template
            result = change_template(portfolio, template_identifier)
            return JsonResponse(result, status=200)
        except ValueError as val_err:
            return JsonResponse({"success": False, "code": "INVALID_TEMPLATE", "message": str(val_err)}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "code": "CHANGE_TEMPLATE_FAILED", "message": f"Change template failed: {str(e)}"}, status=400)


class PortfolioSEOView(LoginRequiredMixin, View):
    """
    GET /portfolio/seo/<portfolio_id>/
    Returns generated SEO meta tags, Open Graph tags, Twitter Card tags, robots.txt, and sitemap.xml.
    """
    def get(self, request, pk=None):
        portfolio_id = pk or request.GET.get("portfolio_id") or request.GET.get("pk")

        if not portfolio_id:
            return JsonResponse({"success": False, "code": "MISSING_PORTFOLIO_ID", "message": "Portfolio ID is required."}, status=400)

        try:
            portfolio = get_portfolio_for_user(portfolio_id, request.user, "VIEWER")
        except PermissionDenied:
            return JsonResponse({"success": False, "code": "PERMISSION_DENIED", "message": "Permission denied."}, status=403)
        except Exception:
            return JsonResponse({"success": False, "code": "PORTFOLIO_NOT_FOUND", "message": "Portfolio not found."}, status=404)

        try:
            from portfolio.services.seo_service import generate_portfolio_seo
            domain = request.build_absolute_uri('/')[:-1]
            seo_data = generate_portfolio_seo(portfolio, domain=domain)
            return JsonResponse({"success": True, **seo_data}, status=200)
        except Exception as e:
            return JsonResponse({"success": False, "code": "SEO_GENERATION_FAILED", "message": f"Failed to generate SEO: {str(e)}"}, status=400)


class PortfolioArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        portfolio.status = Portfolio.Status.ARCHIVED
        portfolio.save(update_fields=["status"])
        messages.success(request, f"Archived portfolio '{portfolio.name}'.")
        return redirect("portfolio:list")


class PortfolioRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        portfolio.status = Portfolio.Status.DRAFT
        portfolio.save(update_fields=["status"])
        messages.success(request, f"Restored portfolio '{portfolio.name}' back to draft.")
        return redirect("portfolio:list")


# ── VISUAL BUILDER WORKSPACE & API ───────────────────────────────────────────

class PortfolioBuilderView(LoginRequiredMixin, View):
    """
    Visual split-screen editor workspace for a specific portfolio ID.
    Renders left editing panel forms and right live preview viewport.
    """
    template_name = "portfolio/builder.html"
    def get(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        active_tab = request.GET.get("tab", "personal")

        from themes.models import Theme, ThemeCategory
        themes = Theme.objects.filter(status=Theme.Status.APPROVED).select_related("category")
        categories = ThemeCategory.objects.all()

        ctx = _base_context(request, active_tab)
        ctx.update({
            "portfolio": portfolio,
            "themes": themes,
            "categories": categories,
            "form": PortfolioForm(instance=portfolio),
            "breadcrumbs": [
                {"title": "My Portfolios", "url": reverse("portfolio:list")},
                {"title": f"Editing: {portfolio.name}", "url": "#"},
            ],
            # Child item forms
            "skill_form": PortfolioSkillForm(),
            "project_form": PortfolioProjectForm(),
            "experience_form": PortfolioExperienceForm(),
            "education_form": PortfolioEducationForm(),
            "certificate_form": PortfolioCertificateForm(),
            "service_form": PortfolioServiceForm(),
            "testimonial_form": PortfolioTestimonialForm(),
            
            # List data
            "skills": portfolio.skills.all(),
            "projects": portfolio.projects.all(),
            "experiences": portfolio.experiences.all(),
            "educations": portfolio.education.all(),
            "certificates": portfolio.certificates.all(),
            "services": portfolio.services.all(),
            "testimonials": portfolio.testimonials.all(),
        })
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        """Standard POST fallback handling if javascript is disabled."""
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        active_tab = request.POST.get("tab", "personal")
        form = PortfolioForm(request.POST, request.FILES, instance=portfolio)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Portfolio information updated successfully.")
            return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio.pk})}?tab={active_tab}")
            
        ctx = _base_context(request, active_tab)
        ctx.update({
            "portfolio": portfolio,
            "form": form,
            "breadcrumbs": [
                {"title": "My Portfolios", "url": reverse("portfolio:list")},
                {"title": f"Editing: {portfolio.name}", "url": "#"},
            ],
            "skill_form": PortfolioSkillForm(),
            "project_form": PortfolioProjectForm(),
            "experience_form": PortfolioExperienceForm(),
            "education_form": PortfolioEducationForm(),
            "certificate_form": PortfolioCertificateForm(),
            "service_form": PortfolioServiceForm(),
            "testimonial_form": PortfolioTestimonialForm(),
            "skills": portfolio.skills.all(),
            "projects": portfolio.projects.all(),
            "experiences": portfolio.experiences.all(),
            "educations": portfolio.education.all(),
            "certificates": portfolio.certificates.all(),
            "services": portfolio.services.all(),
            "testimonials": portfolio.testimonials.all(),
        })
        messages.error(request, "Failed to update portfolio. Please check form fields.")
        return render(request, self.template_name, ctx)


class PortfolioUpdateAPI(LoginRequiredMixin, View):
    """
    AJAX endpoint validating and auto-saving individual fields
    to support real-time preview updates without page reload.
    Returns 403 if the portfolio belongs to a different user.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden("You do not have permission to edit this portfolio.")
        form = PortfolioForm(request.POST, request.FILES, instance=portfolio)
        if form.is_valid():
            saved_portfolio = form.save()
            cache.delete(f"portfolio_rendered_html_{saved_portfolio.pk}")
            cache.delete(f"builder_draft_{saved_portfolio.pk}")
            return JsonResponse({
                "success": True,
                "message": "Draft saved.",
                "photo_url": saved_portfolio.photo.url if saved_portfolio.photo else "",
                "resume_url": saved_portfolio.resume.url if saved_portfolio.resume else "",
            })
        return JsonResponse({"success": False, "errors": form.errors}, status=400)


class PortfolioReorderAPI(LoginRequiredMixin, View):
    """
    AJAX endpoint to update ordering indices of portfolio child items via SortableJS.
    """
    def post(self, request, pk):
        import json
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        item_type = request.POST.get("item_type")
        raw_order = request.POST.get("order_ids")
        
        if not item_type or not raw_order:
            return JsonResponse({"success": False, "error": "Missing parameters"}, status=400)

        try:
            order_ids = json.loads(raw_order)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid order JSON"}, status=400)

        model_map = {
            "projects": (portfolio.projects, PortfolioProject),
            "experiences": (portfolio.experiences, PortfolioExperience),
            "educations": (portfolio.education, PortfolioEducation),
            "certificates": (portfolio.certificates, PortfolioCertificate),
            "services": (portfolio.services, PortfolioService),
            "testimonials": (portfolio.testimonials, PortfolioTestimonial),
        }

        if item_type in model_map:
            rel, model_cls = model_map[item_type]
            for idx, item_id in enumerate(order_ids):
                model_cls.objects.filter(pk=item_id, portfolio=portfolio).update(order=idx)
            return JsonResponse({"success": True, "message": f"Reordered {item_type} successfully."})

        return JsonResponse({"success": False, "error": "Unknown item type"}, status=400)


class PortfolioDuplicateItemAPI(LoginRequiredMixin, View):
    """
    AJAX endpoint to duplicate an existing portfolio child item.
    """
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        item_type = request.POST.get("item_type")
        item_id = request.POST.get("item_id")

        if not item_type or not item_id:
            return JsonResponse({"success": False, "error": "Missing parameters"}, status=400)

        model_map = {
            "projects": PortfolioProject,
            "experiences": PortfolioExperience,
            "educations": PortfolioEducation,
            "certificates": PortfolioCertificate,
            "services": PortfolioService,
            "testimonials": PortfolioTestimonial,
            "skills": PortfolioSkill,
        }

        if item_type not in model_map:
            return JsonResponse({"success": False, "error": "Invalid item type"}, status=400)

        model_cls = model_map[item_type]
        item = get_object_or_404(model_cls, pk=item_id, portfolio=portfolio)
        
        clone = copy.copy(item)
        clone.pk = None
        clone.id = None
        if hasattr(clone, "title"):
            clone.title = f"{clone.title} (Copy)"
        elif hasattr(clone, "name"):
            clone.name = f"{clone.name} (Copy)"
        elif hasattr(clone, "position"):
            clone.position = f"{clone.position} (Copy)"
        clone.save()

        return JsonResponse({"success": True, "message": "Item duplicated successfully", "new_id": clone.pk})


class PortfolioAddComponentAPI(LoginRequiredMixin, View):
    """
    AJAX endpoint to insert component presets into a portfolio.
    """
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        component_type = request.POST.get("component_type", "project")

        if component_type in ["projects", "project"]:
            PortfolioProject.objects.create(
                portfolio=portfolio,
                title="New Showcase Project",
                description="High performance web application showcasing modern design patterns.",
                technologies="Python, Django, Tailwind CSS, JavaScript",
                github_url="https://github.com/",
                live_url="https://example.com"
            )
        elif component_type in ["experiences", "experience"]:
            PortfolioExperience.objects.create(
                portfolio=portfolio,
                company="Tech Innovators Inc",
                position="Senior Full-Stack Engineer",
                duration="2023 - Present",
                description="Designed and deployed scalable Django microservices and interactive user interfaces."
            )
        elif component_type in ["skills", "skill"]:
            PortfolioSkill.objects.create(
                portfolio=portfolio,
                skill_type="technical",
                name="Python / Django",
                level="Expert"
            )
        elif component_type in ["education"]:
            PortfolioEducation.objects.create(
                portfolio=portfolio,
                degree="B.S. in Computer Science",
                college="School of Engineering",
                university="State University",
                year="2019 - 2023"
            )
        elif component_type in ["testimonials", "testimonial", "reviews"]:
            PortfolioTestimonial.objects.create(
                portfolio=portfolio,
                reviewer_name="Sarah Jenkins",
                reviewer_role="Product Manager at CloudCorp",
                text="Delivered outstanding results ahead of schedule. Exceptional code quality and UI design skills!"
            )
        elif component_type in ["services", "service"]:
            PortfolioService.objects.create(
                portfolio=portfolio,
                title="Full-Stack Web Development",
                description="Custom web application architecture, API development, and UI/UX engineering.",
                icon="bi-code-slash"
            )
        elif component_type in ["hero"]:
            portfolio.title = portfolio.title or "Senior Software Engineer"
            portfolio.tagline = portfolio.tagline or "Building scalable cloud applications and user experiences"
            portfolio.save(update_fields=["title", "tagline"])

        return JsonResponse({"success": True, "message": f"Component '{component_type}' added successfully."})


# ── VERSION HISTORY API VIEWS (Phase 6.2) ───────────────────────────────────

class PortfolioVersionListView(LoginRequiredMixin, View):
    """
    GET /portfolio/builder/<pk>/versions/
    Returns JSON array of version history snapshots for a portfolio.
    """
    def get(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden("You do not have permission to view version history.")

        versions = portfolio.versions.select_related("theme", "created_by").all()
        data = [
            {
                "id": v.pk,
                "uuid": str(v.uuid),
                "version_number": v.version_number,
                "title": v.title,
                "description": v.description,
                "tag": v.tag,
                "theme_name": v.theme.name if v.theme else "Default",
                "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "created_by": v.created_by.get_full_name() or v.created_by.username if v.created_by else "System",
                "is_published": v.is_published,
                "is_auto_save": v.is_auto_save,
                "is_manual_save": v.is_manual_save,
            }
            for v in versions
        ]
        return JsonResponse({"success": True, "versions": data})


class PortfolioVersionRestoreAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<pk>/versions/<v_pk>/restore/
    Restores the portfolio to the target version snapshot (supports full or partial section restore).
    """
    def post(self, request, pk, v_pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden("You do not have permission to restore versions.")

        from portfolio.models import PortfolioVersion
        from portfolio.services.versioning import restore_version_snapshot

        sections = request.POST.getlist("sections[]") or request.POST.getlist("sections")
        if not sections:
            sec_param = request.POST.get("sections") or request.POST.get("section")
            if sec_param:
                sections = [s.strip() for s in sec_param.split(",") if s.strip()]

        version_obj = get_object_or_404(PortfolioVersion, pk=v_pk, portfolio=portfolio)
        rollback_version = restore_version_snapshot(portfolio, version_obj, user=request.user, sections_to_restore=sections or None)

        return JsonResponse({
            "success": True,
            "message": f"Successfully restored version #{version_obj.version_number}.",
            "rollback_version_id": rollback_version.pk
        })


class PortfolioVersionPreviewView(LoginRequiredMixin, View):
    """
    GET /portfolio/builder/<pk>/versions/<v_pk>/preview/
    Renders compiled HTML preview of a historical version snapshot inside the builder preview frame.
    """
    def get(self, request, pk, v_pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "VIEWER")
        except PermissionDenied:
            return HttpResponseForbidden("You do not have permission to preview versions.")

        from portfolio.models import PortfolioVersion
        version_obj = get_object_or_404(PortfolioVersion, pk=v_pk, portfolio=portfolio)

        if not portfolio.selected_theme:
            return HttpResponse(
                "<div style='padding:2rem;text-align:center;'><h3>Version Snapshot Preview</h3>"
                "<p>No layout theme selected for this portfolio.</p></div>",
                content_type="text/html"
            )

        theme = version_obj.theme or portfolio.selected_theme
        mapping = theme.mappings.filter(is_active=True).first()
        if not mapping or not theme.index_html_path or not os.path.exists(theme.index_html_path):
            return HttpResponse(
                f"<div style='padding:2rem;text-align:center;'><h3>Version #{version_obj.version_number} Preview</h3>"
                f"<p>Layout template for theme '{theme.name}' is inactive.</p></div>",
                content_type="text/html"
            )

        with open(theme.index_html_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()

        compiled_html = apply_theme_mapping(html_content, mapping, portfolio.get_fields_dict())
        return HttpResponse(compiled_html, content_type="text/html")


class PortfolioVersionCompareAPI(LoginRequiredMixin, View):
    """
    POST /portfolio/builder/<pk>/versions/compare/
    Compares two version snapshots and returns structured field & child diffs.
    """
    def post(self, request, pk):
        try:
            portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden("You do not have permission to compare versions.")

        version_a_id = request.POST.get("version_a_id")
        version_b_id = request.POST.get("version_b_id")

        if not version_a_id or not version_b_id:
            return JsonResponse({"success": False, "error": "Both version_a_id and version_b_id are required."}, status=400)

        from portfolio.models import PortfolioVersion
        from portfolio.services.versioning import compare_version_snapshots

        v_a = get_object_or_404(PortfolioVersion, pk=version_a_id, portfolio=portfolio)
        v_b = get_object_or_404(PortfolioVersion, pk=version_b_id, portfolio=portfolio)

        diff = compare_version_snapshots(v_a, v_b)
        return JsonResponse({"success": True, "diff": diff})


# ── SUB-ITEM CREATE VIEWS ────────────────────────────────────────────────────

class SkillCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        form = PortfolioSkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.portfolio = portfolio
            skill.save()
            messages.success(request, f"Added skill '{skill.name}'.")
        else:
            messages.error(request, "Invalid skill data.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio.pk})}?tab=skills")


class ProjectCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        form = PortfolioProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.portfolio = portfolio
            project.save()
            messages.success(request, f"Added project '{project.title}'.")
        else:
            messages.error(request, "Invalid project data.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio.pk})}?tab=projects")


class ExperienceCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        form = PortfolioExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.portfolio = portfolio
            experience.save()
            messages.success(request, f"Added experience at '{experience.company}'.")
        else:
            messages.error(request, "Invalid experience data.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio.pk})}?tab=experience")


class EducationCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        form = PortfolioEducationForm(request.POST)
        if form.is_valid():
            edu = form.save(commit=False)
            edu.portfolio = portfolio
            edu.save()
            messages.success(request, f"Added education '{edu.degree}'.")
        else:
            messages.error(request, "Invalid education data.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio.pk})}?tab=education")


class CertificateCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        form = PortfolioCertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.portfolio = portfolio
            cert.save()
            messages.success(request, f"Added certificate '{cert.name}'.")
        else:
            messages.error(request, "Invalid certificate data.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio.pk})}?tab=certificates")


class ServiceCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        form = PortfolioServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.portfolio = portfolio
            service.save()
            messages.success(request, f"Added service '{service.title}'.")
        else:
            messages.error(request, "Invalid service data.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio.pk})}?tab=services")


class TestimonialCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        form = PortfolioTestimonialForm(request.POST)
        if form.is_valid():
            test = form.save(commit=False)
            test.portfolio = portfolio
            test.save()
            messages.success(request, f"Added testimonial from '{test.reviewer_name}'.")
        else:
            messages.error(request, "Invalid testimonial data.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio.pk})}?tab=testimonials")


# ── SUB-ITEM DELETE VIEWS ────────────────────────────────────────────────────

class SkillDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        skill = get_object_or_404(PortfolioSkill, pk=pk)
        try:
            get_portfolio_for_user(skill.portfolio.pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden()
        portfolio_id = skill.portfolio.pk
        name = skill.name
        skill.delete()
        messages.success(request, f"Deleted skill '{name}'.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio_id})}?tab=skills")


class ProjectDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(PortfolioProject, pk=pk)
        try:
            get_portfolio_for_user(project.portfolio.pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden()
        portfolio_id = project.portfolio.pk
        title = project.title
        project.delete()
        messages.success(request, f"Deleted project '{title}'.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio_id})}?tab=projects")


class ExperienceDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        exp = get_object_or_404(PortfolioExperience, pk=pk)
        try:
            get_portfolio_for_user(exp.portfolio.pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden()
        portfolio_id = exp.portfolio.pk
        company = exp.company
        exp.delete()
        messages.success(request, f"Deleted experience at '{company}'.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio_id})}?tab=experience")


class EducationDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        edu = get_object_or_404(PortfolioEducation, pk=pk)
        try:
            get_portfolio_for_user(edu.portfolio.pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden()
        portfolio_id = edu.portfolio.pk
        degree = edu.degree
        edu.delete()
        messages.success(request, f"Deleted education '{degree}'.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio_id})}?tab=education")


class CertificateDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cert = get_object_or_404(PortfolioCertificate, pk=pk)
        try:
            get_portfolio_for_user(cert.portfolio.pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden()
        portfolio_id = cert.portfolio.pk
        name = cert.name
        cert.delete()
        messages.success(request, f"Deleted certificate '{name}'.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio_id})}?tab=certificates")


class ServiceDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        service = get_object_or_404(PortfolioService, pk=pk)
        try:
            get_portfolio_for_user(service.portfolio.pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden()
        portfolio_id = service.portfolio.pk
        title = service.title
        service.delete()
        messages.success(request, f"Deleted service '{title}'.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio_id})}?tab=services")


class TestimonialDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        test = get_object_or_404(PortfolioTestimonial, pk=pk)
        try:
            get_portfolio_for_user(test.portfolio.pk, request.user, "EDITOR")
        except PermissionDenied:
            return HttpResponseForbidden()
        portfolio_id = test.portfolio.pk
        name = test.reviewer_name
        test.delete()
        messages.success(request, f"Deleted testimonial from '{name}'.")
        return redirect(f"{reverse('portfolio:builder', kwargs={'pk': portfolio_id})}?tab=testimonials")


# ── THEME SELECTION & LIVE PREVIEW ───────────────────────────────────────────

class SelectThemeView(LoginRequiredMixin, View):
    """
    Renders themes lists allowing user to select a template layout
    for their active portfolio presentation.
    """
    template_name = "portfolio/select_theme.html"

    def get(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        themes = Theme.objects.filter(status=Theme.Status.APPROVED)
        ctx = _base_context(request, "theme")
        ctx.update({
            "portfolio": portfolio,
            "themes": themes,
            "breadcrumbs": [
                {"title": "My Portfolios", "url": reverse("portfolio:list")},
                {"title": "Select Theme", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        portfolio = get_portfolio_for_user(pk, request.user, "EDITOR")
        theme_id = request.POST.get("theme_id")
        if theme_id:
            theme = get_object_or_404(Theme, pk=theme_id, status=Theme.Status.APPROVED)
            
            # Premium Theme Check
            from payments.permissions import get_user_plan_benefits
            plan = get_user_plan_benefits(request.user)
            if theme.is_premium and not plan.premium_themes_enabled:
                messages.error(request, f"Theme '{theme.name}' is a Premium Theme. Please upgrade your subscription to use it.")
                return redirect("payments:billing")

            portfolio.selected_theme = theme
            portfolio.save(update_fields=["selected_theme"])
            messages.success(request, f"Successfully activated theme '{theme.name}'.")
        else:
            portfolio.selected_theme = None
            portfolio.save(update_fields=["selected_theme"])
            messages.success(request, "Theme de-activated. Portfolio is now unmapped.")
        return redirect("portfolio:select_theme", pk=portfolio.pk)


class UserPortfolioPreview(View):
    """
    Live portfolio compiler that renders a specific portfolio's
    active theme template.
    Restricts access to owner unless the status is PUBLISHED.
    """
    def get(self, request, pk):
        portfolio = get_object_or_404(
            Portfolio.objects.select_related("selected_theme", "user")
            .prefetch_related(
                "skills",
                "projects",
                "experiences",
                "education",
                "certificates",
                "services",
                "testimonials",
            ),
            pk=pk
        )
        
        # Security Access check: if unpublished, restrict to owner or org viewer
        has_access = True
        if portfolio.status != Portfolio.Status.PUBLISHED:
            try:
                get_portfolio_for_user(pk, request.user, "VIEWER")
            except PermissionDenied:
                has_access = False
        if not has_access:
            return HttpResponseForbidden("This portfolio draft is unpublished and private.")

        theme = portfolio.selected_theme
        if not theme:
            return HttpResponse(
                "<h3>No active theme selected.</h3><p>Please select a theme from the "
                "Select Theme tab to preview your portfolio.</p>",
                content_type="text/html"
            )
            
        # ALL FEATURES FREE: Premium theme check bypassed — all themes are free for all users.

        mapping = theme.mappings.filter(is_active=True).first()
        if not mapping:
            return HttpResponse(
                f"<h3>Theme '{theme.name}' does not have an active mapping profile.</h3>"
                f"<p>Please contact an admin to map the elements of this theme template.</p>",
                content_type="text/html"
            )
            
        index_path = theme.index_html_path
        if not index_path or not os.path.exists(index_path):
            return HttpResponse("Theme files are missing or incomplete.", status=404)
            
        with open(index_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
            
        # Compile dynamically using BeautifulSoup and mapped selectors
        compiled_html = apply_theme_mapping(html_content, mapping, portfolio.get_fields_dict())
        
        # 1. Track Traffic Analytics
        from analytics.services.tracking_service import track_visit
        track_visit(request, portfolio)

        # 2. Dynamic SEO Injection
        from analytics.services.seo_service import inject_seo_metadata
        compiled_html = inject_seo_metadata(compiled_html, portfolio, request=request)
        
        return HttpResponse(compiled_html, content_type="text/html")


class UseThemeFromMarketplaceView(LoginRequiredMixin, View):
    """
    POST/GET entry point to immediately associate a theme from the Marketplace
    to the user's portfolio and launch the builder.
    """
    def get(self, request, theme_id):
        from themes.models import Theme
        theme = get_object_or_404(Theme, pk=theme_id, status=Theme.Status.APPROVED)
        
        # ALL FEATURES FREE: Premium theme check bypassed — all themes are free for all users.

        portfolios = Portfolio.objects.filter(user=request.user)
        count = portfolios.count()
        
        if count == 0:
            # Create a default new portfolio with this theme
            portfolio = Portfolio.objects.create(
                user=request.user,
                name="My Portfolio 1",
                title="Software Engineer",
                selected_theme=theme,
                status=Portfolio.Status.DRAFT
            )
            messages.success(request, f"New portfolio created with theme '{theme.name}'!")
            return redirect("portfolio:builder", pk=portfolio.pk)
        elif count == 1:
            # Apply layout to their single active portfolio
            portfolio = portfolios.first()
            portfolio.selected_theme = theme
            portfolio.save(update_fields=["selected_theme"])
            messages.success(request, f"Theme '{theme.name}' applied to your portfolio!")
            return redirect("portfolio:builder", pk=portfolio.pk)
        else:
            # Apply to their most recently updated active portfolio
            portfolio = portfolios.order_by("-updated_at").first()
            portfolio.selected_theme = theme
            portfolio.save(update_fields=["selected_theme"])
            messages.success(request, f"Theme '{theme.name}' applied to your active portfolio '{portfolio.name}'!")
            return redirect("portfolio:builder", pk=portfolio.pk)
