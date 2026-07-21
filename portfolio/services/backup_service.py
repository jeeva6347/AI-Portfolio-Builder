"""
portfolio/services/backup_service.py — Portfolio Backup & Restore Engine (Phase 9.5 MVP)

Provides:
  - export_portfolio_backup(): Serializes a complete portfolio and all child records into a JSON backup snapshot.
  - generate_unique_portfolio_name(): Automatically assigns unique names on import conflicts (e.g. "My Portfolio (Imported)").
  - import_portfolio_backup(): Reconstructs a brand new portfolio from JSON backup payload (never overwriting existing records).
"""

import time
import json
from typing import Dict, Any, Optional

from portfolio.models import (
    Portfolio,
    PortfolioSkill,
    PortfolioProject,
    PortfolioExperience,
    PortfolioEducation,
    PortfolioCertificate,
    PortfolioService,
    PortfolioTestimonial
)
from themes.models import Theme

BACKUP_VERSION = "1.0"


def export_portfolio_backup(portfolio: Portfolio) -> Dict[str, Any]:
    """
    Serializes portfolio metadata and all child querysets into a structured JSON backup payload.
    """
    theme_slug = portfolio.selected_theme.slug if portfolio.selected_theme else None

    port_meta = {
        "name": portfolio.name,
        "title": portfolio.title,
        "about": portfolio.about,
        "theme_slug": theme_slug,
    }

    skills_list = [
        {
            "name": s.name,
            "skill_type": s.skill_type,
            "level": s.level
        }
        for s in portfolio.skills.all()
    ]

    projects_list = [
        {
            "title": p.title,
            "description": p.description,
            "technologies": p.technologies,
            "github_url": p.github_url,
            "live_url": p.live_url
        }
        for p in portfolio.projects.all()
    ]

    exp_list = [
        {
            "title": getattr(e, "position", getattr(e, "title", "")),
            "position": getattr(e, "position", getattr(e, "title", "")),
            "company": e.company,
            "description": e.description,
            "duration": getattr(e, "duration", "")
        }
        for e in portfolio.experiences.all()
    ]

    edu_list = [
        {
            "degree": ed.degree,
            "institution": ed.institution,
            "year": ed.year,
            "description": getattr(ed, "description", "")
        }
        for ed in portfolio.education.all()
    ]

    contact_dict = {
        "email": portfolio.email,
        "phone": portfolio.phone,
        "address": portfolio.address,
        "social_github": portfolio.social_github,
        "social_linkedin": portfolio.social_linkedin,
        "social_twitter": getattr(portfolio, "social_twitter", ""),
        "website": getattr(portfolio, "website", "")
    }

    cert_list = [
        {
            "title": cert.title,
            "issuer": cert.issuer,
            "issue_date": str(cert.issue_date) if getattr(cert, "issue_date", None) else "",
            "credential_id": getattr(cert, "credential_id", "")
        }
        for cert in portfolio.certificates.all()
    ]

    serv_list = [
        {
            "title": s.title,
            "description": s.description,
            "icon": s.icon
        }
        for s in portfolio.services.all()
    ]

    test_list = [
        {
            "reviewer_name": t.reviewer_name,
            "reviewer_role": t.reviewer_role,
            "text": t.text
        }
        for t in portfolio.testimonials.all()
    ]

    return {
        "version": BACKUP_VERSION,
        "backup_type": "portfolio_backup",
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "portfolio": port_meta,
        "skills": skills_list,
        "projects": projects_list,
        "experience": exp_list,
        "education": edu_list,
        "contact": contact_dict,
        "certificates": cert_list,
        "services": serv_list,
        "testimonials": test_list
    }


def generate_unique_portfolio_name(user, base_name: str) -> str:
    """
    Generates a unique portfolio name for user when import naming conflicts occur.
    Example: 'My Portfolio' -> 'My Portfolio (Imported)' -> 'My Portfolio (Imported 2)'.
    """
    name = (base_name or "Imported Portfolio").strip()
    if not Portfolio.objects.filter(user=user, name=name).exists():
        return name

    candidate = f"{name} (Imported)"
    if not Portfolio.objects.filter(user=user, name=candidate).exists():
        return candidate

    counter = 2
    while True:
        candidate_indexed = f"{name} (Imported {counter})"
        if not Portfolio.objects.filter(user=user, name=candidate_indexed).exists():
            return candidate_indexed
        counter += 1


def import_portfolio_backup(backup_data: dict, user) -> Portfolio:
    """
    Imports portfolio JSON backup payload and constructs a brand new Portfolio instance.
    Never overwrites existing portfolios! Automatically assigns unique names on conflict.
    """
    if not isinstance(backup_data, dict):
        raise ValueError("Invalid backup format: expected JSON object.")

    port_meta = backup_data.get("portfolio")
    if not isinstance(port_meta, dict) or not port_meta.get("name"):
        raise ValueError("Invalid backup payload: missing portfolio metadata or portfolio name.")

    # 1. Unique Name Resolution
    raw_name = port_meta.get("name")
    unique_name = generate_unique_portfolio_name(user, raw_name)

    # 2. Theme Preset Resolution
    theme_slug = port_meta.get("theme_slug")
    theme = Theme.objects.filter(slug=theme_slug, is_active=True).first() if theme_slug else None
    if not theme:
        theme = Theme.objects.filter(is_active=True).first()

    # 3. Create Brand New Portfolio Record
    new_portfolio = Portfolio.objects.create(
        user=user,
        name=unique_name,
        title=port_meta.get("title", ""),
        about=port_meta.get("about", ""),
        selected_theme=theme
    )

    # 4. Contact Info Restoration
    contact_data = backup_data.get("contact")
    if isinstance(contact_data, dict):
        new_portfolio.email = contact_data.get("email", "")
        new_portfolio.phone = contact_data.get("phone", "")
        new_portfolio.address = contact_data.get("address", "")
        new_portfolio.social_github = contact_data.get("social_github", "")
        new_portfolio.social_linkedin = contact_data.get("social_linkedin", "")
        new_portfolio.save(update_fields=["email", "phone", "address", "social_github", "social_linkedin"])

    # 5. Reconstruct Sub-Records
    for sk in backup_data.get("skills", []):
        if isinstance(sk, dict) and sk.get("name"):
            PortfolioSkill.objects.create(
                portfolio=new_portfolio,
                name=sk.get("name"),
                skill_type=sk.get("skill_type", "technical"),
                level=sk.get("level", "")
            )

    for pr in backup_data.get("projects", []):
        if isinstance(pr, dict) and pr.get("title"):
            PortfolioProject.objects.create(
                portfolio=new_portfolio,
                title=pr.get("title"),
                description=pr.get("description", ""),
                technologies=pr.get("technologies", ""),
                github_url=pr.get("github_url", ""),
                live_url=pr.get("live_url", pr.get("project_url", ""))
            )

    for exp in backup_data.get("experience", []):
        if isinstance(exp, dict) and (exp.get("position") or exp.get("title")):
            PortfolioExperience.objects.create(
                portfolio=new_portfolio,
                position=exp.get("position") or exp.get("title", ""),
                company=exp.get("company", ""),
                duration=exp.get("duration", ""),
                description=exp.get("description", "")
            )

    for edu in backup_data.get("education", []):
        if isinstance(edu, dict) and (edu.get("degree") or edu.get("institution")):
            PortfolioEducation.objects.create(
                portfolio=new_portfolio,
                degree=edu.get("degree", ""),
                institution=edu.get("institution", ""),
                year=edu.get("year", "")
            )

    for cert in backup_data.get("certificates", []):
        if isinstance(cert, dict) and cert.get("title"):
            PortfolioCertificate.objects.create(
                portfolio=new_portfolio,
                title=cert.get("title"),
                issuer=cert.get("issuer", "")
            )

    for serv in backup_data.get("services", []):
        if isinstance(serv, dict) and serv.get("title"):
            PortfolioService.objects.create(
                portfolio=new_portfolio,
                title=serv.get("title"),
                description=serv.get("description", ""),
                icon=serv.get("icon", "")
            )

    for test in backup_data.get("testimonials", []):
        if isinstance(test, dict) and test.get("reviewer_name"):
            PortfolioTestimonial.objects.create(
                portfolio=new_portfolio,
                reviewer_name=test.get("reviewer_name"),
                reviewer_role=test.get("reviewer_role", ""),
                text=test.get("text", "")
            )

    return new_portfolio
