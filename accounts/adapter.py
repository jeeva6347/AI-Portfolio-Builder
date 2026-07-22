from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from allauth.account.utils import get_next_redirect_url


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Overrides get_connect_redirect_url to redirect users to the dashboard home or next URL.
    """
    def get_connect_redirect_url(self, request, socialaccount):
        # 1. First, check if there is a safe next parameter passed
        next_url = get_next_redirect_url(request)
        if next_url:
            return next_url

        # 2. Redirect to dashboard home
        return reverse("dashboard:home")
