"""
Module 14: Team Collaboration & Organization Workspace — forms.py

Django Forms for organization creation, editing, and invitations.
"""
from django import forms
from django.contrib.auth import get_user_model
from .models import Organization, Invitation, OrganizationMember

User = get_user_model()


class OrganizationForm(forms.ModelForm):
    """Form to create or update an Organization."""
    class Meta:
        model = Organization
        fields = ["name", "description", "logo"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control rounded-lg",
                "placeholder": "e.g. Acme Tech Corporation",
                "id": "id_org_name",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control rounded-2xl",
                "placeholder": "Briefly describe your team's mission...",
                "rows": 3,
                "id": "id_org_desc",
            }),
            "logo": forms.FileInput(attrs={
                "class": "form-control rounded-lg",
                "id": "id_org_logo",
            }),
        }
        labels = {
            "name": "Organization Name",
            "description": "Description (optional)",
            "logo": "Workspace Logo (optional)",
        }


class InviteMemberForm(forms.ModelForm):
    """Form to invite a new user to join the organization."""
    class Meta:
        model = Invitation
        fields = ["email", "role"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "form-control rounded-lg",
                "placeholder": "collaborator@company.com",
                "id": "id_invite_email",
            }),
            "role": forms.Select(attrs={
                "class": "form-select rounded-lg",
                "id": "id_invite_role",
            }),
        }
        labels = {
            "email": "Collaborator's Email",
            "role": "Assigned Team Role",
        }
        help_texts = {
            "role": "Choose permissions: Editor can modify, Admin manages, Viewer is read-only.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent inviting someone as OWNER directly
        self.fields["role"].choices = [
            c for c in OrganizationMember.Role.choices if c[0] != OrganizationMember.Role.OWNER
        ]
