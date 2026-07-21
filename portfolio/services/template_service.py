"""
portfolio/services/template_service.py — Portfolio Templates Service (Phase 9.6 MVP)

Provides:
  - list_templates(): Queries active built-in themes and returns a streamlined template preset list.
  - change_template(): Switches a portfolio's visual layout (selected_theme) while keeping all content
                      (About, Skills, Projects, Experience, Education, Contact) 100% untouched.
"""

from typing import List, Dict, Any, Union
from django.core.cache import cache

from portfolio.models import Portfolio
from themes.models import Theme


def list_templates() -> List[Dict[str, Any]]:
    """
    Returns all active built-in portfolio template presets with streamlined attributes:
      - id
      - name
      - slug
      - category
      - description
    """
    active_themes = Theme.objects.filter(is_active=True).select_related("category").order_by("name")

    return [
        {
            "id": theme.pk,
            "name": theme.name,
            "slug": theme.slug,
            "category": theme.category.name if theme.category else "General",
            "description": theme.description or ""
        }
        for theme in active_themes
    ]


def change_template(portfolio: Portfolio, template_identifier: Union[int, str]) -> Dict[str, Any]:
    """
    Updates a portfolio's visual theme template.
    Guarantees 100% data safety: About, Skills, Projects, Experience, Education, Contact remain UNCHANGED.
    Only updates portfolio.selected_theme.
    """
    theme = None

    if isinstance(template_identifier, int) or (isinstance(template_identifier, str) and template_identifier.isdigit()):
        theme = Theme.objects.filter(pk=int(template_identifier), is_active=True).first()

    if not theme and isinstance(template_identifier, str):
        theme = Theme.objects.filter(slug=template_identifier, is_active=True).first()

    if not theme:
        raise ValueError(f"Template '{template_identifier}' not found or is currently inactive.")

    # Update only the visual template relationship
    portfolio.selected_theme = theme
    portfolio.save(update_fields=["selected_theme"])

    # Invalidate rendered HTML draft cache
    cache.delete(f"portfolio_rendered_html_{portfolio.pk}")

    return {
        "success": True,
        "code": "TEMPLATE_CHANGED",
        "message": f"Successfully updated template layout to '{theme.name}'.",
        "portfolio_id": portfolio.pk,
        "template_id": theme.pk,
        "template_name": theme.name,
        "template_slug": theme.slug
    }
