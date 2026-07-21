"""
portfolio/services/ai_prompts.py — Modular Prompt Templates & Context Builder (Phase 8.1 / 8.4 Integration)

Delegates prompt compilation to PromptLibrary (portfolio/services/prompt_library.py)
while preserving 100% backward compatibility for exports and existing function signatures.
"""

import json
from typing import Tuple, Any
from portfolio.services.prompt_library import PromptLibrary, PromptTemplate

PROMPT_VERSION = "1.0"

SYSTEM_PROMPT = (
    "You are an executive resume writer, senior career coach, and digital portfolio architect. "
    "Your objective is to convert raw user profile inputs into a highly polished, professional, "
    "and engaging digital portfolio JSON payload."
)

INSTRUCTIONS_PROMPT = """
Guidelines:
1. Elevate raw summaries into compelling, action-oriented professional statements.
2. Quantify achievements where possible (e.g., "Increased performance by 40%").
3. Organize skills cleanly into 'technical' or 'soft' categories with accurate proficiency levels.
4. Extract key technologies as concise tag lists for projects.
5. Do NOT invent fake companies or false credentials.
6. Ensure no HTML or script tags are included in text output.
"""

OUTPUT_FORMAT_PROMPT = """
Return ONLY a valid JSON object matching this exact schema:
{
  "hero": {"name": "Full Name", "headline": "Title", "bio": "Bio"},
  "about": {"summary": "Summary", "highlights": ["Highlight 1", "Highlight 2"]},
  "skills": [{"name": "Skill", "category": "technical", "level": "Expert"}],
  "projects": [{"title": "Title", "description": "Details", "technologies": ["Tech"], "url": "URL"}],
  "experience": [{"company": "Company", "position": "Role", "duration": "Dates", "description": "Details"}],
  "education": [{"institution": "School", "degree": "Degree", "year": "Year"}],
  "contact": {"email": "email@example.com", "github": "GitHub", "linkedin": "LinkedIn"}
}

Important: Do NOT wrap output in markdown codeblocks. Output valid JSON only.
"""

SECTION_SCHEMAS = {
    "hero": '{"hero": {"name": "Full Name", "headline": "Professional Title / Tagline", "bio": "Elevator pitch"}}',
    "about": '{"about": {"summary": "Full biography", "highlights": ["Highlight 1", "Highlight 2"]}}',
    "skills": '{"skills": [{"name": "Skill Name", "category": "technical or soft", "level": "Expert"}]}',
    "projects": '{"projects": [{"title": "Title", "description": "Details", "technologies": ["Tech1"], "url": "https://..."}]}',
    "experience": '{"experience": [{"company": "Company", "position": "Role", "duration": "Dates", "description": "Bullets"}]}',
    "education": '{"education": [{"institution": "School", "degree": "Degree", "year": "Year"}]}',
    "contact": '{"contact": {"email": "email@example.com", "github": "https://...", "linkedin": "https://..."}}',
}


def build_portfolio_prompt(profile_data: dict) -> Tuple[str, str]:
    """
    Assembles modular prompt context from input profile data using PromptLibrary.
    Returns tuple: (system_prompt, formatted_user_prompt)
    """
    compiled = PromptLibrary.build_prompt("portfolio_generation", {"profile_json": profile_data})
    return compiled["system_prompt"], compiled["user_prompt"]


def build_section_regeneration_prompt(
    portfolio_context: dict,
    section_name: str,
    current_section_data: Any,
    user_prompt: str = ""
) -> Tuple[str, str]:
    """
    Builds AI prompt to regenerate ONLY a single section using PromptLibrary.
    Returns tuple: (system_prompt, formatted_user_prompt)
    """
    sec = section_name.lower()
    prompt_key = f"{sec}_regeneration"

    context_str = f"Skills: {', '.join(portfolio_context.get('skills', []))}, Projects: {', '.join(portfolio_context.get('projects', []))}"
    instruction_str = user_prompt if user_prompt else f"Enhance and rewrite the '{sec}' section to sound highly professional, modern, and engaging."

    compiled = PromptLibrary.build_prompt(
        prompt_key,
        variables={
            "portfolio_title": portfolio_context.get("title", portfolio_context.get("name", "")),
            "portfolio_context": context_str,
            "current_section": current_section_data,
            "user_instruction": instruction_str
        }
    )
    return compiled["system_prompt"], compiled["user_prompt"]
