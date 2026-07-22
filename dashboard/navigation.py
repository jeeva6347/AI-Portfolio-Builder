from django.urls import reverse_lazy

SIDEBAR_NAVIGATION = [
    {
        "title": "Dashboard",
        "icon": "bi-grid-1x2-fill",
        "url": "dashboard:home",
        "name": "dashboard",
    },
    {
        "title": "Themes Gallery",
        "icon": "bi-palette-fill",
        "url": "themes:gallery",
        "name": "my_themes",
    },
    {
        "title": "GitHub",
        "icon": "bi-github",
        "url": "github:index",
        "name": "github",
    },
    {
        "title": "Profile",
        "icon": "bi-person-circle",
        "url": "dashboard:profile",
        "name": "profile",
    },
]


def get_sidebar_navigation(user):
    """Returns sidebar navigation links for authenticated users."""
    if not user.is_authenticated:
        return []

    nav = []
    for item in SIDEBAR_NAVIGATION:
        try:
            resolved_url = reverse_lazy(item["url"])
        except Exception:
            resolved_url = "#"

        nav_item = item.copy()
        nav_item["url"] = resolved_url
        nav.append(nav_item)

    return nav
