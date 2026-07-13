from django import forms
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


class PortfolioForm(forms.ModelForm):
    """
    Form to manage the primary personal, contact, social,
    and footer details of the user portfolio.
    """
    class Meta:
        model = Portfolio
        fields = (
            "name",
            "title",
            "tagline",
            "about",
            "photo",
            "cover",
            "email",
            "phone",
            "address",
            "resume",
            "social_github",
            "social_linkedin",
            "social_twitter",
            "social_instagram",
            "social_youtube",
            "social_facebook",
            "social_portfolio",
            "contact_email",
            "contact_phone",
            "contact_address",
            "contact_form_action",
            "footer_copyright",
            "footer_tagline",
        )
        widgets = {
            "about": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
            "tagline": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Full-Stack Developer"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "City, Country"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "social_github": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://github.com/..."}),
            "social_linkedin": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://linkedin.com/in/..."}),
            "social_twitter": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://twitter.com/..."}),
            "social_instagram": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://instagram.com/..."}),
            "social_youtube": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://youtube.com/..."}),
            "social_facebook": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://facebook.com/..."}),
            "social_portfolio": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "footer_copyright": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. © 2026 Name. All rights reserved."}),
            "footer_tagline": forms.TextInput(attrs={"class": "form-control"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "contact_address": forms.TextInput(attrs={"class": "form-control"}),
            "contact_form_action": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://formspree.io/f/..."}),
        }


class PortfolioSkillForm(forms.ModelForm):
    class Meta:
        model = PortfolioSkill
        fields = ("skill_type", "name", "level")
        widgets = {
            "skill_type": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Python, Public Speaking"}),
            "level": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Advanced, Expert (optional)"}),
        }


class PortfolioProjectForm(forms.ModelForm):
    class Meta:
        model = PortfolioProject
        fields = ("title", "description", "technologies", "github_url", "live_url", "image", "order")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Project Title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "technologies": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Django, Tailwind, MySQL"}),
            "github_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "GitHub Repository Link"}),
            "live_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "Live Demo Link"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class PortfolioExperienceForm(forms.ModelForm):
    class Meta:
        model = PortfolioExperience
        fields = ("company", "position", "duration", "description", "order")
        widgets = {
            "company": forms.TextInput(attrs={"class": "form-control", "placeholder": "Company Name"}),
            "position": forms.TextInput(attrs={"class": "form-control", "placeholder": "Job Title"}),
            "duration": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Jan 2020 - Present"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class PortfolioEducationForm(forms.ModelForm):
    class Meta:
        model = PortfolioEducation
        fields = ("degree", "college", "university", "year", "order")
        widgets = {
            "degree": forms.TextInput(attrs={"class": "form-control", "placeholder": "Degree e.g. B.S. in Computer Science"}),
            "college": forms.TextInput(attrs={"class": "form-control", "placeholder": "College / school"}),
            "university": forms.TextInput(attrs={"class": "form-control", "placeholder": "University (optional)"}),
            "year": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 2020 or 2016 - 2020"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class PortfolioCertificateForm(forms.ModelForm):
    class Meta:
        model = PortfolioCertificate
        fields = ("name", "issuer", "year", "url")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "issuer": forms.TextInput(attrs={"class": "form-control"}),
            "year": forms.TextInput(attrs={"class": "form-control"}),
            "url": forms.URLInput(attrs={"class": "form-control"}),
        }


class PortfolioServiceForm(forms.ModelForm):
    class Meta:
        model = PortfolioService
        fields = ("title", "description", "icon")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "bi-gear-fill"}),
        }


class PortfolioTestimonialForm(forms.ModelForm):
    class Meta:
        model = PortfolioTestimonial
        fields = ("reviewer_name", "reviewer_role", "text")
        widgets = {
            "reviewer_name": forms.TextInput(attrs={"class": "form-control"}),
            "reviewer_role": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. CEO at Startup"}),
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
