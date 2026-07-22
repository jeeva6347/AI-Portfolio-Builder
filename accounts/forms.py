from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class EmailSignupForm(UserCreationForm):
    """
    Email + password registration form.
    New signups always start with role=FREE_USER; role escalation to
    PREMIUM_USER happens via the payments module, and ADMIN/SUPER_ADMIN
    is a Super Admin dashboard action only — never self-service.
    """

    email = forms.EmailField(required=True)
    avatar = forms.ImageField(required=False, help_text="Optional profile picture.")

    class Meta:
        model = User
        fields = ("username", "email", "avatar")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = User.Role.FREE_USER
        if self.cleaned_data.get("avatar"):
            user.avatar = self.cleaned_data["avatar"]
        if commit:
            user.save()
        return user


class EmailLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False, initial=True)


class ProfileForm(forms.ModelForm):
    """Lets a logged-in user update their own profile picture and GitHub username."""

    class Meta:
        model = User
        fields = ("avatar", "github_username")
