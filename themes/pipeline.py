"""
themes/pipeline.py — 6-Stage Dynamic Rendering Pipeline (Phase 5)

Pipeline Execution Flow:
  1. Portfolio Data Retrieval
  2. Theme Resolution & Mapping
  3. Component Rendering Engine
  4. CSS Variable Engine Injection
  5. SEO & Meta Header Injection
  6. Response Compilation & Django Cache Store
"""

from typing import Dict, Optional
from django.core.cache import cache
from django.template.loader import render_to_string

from .css_engine import CSSVariableEngine
from .components import component_registry


class ThemeRenderingPipeline:
    """Renders user portfolio models into compiled HTML with caching."""

    CACHE_TIMEOUT = 3600  # 1 hour cache timeout

    @classmethod
    def render_portfolio(
        cls,
        portfolio,
        use_cache: bool = True,
        css_overrides: Optional[Dict] = None
    ) -> str:
        """
        Executes the 6-stage rendering pipeline for a portfolio instance.
        """
        cache_key = f"rendered_portfolio_html_{portfolio.pk}_{portfolio.updated_at.timestamp()}"
        
        if use_cache:
            cached_html = cache.get(cache_key)
            if cached_html:
                return cached_html

        # Stage 1: Data Serialization
        portfolio_data = portfolio.get_fields_dict()
        theme = portfolio.selected_theme

        # Stage 2 & 3: Template & Component Rendering
        # Fallback to standard template engine if theme path exists
        if theme and theme.index_html_path and os.path.exists(theme.index_html_path):
            with open(theme.index_html_path, "r", encoding="utf-8") as f:
                raw_template = f.read()
            # Perform mapping replacement
            rendered_html = cls._inject_field_data(raw_template, portfolio_data)
        else:
            # Render using default framework template
            context = {
                "portfolio": portfolio,
                "data": portfolio_data,
                "components": component_registry.get_all(),
            }
            try:
                rendered_html = render_to_string("portfolio/default_theme.html", context)
            except Exception:
                rendered_html = f"<!DOCTYPE html><html><head><title>{portfolio.name}</title></head><body><h1>{portfolio.name}</h1><h2>{portfolio.title}</h2><p>{portfolio.about}</p></body></html>"

        # Stage 4: CSS Variable Engine Injection
        css_vars_block = CSSVariableEngine.generate_css_variables(theme, css_overrides)
        css_style_tag = f"<style id='theme-css-engine'>\n{css_vars_block}\n</style>"

        if "</head>" in rendered_html:
            rendered_html = rendered_html.replace("</head>", f"{css_style_tag}\n</head>")
        else:
            rendered_html = f"{css_style_tag}\n" + rendered_html

        # Stage 5: SEO Meta Injection
        seo_meta = f"""
        <!-- Automated SEO & Indexing Meta Tags -->
        <meta name="title" content="{portfolio.name} - {portfolio.title}">
        <meta name="description" content="{portfolio.tagline or portfolio.about[:150]}">
        """
        if "</head>" in rendered_html:
            rendered_html = rendered_html.replace("</head>", f"{seo_meta}\n</head>")

        # Stage 6: Store in Cache
        if use_cache:
            cache.set(cache_key, rendered_html, cls.CACHE_TIMEOUT)

        return rendered_html

    @classmethod
    def _inject_field_data(cls, html: str, data: Dict) -> str:
        """Replaces {{ key }} placeholder tokens with serialized portfolio field data."""
        import re
        def replace_match(match):
            key = match.group(1).strip()
            return str(data.get(key, ""))
        return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", replace_match, html)
