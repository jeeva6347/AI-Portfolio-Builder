"""
portfolio/services/ai_import.py — Advanced AI Portfolio Import Engine (Phase 8.2)

Architecture:
  Structured Input -> Section Importers (Hero, About, Skills, Projects, Experience, Education, Contact) ->
  Atomic Transaction -> Version Snapshot with AI Metadata -> Audit Logging -> Selective Cache Purge -> Import Report

Supports:
  - Partial section import filtering (sections=["hero", "skills"])
  - Configurable import modes: "replace", "merge", "skip_existing"
  - Pure Draft isolation (never mutates published versions/snapshots)
  - Complete rollback on error (@transaction.atomic)
"""

import time
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from django.db import transaction
from django.core.cache import cache

from portfolio.models import (
    Portfolio,
    PortfolioSkill,
    PortfolioProject,
    PortfolioExperience,
    PortfolioEducation,
    PortfolioVersion,
    PortfolioBuildLog,
)
from portfolio.services.versioning import create_version_snapshot
from portfolio.services.ai_generation import validate_and_sanitize_output


class BaseSectionImporter(ABC):
    """Abstract Base Class for Portfolio Section Importers."""

    @abstractmethod
    def import_section(self, portfolio: Portfolio, data: Any, mode: str = "replace") -> Tuple[str, List[str]]:
        """
        Imports section data into target portfolio models according to mode ('replace', 'merge', 'skip_existing').
        Returns tuple: (status_action, warnings_list)
        """
        pass


class HeroImporter(BaseSectionImporter):
    """Imports Hero section fields (name, headline, bio)."""

    def import_section(self, portfolio: Portfolio, data: dict, mode: str = "replace") -> Tuple[str, List[str]]:
        if not isinstance(data, dict) or not data:
            return "skipped", ["Hero data is empty."]

        if mode == "skip_existing" and (portfolio.name or portfolio.title):
            return "skipped", ["Skipped existing hero section."]

        name = data.get("name")
        headline = data.get("headline")
        bio = data.get("bio")

        if name:
            portfolio.name = name
        if headline:
            portfolio.title = headline
        if bio and not portfolio.about:
            portfolio.about = bio

        portfolio.save()
        return "updated", []


class AboutImporter(BaseSectionImporter):
    """Imports About section fields (biography summary)."""

    def import_section(self, portfolio: Portfolio, data: dict, mode: str = "replace") -> Tuple[str, List[str]]:
        if not isinstance(data, dict) or not data:
            return "skipped", ["About data is empty."]

        if mode == "skip_existing" and portfolio.about:
            return "skipped", ["Skipped existing about section."]

        summary = data.get("summary")
        if summary:
            portfolio.about = summary
            portfolio.save()
            return "updated", []
        return "skipped", []


class SkillsImporter(BaseSectionImporter):
    """Imports Skills section items (technical & soft skills)."""

    def import_section(self, portfolio: Portfolio, data: list, mode: str = "replace") -> Tuple[str, List[str]]:
        if not isinstance(data, list) or not data:
            return "skipped", ["Skills data is empty."]

        if mode == "skip_existing" and portfolio.skills.exists():
            return "skipped", ["Skipped existing skills collection."]

        if mode == "replace":
            portfolio.skills.all().delete()

        existing_names = set(portfolio.skills.values_list("name", flat=True)) if mode == "merge" else set()
        created_count = 0

        for item in data:
            if isinstance(item, dict):
                name = item.get("name", "").strip()
                if not name:
                    continue
                if mode == "merge" and name.lower() in {n.lower() for n in existing_names}:
                    continue

                PortfolioSkill.objects.create(
                    portfolio=portfolio,
                    name=name,
                    skill_type=item.get("category", "technical").lower(),
                    level=item.get("level", "Intermediate"),
                )
                existing_names.add(name)
                created_count += 1

        action = "replaced" if mode == "replace" else ("merged" if created_count > 0 else "unchanged")
        return action, []


class ProjectsImporter(BaseSectionImporter):
    """Imports Projects section items."""

    def import_section(self, portfolio: Portfolio, data: list, mode: str = "replace") -> Tuple[str, List[str]]:
        if not isinstance(data, list) or not data:
            return "skipped", ["Projects data is empty."]

        if mode == "skip_existing" and portfolio.projects.exists():
            return "skipped", ["Skipped existing projects collection."]

        if mode == "replace":
            portfolio.projects.all().delete()

        existing_titles = set(portfolio.projects.values_list("title", flat=True)) if mode == "merge" else set()
        created_count = 0

        for idx, item in enumerate(data):
            if isinstance(item, dict):
                title = item.get("title", "").strip()
                if not title:
                    continue
                if mode == "merge" and title.lower() in {t.lower() for t in existing_titles}:
                    continue

                techs = item.get("technologies", [])
                tech_str = ", ".join(techs) if isinstance(techs, list) else str(techs)

                PortfolioProject.objects.create(
                    portfolio=portfolio,
                    title=title,
                    description=item.get("description", ""),
                    technologies=tech_str,
                    live_url=item.get("url", ""),
                    order=idx,
                )
                existing_titles.add(title)
                created_count += 1

        action = "replaced" if mode == "replace" else ("merged" if created_count > 0 else "unchanged")
        return action, []


class ExperienceImporter(BaseSectionImporter):
    """Imports Experience section items."""

    def import_section(self, portfolio: Portfolio, data: list, mode: str = "replace") -> Tuple[str, List[str]]:
        if not isinstance(data, list) or not data:
            return "skipped", ["Experience data is empty."]

        if mode == "skip_existing" and portfolio.experiences.exists():
            return "skipped", ["Skipped existing experience collection."]

        if mode == "replace":
            portfolio.experiences.all().delete()

        existing_roles = set(portfolio.experiences.values_list("position", flat=True)) if mode == "merge" else set()
        created_count = 0

        for idx, item in enumerate(data):
            if isinstance(item, dict):
                position = item.get("position", "").strip()
                company = item.get("company", "").strip()
                if not position or not company:
                    continue
                if mode == "merge" and position.lower() in {p.lower() for p in existing_roles}:
                    continue

                PortfolioExperience.objects.create(
                    portfolio=portfolio,
                    company=company,
                    position=position,
                    duration=item.get("duration", ""),
                    description=item.get("description", ""),
                    order=idx,
                )
                existing_roles.add(position)
                created_count += 1

        action = "replaced" if mode == "replace" else ("merged" if created_count > 0 else "unchanged")
        return action, []


class EducationImporter(BaseSectionImporter):
    """Imports Education section items."""

    def import_section(self, portfolio: Portfolio, data: list, mode: str = "replace") -> Tuple[str, List[str]]:
        if not isinstance(data, list) or not data:
            return "skipped", ["Education data is empty."]

        if mode == "skip_existing" and portfolio.education.exists():
            return "skipped", ["Skipped existing education collection."]

        if mode == "replace":
            portfolio.education.all().delete()

        existing_degrees = set(portfolio.education.values_list("degree", flat=True)) if mode == "merge" else set()
        created_count = 0

        for idx, item in enumerate(data):
            if isinstance(item, dict):
                degree = item.get("degree", "").strip()
                institution = item.get("institution", item.get("college", "")).strip()
                if not degree or not institution:
                    continue
                if mode == "merge" and degree.lower() in {d.lower() for d in existing_degrees}:
                    continue

                PortfolioEducation.objects.create(
                    portfolio=portfolio,
                    degree=degree,
                    college=institution,
                    year=item.get("year", ""),
                    order=idx,
                )
                existing_degrees.add(degree)
                created_count += 1

        action = "replaced" if mode == "replace" else ("merged" if created_count > 0 else "unchanged")
        return action, []


class ContactImporter(BaseSectionImporter):
    """Imports Contact section fields (email, github, linkedin)."""

    def import_section(self, portfolio: Portfolio, data: dict, mode: str = "replace") -> Tuple[str, List[str]]:
        if not isinstance(data, dict) or not data:
            return "skipped", ["Contact data is empty."]

        if mode == "skip_existing" and portfolio.contact_email:
            return "skipped", ["Skipped existing contact section."]

        email = data.get("email")
        github = data.get("github")
        linkedin = data.get("linkedin")

        if email:
            portfolio.contact_email = email
        if github:
            portfolio.social_github = github
        if linkedin:
            portfolio.social_linkedin = linkedin

        portfolio.save()
        return "updated", []


# Registry of section importers
SECTION_IMPORTERS = {
    "hero": HeroImporter(),
    "about": AboutImporter(),
    "skills": SkillsImporter(),
    "projects": ProjectsImporter(),
    "experience": ExperienceImporter(),
    "education": EducationImporter(),
    "contact": ContactImporter(),
}


def import_generated_portfolio(
    portfolio: Portfolio,
    ai_data: dict,
    sections: Optional[List[str]] = None,
    mode: str = "replace",
    ai_metadata: Optional[dict] = None,
    user=None
) -> Dict:
    """
    Imports structured AI portfolio JSON into the database draft:
      1. Validates schema and sanitizes input data.
      2. Executes inside @transaction.atomic for complete rollback safety.
      3. Dispatches partial/full sections to modular section importers.
      4. Only mutates active Draft state (never published site versions).
      5. Creates an 'AI Generated' PortfolioVersion snapshot with AI metadata.
      6. Records audit transaction log in PortfolioBuildLog.
      7. Purges draft preview caches and returns detailed import report.
    """
    start_time = time.time()

    # 1. Pre-flight Schema Validation & Sanitization
    sanitized_data, validation_errors = validate_and_sanitize_output(ai_data, required_sections=sections)
    if validation_errors:
        return {
            "success": False,
            "status": "FAILED",
            "code": "VALIDATION_FAILED",
            "message": "AI portfolio import validation failed.",
            "errors": validation_errors
        }

    # Determine sections to import
    available_sections = [s for s in SECTION_IMPORTERS.keys() if s in sanitized_data]
    target_sections = sections if sections else available_sections

    sections_report = {}
    all_warnings = []

    try:
        with transaction.atomic():
            # 2. Section Import Dispatcher
            for sec_name in target_sections:
                importer = SECTION_IMPORTERS.get(sec_name)
                if importer and sec_name in sanitized_data:
                    status_action, warnings = importer.import_section(
                        portfolio=portfolio,
                        data=sanitized_data[sec_name],
                        mode=mode
                    )
                    sections_report[sec_name] = status_action
                    all_warnings.extend(warnings)

            # Ensure portfolio status remains DRAFT
            portfolio.status = Portfolio.Status.DRAFT
            portfolio.save()

            # 3. Create Version History Snapshot with AI Metadata
            snapshot = create_version_snapshot(
                portfolio=portfolio,
                title="AI Generated Portfolio",
                tag="AI Generated",
                description="Imported from AI generation engine.",
                is_published=False,
                is_manual_save=True,
                created_by=user
            )

            # Attach AI metadata to snapshot dictionary if provided
            if ai_metadata and isinstance(ai_metadata, dict):
                snapshot_data = snapshot.snapshot_json
                snapshot_data["_ai_metadata"] = ai_metadata
                snapshot.snapshot_json = snapshot_data
                snapshot.save(update_fields=["snapshot_json"])

            # 4. Audit Transaction Logging
            elapsed_ms = int((time.time() - start_time) * 1000)
            PortfolioBuildLog.objects.create(
                portfolio=portfolio,
                status="IMPORTED",
                step="AI Import",
                message=f"Imported sections: {list(sections_report.keys())} [Mode: {mode}]",
                duration_ms=elapsed_ms
            )

            # 5. Selective Cache Invalidation (Draft preview cache & AI analysis cache)
            cache.delete(f"builder_draft_{portfolio.pk}")
            cache.delete_pattern(f"ai_analysis_{portfolio.pk}_*") if hasattr(cache, "delete_pattern") else None

            return {
                "success": True,
                "status": "IMPORTED",
                "mode": mode,
                "version_number": snapshot.version_number,
                "sections": sections_report,
                "warnings": all_warnings,
                "errors": []
            }

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)

        return {
            "success": False,
            "status": "FAILED",
            "code": "AI_IMPORT_FAILED",
            "message": f"AI Portfolio import failed: {error_msg}",
            "errors": [{"code": "AI_IMPORT_FAILED", "message": error_msg}]
        }
