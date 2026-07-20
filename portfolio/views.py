import os
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
import copy

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
            form.save()
            return JsonResponse({"success": True, "message": "Draft saved."})
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
            
        # Premium Theme Check
        if theme.is_premium:
            from payments.permissions import get_user_plan_benefits
            plan = get_user_plan_benefits(portfolio.user)
            if not plan.premium_themes_enabled:
                return HttpResponse(
                    "<h3>Premium Theme Required</h3><p>This portfolio template requires a Premium "
                    "subscription upgrade. Please upgrade your plan to render.</p>",
                    content_type="text/html",
                    status=403
                )
            
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
        
        # Check premium theme layout permissions
        from payments.permissions import get_user_plan_benefits
        plan = get_user_plan_benefits(request.user)
        if theme.is_premium and not plan.premium_themes_enabled:
            messages.error(request, f"Theme '{theme.name}' is a Premium Theme. Please upgrade your subscription to use it.")
            return redirect("payments:billing")
            
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
