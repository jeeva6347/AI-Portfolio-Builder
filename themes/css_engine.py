"""
themes/css_engine.py — CSS Variable Engine (Phase 5)

Generates dynamic CSS custom properties (:root variable blocks)
handling colors, typography, border radius, glassmorphism, and dark mode.
"""

from typing import Dict, Optional


class CSSVariableEngine:
    """Computes CSS variables for theme rendering."""

    DEFAULT_VARIABLES = {
        "primary_color": "#3b82f6",
        "secondary_color": "#64748b",
        "accent_color": "#f59e0b",
        "font_family": "Inter",
        "border_radius": "8px",
        "bg_color": "#ffffff",
        "text_color": "#0f172a",
        "card_bg": "#ffffff",
        "card_border": "#e2e8f0",
        "glass_blur": "12px",
    }

    @classmethod
    def generate_css_variables(
        cls,
        theme=None,
        overrides: Optional[Dict] = None
    ) -> str:
        """
        Generates a valid CSS :root block string containing custom variable definitions.
        Merges theme defaults with user overrides.
        """
        vars_dict = cls.DEFAULT_VARIABLES.copy()

        # Merge Theme model default css_variables if defined
        if theme and hasattr(theme, "css_variables") and isinstance(theme.css_variables, dict):
            vars_dict.update(theme.css_variables)

        # Merge User overrides (from portfolio settings / Alpine right panel)
        if overrides and isinstance(overrides, dict):
            for k, v in overrides.items():
                if v:
                    vars_dict[k] = str(v)

        # Build :root css block
        lines = [
            ":root {",
            f"  --primary-color: {vars_dict.get('primary_color', '#3b82f6')};",
            f"  --secondary-color: {vars_dict.get('secondary_color', '#64748b')};",
            f"  --accent-color: {vars_dict.get('accent_color', '#f59e0b')};",
            f"  --font-family: '{vars_dict.get('font_family', 'Inter')}', sans-serif;",
            f"  --border-radius: {vars_dict.get('border_radius', '8px')};",
            f"  --bg-color: {vars_dict.get('bg_color', '#ffffff')};",
            f"  --text-color: {vars_dict.get('text_color', '#0f172a')};",
            f"  --card-bg: {vars_dict.get('card_bg', '#ffffff')};",
            f"  --card-border: {vars_dict.get('card_border', '#e2e8f0')};",
            f"  --glass-blur: {vars_dict.get('glass_blur', '12px')};",
            "}"
        ]

        return "\n".join(lines)
