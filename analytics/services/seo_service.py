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


def inject_seo_metadata(html_content, portfolio):
    """
    Parses compiled portfolio HTML using BeautifulSoup and injects custom
    SEO, Open Graph, Twitter Cards, and Favicon tags.
    """
    if not hasattr(portfolio, "seo"):
        return html_content

    seo = portfolio.seo
    soup = BeautifulSoup(html_content, "html.parser")
    head = soup.find("head")
    
    # If no head tag is found, wrap or return original
    if not head:
        return html_content

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

    # 1. Custom Title override
    title_str = seo.seo_title or portfolio.name
    title_tag = head.find("title")
    if title_tag:
        title_tag.string = title_str
    else:
        new_title = soup.new_tag("title")
        new_title.string = title_str
        head.append(new_title)

    # 2. Descriptions and Keywords
    if seo.meta_description:
        upsert_meta_name("description", seo.meta_description)
    if seo.keywords:
        upsert_meta_name("keywords", seo.keywords)

    # 3. Canonical URL
    if seo.canonical_url:
        link_tag = head.find("link", attrs={"rel": "canonical"})
        if link_tag:
            link_tag["href"] = seo.canonical_url
        else:
            new_link = soup.new_tag("link", attrs={"rel": "canonical", "href": seo.canonical_url})
            head.append(new_link)

    # 4. Open Graph Social tags
    og_title = seo.og_title or title_str
    og_desc = seo.og_description or seo.meta_description
    upsert_meta_property("og:title", og_title)
    upsert_meta_property("og:type", "website")
    if og_desc:
        upsert_meta_property("og:description", og_desc)
    if seo.canonical_url:
        upsert_meta_property("og:url", seo.canonical_url)

    # 5. Twitter Card properties
    tw_title = seo.twitter_title or og_title
    tw_desc = seo.twitter_description or og_desc
    upsert_meta_name("twitter:card", "summary_large_image")
    upsert_meta_name("twitter:title", tw_title)
    if tw_desc:
        upsert_meta_name("twitter:description", tw_desc)

    # 6. Social Share Image Urls
    if seo.og_image:
        img_url = seo.og_image.url
        upsert_meta_property("og:image", img_url)
        upsert_meta_name("twitter:image", img_url)

    # 7. Favicon asset link overrides
    if seo.favicon:
        fav_url = seo.favicon.url
        # Remove any existing favicon tags
        for old_fav in head.find_all("link", attrs={"rel": lambda x: x and "icon" in x.lower()}):
            old_fav.decompose()
        # Add new one
        new_fav = soup.new_tag("link", attrs={"rel": "icon", "type": "image/x-icon", "href": fav_url})
        head.append(new_fav)

    return str(soup)
