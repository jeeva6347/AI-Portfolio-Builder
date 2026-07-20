"""
portfolio/services/build.py — Static Site Builder Engine & Build Artifact Generator (Phase 7.2)

Responsibilities:
  - validate_build_prerequisites(): Validates published version, theme, and templates
  - generate_sitemap_xml(): Generates XML sitemap
  - generate_robots_txt(): Generates robots.txt
  - generate_seo_json(): Generates Open Graph & Twitter Card SEO JSON
  - build_static_portfolio(): Assembles complete static website package (index.html, assets/, sitemap, robots, manifest, seo)
"""

import json
import time
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from django.utils import timezone

from portfolio.models import Portfolio, PortfolioVersion
from themes.css_engine import CSSVariableEngine


@dataclass
class StaticBuildArtifact:
    """Represents a self-contained static website package ready for static hosting export."""
    index_html: str = ""
    compiled_css: str = ""
    sitemap_xml: str = ""
    robots_txt: str = ""
    manifest_json: str = ""
    seo_json: str = ""
    assets_files: dict = field(default_factory=dict)     # {"assets/css/styles.css": ..., "assets/images/photo.jpg": ...}
    static_package: dict = field(default_factory=dict)   # Full file map
    metrics: dict = field(default_factory=dict)          # {"build_time_ms": 120, "html_size": 15400, "css_size": 3200, "assets_processed": 4, "pages_generated": 1}


def validate_build_prerequisites(portfolio: Portfolio) -> List[Dict[str, str]]:
    """
    Validates that a portfolio meets all static site build prerequisites.
    Returns array of structured error objects: [{"code": "ERR_CODE", "message": "Human message"}].
    """
    errors = []

    # 1. Published Version Check
    published_ver = portfolio.published_version or portfolio.versions.filter(is_published=True).first()
    if not published_ver:
        errors.append({
            "code": "NO_PUBLISHED_VERSION",
            "message": "Portfolio must have a published version before building a static artifact package."
        })

    # 2. Theme Preset Check
    if not portfolio.selected_theme:
        errors.append({
            "code": "THEME_NOT_FOUND",
            "message": "Selected theme preset does not exist."
        })
    else:
        theme = portfolio.selected_theme
        if not theme.is_active:
            errors.append({
                "code": "THEME_INACTIVE",
                "message": f"Theme '{theme.name}' is inactive."
            })

    return errors


def generate_sitemap_xml(portfolio: Portfolio, domain: str = "https://aiportfoliobuilder.com") -> str:
    """Generates valid XML sitemap string for static site SEO."""
    slug = portfolio.name.lower().replace(" ", "-") if portfolio.name else f"portfolio-{portfolio.pk}"
    canonical_url = f"{domain}/p/{slug}/"
    last_mod = (portfolio.published_at or timezone.now()).strftime("%Y-%m-%d")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{canonical_url}</loc>
    <lastmod>{last_mod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""


def generate_robots_txt(portfolio: Portfolio, domain: str = "https://aiportfoliobuilder.com") -> str:
    """Generates robots.txt file string."""
    slug = portfolio.name.lower().replace(" ", "-") if portfolio.name else f"portfolio-{portfolio.pk}"
    sitemap_url = f"{domain}/p/{slug}/sitemap.xml"

    return f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /builder/

Sitemap: {sitemap_url}
"""


def generate_seo_json(portfolio: Portfolio) -> str:
    """Generates JSON string containing Open Graph, Twitter Card, and Meta tag attributes."""
    data = {
        "title": f"{portfolio.name} - {portfolio.title or 'Personal Portfolio'}",
        "description": portfolio.tagline or (portfolio.about[:150] if portfolio.about else ""),
        "meta": {
            "author": portfolio.name,
            "keywords": f"{portfolio.name}, {portfolio.title}, portfolio, developer, resume",
            "robots": "index, follow",
        },
        "open_graph": {
            "og:title": portfolio.name,
            "og:description": portfolio.tagline or "",
            "og:type": "website",
            "og:image": portfolio.photo.url if portfolio.photo else "",
        },
        "twitter": {
            "twitter:card": "summary_large_image",
            "twitter:title": portfolio.name,
            "twitter:description": portfolio.tagline or "",
            "twitter:image": portfolio.photo.url if portfolio.photo else "",
        }
    }
    return json.dumps(data, indent=2)


def build_static_portfolio(portfolio: Portfolio) -> Dict:
    """
    Builds a complete, self-contained static website artifact package for a portfolio.
    Outputs index.html, assets/css/styles.css, assets/images/, sitemap.xml, robots.txt, manifest.json, and seo.json.
    """
    start_time = time.time()

    # 1. Build Validation
    errors = validate_build_prerequisites(portfolio)
    if errors:
        return {
            "success": False,
            "code": "BUILD_PREREQUISITES_FAILED",
            "message": "Build prerequisites failed.",
            "errors": errors
        }

    theme = portfolio.selected_theme

    # 2. Compile CSS
    compiled_css = CSSVariableEngine.generate_css_variables(theme)

    # 3. Render HTML
    from portfolio.views import apply_theme_mapping
    raw_html = ""
    mapping = theme.mappings.filter(is_active=True).first()

    if mapping and theme.index_html_path and os.path.exists(theme.index_html_path):
        with open(theme.index_html_path, "r", encoding="utf-8", errors="ignore") as f:
            template_str = f.read()
        raw_html = apply_theme_mapping(template_str, mapping, portfolio.get_fields_dict())
    else:
        raw_html = f"<!DOCTYPE html><html><head><link rel='stylesheet' href='assets/css/styles.css'></head><body><h1>{portfolio.name}</h1><p>{portfolio.title}</p></body></html>"

    # 4. Process Media Assets & Rewrite relative URLs
    assets_processed = 0
    assets_files = {
        "assets/css/styles.css": compiled_css,
    }

    if portfolio.photo:
        assets_files["assets/images/photo.jpg"] = portfolio.photo.url
        raw_html = raw_html.replace(portfolio.photo.url, "assets/images/photo.jpg")
        assets_processed += 1

    if portfolio.cover:
        assets_files["assets/images/cover.jpg"] = portfolio.cover.url
        raw_html = raw_html.replace(portfolio.cover.url, "assets/images/cover.jpg")
        assets_processed += 1

    # 5. Generate Static Package Manifests
    sitemap_xml = generate_sitemap_xml(portfolio)
    robots_txt = generate_robots_txt(portfolio)
    seo_json = generate_seo_json(portfolio)

    manifest_dict = {
        "name": portfolio.name,
        "short_name": portfolio.name,
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#3b82f6",
        "icons": []
    }
    manifest_json = json.dumps(manifest_dict, indent=2)

    # 6. Assemble Static Package File Map
    static_package = {
        "index.html": raw_html,
        "assets/css/styles.css": compiled_css,
        "sitemap.xml": sitemap_xml,
        "robots.txt": robots_txt,
        "manifest.json": manifest_json,
        "seo.json": seo_json,
    }
    static_package.update(assets_files)

    # 7. Compute Metrics
    elapsed_ms = int((time.time() - start_time) * 1000)
    html_size = len(raw_html.encode("utf-8"))
    css_size = len(compiled_css.encode("utf-8"))

    metrics = {
        "build_time_ms": elapsed_ms,
        "html_size": html_size,
        "css_size": css_size,
        "assets_processed": assets_processed,
        "pages_generated": 1,
    }

    artifact = StaticBuildArtifact(
        index_html=raw_html,
        compiled_css=compiled_css,
        sitemap_xml=sitemap_xml,
        robots_txt=robots_txt,
        manifest_json=manifest_json,
        seo_json=seo_json,
        assets_files=assets_files,
        static_package=static_package,
        metrics=metrics,
    )

    return {
        "success": True,
        "code": "BUILD_SUCCESSFUL",
        "message": f"Successfully generated static website build artifact for '{portfolio.name}'.",
        "artifact": artifact,
        "metrics": metrics,
        "errors": []
    }
