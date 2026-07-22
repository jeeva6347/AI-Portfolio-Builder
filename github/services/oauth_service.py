from allauth.socialaccount.models import SocialToken, SocialAccount


def get_github_token(user) -> str:
    """
    Retrieves the active GitHub OAuth access token from allauth storage.
    """
    if not user or not user.is_authenticated:
        return None

    token_obj = SocialToken.objects.filter(
        account__user=user,
        account__provider="github"
    ).first()
    if token_obj:
        return token_obj.token
    return None


def is_github_connected(user) -> bool:
    """
    Checks if the user has a linked GitHub social account connection.
    """
    if not user or not user.is_authenticated:
        return False

    return SocialAccount.objects.filter(user=user, provider="github").exists()


def get_github_username(user) -> str:
    """
    Retrieves the connected user's GitHub username from their social profile.
    """
    if not user or not user.is_authenticated:
        return ""

    account = SocialAccount.objects.filter(user=user, provider="github").first()
    if account and account.extra_data:
        return account.extra_data.get("login", "")
    return getattr(user, "github_username", "")


def disconnect_github(user):
    """
    Revokes the user's GitHub OAuth connection.
    """
    if not user or not user.is_authenticated:
        return

    SocialAccount.objects.filter(user=user, provider="github").delete()
