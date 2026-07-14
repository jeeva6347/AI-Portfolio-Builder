"""
Module 14: Team Collaboration & Organization Workspace — urls.py
"""
from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    path("", views.OrganizationListView.as_view(), name="list"),
    path("new/", views.OrganizationCreateView.as_view(), name="create"),
    path("workspace/<slug:slug>/", views.OrganizationDashboardView.as_view(), name="dashboard"),
    
    # Invitations
    path("workspace/<slug:slug>/invite/", views.InviteMemberView.as_view(), name="invite"),
    path("invitations/accept/<str:token>/", views.AcceptInviteView.as_view(), name="accept_invite"),
    
    # Team Actions
    path("workspace/<slug:slug>/members/remove/<int:member_id>/", views.RemoveMemberView.as_view(), name="remove_member"),
    path("workspace/<slug:slug>/members/role/<int:member_id>/", views.ChangeRoleView.as_view(), name="change_role"),
    path("workspace/<slug:slug>/transfer-ownership/", views.TransferOwnershipView.as_view(), name="transfer_ownership"),
    path("workspace/<slug:slug>/leave/", views.LeaveOrganizationView.as_view(), name="leave"),
    
    # Portfolio Link / Unlink
    path("workspace/<slug:slug>/portfolios/link/", views.LinkPortfolioView.as_view(), name="link_portfolio"),
    path("workspace/<slug:slug>/portfolios/unlink/<int:portfolio_id>/", views.UnlinkPortfolioView.as_view(), name="unlink_portfolio"),
]
