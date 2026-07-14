"""
Module 13: Custom Domains — forms.py

Django ModelForms for domain creation and management.
"""
from django import forms
from .models import CustomDomain


class CustomDomainForm(forms.ModelForm):
    """
    Form for adding a new custom domain.
    Users provide the root domain, optional subdomain, provider, and
    preferred verification method.
    """

    class Meta:
        model = CustomDomain
        fields = ["domain_name", "subdomain", "provider", "verification_method"]
        widgets = {
            "domain_name": forms.TextInput(attrs={
                "class": "form-control rounded-lg",
                "placeholder": "e.g. myportfolio.com",
                "autocomplete": "off",
                "id": "id_domain_name",
            }),
            "subdomain": forms.TextInput(attrs={
                "class": "form-control rounded-lg",
                "placeholder": "e.g. www  (leave blank for root domain)",
                "autocomplete": "off",
                "id": "id_subdomain",
            }),
            "provider": forms.Select(attrs={
                "class": "form-select rounded-lg",
                "id": "id_provider",
            }),
            "verification_method": forms.RadioSelect(attrs={
                "class": "form-check-input",
            }),
        }
        labels = {
            "domain_name": "Root Domain",
            "subdomain": "Subdomain (optional)",
            "provider": "DNS Provider",
            "verification_method": "Verification Method",
        }
        help_texts = {
            "domain_name": "The base domain without www or subdomain prefix.",
            "subdomain": "Optional prefix, e.g. 'www' or 'portfolio'.",
            "verification_method": "Choose how to prove domain ownership.",
        }

    def clean_domain_name(self) -> str:
        value = self.cleaned_data.get("domain_name", "").strip().lower()
        # Strip leading http(s):// if user pastes a URL
        for prefix in ("https://", "http://", "www."):
            if value.startswith(prefix):
                value = value[len(prefix):]
        return value

    def clean_subdomain(self) -> str:
        return self.cleaned_data.get("subdomain", "").strip().lower()
