"""
portfolio/services/ai_regeneration.py — AI Section Regeneration & Smart Editing (Phase 8.3)

Provides:
  - compute_section_checksum(): Generates SHA-256 hash for section content
  - extract_current_section_data(): Extracts current draft section content
  - regenerate_section(): Generates AI section preview (Zero DB Writes)
  - apply_regenerated_section(): Atomically applies accepted section to draft & creates PortfolioVersion
"""

import time
import json
import hashlib
from typing import Dict, Any, Tuple, Optional
from django.db import transaction
from django.core.cache import cache

from portfolio.models import Portfolio, PortfolioVersion, PortfolioBuildLog
from portfolio.services.ai_prompts import PROMPT_VERSION, build_section_regeneration_prompt
from portfolio.services.ai_provider import GeminiProvider, BaseAIProvider
from portfolio.services.ai_generation import validate_and_sanitize_output
from portfolio.services.ai_import import SECTION_IMPORTERS
from portfolio.services.versioning import create_version_snapshot


def compute_section_checksum(section_data: Any) -> str:
    """Generates a SHA-256 checksum hash (16 chars) for section data to detect identical outputs."""
    raw_str = json.dumps(section_data, sort_keys=True, default=str)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]


def extract_current_section_data(portfolio: Portfolio, section_name: str) -> Any:
    """Extracts structured draft data for a single section from Portfolio and child models."""
    sec = section_name.lower()

    if sec == "hero":
        return {
            "name": portfolio.name,
            "headline": portfolio.title,
            "bio": portfolio.about
        }

    elif sec == "about":
        return {
            "summary": portfolio.about,
            "highlights": []
        }

    elif sec == "skills":
        return [
            {
                "name": s.name,
                "category": s.skill_type,
                "level": s.level or "Intermediate"
            }
            for s in portfolio.skills.all()
        ]

    elif sec == "projects":
        return [
            {
                "title": p.title,
                "description": p.description,
                "technologies": [t.strip() for t in p.technologies.split(",") if t.strip()],
                "url": p.live_url
            }
            for p in portfolio.projects.all()
        ]

    elif sec == "experience":
        return [
            {
                "company": e.company,
                "position": e.position,
                "duration": e.duration,
                "description": e.description
            }
            for e in portfolio.experiences.all()
        ]

    elif sec == "education":
        return [
            {
                "institution": ed.college,
                "degree": ed.degree,
                "year": ed.year
            }
            for ed in portfolio.education.all()
        ]

    elif sec == "contact":
        return {
            "email": portfolio.contact_email,
            "github": portfolio.social_github,
            "linkedin": portfolio.social_linkedin
        }

    return {}


def regenerate_section(
    portfolio: Portfolio,
    section_name: str,
    user_prompt: str = "",
    provider_instance: Optional[BaseAIProvider] = None
) -> Dict:
    """
    Executes targeted AI section regeneration in Preview Mode:
      1. Extracts current draft section data and computes current_checksum.
      2. Assembles section prompt context (ai_prompts.py).
      3. Invokes AI Provider with retry logic and token usage tracking.
      4. Parses & sanitizes section output.
      5. Computes regenerated_checksum and evaluates is_identical.
    Guarantees: Zero database writes.
    """
    start_time = time.time()
    sec_name = section_name.lower()

    if sec_name not in SECTION_IMPORTERS:
        return {
            "success": False,
            "code": "INVALID_SECTION",
            "message": f"Unsupported portfolio section '{section_name}'.",
            "errors": [{"code": "INVALID_SECTION", "message": f"Section '{section_name}' is not supported."}]
        }

    # 1. Extract Current Draft Section & Checksum
    current_data = extract_current_section_data(portfolio, sec_name)
    current_checksum = compute_section_checksum(current_data)

    # 2. Portfolio Context Assembly
    skills_summary = list(portfolio.skills.values_list("name", flat=True)[:10])
    projects_summary = list(portfolio.projects.values_list("title", flat=True)[:5])
    portfolio_context = {
        "name": portfolio.name,
        "title": portfolio.title,
        "skills": skills_summary,
        "projects": projects_summary
    }

    # 3. Build Section Prompt Context
    system_prompt, formatted_user_prompt = build_section_regeneration_prompt(
        portfolio_context=portfolio_context,
        section_name=sec_name,
        current_section_data=current_data,
        user_prompt=user_prompt
    )

    # 4. Invoke AI LLM Provider
    provider = provider_instance or GeminiProvider()

    try:
        raw_response, token_meta = provider.generate(formatted_user_prompt, system_prompt=system_prompt)
        elapsed_ms = int((time.time() - start_time) * 1000)

        clean_text = raw_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        parsed_json = json.loads(clean_text)

        # 5. Section Output Validation & Sanitization
        sanitized_dict, validation_errors = validate_and_sanitize_output(parsed_json, required_sections=[sec_name])

        if validation_errors:
            return {
                "success": False,
                "code": "VALIDATION_FAILED",
                "message": f"Regenerated section '{sec_name}' failed schema validation.",
                "errors": validation_errors
            }

        regenerated_data = sanitized_dict.get(sec_name, {})
        regenerated_checksum = compute_section_checksum(regenerated_data)

        return {
            "success": True,
            "code": "REGENERATION_PREVIEW_READY",
            "section_name": sec_name,
            "current_data": current_data,
            "regenerated_data": regenerated_data,
            "current_checksum": current_checksum,
            "regenerated_checksum": regenerated_checksum,
            "is_identical": (current_checksum == regenerated_checksum),
            "metadata": {
                "provider": provider.__class__.__name__.replace("Provider", ""),
                "model": getattr(provider, "MODEL_NAME", "gemini-1.5-flash"),
                "prompt_version": PROMPT_VERSION,
                "section": sec_name,
                "generation_time_ms": elapsed_ms,
                "token_usage": token_meta
            },
            "errors": []
        }

    except json.JSONDecodeError as json_err:
        return {
            "success": False,
            "code": "JSON_PARSE_ERROR",
            "message": f"AI response for section '{sec_name}' was not valid JSON: {str(json_err)}",
            "errors": [{"code": "JSON_PARSE_ERROR", "message": str(json_err)}]
        }
    except Exception as e:
        return {
            "success": False,
            "code": "REGENERATION_FAILED",
            "message": f"Section regeneration failed: {str(e)}",
            "errors": [{"code": "REGENERATION_FAILED", "message": str(e)}]
        }


def apply_regenerated_section(
    portfolio: Portfolio,
    section_name: str,
    regenerated_data: Any,
    ai_metadata: Optional[dict] = None,
    expected_checksum: Optional[str] = None,
    user=None
) -> Dict:
    """
    Atomically applies an accepted regenerated section to portfolio draft state:
      1. Validates section name and conflict detection checksum if provided.
      2. Executes inside @transaction.atomic for complete rollback safety.
      3. Invokes target Section Importer (mode="replace").
      4. Creates a new PortfolioVersion snapshot with AI metadata.
      5. Purges draft preview cache and returns updated section data.
    """
    start_time = time.time()
    sec_name = section_name.lower()

    importer = SECTION_IMPORTERS.get(sec_name)
    if not importer:
        return {
            "success": False,
            "code": "INVALID_SECTION",
            "message": f"Unsupported section '{section_name}'.",
            "errors": [{"code": "INVALID_SECTION", "message": f"Section '{section_name}' is not supported."}]
        }

    # Conflict Detection Check
    current_data = extract_current_section_data(portfolio, sec_name)
    current_checksum = compute_section_checksum(current_data)

    if expected_checksum and expected_checksum != current_checksum:
        return {
            "success": False,
            "code": "CONFLICT_DETECTED",
            "message": f"Draft section '{sec_name}' was modified after AI generation. Please re-generate preview.",
            "errors": [{"code": "CONFLICT_DETECTED", "message": "Draft state checksum mismatch."}]
        }

    try:
        with transaction.atomic():
            # 1. Replace only the target section
            status_action, warnings = importer.import_section(
                portfolio=portfolio,
                data=regenerated_data,
                mode="replace"
            )

            portfolio.status = Portfolio.Status.DRAFT
            portfolio.save()

            # 2. Create PortfolioVersion Snapshot
            version_title = f"Regenerated {sec_name.title()} Section"
            snapshot = create_version_snapshot(
                portfolio=portfolio,
                title=version_title,
                tag="AI Generated",
                description=f"AI regenerated section '{sec_name}'",
                is_published=False,
                is_manual_save=True,
                created_by=user
            )

            # Attach AI metadata to snapshot
            meta_payload = ai_metadata or {}
            meta_payload["section"] = sec_name
            meta_payload["checksum"] = compute_section_checksum(regenerated_data)

            snapshot_dict = snapshot.snapshot_json
            snapshot_dict["_ai_metadata"] = meta_payload
            snapshot.snapshot_json = snapshot_dict
            snapshot.save(update_fields=["snapshot_json"])

            # 3. Audit Transaction Log & Cache Purge
            elapsed_ms = int((time.time() - start_time) * 1000)
            PortfolioBuildLog.objects.create(
                portfolio=portfolio,
                status="IMPORTED",
                step=f"AI Regenerate {sec_name.title()}",
                message=f"Regenerated section '{sec_name}' applied successfully.",
                duration_ms=elapsed_ms
            )

            cache.delete(f"builder_draft_{portfolio.pk}")
            cache.delete_pattern(f"ai_analysis_{portfolio.pk}_*") if hasattr(cache, "delete_pattern") else None

            updated_section_content = extract_current_section_data(portfolio, sec_name)

            return {
                "success": True,
                "status": "SECTION_APPLIED",
                "section_name": sec_name,
                "version_number": snapshot.version_number,
                "updated_section_data": updated_section_content,
                "warnings": warnings,
                "errors": []
            }

    except Exception as e:
        error_msg = str(e)
        return {
            "success": False,
            "code": "APPLY_SECTION_FAILED",
            "message": f"Failed to apply regenerated section '{sec_name}': {error_msg}",
            "errors": [{"code": "APPLY_SECTION_FAILED", "message": error_msg}]
        }
