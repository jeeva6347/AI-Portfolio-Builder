"""
portfolio/services/ai_assistant.py — AI Assistant & Smart Suggestions Service (Phase 8.5)

Provides:
  - compute_draft_version_hash(): Generates SHA-256 hash of portfolio draft content
  - DeterministicRuleEngine: Instant, zero-latency rule check evaluator
  - analyze_portfolio(): Hybrid Portfolio Analyzer combining Rule Engine + Gemini AI analysis

Guarantees:
  - Zero Database Writes (Pure Read-Only Analyzer)
  - Multidimensional Scoring (Overall, Completeness, Professionalism, SEO, Readability: 0-100)
  - Priority Sorting (critical > recommended > optional)
  - Stable Suggestion IDs, Explainability reasons, and Rule vs AI Source Metadata
  - Draft-Versioned Caching & Instant Invalidation
"""

import time
import json
import hashlib
from typing import Dict, List, Any, Tuple, Optional
from django.core.cache import cache

from portfolio.models import Portfolio
from portfolio.services.ai_provider import GeminiProvider, BaseAIProvider
from portfolio.services.prompt_library import PromptLibrary, PROMPT_VERSION
from portfolio.services.ai_generation import validate_and_sanitize_output


def compute_draft_version_hash(portfolio: Portfolio) -> str:
    """Computes a SHA-256 checksum (16 chars) representing the current draft state of a portfolio."""
    skills = list(portfolio.skills.values_list("name", "skill_type", "level"))
    projects = list(portfolio.projects.values_list("title", "description", "technologies"))
    experiences = list(portfolio.experiences.values_list("company", "position", "duration"))
    education = list(portfolio.education.values_list("degree", "college", "year"))

    draft_state = {
        "id": portfolio.pk,
        "name": portfolio.name,
        "title": portfolio.title,
        "about": portfolio.about,
        "email": portfolio.contact_email,
        "github": portfolio.social_github,
        "linkedin": portfolio.social_linkedin,
        "skills": skills,
        "projects": projects,
        "experiences": experiences,
        "education": education,
    }
    raw = json.dumps(draft_state, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class DeterministicRuleEngine:
    """Instant rule-based evaluator for deterministic checks (missing fields, SEO, accessibility)."""

    @classmethod
    def evaluate_rules(cls, portfolio: Portfolio) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        suggestions = []

        # 1. Contact Section Checks
        has_email = bool(portfolio.contact_email and portfolio.contact_email.strip())
        has_github = bool(portfolio.social_github and portfolio.social_github.strip())
        has_linkedin = bool(portfolio.social_linkedin and portfolio.social_linkedin.strip())

        if not has_email:
            suggestions.append({
                "id": "rule_missing_contact_email",
                "category": "contact",
                "intent": "SEO",
                "priority": "critical",
                "severity": "high",
                "source": "rule",
                "confidence": 0.95,
                "title": "Add contact email address",
                "description": "Your portfolio contact section is missing an email address.",
                "recommendation": "Provide a professional contact email to allow recruiters and clients to reach out.",
                "reason": "Direct contact options are critical for inbound career opportunities.",
                "section": "contact",
                "actionable": True,
                "action": {"type": "edit_field", "field": "contact_email"}
            })

        if not has_linkedin:
            suggestions.append({
                "id": "rule_missing_linkedin",
                "category": "contact",
                "intent": "Professionalism",
                "priority": "critical",
                "severity": "high",
                "source": "rule",
                "confidence": 0.95,
                "title": "Add LinkedIn profile URL",
                "description": "Your portfolio contact section is missing a LinkedIn profile link.",
                "recommendation": "Link your professional LinkedIn profile to boost recruiter trust.",
                "reason": "Hiring managers use LinkedIn to verify professional background and recommendations.",
                "section": "contact",
                "actionable": True,
                "action": {"type": "edit_field", "field": "social_linkedin"}
            })

        if not has_github:
            suggestions.append({
                "id": "rule_missing_github",
                "category": "contact",
                "intent": "SEO",
                "priority": "recommended",
                "severity": "medium",
                "source": "rule",
                "confidence": 0.90,
                "title": "Add GitHub profile link",
                "description": "No GitHub URL found in contact links.",
                "recommendation": "Add your GitHub URL to showcase open-source work and repositories.",
                "reason": "Technical recruiters look for GitHub links to review code samples.",
                "section": "contact",
                "actionable": True,
                "action": {"type": "edit_field", "field": "social_github"}
            })

        # 2. Hero & About Checks
        about_len = len(portfolio.about or "")
        if about_len < 40:
            suggestions.append({
                "id": "rule_short_about_bio",
                "category": "about",
                "intent": "Readability",
                "priority": "recommended",
                "severity": "medium",
                "source": "rule",
                "confidence": 0.95,
                "title": "Expand personal summary biography",
                "description": f"Your biography summary is only {about_len} characters long.",
                "recommendation": "Expand your about section with a 3-4 sentence overview of your domain expertise and goals.",
                "reason": "A comprehensive summary gives visitors quick insight into your background.",
                "section": "about",
                "actionable": True,
                "action": {"type": "regenerate_section", "target_section": "about"}
            })

        # 3. Skills Collection Checks
        skills_count = portfolio.skills.count()
        if skills_count < 3:
            suggestions.append({
                "id": "rule_empty_skills_collection",
                "category": "skills",
                "intent": "Content",
                "priority": "critical",
                "severity": "high",
                "source": "rule",
                "confidence": 0.95,
                "title": "Add technical and soft skills",
                "description": f"Only {skills_count} skill(s) found in your portfolio.",
                "recommendation": "Add at least 5-8 core technical skills and tools relevant to your career.",
                "reason": "Skill tags are indexed by ATS search filters and keyword queries.",
                "section": "skills",
                "actionable": True,
                "action": {"type": "add_item", "target_section": "skills"}
            })

        # 4. Projects Collection Checks
        projects_count = portfolio.projects.count()
        if projects_count == 0:
            suggestions.append({
                "id": "rule_empty_projects_collection",
                "category": "projects",
                "intent": "Content",
                "priority": "critical",
                "severity": "high",
                "source": "rule",
                "confidence": 0.95,
                "title": "Add featured projects",
                "description": "Your portfolio has zero showcased projects.",
                "recommendation": "Add at least 2-3 key projects demonstrating your technical problem-solving capabilities.",
                "reason": "Projects prove your practical skills through real-world applications.",
                "section": "projects",
                "actionable": True,
                "action": {"type": "add_item", "target_section": "projects"}
            })

        # Calculate Score Breakdowns based on Rule Checks
        comp_score = max(20, 100 - (25 if projects_count == 0 else 0) - (20 if skills_count < 3 else 0) - (15 if not has_email else 0))
        seo_score = max(25, 100 - (20 if not has_linkedin else 0) - (15 if not has_github else 0) - (15 if about_len < 40 else 0))
        prof_score = max(30, 100 - (20 if not has_linkedin else 0) - (15 if not has_email else 0) - (15 if projects_count == 0 else 0))
        read_score = max(30, 100 - (20 if about_len < 40 else 0))
        overall_score = int((comp_score + seo_score + prof_score + read_score) / 4)

        factors = {
            "completeness": {
                "score": comp_score,
                "factors": ["Projects populated" if projects_count > 0 else "Missing projects collection", "Skills populated" if skills_count >= 3 else "Insufficient skills"]
            },
            "seo": {
                "score": seo_score,
                "factors": ["LinkedIn profile linked" if has_linkedin else "Missing LinkedIn URL", "GitHub profile linked" if has_github else "Missing GitHub URL"]
            },
            "professionalism": {
                "score": prof_score,
                "factors": ["Contact email specified" if has_email else "Missing email contact"]
            },
            "readability": {
                "score": read_score,
                "factors": ["Adequate bio length" if about_len >= 40 else "Short bio summary"]
            },
            "overall": {
                "score": overall_score,
                "factors": ["Rule engine baseline evaluation complete"]
            }
        }

        return suggestions, factors


def analyze_portfolio(
    portfolio: Portfolio,
    user_instruction: Optional[str] = None,
    target_role: Optional[str] = None,
    industry: Optional[str] = None,
    seniority: Optional[str] = None,
    provider_instance: Optional[BaseAIProvider] = None
) -> Dict[str, Any]:
    """
    Executes hybrid AI Assistant analysis pipeline:
      1. Evaluates DeterministicRuleEngine checks (zero latency).
      2. Invokes AI Provider for qualitative LLM portfolio critique.
      3. Merges rule and AI suggestions into a priority-sorted list (critical > recommended > optional).
      4. Calculates multidimensional scores with factor lists.
      5. Caches analysis results under versioned draft hash.
    Guarantees: Zero database writes.
    """
    start_time = time.time()

    # Draft version hash check for caching
    draft_hash = compute_draft_version_hash(portfolio)
    cache_key = f"ai_analysis_{portfolio.pk}_{draft_hash}"

    cached_analysis = cache.get(cache_key)
    if cached_analysis and not user_instruction:
        return cached_analysis

    # 1. Run Deterministic Rule Engine
    rule_suggestions, rule_factors = DeterministicRuleEngine.evaluate_rules(portfolio)

    # 2. Extract Draft Portfolio Context
    skills_list = list(portfolio.skills.values_list("name", flat=True))
    projects_list = [
        {"title": p.title, "description": p.description, "tech": p.technologies}
        for p in portfolio.projects.all()
    ]
    experience_list = [
        {"company": e.company, "position": e.position, "duration": e.duration}
        for e in portfolio.experiences.all()
    ]

    draft_context = {
        "name": portfolio.name,
        "title": portfolio.title,
        "about": portfolio.about,
        "contact_email": portfolio.contact_email,
        "social_github": portfolio.social_github,
        "social_linkedin": portfolio.social_linkedin,
        "skills": skills_list,
        "projects": projects_list,
        "experience": experience_list,
        "target_role": target_role or "",
        "industry": industry or "",
        "seniority": seniority or ""
    }

    # 3. Invoke AI Provider for Qualitative Evaluation
    provider = provider_instance or GeminiProvider()
    ai_suggestions = []
    ai_scores = rule_factors

    try:
        compiled_prompt = PromptLibrary.build_prompt(
            "portfolio_analysis",
            variables={
                "portfolio_data": draft_context,
                "user_instruction": user_instruction or "Focus on improving tone, SEO keywords, and executive impact."
            }
        )

        raw_response, token_meta = provider.generate(
            compiled_prompt["user_prompt"],
            system_prompt=compiled_prompt["system_prompt"]
        )
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

        # Extract AI scores and AI suggestions
        ai_scores_raw = parsed_json.get("scores", {})
        if isinstance(ai_scores_raw, dict) and "overall" in ai_scores_raw:
            ai_scores = ai_scores_raw

        raw_ai_suggs = parsed_json.get("suggestions", [])
        if isinstance(raw_ai_suggs, list):
            for idx, item in enumerate(raw_ai_suggs):
                if isinstance(item, dict):
                    category = item.get("category", "overall")
                    priority = item.get("priority", "recommended").lower()
                    if priority not in ["critical", "recommended", "optional"]:
                        priority = "recommended"

                    ai_suggestions.append({
                        "id": item.get("id", f"ai_{category}_{idx}"),
                        "category": category,
                        "intent": item.get("intent", "Professionalism"),
                        "priority": priority,
                        "severity": item.get("severity", "medium"),
                        "source": "ai",
                        "confidence": float(item.get("confidence", 0.88)),
                        "title": item.get("title", f"Improve {category} section"),
                        "description": item.get("description", ""),
                        "recommendation": item.get("recommendation", ""),
                        "reason": item.get("reason", "Enhances portfolio clarity and presentation."),
                        "section": item.get("section", category),
                        "actionable": bool(item.get("actionable", True)),
                        "action": {"type": "regenerate_section", "target_section": category}
                    })

    except Exception:
        # Fall back gracefully to rule-engine evaluation on LLM timeout/error
        elapsed_ms = int((time.time() - start_time) * 1000)
        token_meta = {"prompt_tokens": 0, "completion_tokens": 0, "tokens_used": 0}

    # 4. Merge Rule and AI Suggestions & Sort by Priority
    all_suggestions = rule_suggestions + ai_suggestions

    priority_map = {"critical": 0, "recommended": 1, "optional": 2}
    all_suggestions.sort(key=lambda s: priority_map.get(s.get("priority", "recommended"), 1))

    # Format final payload
    payload = {
        "success": True,
        "code": "ANALYSIS_COMPLETE",
        "scores": ai_scores,
        "suggestions": all_suggestions,
        "metadata": {
            "provider": provider.__class__.__name__.replace("Provider", ""),
            "model": getattr(provider, "MODEL_NAME", "gemini-1.5-flash"),
            "prompt_version": PROMPT_VERSION,
            "analysis_version": "1.0",
            "generation_time_ms": elapsed_ms,
            "token_usage": token_meta
        },
        "errors": []
    }

    cache.set(cache_key, payload, timeout=3600)
    return payload
