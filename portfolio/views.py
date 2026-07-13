from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
import os
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, HttpResponseForbidden

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


def _base_context(request, active_tab="personal"):
    """Helper to return consistent navigation context for portfolio views."""
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "active_tab": active_tab,
    }


# ── PORTFOLIO BUILDER WORKSPACE ───────────────────────────────────────────────

class PortfolioBuilderView(LoginRequiredMixin, View):
    """
    Main tabbed visual workspace for editing all portfolio details,
    social links, and footer configurations.
    """
    template_name = "portfolio/builder.html"
    login_url = "/accounts/login/"

    def get(self, request):
        portfolio, _ = Portfolio.objects.get_or_create(user=request.user)
        active_tab = request.GET.get("tab", "personal")
        
        ctx = _base_context(request, active_tab)
        ctx.update({
            "portfolio": portfolio,
            "form": PortfolioForm(instance=portfolio),
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Portfolio Builder", "url": "#"},
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

    def post(self, request):
        portfolio, _ = Portfolio.objects.get_or_create(user=request.user)
        active_tab = request.POST.get("tab", "personal")
        form = PortfolioForm(request.POST, request.FILES, instance=portfolio)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Portfolio information updated successfully.")
            return redirect(f"{reverse('portfolio:builder')}?tab={active_tab}")
            
        ctx = _base_context(request, active_tab)
        ctx.update({
            "portfolio": portfolio,
            "form": form,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Portfolio Builder", "url": "#"},
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


# ── SUB-ITEM CREATE VIEWS ────────────────────────────────────────────────────

class SkillCreateView(LoginRequiredMixin, View):
    def post(self, request):
        portfolio = get_object_or_404(Portfolio, user=request.user)
        form = PortfolioSkillForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.portfolio = portfolio
            skill.save()
            messages.success(request, f"Added skill '{skill.name}'.")
        else:
            messages.error(request, "Invalid skill data.")
        return redirect(f"{reverse('portfolio:builder')}?tab=skills")


class ProjectCreateView(LoginRequiredMixin, View):
    def post(self, request):
        portfolio = get_object_or_404(Portfolio, user=request.user)
        form = PortfolioProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.portfolio = portfolio
            project.save()
            messages.success(request, f"Added project '{project.title}'.")
        else:
            messages.error(request, "Invalid project data.")
        return redirect(f"{reverse('portfolio:builder')}?tab=projects")


class ExperienceCreateView(LoginRequiredMixin, View):
    def post(self, request):
        portfolio = get_object_or_404(Portfolio, user=request.user)
        form = PortfolioExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.portfolio = portfolio
            experience.save()
            messages.success(request, f"Added experience at '{experience.company}'.")
        else:
            messages.error(request, "Invalid experience data.")
        return redirect(f"{reverse('portfolio:builder')}?tab=experience")


class EducationCreateView(LoginRequiredMixin, View):
    def post(self, request):
        portfolio = get_object_or_404(Portfolio, user=request.user)
        form = PortfolioEducationForm(request.POST)
        if form.is_valid():
            edu = form.save(commit=False)
            edu.portfolio = portfolio
            edu.save()
            messages.success(request, f"Added education '{edu.degree}'.")
        else:
            messages.error(request, "Invalid education data.")
        return redirect(f"{reverse('portfolio:builder')}?tab=education")


class CertificateCreateView(LoginRequiredMixin, View):
    def post(self, request):
        portfolio = get_object_or_404(Portfolio, user=request.user)
        form = PortfolioCertificateForm(request.POST)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.portfolio = portfolio
            cert.save()
            messages.success(request, f"Added certificate '{cert.name}'.")
        else:
            messages.error(request, "Invalid certificate data.")
        return redirect(f"{reverse('portfolio:builder')}?tab=certificates")


class ServiceCreateView(LoginRequiredMixin, View):
    def post(self, request):
        portfolio = get_object_or_404(Portfolio, user=request.user)
        form = PortfolioServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.portfolio = portfolio
            service.save()
            messages.success(request, f"Added service '{service.title}'.")
        else:
            messages.error(request, "Invalid service data.")
        return redirect(f"{reverse('portfolio:builder')}?tab=services")


class TestimonialCreateView(LoginRequiredMixin, View):
    def post(self, request):
        portfolio = get_object_or_404(Portfolio, user=request.user)
        form = PortfolioTestimonialForm(request.POST)
        if form.is_valid():
            test = form.save(commit=False)
            test.portfolio = portfolio
            test.save()
            messages.success(request, f"Added testimonial from '{test.reviewer_name}'.")
        else:
            messages.error(request, "Invalid testimonial data.")
        return redirect(f"{reverse('portfolio:builder')}?tab=testimonials")


# ── SUB-ITEM DELETE VIEWS ────────────────────────────────────────────────────

class SkillDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        skill = get_object_or_404(PortfolioSkill, pk=pk)
        if skill.portfolio.user != request.user:
            return HttpResponseForbidden()
        name = skill.name
        skill.delete()
        messages.success(request, f"Deleted skill '{name}'.")
        return redirect(f"{reverse('portfolio:builder')}?tab=skills")


class ProjectDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(PortfolioProject, pk=pk)
        if project.portfolio.user != request.user:
            return HttpResponseForbidden()
        title = project.title
        project.delete()
        messages.success(request, f"Deleted project '{title}'.")
        return redirect(f"{reverse('portfolio:builder')}?tab=projects")


class ExperienceDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        exp = get_object_or_404(PortfolioExperience, pk=pk)
        if exp.portfolio.user != request.user:
            return HttpResponseForbidden()
        company = exp.company
        exp.delete()
        messages.success(request, f"Deleted experience at '{company}'.")
        return redirect(f"{reverse('portfolio:builder')}?tab=experience")


class EducationDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        edu = get_object_or_404(PortfolioEducation, pk=pk)
        if edu.portfolio.user != request.user:
            return HttpResponseForbidden()
        degree = edu.degree
        edu.delete()
        messages.success(request, f"Deleted education '{degree}'.")
        return redirect(f"{reverse('portfolio:builder')}?tab=education")


class CertificateDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cert = get_object_or_404(PortfolioCertificate, pk=pk)
        if cert.portfolio.user != request.user:
            return HttpResponseForbidden()
        name = cert.name
        cert.delete()
        messages.success(request, f"Deleted certificate '{name}'.")
        return redirect(f"{reverse('portfolio:builder')}?tab=certificates")


class ServiceDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        service = get_object_or_404(PortfolioService, pk=pk)
        if service.portfolio.user != request.user:
            return HttpResponseForbidden()
        title = service.title
        service.delete()
        messages.success(request, f"Deleted service '{title}'.")
        return redirect(f"{reverse('portfolio:builder')}?tab=services")


class TestimonialDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        test = get_object_or_404(PortfolioTestimonial, pk=pk)
        if test.portfolio.user != request.user:
            return HttpResponseForbidden()
        name = test.reviewer_name
        test.delete()
        messages.success(request, f"Deleted testimonial from '{name}'.")
        return redirect(f"{reverse('portfolio:builder')}?tab=testimonials")


# ── THEME SELECTION & LIVE PREVIEW ───────────────────────────────────────────

class SelectThemeView(LoginRequiredMixin, View):
    """
    Renders themes lists allowing user to select a template layout
    for their active portfolio presentation.
    """
    template_name = "portfolio/select_theme.html"

    def get(self, request):
        portfolio, _ = Portfolio.objects.get_or_create(user=request.user)
        themes = Theme.objects.filter(status=Theme.Status.APPROVED)
        ctx = _base_context(request, "theme")
        ctx.update({
            "portfolio": portfolio,
            "themes": themes,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Select Theme", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)

    def post(self, request):
        portfolio, _ = Portfolio.objects.get_or_create(user=request.user)
        theme_id = request.POST.get("theme_id")
        if theme_id:
            theme = get_object_or_404(Theme, pk=theme_id, status=Theme.Status.APPROVED)
            portfolio.selected_theme = theme
            portfolio.save(update_fields=["selected_theme"])
            messages.success(request, f"Successfully activated theme '{theme.name}'.")
        else:
            portfolio.selected_theme = None
            portfolio.save(update_fields=["selected_theme"])
            messages.success(request, "Theme de-activated. Portfolio is now unmapped.")
        return redirect("portfolio:select_theme")


class UserPortfolioPreview(LoginRequiredMixin, View):
    """
    Live portfolio compiler that renders the user's active theme
    populated with their own dynamic database values.
    """
    def get(self, request):
        portfolio = get_object_or_404(Portfolio, user=request.user)
        theme = portfolio.selected_theme
        
        if not theme:
            return HttpResponse(
                "<h3>No active theme selected.</h3><p>Please select a theme from the "
                "<a href='/portfolio/theme/' target='_parent'>Select Theme</a> tab to preview your portfolio.</p>",
                content_type="text/html"
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
        
        return HttpResponse(compiled_html, content_type="text/html")
