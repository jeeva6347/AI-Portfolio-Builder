"""
Module 14: Team Collaboration & Organization Workspace — views.py

Implements Class-Based Views for organization lists, dashboards, member roles,
invitations flow, portfolio sharing, and team activity auditing logs.
"""
import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponseForbidden, Http404
from django.urls import reverse
from django.db.models import Count

from dashboard.navigation import get_sidebar_navigation
from portfolio.models import Portfolio
from payments.permissions import get_user_plan_benefits

from .models import Organization, OrganizationMember, Invitation, ActivityLog
from .forms import OrganizationForm, InviteMemberForm
from .services.org_service import (
    create_organization,
    invite_member,
    accept_invitation,
    remove_member,
    leave_organization,
    change_member_role,
    transfer_ownership,
    log_activity,
)

logger = logging.getLogger(__name__)


def _base_context(request, active_tab: str = "organizations") -> dict:
    return {
        "sidebar_nav": get_sidebar_navigation(request.user),
        "active_tab": active_tab,
    }


# ── ORGANIZATION LIST ─────────────────────────────────────────────────────────

class OrganizationListView(LoginRequiredMixin, View):
    """Lists all organizations the user is currently associated with."""
    template_name = "organizations/list.html"

    def get(self, request):
        memberships = (
            OrganizationMember.objects
            .filter(user=request.user, active=True)
            .select_related("organization", "organization__owner")
        )
        ctx = _base_context(request)
        ctx.update({
            "memberships": memberships,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "My Teams", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)


# ── ORGANIZATION CREATE ───────────────────────────────────────────────────────

class OrganizationCreateView(LoginRequiredMixin, View):
    """Renders creation workspace form and processes organization setup."""
    template_name = "organizations/create.html"

    def get(self, request):
        form = OrganizationForm()
        ctx = _base_context(request)
        ctx.update({
            "form": form,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "My Teams", "url": reverse("organizations:list")},
                {"title": "New Workspace", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = OrganizationForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data["name"]
            desc = form.cleaned_data["description"]
            
            org, error = create_organization(request.user, name, desc)
            if org:
                # Handle logo if uploaded
                if "logo" in request.FILES:
                    org.logo = request.FILES["logo"]
                    org.save(update_fields=["logo"])
                    
                messages.success(request, f"Organization workspace '{org.name}' setup successfully!")
                return redirect("organizations:dashboard", slug=org.slug)
            else:
                messages.error(request, f"Failed to create workspace: {error}")

        ctx = _base_context(request)
        ctx.update({
            "form": form,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "My Teams", "url": reverse("organizations:list")},
                {"title": "New Workspace", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)


# ── ORGANIZATION DASHBOARD ────────────────────────────────────────────────────

class OrganizationDashboardView(LoginRequiredMixin, View):
    """Main hub for team portfolios, invitations, logs, and member roles."""
    template_name = "organizations/dashboard.html"

    def _check_membership(self, request, slug) -> Tuple[Optional[Organization], Optional[OrganizationMember]]:
        org = get_object_or_404(Organization, slug=slug)
        member = OrganizationMember.objects.filter(organization=org, user=request.user, active=True).first()
        return org, member

    def get(self, request, slug):
        org, member = self._check_membership(request, slug)
        if not member:
            return HttpResponseForbidden("You are not authorized to access this organization.")

        active_subtab = request.GET.get("tab", "portfolios")

        # Stats
        total_portfolios = Portfolio.objects.filter(organization=org).count()
        total_members = OrganizationMember.objects.filter(organization=org, active=True).count()
        total_invites = Invitation.objects.filter(organization=org, status=Invitation.Status.PENDING).count()

        # Collections
        portfolios = (
            Portfolio.objects
            .filter(organization=org)
            .select_related("selected_theme")
        )
        members = (
            OrganizationMember.objects
            .filter(organization=org)
            .select_related("user")
            .order_by("joined_at")
        )
        invites = (
            Invitation.objects
            .filter(organization=org, status=Invitation.Status.PENDING)
            .select_related("invited_by")
        )
        activities = (
            ActivityLog.objects
            .filter(organization=org)
            .select_related("user")[:15]
        )

        # Dropdown list of user's personal portfolios to associate
        personal_portfolios = (
            Portfolio.objects
            .filter(user=request.user, organization__isnull=True)
            .exclude(status=Portfolio.Status.ARCHIVED)
        )

        ctx = _base_context(request)
        ctx.update({
            "org": org,
            "member": member,
            "portfolios": portfolios,
            "members": members,
            "invites": invites,
            "activities": activities,
            "personal_portfolios": personal_portfolios,
            "invite_form": InviteMemberForm(),
            "total_portfolios": total_portfolios,
            "total_members": total_members,
            "total_invites": total_invites,
            "active_subtab": active_subtab,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "My Teams", "url": reverse("organizations:list")},
                {"title": org.name, "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)


# ── MEMBER MANAGEMENT ACTIONS ─────────────────────────────────────────────────

class InviteMemberView(LoginRequiredMixin, View):
    """Triggers an email invitation pipeline."""
    def post(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)
        form = InviteMemberForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            role = form.cleaned_data["role"]

            invite, error = invite_member(org, request.user, email, role)
            if invite:
                messages.success(request, f"Invitation sent successfully to '{email}' as {role}.")
            else:
                messages.error(request, f"Failed to send invitation: {error}")
        else:
            messages.error(request, "Invalid form data.")

        return redirect(f"{reverse('organizations:dashboard', kwargs={'slug': slug})}?tab=members")


class AcceptInviteView(LoginRequiredMixin, View):
    """Accepts invitation based on token."""
    template_name = "organizations/accept_invite.html"

    def get(self, request, token):
        invite = get_object_or_404(Invitation, token=token)
        if not invite.is_valid:
            messages.error(request, "This invitation link is invalid or expired.")
            return redirect("organizations:list")

        ctx = _base_context(request)
        ctx.update({
            "invite": invite,
            "breadcrumbs": [
                {"title": "Dashboard", "url": "#"},
                {"title": "Join Team", "url": "#"},
            ],
        })
        return render(request, self.template_name, ctx)

    def post(self, request, token):
        member, error = accept_invitation(request.user, token)
        if member:
            messages.success(request, f"Welcome to the team! You have joined '{member.organization.name}'.")
            return redirect("organizations:dashboard", slug=member.organization.slug)
        else:
            messages.error(request, f"Could not accept invite: {error}")
            return redirect("organizations:list")


class RemoveMemberView(LoginRequiredMixin, View):
    """Disconnects collaborator from team roster."""
    def post(self, request, slug, member_id):
        org = get_object_or_404(Organization, slug=slug)
        success, error = remove_member(org, request.user, member_id)
        if success:
            messages.success(request, "Team member removed successfully.")
        else:
            messages.error(request, f"Could not remove member: {error}")

        return redirect(f"{reverse('organizations:dashboard', kwargs={'slug': slug})}?tab=members")


class ChangeRoleView(LoginRequiredMixin, View):
    """Mutates member access privileges."""
    def post(self, request, slug, member_id):
        org = get_object_or_404(Organization, slug=slug)
        new_role = request.POST.get("role")
        success, error = change_member_role(org, request.user, member_id, new_role)
        if success:
            messages.success(request, f"Updated member permissions to {new_role}.")
        else:
            messages.error(request, f"Failed to modify role: {error}")

        return redirect(f"{reverse('organizations:dashboard', kwargs={'slug': slug})}?tab=members")


class TransferOwnershipView(LoginRequiredMixin, View):
    """Transfers the organization owner property."""
    def post(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)
        new_owner_id = request.POST.get("member_id")
        if not new_owner_id:
            messages.error(request, "No member selected for transfer.")
            return redirect(f"{reverse('organizations:dashboard', kwargs={'slug': slug})}?tab=members")

        success, error = transfer_ownership(org, request.user, int(new_owner_id))
        if success:
            messages.success(request, "Ownership transferred successfully. Your role is now Admin.")
        else:
            messages.error(request, f"Failed to transfer ownership: {error}")

        return redirect(f"{reverse('organizations:dashboard', kwargs={'slug': slug})}?tab=members")


class LeaveOrganizationView(LoginRequiredMixin, View):
    """Leaves organization workspace."""
    def post(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)
        success, error = leave_organization(org, request.user)
        if success:
            messages.success(request, f"You left '{org.name}' successfully.")
            return redirect("organizations:list")
        else:
            messages.error(request, f"Could not leave workspace: {error}")
            return redirect(f"{reverse('organizations:dashboard', kwargs={'slug': slug})}?tab=members")


# ── PORTFOLIO COLLABORATION ACTIONS ───────────────────────────────────────────

class LinkPortfolioView(LoginRequiredMixin, View):
    """Transfers a personal portfolio to be owned by the organization."""
    def post(self, request, slug):
        org = get_object_or_404(Organization, slug=slug)
        member = OrganizationMember.objects.filter(organization=org, user=request.user, active=True).first()
        if not member or member.role not in [OrganizationMember.Role.OWNER, OrganizationMember.Role.ADMIN]:
            return HttpResponseForbidden("Only Owners and Admins can link portfolios to this organization.")

        portfolio_pk = request.POST.get("portfolio_pk")
        portfolio = get_object_or_404(Portfolio, pk=portfolio_pk, user=request.user)

        portfolio.organization = org
        portfolio.save(update_fields=["organization"])

        # Log activity
        log_activity(org, request.user, f"linked portfolio '{portfolio.name}' to team", "Portfolio", portfolio.id)

        messages.success(request, f"Portfolio '{portfolio.name}' is now a shared team asset.")
        return redirect(f"{reverse('organizations:dashboard', kwargs={'slug': slug})}?tab=portfolios")


class UnlinkPortfolioView(LoginRequiredMixin, View):
    """Restores ownership of portfolio back to its original creator."""
    def post(self, request, slug, portfolio_id):
        org = get_object_or_404(Organization, slug=slug)
        member = OrganizationMember.objects.filter(organization=org, user=request.user, active=True).first()
        if not member or member.role not in [OrganizationMember.Role.OWNER, OrganizationMember.Role.ADMIN]:
            return HttpResponseForbidden("Only Owners and Admins can unlink portfolios.")

        portfolio = get_object_or_404(Portfolio, pk=portfolio_id, organization=org)
        
        # Verify unlinker is either Owner/Admin or the original owner of the portfolio
        portfolio.organization = None
        portfolio.save(update_fields=["organization"])

        # Log activity
        log_activity(org, request.user, f"unlinked portfolio '{portfolio.name}' from team", "Portfolio", portfolio.id)

        messages.success(request, f"Portfolio '{portfolio.name}' restored to personal assets.")
        return redirect(f"{reverse('organizations:dashboard', kwargs={'slug': slug})}?tab=portfolios")
