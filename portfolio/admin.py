from django.contrib import admin
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


class PortfolioSkillInline(admin.TabularInline):
    model = PortfolioSkill
    extra = 0


class PortfolioProjectInline(admin.TabularInline):
    model = PortfolioProject
    extra = 0


class PortfolioExperienceInline(admin.TabularInline):
    model = PortfolioExperience
    extra = 0


class PortfolioEducationInline(admin.TabularInline):
    model = PortfolioEducation
    extra = 0


class PortfolioCertificateInline(admin.TabularInline):
    model = PortfolioCertificate
    extra = 0


class PortfolioServiceInline(admin.TabularInline):
    model = PortfolioService
    extra = 0


class PortfolioTestimonialInline(admin.TabularInline):
    model = PortfolioTestimonial
    extra = 0


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "title", "selected_theme", "created_at")
    search_fields = ("name", "user__username", "user__email")
    inlines = [
        PortfolioSkillInline,
        PortfolioProjectInline,
        PortfolioExperienceInline,
        PortfolioEducationInline,
        PortfolioCertificateInline,
        PortfolioServiceInline,
        PortfolioTestimonialInline,
    ]
