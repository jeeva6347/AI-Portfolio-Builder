from django.urls import reverse_lazy

SIDEBAR_NAVIGATION = [
    {
        "title": "Dashboard",
        "icon": "bi-grid-1x2-fill",
        "url": "dashboard:super_admin", # Handled dynamically in get_sidebar_navigation
        "required_role": ["SUPER_ADMIN", "ADMIN", "PREMIUM_USER", "FREE_USER"],
        "badge": None,
        "coming_soon": False,
        "name": "dashboard",
    },
    {
        "title": "Themes",
        "icon": "bi-palette-fill",
        "url": "themes:theme_list_admin",
        "required_role": ["SUPER_ADMIN", "ADMIN"],
        "badge": None,
        "coming_soon": False,
        "name": "themes",
    },
    {
        "title": "Portfolio",
        "icon": "bi-briefcase-fill",
        "url": "dashboard:portfolio_placeholder",
        "required_role": ["SUPER_ADMIN", "ADMIN", "PREMIUM_USER", "FREE_USER"],
        "badge": None,
        "coming_soon": True,
        "name": "portfolio",
    },
    {
        "title": "Marketplace",
        "icon": "bi-shop",
        "url": "themes:marketplace",
        "required_role": ["SUPER_ADMIN", "ADMIN", "PREMIUM_USER", "FREE_USER"],
        "badge": None,
        "coming_soon": False,
        "name": "marketplace",
    },
    {
        "title": "GitHub",
        "icon": "bi-github",
        "url": "dashboard:github_placeholder",
        "required_role": ["SUPER_ADMIN", "PREMIUM_USER", "FREE_USER"],
        "badge": None,
        "coming_soon": True,
        "name": "github",
    },
    {
        "title": "AI Content",
        "icon": "bi-robot",
        "url": "dashboard:ai_placeholder",
        "required_role": ["SUPER_ADMIN", "PREMIUM_USER", "FREE_USER"],
        "badge": "Beta",
        "coming_soon": True,
        "name": "ai",
    },
    {
        "title": "Analytics",
        "icon": "bi-graph-up",
        "url": "dashboard:analytics_placeholder",
        "required_role": ["SUPER_ADMIN", "PREMIUM_USER"],
        "badge": "Premium",
        "coming_soon": True,
        "name": "analytics",
    },
    {
        "title": "Payments",
        "icon": "bi-credit-card-fill",
        "url": "dashboard:payments_placeholder",
        "required_role": ["SUPER_ADMIN", "PREMIUM_USER", "FREE_USER"],
        "badge": None,
        "coming_soon": True,
        "name": "payments",
    },
    {
        "title": "Settings",
        "icon": "bi-gear-fill",
        "url": "dashboard:settings_placeholder",
        "required_role": ["SUPER_ADMIN", "ADMIN", "PREMIUM_USER", "FREE_USER"],
        "badge": None,
        "coming_soon": True,
        "name": "settings",
    },
]

def get_sidebar_navigation(user):
    """Filters navigation based on user role."""
    if not user.is_authenticated:
        return []
        
    nav = []
    for item in SIDEBAR_NAVIGATION:
        if user.role in item["required_role"]:
            # Special case for Dashboard URL routing
            url_name = item["url"]
            if item["name"] == "dashboard":
                if user.is_super_admin:
                    url_name = "dashboard:super_admin"
                elif user.is_platform_admin:
                    url_name = "dashboard:admin"
                else:
                    url_name = "dashboard:user"
                    
            try:
                resolved_url = reverse_lazy(url_name)
            except Exception:
                resolved_url = "#"

            nav_item = item.copy()
            nav_item["url"] = resolved_url
            nav.append(nav_item)
            
    return nav
