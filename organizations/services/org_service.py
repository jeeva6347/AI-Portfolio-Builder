"""
Module 14: Team Collaboration & Organization Workspace — services/org_service.py

Handles team features business logic: organization management, membership updates,
invitations flow, ownership transfer, activity logs, and permission helpers.
"""
import logging
from typing import Tuple, List, Optional
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from organizations.models import Organization, OrganizationMember, Invitation, ActivityLog
from portfolio.models import Portfolio

User = get_user_model()
logger = logging.getLogger(__name__)


def create_organization(user, name: str, description: str = "") -> Tuple[Organization, str]:
    """
    Creates a new organization and registers the creator as OWNER.
    """
    if not name.strip():
        return None, "Organization name cannot be empty."

    # Generate a unique slug
    base_slug = slugify(name)
    slug = base_slug
    counter = 1
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    try:
        with transaction.atomic():
            org = Organization.objects.create(
                name=name.strip(),
                slug=slug,
                owner=user,
                description=description,
            )
            # Create OWNER member record
            OrganizationMember.objects.create(
                organization=org,
                user=user,
                role=OrganizationMember.Role.OWNER,
                active=True,
            )
            
            # Log activity
            log_activity(org, user, "created the organization", "Organization", org.id)
            
        logger.info("Created organization: %s (slug: %s) by owner %s", org.name, org.slug, user.username)
        return org, ""
    except Exception as e:
        logger.error("Failed to create organization: %s", e)
        return None, f"Database error: {e}"


def invite_member(org: Organization, invited_by, email: str, role: str) -> Tuple[Invitation, str]:
    """
    Creates a pending Invitation record for the target email address.
    """
    email = email.lower().strip()
    if not email:
        return None, "Email address is required."

    if role not in OrganizationMember.Role.values:
        return None, "Invalid member role specified."

    # Verify user inviting has permission (OWNER or ADMIN)
    member = OrganizationMember.objects.filter(organization=org, user=invited_by, active=True).first()
    if not member or member.role not in [OrganizationMember.Role.OWNER, OrganizationMember.Role.ADMIN]:
        return None, "Permission denied. Only Owners and Admins can invite team members."

    # Verify user is not already an active member of this organization
    if OrganizationMember.objects.filter(organization=org, user__email=email, active=True).exists():
        return None, "A user with this email is already a member of this organization."

    # Expiry defaults to 7 days
    expires_at = timezone.now() + timedelta(days=7)

    # Cancel previous pending invitations for this email to avoid duplicates
    Invitation.objects.filter(organization=org, email=email, status=Invitation.Status.PENDING).update(
        status=Invitation.Status.CANCELLED
    )

    invite = Invitation(
        organization=org,
        email=email,
        role=role,
        invited_by=invited_by,
        expires_at=expires_at,
    )
    invite.generate_token()
    invite.save()

    # Log activity
    log_activity(org, invited_by, f"invited '{email}' as {role}", "Invitation", invite.id)
    
    # Notify (mock notifications module support)
    send_team_notification(
        org,
        f"Invitation sent to {email} by {invited_by.username}."
    )

    logger.info("Sent invite to %s for org %s by %s", email, org.name, invited_by.username)
    return invite, ""


def accept_invitation(user, token: str) -> Tuple[OrganizationMember, str]:
    """
    Validates the invite token and adds the user as an active OrganizationMember.
    """
    invite = Invitation.objects.filter(token=token).first()
    if not invite:
        return None, "Invalid invitation link."

    if not invite.is_valid:
        # Auto-update status if expired
        if invite.status == Invitation.Status.PENDING and invite.expires_at <= timezone.now():
            invite.status = Invitation.Status.EXPIRED
            invite.save(update_fields=["status"])
        return None, f"This invitation has already been {invite.status}."

    # Confirm email match (case-insensitive) or associate user
    if user.email.lower() != invite.email.lower():
        return None, "This invitation was sent to a different email address."

    try:
        with transaction.atomic():
            # Check if membership already exists (inactive or otherwise)
            member, created = OrganizationMember.objects.get_or_create(
                organization=invite.organization,
                user=user,
                defaults={
                    "role": invite.role,
                    "invited_by": invite.invited_by,
                    "active": True,
                }
            )
            if not created:
                member.role = invite.role
                member.active = True
                member.save()

            invite.status = Invitation.Status.ACCEPTED
            invite.save(update_fields=["status"])

            # Log activity
            log_activity(invite.organization, user, "joined the team", "Member", member.id)

            # Notify
            send_team_notification(
                invite.organization,
                f"{user.username} accepted invitation and joined as {invite.role}."
            )

        logger.info("User %s accepted invitation to org %s", user.username, invite.organization.name)
        return member, ""
    except Exception as e:
        logger.error("Failed to accept invitation: %s", e)
        return None, f"Database error: {e}"


def remove_member(org: Organization, actor, member_id: int) -> Tuple[bool, str]:
    """
    Removes a member from the organization.
    """
    actor_member = OrganizationMember.objects.filter(organization=org, user=actor, active=True).first()
    if not actor_member:
        return False, "You are not a member of this organization."

    target_member = OrganizationMember.objects.filter(id=member_id, organization=org).first()
    if not target_member:
        return False, "Target member not found in this organization."

    # Prevent removing the owner
    if target_member.role == OrganizationMember.Role.OWNER:
        return False, "The owner cannot be removed. Transfer ownership first."

    # Permission check: OWNER can remove anyone. ADMIN can remove ADMIN/EDITOR/VIEWER, but cannot remove OWNER.
    # EDITORS and VIEWERS cannot remove anyone.
    if actor_member.role == OrganizationMember.Role.OWNER:
        pass
    elif actor_member.role == OrganizationMember.Role.ADMIN:
        if target_member.role == OrganizationMember.Role.ADMIN and actor != target_member.user:
            # Admins cannot remove other Admins
            return False, "Admins cannot remove other Admins from the team."
    else:
        return False, "Permission denied. Only Owners and Admins can remove members."

    # Can remove self (Leave)
    if actor == target_member.user:
        return leave_organization(org, actor)

    target_user_name = target_member.user.username
    target_member.delete()

    # Log activity
    log_activity(org, actor, f"removed member '{target_user_name}'", "Member", member_id)

    # Notify
    send_team_notification(
        org,
        f"Member {target_user_name} was removed by {actor.username}."
    )

    logger.info("Removed member %s from org %s by %s", target_user_name, org.name, actor.username)
    return True, ""


def leave_organization(org: Organization, user) -> Tuple[bool, str]:
    """
    Allows a user to leave the organization.
    """
    member = OrganizationMember.objects.filter(organization=org, user=user, active=True).first()
    if not member:
        return False, "You are not a member of this organization."

    if member.role == OrganizationMember.Role.OWNER:
        return False, "Owners cannot leave the organization. You must transfer ownership first."

    username = user.username
    member.delete()

    # Log activity
    log_activity(org, user, "left the organization", "Member", member.id)

    # Notify
    send_team_notification(
        org,
        f"{username} has left the team."
    )

    return True, ""


def change_member_role(org: Organization, actor, member_id: int, new_role: str) -> Tuple[bool, str]:
    """
    Changes a member's role.
    """
    if new_role not in OrganizationMember.Role.values:
        return False, "Invalid role specified."

    actor_member = OrganizationMember.objects.filter(organization=org, user=actor, active=True).first()
    if not actor_member or actor_member.role not in [OrganizationMember.Role.OWNER, OrganizationMember.Role.ADMIN]:
        return False, "Permission denied. Only Owners and Admins can change member roles."

    target_member = OrganizationMember.objects.filter(id=member_id, organization=org).first()
    if not target_member:
        return False, "Member not found."

    if target_member.role == OrganizationMember.Role.OWNER:
        return False, "Cannot change the Owner's role. Use Transfer Ownership."

    if new_role == OrganizationMember.Role.OWNER:
        return False, "Cannot promote to Owner directly. Use Transfer Ownership."

    # Admins cannot demote or promote other Admins
    if actor_member.role == OrganizationMember.Role.ADMIN:
        if target_member.role == OrganizationMember.Role.ADMIN:
            return False, "Admins cannot change roles of other Admins."
        if new_role == OrganizationMember.Role.ADMIN:
            return False, "Admins cannot promote other members to Admin."

    old_role = target_member.role
    target_member.role = new_role
    target_member.save(update_fields=["role"])

    # Log activity
    log_activity(
        org,
        actor,
        f"changed role of {target_member.user.username} from {old_role} to {new_role}",
        "Member",
        target_member.id
    )

    return True, ""


def transfer_ownership(org: Organization, owner, new_owner_member_id: int) -> Tuple[bool, str]:
    """
    Transfers organization ownership to another active member.
    """
    owner_member = OrganizationMember.objects.filter(organization=org, user=owner, active=True).first()
    if not owner_member or owner_member.role != OrganizationMember.Role.OWNER:
        return False, "Only the owner can transfer ownership."

    target_member = OrganizationMember.objects.filter(id=new_owner_member_id, organization=org, active=True).first()
    if not target_member:
        return False, "Target member not found or inactive."

    if target_member.user == owner:
        return False, "You are already the owner."

    try:
        with transaction.atomic():
            # Update organization owner field
            org.owner = target_member.user
            org.save(update_fields=["owner"])

            # Downgrade former owner to ADMIN
            owner_member.role = OrganizationMember.Role.ADMIN
            owner_member.save(update_fields=["role"])

            # Upgrade new owner member record
            target_member.role = OrganizationMember.Role.OWNER
            target_member.save(update_fields=["role"])

            # Log activity
            log_activity(org, owner, f"transferred ownership to {target_member.user.username}", "Owner", target_member.id)

            # Notify
            send_team_notification(
                org,
                f"Ownership transferred from {owner.username} to {target_member.user.username}."
            )

        logger.info("Ownership of org %s transferred to %s", org.name, target_member.user.username)
        return True, ""
    except Exception as e:
        logger.error("Failed to transfer ownership: %s", e)
        return False, f"Database error: {e}"


def log_activity(org: Organization, user, action: str, object_type: str, object_id: Optional[int] = None) -> ActivityLog:
    """
    Writes a record to the team's ActivityLog.
    """
    return ActivityLog.objects.create(
        organization=org,
        user=user,
        action=action,
        object_type=object_type,
        object_id=object_id,
    )


def send_team_notification(org: Organization, message: str) -> None:
    """
    Helper function to publish messages to team notifications.
    Uses mock/stub logger log here to support notifications framework.
    """
    logger.info("[NOTIFICATION] Organization %s: %s", org.name, message)
    # If the project notifications app gets built out, we hook it here
    try:
        # Example notifications trigger if existing models exist
        pass
    except Exception:
        pass


def check_portfolio_collaboration_permission(portfolio: Portfolio, user, required_role: str) -> bool:
    """
    Checks if a user has permission to perform an action on a portfolio.
    If the portfolio is shared (owned by an organization), permission depends
    on the user's role in the organization:
    - OWNER: OWNER, ADMIN, EDITOR, VIEWER
    - ADMIN: ADMIN, EDITOR, VIEWER
    - EDITOR: EDITOR, VIEWER
    - VIEWER: VIEWER only

    If it's a personal portfolio, only the owner has access.
    """
    # Personal portfolio checks
    if not portfolio.organization:
        return portfolio.user == user

    # Organization mapped portfolio checks
    member = OrganizationMember.objects.filter(organization=portfolio.organization, user=user, active=True).first()
    if not member:
        return False

    role_hierarchy = {
        OrganizationMember.Role.OWNER: 4,
        OrganizationMember.Role.ADMIN: 3,
        OrganizationMember.Role.EDITOR: 2,
        OrganizationMember.Role.VIEWER: 1,
    }

    required_level = role_hierarchy.get(required_role, 1)
    user_level = role_hierarchy.get(member.role, 1)

    return user_level >= required_level
