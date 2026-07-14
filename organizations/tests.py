"""
Module 14: Team Collaboration & Organization Workspace — tests.py

Unit and integration tests verifying organization setups, invitations, roles,
permissions, shared portfolios access control, and activity logging.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import PermissionDenied

from payments.models import SubscriptionPlan
from portfolio.models import Portfolio
from themes.models import Theme, ThemeCategory
from organizations.models import Organization, OrganizationMember, Invitation, ActivityLog
from organizations.services.org_service import (
    create_organization,
    invite_member,
    accept_invitation,
    remove_member,
    leave_organization,
    change_member_role,
    transfer_ownership,
    check_portfolio_collaboration_permission,
)

User = get_user_model()


class OrganizationCollaborationTestCase(TestCase):
    """
    Test suite verifying organization mappings, collaborator roles,
    invitations flow, activity feeds, and shared portfolio access rights.
    """

    def setUp(self):
        # Setup plans
        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            slug="free",
            defaults={
                "name": "Free Plan",
                "price": 0.00,
                "portfolio_limit": 1,
            }
        )

        # Create Users
        self.owner_user = User.objects.create_user(
            username="owner_guy", email="owner@acme.com", password="pwd"
        )
        self.admin_user = User.objects.create_user(
            username="admin_guy", email="admin@acme.com", password="pwd"
        )
        self.editor_user = User.objects.create_user(
            username="editor_guy", email="editor@acme.com", password="pwd"
        )
        self.viewer_user = User.objects.create_user(
            username="viewer_guy", email="viewer@acme.com", password="pwd"
        )

        # Create Theme
        self.theme_cat = ThemeCategory.objects.create(name="Modern", slug="modern")
        self.theme = Theme.objects.create(
            name="Classic Minimal",
            slug="classic-minimal",
            category=self.theme_cat,
            status=Theme.Status.APPROVED,
        )

    def test_create_organization(self):
        """Verify organization setup registers OWNER member and logs activity."""
        org, error = create_organization(self.owner_user, "Acme Corporation", "Acme headquarters.")
        self.assertIsNotNone(org)
        self.assertEqual(error, "")
        self.assertEqual(org.owner, self.owner_user)
        self.assertEqual(org.slug, "acme-corporation")

        # Verify Owner membership
        member = OrganizationMember.objects.filter(organization=org, user=self.owner_user).first()
        self.assertIsNotNone(member)
        self.assertEqual(member.role, OrganizationMember.Role.OWNER)

        # Verify Activity Log
        log = ActivityLog.objects.filter(organization=org, user=self.owner_user).first()
        self.assertIsNotNone(log)
        self.assertIn("created the organization", log.action)

    def test_invite_member(self):
        """Verify sending invitations creates a pending invite record with token."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        
        invite, error = invite_member(org, self.owner_user, "admin@acme.com", "ADMIN")
        self.assertIsNotNone(invite)
        self.assertEqual(error, "")
        self.assertEqual(invite.email, "admin@acme.com")
        self.assertEqual(invite.role, "ADMIN")
        self.assertEqual(invite.status, Invitation.Status.PENDING)
        self.assertIsNotNone(invite.token)
        self.assertTrue(invite.is_valid)

        # Activity log checked
        log = ActivityLog.objects.filter(organization=org, user=self.owner_user).first()
        self.assertIn("invited 'admin@acme.com'", log.action)

    def test_invite_permission_denied(self):
        """Verify Editors / Viewers cannot invite members to the team."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        
        # Add a viewer member
        OrganizationMember.objects.create(
            organization=org, user=self.viewer_user, role=OrganizationMember.Role.VIEWER
        )

        invite, error = invite_member(org, self.viewer_user, "test@acme.com", "EDITOR")
        self.assertNil = invite
        self.assertIn("Permission denied", error)

    def test_accept_invitation(self):
        """Verify accepting active invitation adds member and changes status."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        invite, _ = invite_member(org, self.owner_user, "admin@acme.com", "ADMIN")

        # Accept
        member, error = accept_invitation(self.admin_user, invite.token)
        self.assertIsNotNone(member)
        self.assertEqual(error, "")
        self.assertEqual(member.role, OrganizationMember.Role.ADMIN)
        self.assertTrue(member.active)

        invite.refresh_from_db()
        self.assertEqual(invite.status, Invitation.Status.ACCEPTED)

        # Log check
        log = ActivityLog.objects.filter(organization=org, user=self.admin_user).first()
        self.assertIn("joined the team", log.action)

    def test_accept_expired_invitation_rejected(self):
        """Verify expired invitations are rejected and status set to expired."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        invite, _ = invite_member(org, self.owner_user, "admin@acme.com", "ADMIN")

        # Fast forward time to expire invitation
        invite.expires_at = timezone.now() - timedelta(days=1)
        invite.save()

        member, error = accept_invitation(self.admin_user, invite.token)
        self.assertIsNone(member)
        self.assertIn("expired", error)

    def test_accept_email_mismatch_rejected(self):
        """Verify invitation cannot be accepted by a different email address."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        invite, _ = invite_member(org, self.owner_user, "admin@acme.com", "ADMIN")

        member, error = accept_invitation(self.viewer_user, invite.token) # viewer has viewer@acme.com email
        self.assertIsNone(member)
        self.assertIn("different email address", error)

    def test_remove_member(self):
        """Verify Owners can remove team members."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        member = OrganizationMember.objects.create(
            organization=org, user=self.admin_user, role=OrganizationMember.Role.ADMIN
        )

        success, error = remove_member(org, self.owner_user, member.id)
        self.assertTrue(success)
        self.assertFalse(OrganizationMember.objects.filter(id=member.id).exists())

    def test_remove_owner_rejected(self):
        """Verify Owner cannot be removed from the team."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        owner_member = OrganizationMember.objects.filter(organization=org, user=self.owner_user).first()

        # Admin user tries to remove owner
        admin_member = OrganizationMember.objects.create(
            organization=org, user=self.admin_user, role=OrganizationMember.Role.ADMIN
        )

        success, error = remove_member(org, self.admin_user, owner_member.id)
        self.assertFalse(success)
        self.assertIn("owner cannot be removed", error)

    def test_change_member_role(self):
        """Verify role changes are restricted to Owners/Admins."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        editor_member = OrganizationMember.objects.create(
            organization=org, user=self.editor_user, role=OrganizationMember.Role.EDITOR
        )

        success, error = change_member_role(org, self.owner_user, editor_member.id, "VIEWER")
        self.assertTrue(success)
        editor_member.refresh_from_db()
        self.assertEqual(editor_member.role, OrganizationMember.Role.VIEWER)

    def test_transfer_ownership(self):
        """Verify Owner can transfer workspace ownership to Admin."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        admin_member = OrganizationMember.objects.create(
            organization=org, user=self.admin_user, role=OrganizationMember.Role.ADMIN
        )

        success, error = transfer_ownership(org, self.owner_user, admin_member.id)
        self.assertTrue(success)
        org.refresh_from_db()
        self.assertEqual(org.owner, self.admin_user)

        # Check downgraded former owner role
        owner_membership = OrganizationMember.objects.filter(organization=org, user=self.owner_user).first()
        self.assertEqual(owner_membership.role, OrganizationMember.Role.ADMIN)

    def test_leave_organization(self):
        """Verify Admins/Editors can leave organizations, but Owners cannot leave directly."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        admin_member = OrganizationMember.objects.create(
            organization=org, user=self.admin_user, role=OrganizationMember.Role.ADMIN
        )

        # Admin leaves
        success, error = leave_organization(org, self.admin_user)
        self.assertTrue(success)

        # Owner tries to leave
        success2, error2 = leave_organization(org, self.owner_user)
        self.assertFalse(success2)
        self.assertIn("transfer ownership first", error2)

    def test_shared_portfolio_collaboration_permissions(self):
        """Verify collaboration permissions hierarchy checks."""
        org, _ = create_organization(self.owner_user, "Acme Corp")
        portfolio = Portfolio.objects.create(
            user=self.owner_user,
            name="Shared Site",
            selected_theme=self.theme,
            organization=org,
        )

        admin = OrganizationMember.objects.create(
            organization=org, user=self.admin_user, role=OrganizationMember.Role.ADMIN
        )
        editor = OrganizationMember.objects.create(
            organization=org, user=self.editor_user, role=OrganizationMember.Role.EDITOR
        )
        viewer = OrganizationMember.objects.create(
            organization=org, user=self.viewer_user, role=OrganizationMember.Role.VIEWER
        )

        # 1. OWNER permission
        self.assertTrue(check_portfolio_collaboration_permission(portfolio, self.owner_user, "ADMIN"))
        
        # 2. ADMIN permission on portfolio
        self.assertTrue(check_portfolio_collaboration_permission(portfolio, self.admin_user, "ADMIN"))
        self.assertTrue(check_portfolio_collaboration_permission(portfolio, self.admin_user, "EDITOR"))

        # 3. EDITOR permission on portfolio
        self.assertFalse(check_portfolio_collaboration_permission(portfolio, self.editor_user, "ADMIN"))
        self.assertTrue(check_portfolio_collaboration_permission(portfolio, self.editor_user, "EDITOR"))

        # 4. VIEWER permission on portfolio
        self.assertFalse(check_portfolio_collaboration_permission(portfolio, self.viewer_user, "EDITOR"))
        self.assertTrue(check_portfolio_collaboration_permission(portfolio, self.viewer_user, "VIEWER"))

    def test_unauthorized_dashboard_access_rejected(self):
        """Verify non-members are rejected with 403 when accessing organization dashboards."""
        org, _ = create_organization(self.owner_user, "Acme Corp")

        self.client.login(username="viewer_guy", password="pwd")
        res = self.client.get(reverse("organizations:dashboard", kwargs={"slug": org.slug}))
        self.assertEqual(res.status_code, 403)
