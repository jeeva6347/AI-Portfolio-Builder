from bs4 import BeautifulSoup
from django.utils.html import escape
from django.conf import settings


def calculate_seo_score(portfolio):
    """
    Computes an SEO scoring metrics card between 0 and 100 based on
    meta tags configuration completeness.
    """
    if not hasattr(portfolio, "seo"):
        return 0

    seo = portfolio.seo
    score = 100
    
    # Penalties checklist
    if not seo.seo_title:
        score -= 20
    if not seo.meta_description:
        score -= 20
    elif len(seo.meta_description) < 50:
        score -= 10 # description too short
        
    if not seo.keywords:
        score -= 10
    if not seo.canonical_url:
        score -= 10
        
    if not seo.og_title or not seo.og_description:
        score -= 15
    if not seo.og_image:
        score -= 15
        
    if not seo.favicon:
        score -= 10

    final_score = max(0, min(score, 100))
    
    # Save back to metric record
    if hasattr(portfolio, "metric"):
        portfolio.metric.seo_score = final_score
        portfolio.metric.save(update_fields=["seo_score"])

    return final_score


def inject_seo_metadata(html_content, portfolio, request=None):
    """
    Parses compiled portfolio HTML using BeautifulSoup and injects custom
    SEO, Open Graph, Twitter Cards, Favicon tags, and Schema.org Structured Data.
    """
    if not hasattr(portfolio, "seo"):
        return html_content

    seo = portfolio.seo
    soup = BeautifulSoup(html_content, "html.parser")
    head = soup.find("head")
    
    # If no head tag is found, wrap or return original
    if not head:
        return html_content

    # Clean and override robots indexing directives to prevent pre-existing template overrides (none, noindex, nofollow)
    for old_robots in head.find_all("meta", attrs={"name": "robots"}):
        old_robots.decompose()
        
    from portfolio.models import Portfolio
    robots_content = "index,follow" if portfolio.status == Portfolio.Status.PUBLISHED else "noindex,nofollow"
    new_robots = soup.new_tag("meta", attrs={"name": "robots", "content": robots_content})
    head.append(new_robots)

    # helper to upsert meta by name
    def upsert_meta_name(name, content):
        if not content:
            return
        meta = head.find("meta", attrs={"name": name})
        if meta:
            meta["content"] = content
        else:
            new_meta = soup.new_tag("meta", attrs={"name": name, "content": content})
            head.append(new_meta)

    # helper to upsert meta by property (Open Graph)
    def upsert_meta_property(property_name, content):
        if not content:
            return
        meta = head.find("meta", attrs={"property": property_name})
        if meta:
            meta["content"] = content
        else:
            new_meta = soup.new_tag("meta", attrs={"property": property_name, "content": content})
            head.append(new_meta)

    # 1. Custom Title override (Dynamic fallback to User details)
    owner_name = portfolio.user.first_name + " " + portfolio.user.last_name if (portfolio.user.first_name or portfolio.user.last_name) else portfolio.user.username
    title_str = seo.seo_title or f"{owner_name} | {portfolio.name} Professional Resume Portfolio"
    
    title_tag = head.find("title")
    if title_tag:
        title_tag.string = title_str
    else:
        new_title = soup.new_tag("title")
        new_title.string = title_str
        head.append(new_title)

    # 2. Descriptions and Keywords (Dynamic fallback to about / tagline)
    desc_str = seo.meta_description or portfolio.about or portfolio.tagline or portfolio.title or f"Explore the professional resume portfolio of {owner_name} containing experience, education, projects, and skills."
    upsert_meta_name("description", desc_str)
    
    keywords_str = seo.keywords or "resume, portfolio, developer, experience, projects, skills"
    upsert_meta_name("keywords", keywords_str)

    # 3. Canonical URL
    canonical_url = seo.canonical_url
    if not canonical_url and request:
        canonical_url = request.build_absolute_uri(request.path)
    if not canonical_url:
        # Fallback domain representation
        canonical_url = f"https://ai-portfolio-builder-icmv.onrender.com/portfolio/preview/{portfolio.pk}/"
        
    link_tag = head.find("link", attrs={"rel": "canonical"})
    if link_tag:
        link_tag["href"] = canonical_url
    else:
        new_link = soup.new_tag("link", attrs={"rel": "canonical", "href": canonical_url})
        head.append(new_link)

    # 4. Open Graph Social tags
    og_title = seo.og_title or title_str
    og_desc = seo.og_description or desc_str
    upsert_meta_property("og:title", og_title)
    upsert_meta_property("og:type", "profile")
    upsert_meta_property("og:description", og_desc)
    upsert_meta_property("og:url", canonical_url)

    # 5. Twitter Card properties
    tw_title = seo.twitter_title or og_title
    tw_desc = seo.twitter_description or og_desc
    upsert_meta_name("twitter:card", "summary_large_image")
    upsert_meta_name("twitter:title", tw_title)
    upsert_meta_name("twitter:description", tw_desc)

    # 6. Social Share Image Urls (Dynamic fallback to photo, cover, or site default)
    img_url = ""
    if seo.og_image:
        img_url = seo.og_image.url
    elif portfolio.photo:
        img_url = portfolio.photo.url
    elif portfolio.cover:
        img_url = portfolio.cover.url
        
    if img_url:
        if request and not img_url.startswith("http"):
            img_url = request.build_absolute_uri(img_url)
        elif not img_url.startswith("http"):
            img_url = f"https://ai-portfolio-builder-icmv.onrender.com{img_url}"
    else:
        # Fallback to site default share card image
        if request:
            img_url = request.build_absolute_uri("/static/img/og_default_share_card.png")
        else:
            img_url = "https://ai-portfolio-builder-icmv.onrender.com/static/img/og_default_share_card.png"
            
    upsert_meta_property("og:image", img_url)
    upsert_meta_name("twitter:image", img_url)

    # 7. Favicon asset link overrides (Dynamic fallback to default site favicon if empty)
    fav_url = seo.favicon.url if seo.favicon else "/favicon.ico"
    if request and not fav_url.startswith("http"):
        fav_url = request.build_absolute_uri(fav_url)
        
    # Remove any existing favicon tags
    for old_fav in head.find_all("link", attrs={"rel": lambda x: x and "icon" in x.lower()}):
        old_fav.decompose()
        
    new_fav = soup.new_tag("link", attrs={"rel": "icon", "href": fav_url})
    head.append(new_fav)

    # 8. Schema.org Person & ProfilePage JSON-LD Structured Data
    import json
    person_schema = {
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "name": f"{owner_name}'s Professional Resume Portfolio",
        "description": desc_str,
        "url": canonical_url,
        "mainEntity": {
            "@type": "Person",
            "name": owner_name,
            "jobTitle": portfolio.title or portfolio.tagline or "Professional Profile",
            "description": portfolio.about or desc_str,
            "url": canonical_url
        }
    }
    if portfolio.photo:
        photo_url = portfolio.photo.url
        if request:
            photo_url = request.build_absolute_uri(photo_url)
        else:
            photo_url = f"https://ai-portfolio-builder-icmv.onrender.com{photo_url}"
        person_schema["mainEntity"]["image"] = photo_url
        
    new_schema_tag = soup.new_tag("script", attrs={"type": "application/ld+json"})
    new_schema_tag.string = json.dumps(person_schema, indent=2)
    head.append(new_schema_tag)

    return str(soup)
