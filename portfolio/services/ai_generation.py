"""
portfolio/services/ai_generation.py — Advanced AI Portfolio Generation Pipeline (Phase 8.1)

Pipeline Stages:
  User Profile Input Data -> Prompt Context Assembly -> AI Provider -> Response Parser -> Safety & Schema Validator -> Output Payload

Guarantees:
  - Zero Database Writes (Pure Functional Generator)
  - JSON Schema Validation
  - AI Safety & XSS Sanitization
  - Provider Abstraction & Token Tracking
"""

import json
import re
import time
from typing import Dict, List, Tuple

from portfolio.services.ai_prompts import PROMPT_VERSION, build_portfolio_prompt
from portfolio.services.ai_provider import GeminiProvider, BaseAIProvider


def sanitize_text(text: str) -> str:
    """Strips HTML/JavaScript injection tags and truncates excessive whitespace."""
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    # Strip script, iframe, and dangerous HTML tags
    clean = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r"<iframe.*?>.*?</iframe>", "", clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r"<.*?>", "", clean)
    return clean.strip()


def validate_and_sanitize_output(raw_dict: dict, required_sections: Optional[List[str]] = None) -> Tuple[dict, List[Dict[str, str]]]:
    if not isinstance(raw_dict, dict):
        raw_dict = {}

    errors = []
    sanitized = {}

    all_keys = ["hero", "about", "skills", "projects", "experience", "education", "contact"]
    target_keys = required_sections if required_sections else [k for k in all_keys if k in raw_dict]

    if not target_keys:
        return raw_dict, [{"code": "NO_VALID_SECTIONS", "message": "No valid portfolio sections found in payload."}]

    for key in target_keys:
        if key not in raw_dict or raw_dict[key] is None:
            errors.append({
                "code": f"MISSING_SECTION_{key.upper()}",
                "message": f"Required portfolio section '{key}' is missing or null."
            })

    if errors:
        return raw_dict, errors

    # 1. Sanitize Hero Section
    if "hero" in raw_dict and raw_dict["hero"]:
        hero = raw_dict.get("hero", {})
        sanitized["hero"] = {
            "name": sanitize_text(hero.get("name", "")),
            "headline": sanitize_text(hero.get("headline", "")),
            "bio": sanitize_text(hero.get("bio", "")),
        }

    # 2. Sanitize About Section
    if "about" in raw_dict and raw_dict["about"]:
        about = raw_dict.get("about", {})
        highlights = [sanitize_text(h) for h in about.get("highlights", []) if h]
        sanitized["about"] = {
            "summary": sanitize_text(about.get("summary", "")),
            "highlights": highlights[:6],  # Max 6 highlights
        }

    # 3. Sanitize Skills Section (Deduplicate by name)
    if "skills" in raw_dict and raw_dict["skills"] is not None:
        skills = raw_dict.get("skills", [])
        seen_skills = set()
        sanitized_skills = []
        if isinstance(skills, list):
            for s in skills:
                if isinstance(s, dict):
                    name = sanitize_text(s.get("name", ""))
                    norm_name = name.lower()
                    if name and norm_name not in seen_skills:
                        seen_skills.add(norm_name)
                        sanitized_skills.append({
                            "name": name,
                            "category": sanitize_text(s.get("category", "technical")).lower(),
                            "level": sanitize_text(s.get("level", "Intermediate")),
                        })
                elif isinstance(s, str) and s.strip():
                    name = sanitize_text(s.strip())
                    norm_name = name.lower()
                    if norm_name not in seen_skills:
                        seen_skills.add(norm_name)
                        sanitized_skills.append({
                            "name": name,
                            "category": "technical",
                            "level": "Intermediate",
                        })
        sanitized["skills"] = sanitized_skills

    # 4. Sanitize Projects Section
    if "projects" in raw_dict and raw_dict["projects"] is not None:
        projects = raw_dict.get("projects", [])
        sanitized_projects = []
        if isinstance(projects, list):
            for p in projects:
                if isinstance(p, dict):
                    techs = p.get("technologies", [])
                    if isinstance(techs, str):
                        techs = techs.split()
                    sanitized_techs = list(dict.fromkeys([sanitize_text(t) for t in techs if t]))

                    sanitized_projects.append({
                        "title": sanitize_text(p.get("title", "")),
                        "description": sanitize_text(p.get("description", "")),
                        "technologies": sanitized_techs,
                        "url": sanitize_text(p.get("url", "")),
                    })
        sanitized["projects"] = sanitized_projects

    # 5. Sanitize Experience Section
    if "experience" in raw_dict and raw_dict["experience"] is not None:
        experience = raw_dict.get("experience", [])
        sanitized_exp = []
        if isinstance(experience, list):
            for e in experience:
                if isinstance(e, dict):
                    sanitized_exp.append({
                        "company": sanitize_text(e.get("company", "")),
                        "position": sanitize_text(e.get("position", "")),
                        "duration": sanitize_text(e.get("duration", "")),
                        "description": sanitize_text(e.get("description", "")),
                    })
        sanitized["experience"] = sanitized_exp

    # 6. Sanitize Education Section
    if "education" in raw_dict and raw_dict["education"] is not None:
        education = raw_dict.get("education", [])
        sanitized_edu = []
        if isinstance(education, list):
            for ed in education:
                if isinstance(ed, dict):
                    sanitized_edu.append({
                        "institution": sanitize_text(ed.get("institution", ed.get("college", ""))),
                        "degree": sanitize_text(ed.get("degree", "")),
                        "year": sanitize_text(ed.get("year", "")),
                    })
        sanitized["education"] = sanitized_edu

    # 7. Sanitize Contact Section
    if "contact" in raw_dict and raw_dict["contact"]:
        contact = raw_dict.get("contact", {})
        sanitized["contact"] = {
            "email": sanitize_text(contact.get("email", "")),
            "github": sanitize_text(contact.get("github", "")),
            "linkedin": sanitize_text(contact.get("linkedin", "")),
        }

    return sanitized, errors


def generate_portfolio_with_ai(profile_data: dict, provider_instance: BaseAIProvider = None) -> Dict:
    """
    Executes AI Portfolio Generation Pipeline:
      1. Builds prompt context (ai_prompts.py).
      2. Invokes AI Provider (GeminiProvider with retry logic).
      3. Parses raw JSON response.
      4. Runs JSON Schema validation & XSS safety sanitization.
      5. Returns structured output payload with AI metadata.

    Guarantees: Zero database writes.
    """
    start_time = time.time()

    # Input validation
    if not isinstance(profile_data, dict) or not profile_data:
        return {
            "success": False,
            "code": "INVALID_PROFILE_DATA",
            "message": "Input profile data must be a non-empty dictionary.",
            "errors": [{"code": "INVALID_PROFILE_DATA", "message": "Profile data empty or malformed."}]
        }

    # 1. Modular Prompt Assembly
    system_prompt, user_prompt = build_portfolio_prompt(profile_data)

    # 2. Provider Selection
    provider = provider_instance or GeminiProvider()

    try:
        # 3. Execute AI LLM Generation
        raw_response, token_meta = provider.generate(user_prompt, system_prompt=system_prompt)
        elapsed_ms = int((time.time() - start_time) * 1000)

        # 4. Clean JSON response wrappers if present
        clean_text = raw_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        parsed_json = json.loads(clean_text)

        # 5. Schema & Safety Validation
        sanitized_data, errors = validate_and_sanitize_output(parsed_json)

        if errors:
            return {
                "success": False,
                "code": "SCHEMA_VALIDATION_FAILED",
                "message": "Generated AI portfolio output failed schema validation.",
                "errors": errors
            }

        return {
            "success": True,
            "code": "AI_GENERATION_SUCCESSFUL",
            "message": "Successfully generated structured AI portfolio data.",
            "data": sanitized_data,
            "metadata": {
                "provider": provider.__class__.__name__.replace("Provider", ""),
                "model": getattr(provider, "MODEL_NAME", "gemini-1.5-flash"),
                "prompt_version": PROMPT_VERSION,
                "generation_time_ms": elapsed_ms,
                "token_usage": token_meta
            },
            "errors": []
        }

    except json.JSONDecodeError as json_err:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "code": "JSON_PARSE_ERROR",
            "message": f"AI response was not valid JSON: {str(json_err)}",
            "errors": [{"code": "JSON_PARSE_ERROR", "message": str(json_err)}]
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "code": "AI_GENERATION_FAILED",
            "message": f"AI Portfolio Generation failed: {str(e)}",
            "errors": [{"code": "AI_GENERATION_FAILED", "message": str(e)}]
        }
