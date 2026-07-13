from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sessions.models import Session
from django.utils import timezone

from .forms import EmailSignupForm, EmailLoginForm, ProfileForm

User = get_user_model()


class SignupView(FormView):
    template_name = "accounts/signup.html"
    form_class = EmailSignupForm
    success_url = reverse_lazy("accounts:dashboard_redirect")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(self.request, "Account created successfully.")
        return super().form_valid(form)


class EmailLoginView(FormView):
    template_name = "accounts/login.html"
    form_class = EmailLoginForm
    success_url = reverse_lazy("accounts:dashboard_redirect")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        remember_me = form.cleaned_data.get("remember_me", True)

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            form.add_error(None, "Invalid email or password.")
            return self.form_invalid(form)

        user = authenticate(
            self.request, username=user_obj.username, password=password
        )
        if user is None:
            form.add_error(None, "Invalid email or password.")
            return self.form_invalid(form)

        login(self.request, user)

        # Remember Me: checked -> session persists for SESSION_COOKIE_AGE
        # (default 2 weeks, see settings.py). Unchecked -> session ends
        # when the browser closes.
        if remember_me:
            self.request.session.set_expiry(None)  # use SESSION_COOKIE_AGE
        else:
            self.request.session.set_expiry(0)  # expire on browser close

        return super().form_valid(form)


class LogoutView(View):
    def post(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect("accounts:login")


@login_required
def dashboard_redirect(request):
    """
    Routes an authenticated user to the correct dashboard based on role.
    """
    user = request.user
    if user.is_super_admin:
        return redirect("dashboard:super_admin")
    elif user.is_platform_admin:
        return redirect("dashboard:admin")
    else:
        return redirect("dashboard:user")


class ProfileView(LoginRequiredMixin, UpdateView):
    """Lets a logged-in user update their avatar and GitHub username."""

    login_url = reverse_lazy("accounts:login")

    model = User
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


@login_required
def sessions_view(request):
    """
    Session management: lists this user's active sessions and lets them
    revoke all other sessions (e.g. after a password change or if they
    suspect unauthorized access).
    """
    if request.method == "POST" and request.POST.get("action") == "revoke_others":
        current_key = request.session.session_key
        revoked = 0
        for session in Session.objects.filter(expire_date__gte=timezone.now()):
            data = session.get_decoded()
            if str(data.get("_auth_user_id")) == str(request.user.pk) and session.session_key != current_key:
                session.delete()
                revoked += 1
        messages.success(request, f"Signed out of {revoked} other session(s).")
        return redirect("accounts:sessions")

    active_sessions = []
    current_key = request.session.session_key
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(request.user.pk):
            active_sessions.append(
                {
                    "key": session.session_key,
                    "expire_date": session.expire_date,
                    "is_current": session.session_key == current_key,
                }
            )

    return render(request, "accounts/sessions.html", {"sessions": active_sessions})


# --- Password reset (Django's built-in views, styled with our templates) ---

class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
