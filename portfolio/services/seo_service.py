"""
portfolio/services/seo_service.py — Portfolio SEO Generation Engine (Phase 9.7 MVP)

Provides:
  - clean_seo_description(): Strips HTML tags, normalizes whitespace, and truncates to 150-160 characters.
  - generate_meta_tags(): Generates Meta Title & Meta Description from portfolio fields.
  - generate_open_graph(): Generates og:title, og:description, og:image, og:url, og:type.
  - generate_twitter_card(): Generates twitter:card, twitter:title, twitter:description, twitter:image.
  - generate_robots_txt(): Generates basic robots.txt specification.
  - generate_sitemap(): Generates basic sitemap.xml specification.
  - generate_portfolio_seo(): Aggregates complete structured SEO payload.
"""

import re
import time
from typing import Dict, Any
from django.utils.html import strip_tags

from portfolio.models import Portfolio


def clean_seo_description(text: str, max_length: int = 155) -> str:
    """
    Cleans raw portfolio text into a search-engine ready meta description:
      1. Strips HTML tags
      2. Normalizes extra whitespace
      3. Gracefully truncates to 150-160 characters
    """
    if not text:
        return ""

    clean_text = strip_tags(str(text))
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    if len(clean_text) > max_length:
        return clean_text[: max_length - 3].strip() + "..."

    return clean_text


def generate_meta_tags(portfolio: Portfolio, domain: str = "") -> Dict[str, str]:
    """
    Generates Meta Title and Meta Description for the portfolio.
    """
    name = (portfolio.name or "Portfolio").strip()
    title = (portfolio.title or "").strip()

    if title:
        meta_title = f"{name} - {title}"
    else:
        meta_title = name

    raw_desc = portfolio.about or portfolio.tagline or f"{name} - Professional Portfolio"
    meta_desc = clean_seo_description(raw_desc, max_length=155)

    return {
        "title": meta_title,
        "description": meta_desc
    }


def generate_open_graph(portfolio: Portfolio, domain: str = "") -> Dict[str, str]:
    """
    Generates Open Graph social meta tags (og:title, og:description, og:image, og:url, og:type).
    """
    meta = generate_meta_tags(portfolio, domain)

    image_url = ""
    if hasattr(portfolio, "photo") and portfolio.photo and hasattr(portfolio.photo, "url"):
        raw_url = portfolio.photo.url
        if raw_url.startswith("http"):
            image_url = raw_url
        elif domain:
            image_url = f"{domain}{raw_url}"
        else:
            image_url = raw_url

    portfolio_url = f"{domain}/p/{portfolio.pk}/" if domain else f"/p/{portfolio.pk}/"

    return {
        "og:title": meta["title"],
        "og:description": meta["description"],
        "og:image": image_url,
        "og:url": portfolio_url,
        "og:type": "website"
    }


def generate_twitter_card(portfolio: Portfolio, domain: str = "") -> Dict[str, str]:
    """
    Generates Twitter Card social meta tags (twitter:card, twitter:title, twitter:description, twitter:image).
    """
    meta = generate_meta_tags(portfolio, domain)
    og = generate_open_graph(portfolio, domain)

    return {
        "twitter:card": "summary_large_image",
        "twitter:title": meta["title"],
        "twitter:description": meta["description"],
        "twitter:image": og["og:image"]
    }


def generate_robots_txt(portfolio: Portfolio, domain: str = "") -> str:
    """
    Generates a basic robots.txt specification pointing to the sitemap.
    """
    sitemap_url = f"{domain}/sitemap.xml" if domain else "/sitemap.xml"
    return f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"


def generate_sitemap(portfolio: Portfolio, domain: str = "") -> str:
    """
    Generates a basic sitemap.xml XML document string for the portfolio.
    """
    loc = f"{domain}/p/{portfolio.pk}/" if domain else f"/p/{portfolio.pk}/"
    lastmod = time.strftime("%Y-%m-%d", time.gmtime())

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        f'    <loc>{loc}</loc>\n'
        f'    <lastmod>{lastmod}</lastmod>\n'
        '    <changefreq>weekly</changefreq>\n'
        '    <priority>1.0</priority>\n'
        '  </url>\n'
        '</urlset>'
    )


def generate_portfolio_seo(portfolio: Portfolio, domain: str = "") -> Dict[str, Any]:
    """
    Aggregates complete SEO specifications for a portfolio.
    """
    return {
        "portfolio_id": portfolio.pk,
        "meta_tags": generate_meta_tags(portfolio, domain),
        "open_graph": generate_open_graph(portfolio, domain),
        "twitter_card": generate_twitter_card(portfolio, domain),
        "robots_txt": generate_robots_txt(portfolio, domain),
        "sitemap_xml": generate_sitemap(portfolio, domain)
    }
