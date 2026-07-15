from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from allauth.account.utils import get_next_redirect_url

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Overrides get_connect_redirect_url to always redirect users back to the original 
    dashboard or next parameter URL, ensuring they do not remain on the connections page.
    """
    def get_connect_redirect_url(self, request, socialaccount):
        # 1. First, check if there is a safe next parameter passed
        next_url = get_next_redirect_url(request)
        if next_url:
            return next_url

        # 2. If no next parameter, redirect to the user's latest portfolio's GitHub deployment dashboard
        from portfolio.models import Portfolio
        user = request.user
        if user.is_authenticated:
            portfolio = Portfolio.objects.filter(user=user).order_by("-updated_at").first()
            if portfolio:
                return reverse("github:dashboard", kwargs={"pk": portfolio.pk})

        # 3. Fallback to portfolio list page
        return reverse("portfolio:list")
