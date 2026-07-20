"""
themes/registry.py — Theme Auto-Discovery Engine (Phase 5)

Scans filesystem theme directories for theme.json manifests and automatically
syncs installed package themes into database Theme records without hardcoding.
"""

import json
import os
from typing import Dict, List, Optional
from django.conf import settings
from django.utils.text import slugify

from .models import Theme, ThemeCategory


class ThemeRegistry:
    """Discovers filesystem themes and manages runtime registration."""

    def __init__(self):
        self.search_dirs = [
            os.path.join(settings.MEDIA_ROOT, "themes"),
            os.path.join(settings.BASE_DIR, "themes", "templates_pkg"),
        ]

    def discover_themes() -> List[Theme]:
        """
        Scans all search directories for theme.json configuration manifests.
        Creates or updates Theme records in the database.
        """
        discovered = []

        for search_dir in self.search_dirs:
            if not os.path.exists(search_dir):
                continue

            for root, dirs, files in os.walk(search_dir):
                if "theme.json" in files:
                    manifest_path = os.path.join(root, "theme.json")
                    theme_obj = self._process_manifest(manifest_path, root)
                    if theme_obj:
                        discovered.append(theme_obj)

        return discovered

    def _process_manifest(self, manifest_path: str, theme_dir: str) -> Optional[Theme]:
        """Parses theme.json manifest and syncs with Theme model."""
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        name = data.get("name")
        if not name:
            return None

        slug = data.get("slug") or slugify(name)
        category_name = data.get("category", "General")
        
        # Ensure category exists
        category, _ = ThemeCategory.objects.get_or_create(
            name=category_name,
            defaults={"slug": slugify(category_name)}
        )

        rel_extracted_path = os.path.relpath(theme_dir, settings.MEDIA_ROOT).replace("\\", "/")

        theme, created = Theme.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": data.get("description", ""),
                "author": data.get("author", "AI Portfolio Team"),
                "category": category,
                "status": Theme.Status.APPROVED if data.get("approved", True) else Theme.Status.DRAFT,
                "is_premium": data.get("is_premium", False),
                "price": data.get("price", 0.00),
                "version": data.get("version", "1.0.0"),
                "extracted_path": rel_extracted_path,
                "template_directory": data.get("template_directory", rel_extracted_path),
                "configuration_file": "theme.json",
                "default_css": data.get("default_css", ""),
                "css_variables": data.get("css_variables", {}),
                "font_family": data.get("font_family", "Inter"),
                "supports_dark_mode": data.get("supports_dark_mode", True),
                "supports_custom_colors": data.get("supports_custom_colors", True),
                "supports_custom_fonts": data.get("supports_custom_fonts", True),
                "supports_animation": data.get("supports_animation", True),
                "is_active": True
            }
        )
        return theme


# Global theme registry singleton
theme_registry = ThemeRegistry()
