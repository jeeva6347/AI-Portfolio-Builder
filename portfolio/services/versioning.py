"""
portfolio/services/versioning.py — Backend Version Management Engine (Phase 6.4)

Provides services for:
  - compress_snapshot() / decompress_snapshot(): Transparent zlib compression for snapshots
  - create_version_snapshot() : Serializes portfolio + child models into version snapshot
  - restore_version_snapshot(): Full or partial section restoration from snapshot & logs Rollback
  - compare_version_snapshots(): Rich field-by-field and component diffing
  - invalidate_portfolio_caches(): Complete multi-layer cache purging
"""

import json
import zlib
import base64
from typing import Dict, List, Optional, Union
from django.db import transaction
from django.db.models import Max
from django.core.cache import cache

from portfolio.models import (
    Portfolio,
    PortfolioVersion,
    PortfolioSkill,
    PortfolioProject,
    PortfolioExperience,
    PortfolioEducation,
    PortfolioCertificate,
    PortfolioService,
    PortfolioTestimonial,
)


def compress_snapshot(data: dict) -> dict:
    """
    Compresses a snapshot dictionary using zlib + base64 if size exceeds 500 bytes.
    Returns compressed wrapper dict or original payload.
    """
    json_bytes = json.dumps(data).encode("utf-8")
    if len(json_bytes) > 500:
        compressed = zlib.compress(json_bytes, level=6)
        b64_str = base64.b64encode(compressed).decode("ascii")
        return {"_compressed": True, "raw": b64_str}
    return data


def decompress_snapshot(data: Union[dict, str]) -> dict:
    """
    Decompresses a snapshot payload if compressed, or returns original dictionary.
    """
    if isinstance(data, dict) and data.get("_compressed") is True:
        b64_str = data.get("raw", "")
        compressed = base64.b64decode(b64_str.encode("ascii"))
        decompressed_bytes = zlib.decompress(compressed)
        return json.loads(decompressed_bytes.decode("utf-8"))
    return data if isinstance(data, dict) else {}


def create_version_snapshot(
    portfolio: Portfolio,
    title: str = "",
    description: str = "",
    tag: str = "Draft",
    is_published: bool = False,
    is_auto_save: bool = False,
    is_manual_save: bool = False,
    created_by=None,
    git_commit_sha: Optional[str] = None
) -> PortfolioVersion:
    """
    Serializes portfolio fields and child models into a PortfolioVersion snapshot record.
    Auto-increments version number, applies zlib compression, and prunes excess autosaves.
    """
    with transaction.atomic():
        # 1. Determine version number
        max_num = portfolio.versions.aggregate(Max("version_number"))["version_number__max"] or 0
        version_number = max_num + 1

        # 2. Serialize top-level portfolio attributes
        fields_data = {
            "name": portfolio.name,
            "title": portfolio.title,
            "tagline": portfolio.tagline,
            "about": portfolio.about,
            "photo_url": portfolio.photo.url if portfolio.photo else "",
            "cover_url": portfolio.cover.url if portfolio.cover else "",
            "email": portfolio.email,
            "phone": portfolio.phone,
            "address": portfolio.address,
            "resume_url": portfolio.resume.url if portfolio.resume else "",
            "social_github": portfolio.social_github,
            "social_linkedin": portfolio.social_linkedin,
            "social_twitter": portfolio.social_twitter,
            "social_instagram": portfolio.social_instagram,
            "social_youtube": portfolio.social_youtube,
            "social_facebook": portfolio.social_facebook,
            "social_portfolio": portfolio.social_portfolio,
            "contact_email": portfolio.contact_email,
            "contact_phone": portfolio.contact_phone,
            "contact_address": portfolio.contact_address,
            "contact_form_action": portfolio.contact_form_action,
            "footer_copyright": portfolio.footer_copyright,
            "footer_tagline": portfolio.footer_tagline,
        }

        # 3. Serialize child models
        child_data = {
            "skills": [
                {"skill_type": s.skill_type, "name": s.name, "level": s.level}
                for s in portfolio.skills.all()
            ],
            "projects": [
                {
                    "title": p.title,
                    "description": p.description,
                    "technologies": p.technologies,
                    "github_url": p.github_url,
                    "live_url": p.live_url,
                    "order": p.order,
                }
                for p in portfolio.projects.all()
            ],
            "experiences": [
                {
                    "company": e.company,
                    "position": e.position,
                    "duration": e.duration,
                    "description": e.description,
                    "order": e.order,
                }
                for e in portfolio.experiences.all()
            ],
            "educations": [
                {
                    "degree": ed.degree,
                    "college": ed.college,
                    "university": ed.university,
                    "year": ed.year,
                    "order": ed.order,
                }
                for ed in portfolio.education.all()
            ],
            "certificates": [
                {"name": c.name, "issuer": c.issuer, "year": c.year, "url": c.url}
                for c in portfolio.certificates.all()
            ],
            "services": [
                {"title": s.title, "description": s.description, "icon": s.icon}
                for s in portfolio.services.all()
            ],
            "testimonials": [
                {
                    "reviewer_name": t.reviewer_name,
                    "reviewer_role": t.reviewer_role,
                    "text": t.text,
                }
                for t in portfolio.testimonials.all()
            ],
        }

        raw_snapshot = {
            "fields": fields_data,
            "children": child_data,
            "theme_name": portfolio.selected_theme.name if portfolio.selected_theme else "None",
        }

        compressed_snapshot = compress_snapshot(raw_snapshot)

        seo_snapshot = {
            "title": f"{portfolio.name} - {portfolio.title}",
            "description": portfolio.tagline or portfolio.about[:150],
        }

        # 4. Create PortfolioVersion record
        version_obj = PortfolioVersion.objects.create(
            portfolio=portfolio,
            version_number=version_number,
            title=title or f"Version {version_number}",
            description=description,
            snapshot_json=compressed_snapshot,
            theme=portfolio.selected_theme,
            seo_snapshot=seo_snapshot,
            tag=tag,
            created_by=created_by or portfolio.user,
            is_published=is_published,
            is_auto_save=is_auto_save,
            is_manual_save=is_manual_save,
            git_commit_sha=git_commit_sha,
        )

        # 5. Smart pruning: prune excess autosave records if total > 20
        _prune_old_autosaves(portfolio)

        return version_obj


def restore_version_snapshot(
    portfolio: Portfolio,
    version: PortfolioVersion,
    user=None,
    sections_to_restore: Optional[List[str]] = None
) -> PortfolioVersion:
    """
    Restores an active Portfolio instance from a PortfolioVersion snapshot.
    Supports full restore or partial section restore (e.g. ['projects', 'skills']).
    Creates a new 'Rollback' snapshot version and invalidates rendering cache.
    """
    snapshot = decompress_snapshot(version.snapshot_json)
    fields_data = snapshot.get("fields", {})
    child_data = snapshot.get("children", {})

    do_all = not sections_to_restore or "all" in sections_to_restore

    with transaction.atomic():
        # 1. Update top-level portfolio properties
        if do_all or "personal" in sections_to_restore or "about" in sections_to_restore or "contact" in sections_to_restore or "socials" in sections_to_restore or "settings" in sections_to_restore:
            for field, val in fields_data.items():
                if hasattr(portfolio, field) and not field.endswith("_url"):
                    # Section-specific filtering
                    if not do_all:
                        if "personal" in sections_to_restore and field in ["name", "title", "tagline", "phone", "address"]:
                            setattr(portfolio, field, val)
                        elif "about" in sections_to_restore and field in ["about"]:
                            setattr(portfolio, field, val)
                        elif "contact" in sections_to_restore and field in ["contact_email", "contact_phone", "contact_address", "contact_form_action"]:
                            setattr(portfolio, field, val)
                        elif "socials" in sections_to_restore and field.startswith("social_"):
                            setattr(portfolio, field, val)
                        elif "settings" in sections_to_restore and field.startswith("footer_"):
                            setattr(portfolio, field, val)
                    else:
                        setattr(portfolio, field, val)

        if (do_all or "theme" in sections_to_restore) and version.theme:
            portfolio.selected_theme = version.theme

        portfolio.save()

        # 2. Reconstruct child models based on sections_to_restore
        if do_all or "skills" in sections_to_restore:
            portfolio.skills.all().delete()
            for item in child_data.get("skills", []):
                PortfolioSkill.objects.create(portfolio=portfolio, **item)

        if do_all or "projects" in sections_to_restore:
            portfolio.projects.all().delete()
            for item in child_data.get("projects", []):
                PortfolioProject.objects.create(portfolio=portfolio, **item)

        if do_all or "experiences" in sections_to_restore or "experience" in sections_to_restore:
            portfolio.experiences.all().delete()
            for item in child_data.get("experiences", []):
                PortfolioExperience.objects.create(portfolio=portfolio, **item)

        if do_all or "educations" in sections_to_restore or "education" in sections_to_restore:
            portfolio.education.all().delete()
            for item in child_data.get("educations", []):
                PortfolioEducation.objects.create(portfolio=portfolio, **item)

        if do_all or "certificates" in sections_to_restore:
            portfolio.certificates.all().delete()
            for item in child_data.get("certificates", []):
                PortfolioCertificate.objects.create(portfolio=portfolio, **item)

        if do_all or "services" in sections_to_restore:
            portfolio.services.all().delete()
            for item in child_data.get("services", []):
                PortfolioService.objects.create(portfolio=portfolio, **item)

        if do_all or "testimonials" in sections_to_restore:
            portfolio.testimonials.all().delete()
            for item in child_data.get("testimonials", []):
                PortfolioTestimonial.objects.create(portfolio=portfolio, **item)

        # 3. Create a new Rollback snapshot
        restored_desc = f"Restored {', '.join(sections_to_restore)}" if sections_to_restore and not do_all else "Full Rollback"
        rollback_version = create_version_snapshot(
            portfolio=portfolio,
            title=f"Restored v{version.version_number} ({restored_desc})",
            description=f"Rollback performed from version #{version.version_number}",
            tag="Rollback",
            is_manual_save=True,
            created_by=user or portfolio.user,
        )

        # 4. Invalidate portfolio & theme rendering cache
        invalidate_portfolio_caches(portfolio.pk)

        return rollback_version


def compare_version_snapshots(
    version_a: PortfolioVersion,
    version_b: PortfolioVersion
) -> Dict:
    """
    Compares two PortfolioVersion snapshots and returns structured diff dictionary.
    Supports decompressed JSON inspection.
    """
    snap_a_raw = decompress_snapshot(version_a.snapshot_json)
    snap_b_raw = decompress_snapshot(version_b.snapshot_json)

    snap_a = snap_a_raw.get("fields", {})
    snap_b = snap_b_raw.get("fields", {})

    field_diffs = {}
    for key in set(snap_a.keys()).union(set(snap_b.keys())):
        val_a = snap_a.get(key, "")
        val_b = snap_b.get(key, "")
        if val_a != val_b:
            field_diffs[key] = {"old": val_a, "new": val_b}

    children_a = snap_a_raw.get("children", {})
    children_b = snap_b_raw.get("children", {})

    child_diffs = {
        "projects_count": {"old": len(children_a.get("projects", [])), "new": len(children_b.get("projects", []))},
        "experiences_count": {"old": len(children_a.get("experiences", [])), "new": len(children_b.get("experiences", []))},
        "skills_count": {"old": len(children_a.get("skills", [])), "new": len(children_b.get("skills", []))},
    }

    return {
        "version_a": version_a.version_number,
        "version_b": version_b.version_number,
        "theme_changed": version_a.theme_id != version_b.theme_id,
        "field_diffs": field_diffs,
        "child_diffs": child_diffs,
    }


def invalidate_portfolio_caches(portfolio_id: int):
    """
    Invalidates compiled HTML, CSS, theme, and SEO caches for a given portfolio ID.
    """
    cache_key_patterns = [
        f"rendered_portfolio_html_{portfolio_id}_*",
        f"portfolio_seo_meta_{portfolio_id}",
        f"portfolio_theme_css_{portfolio_id}",
    ]
    for pattern in cache_key_patterns:
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(pattern)
        else:
            cache.clear()


def _prune_old_autosaves(portfolio: Portfolio, max_total: int = 20):
    """
    Prunes old non-published autosave records if total versions exceed max_total.
    Never deletes published versions or manual saves.
    """
    autosaves = portfolio.versions.filter(is_published=False, is_manual_save=False, tag="Autosave")
    total_count = portfolio.versions.count()

    if total_count > max_total and autosaves.exists():
        to_delete = autosaves.order_by("created_at")[: (total_count - max_total)]
        pks = list(to_delete.values_list("pk", flat=True))
        PortfolioVersion.objects.filter(pk__in=pks).delete()
