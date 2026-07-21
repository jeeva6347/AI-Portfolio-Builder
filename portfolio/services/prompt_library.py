"""
portfolio/services/prompt_library.py — Centralized AI Prompt Library & Prompt Management (Phase 8.4)

Provides:
  - PromptTemplate: Immutable dataclass container (@dataclass(frozen=True)) for prompt definitions
  - PromptLibrary: Singleton/class-based repository for registering, versioning, compiling, and caching prompt templates

Features:
  - Registration-time template validation (rejects empty prompts, invalid schemas, duplicate versions)
  - Nested version registry (cls._registry[prompt_key][version])
  - Automatic {{placeholder}} extraction & verification
  - Variable-hashed template caching
  - Rich prompt metadata packaging
"""

import re
import json
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from django.core.cache import cache

PROMPT_VERSION = "1.0"


@dataclass(frozen=True)
class PromptTemplate:
    """Immutable data container for AI prompt template definitions."""
    key: str
    category: str
    version: str
    description: str
    system_prompt: str
    user_template: str
    required_variables: List[str]
    schema: dict
    created_at: str = "2026-07-21"


class PromptLibrary:
    """Centralized registry and compiler for versioned AI prompt templates."""

    _registry: Dict[str, Dict[str, PromptTemplate]] = {}

    @classmethod
    def register(cls, template: PromptTemplate):
        """
        Registers a prompt template into the nested registry.
        Executes registration-time validation checks:
          - Non-empty system and user prompt templates
          - Valid non-empty schema dictionary
          - Duplicate key + version check
          - Placeholder syntax validation
        """
        if not isinstance(template, PromptTemplate):
            raise TypeError("template must be an instance of PromptTemplate.")

        if not template.key or not isinstance(template.key, str):
            raise ValueError("PromptTemplate must have a non-empty string 'key'.")

        if not template.version or not isinstance(template.version, str):
            raise ValueError(f"PromptTemplate '{template.key}' must have a non-empty string 'version'.")

        if not template.system_prompt or not template.system_prompt.strip():
            raise ValueError(f"PromptTemplate '{template.key}' system_prompt cannot be empty.")

        if not template.user_template or not template.user_template.strip():
            raise ValueError(f"PromptTemplate '{template.key}' user_template cannot be empty.")

        if not isinstance(template.schema, dict) or not template.schema:
            raise ValueError(f"PromptTemplate '{template.key}' must have a valid non-empty schema dict.")

        # Check duplicate version
        if template.key in cls._registry and template.version in cls._registry[template.key]:
            raise ValueError(f"PromptTemplate '{template.key}' version '{template.version}' is already registered.")

        # Extract {{placeholders}} using regex and verify against required_variables
        placeholders_in_user = set(re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", template.user_template))
        placeholders_in_sys = set(re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", template.system_prompt))
        all_detected = placeholders_in_user.union(placeholders_in_sys)

        missing_declared = all_detected.difference(set(template.required_variables))
        if missing_declared:
            raise ValueError(
                f"PromptTemplate '{template.key}' uses placeholder(s) {list(missing_declared)} "
                f"which are missing from required_variables."
            )

        if template.key not in cls._registry:
            cls._registry[template.key] = {}
        cls._registry[template.key][template.version] = template

    @classmethod
    def get_template(cls, key: str, version: Optional[str] = None) -> PromptTemplate:
        """Retrieves prompt template by key and version (defaults to latest/highest version)."""
        if key not in cls._registry or not cls._registry[key]:
            raise KeyError(f"Prompt template key '{key}' is not registered.")

        versions = cls._registry[key]
        if version:
            if version not in versions:
                raise KeyError(f"Prompt template '{key}' version '{version}' not found.")
            return versions[version]

        latest_version = sorted(versions.keys())[-1]
        return versions[latest_version]

    @classmethod
    def build_prompt(cls, prompt_key: str, variables: Dict[str, Any], version: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates required variables, substitutes {{placeholders}} safely, rejects unresolved placeholders,
        caches compiled template using variable-hashing, and returns rich metadata payload.
        """
        template = cls.get_template(prompt_key, version=version)

        # 1. Validate required variables
        missing_vars = [v for v in template.required_variables if v not in variables]
        if missing_vars:
            raise ValueError(f"Missing required variable(s) for prompt '{prompt_key}': {', '.join(missing_vars)}")

        # 2. Check compiled cache
        var_hash = hashlib.sha256(json.dumps(variables, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        cache_key = f"compiled_prompt_{prompt_key}_{template.version}_{var_hash}"

        cached_prompt = cache.get(cache_key)
        if cached_prompt:
            return cached_prompt

        # 3. Perform Variable Injection
        rendered_user_prompt = template.user_template
        rendered_system_prompt = template.system_prompt

        for var_name, var_value in variables.items():
            if isinstance(var_value, (dict, list)):
                str_val = json.dumps(var_value, indent=2, default=str)
            else:
                str_val = str(var_value) if var_value is not None else ""

            placeholder = f"{{{{{var_name}}}}}"
            rendered_user_prompt = rendered_user_prompt.replace(placeholder, str_val)
            rendered_system_prompt = rendered_system_prompt.replace(placeholder, str_val)

        # 4. Reject Unresolved {{placeholders}}
        unresolved = set(re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", rendered_user_prompt) + re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", rendered_system_prompt))
        if unresolved:
            raise ValueError(f"Unresolved placeholder(s) in prompt '{prompt_key}': {', '.join(unresolved)}")

        result = {
            "key": template.key,
            "category": template.category,
            "version": template.version,
            "description": template.description,
            "created_at": template.created_at,
            "system_prompt": rendered_system_prompt,
            "user_prompt": rendered_user_prompt,
            "schema": template.schema,
        }

        cache.set(cache_key, result, timeout=3600)
        return result

    @classmethod
    def list_registered_prompts(cls) -> List[Dict[str, Any]]:
        """Returns summary list of all registered prompt templates."""
        summary = []
        for key, versions in cls._registry.items():
            for ver, tmpl in versions.items():
                summary.append({
                    "key": tmpl.key,
                    "category": tmpl.category,
                    "version": tmpl.version,
                    "description": tmpl.description,
                    "required_variables": tmpl.required_variables
                })
        return summary


# ----------------------------------------------------------------------
# Initialize & Register Default Prompt Templates
# ----------------------------------------------------------------------

# 1. Full Portfolio Generation Template
PromptLibrary.register(PromptTemplate(
    key="portfolio_generation",
    category="portfolio_generation",
    version="1.0",
    description="Full portfolio generation prompt converting user profile inputs into JSON schema.",
    system_prompt="You are an executive resume writer, senior career coach, and digital portfolio architect.",
    user_template="""
Guidelines:
1. Elevate raw summaries into compelling, action-oriented professional statements.
2. Quantify achievements where possible (e.g., "Increased performance by 40%").
3. Organize skills cleanly into 'technical' or 'soft' categories with accurate proficiency levels.
4. Extract key technologies as concise tag lists for projects.
5. Do NOT invent fake companies or false credentials.
6. Ensure no HTML or script tags are included in text output.

USER PROFILE DATA:
{{profile_json}}

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
""",
    required_variables=["profile_json"],
    schema={
        "type": "object",
        "required": ["hero", "about", "skills", "projects", "experience", "education", "contact"]
    }
))


# Standard schema for single section regenerations
_SECTION_SCHEMAS = {
    "hero": {"hero": {"name": "Full Name", "headline": "Title", "bio": "Bio"}},
    "about": {"about": {"summary": "Biography", "highlights": ["Highlight 1"]}},
    "skills": {"skills": [{"name": "Skill Name", "category": "technical", "level": "Expert"}]},
    "projects": {"projects": [{"title": "Title", "description": "Details", "technologies": ["Tech"], "url": "URL"}]},
    "experience": {"experience": [{"company": "Company", "position": "Role", "duration": "Dates", "description": "Details"}]},
    "education": {"education": [{"institution": "School", "degree": "Degree", "year": "Year"}]},
    "contact": {"contact": {"email": "email", "github": "github", "linkedin": "linkedin"}}
}

# 2-8. Register Section Regeneration Templates
_REGEN_SECTIONS = ["hero", "about", "skills", "projects", "experience", "education", "contact"]

for sec in _REGEN_SECTIONS:
    PromptLibrary.register(PromptTemplate(
        key=f"{sec}_regeneration",
        category=f"{sec}_regeneration",
        version="1.0",
        description=f"Targeted AI rewrite for portfolio {sec} section.",
        system_prompt=f"You are an expert AI portfolio editor. Your task is to regenerate ONLY the '{sec}' section.",
        user_template=f"""
PORTFOLIO CONTEXT:
Name: {{{{portfolio_title}}}}
Existing Context: {{{{portfolio_context}}}}

CURRENT SECTION CONTENT ('{sec}'):
{{{{current_section}}}}

USER INSTRUCTIONS / REGENERATION GOAL:
{{{{user_instruction}}}}

REQUIRED OUTPUT FORMAT:
Return ONLY a valid JSON object wrapped in top-level key '{sec}':
{json.dumps(_SECTION_SCHEMAS[sec], indent=2)}

Do NOT wrap in markdown codeblocks. Return valid JSON only.
""",
        required_variables=["portfolio_title", "portfolio_context", "current_section", "user_instruction"],
        schema=_SECTION_SCHEMAS[sec]
    ))


# 9. Register Portfolio Analysis Assistant Template
PromptLibrary.register(PromptTemplate(
    key="portfolio_analysis",
    category="portfolio_analysis",
    version="1.0",
    description="Analyzes portfolio draft completeness, readability, SEO, and professionalism.",
    system_prompt="You are an expert AI Career Assistant and Digital Portfolio Critic.",
    user_template="""
Analyze the following portfolio draft data and provide actionable feedback, scores, and improvement recommendations.

PORTFOLIO DRAFT DATA:
{{portfolio_data}}

USER INSTRUCTION / FOCUS AREA:
{{user_instruction}}

Return ONLY a valid JSON object matching this schema:
{
  "scores": {
    "overall": {"score": 90, "factors": ["Factor 1"]},
    "completeness": {"score": 85, "factors": ["Factor 1"]},
    "professionalism": {"score": 92, "factors": ["Factor 1"]},
    "seo": {"score": 80, "factors": ["Factor 1"]},
    "readability": {"score": 95, "factors": ["Factor 1"]}
  },
  "suggestions": [
    {
      "id": "ai_hero_impact",
      "category": "hero",
      "intent": "Professionalism",
      "priority": "critical",
      "severity": "high",
      "source": "ai",
      "confidence": 0.88,
      "title": "Action-oriented headline",
      "description": "Short headline description.",
      "recommendation": "Recommendation statement.",
      "reason": "Explainability reason why this helps.",
      "section": "hero",
      "actionable": true
    }
  ]
}

Important: Do NOT wrap output in markdown codeblocks. Return valid JSON only.
""",
    required_variables=["portfolio_data", "user_instruction"],
    schema={
        "type": "object",
        "required": ["scores", "suggestions"]
    }
))


# 10. Register Job Description Optimization Template
PromptLibrary.register(PromptTemplate(
    key="job_optimization",
    category="job_optimization",
    version="1.0",
    description="Optimizes portfolio draft content to match specific job description requirements and ATS keywords.",
    system_prompt="You are an expert AI Career Coach and ATS Portfolio Optimizer.",
    user_template="""
Analyze the target job description requirements and optimize the portfolio draft sections to maximize ATS keyword alignment and recruiter impact.

TARGET JOB REQUIREMENTS:
{{job_requirements}}

CURRENT PORTFOLIO DRAFT CONTENT:
{{portfolio_data}}

USER INSTRUCTION:
{{user_instruction}}

Return ONLY a valid JSON object matching this schema:
{
  "optimizations": {
    "hero": {
      "section_name": "hero",
      "current_data": {"name": "Name", "headline": "Title", "bio": "Bio"},
      "optimized_data": {"name": "Name", "headline": "Optimized Title", "bio": "Optimized Bio"},
      "reason": "Incorporates target job keywords.",
      "category": "ATS",
      "confidence": 0.94,
      "risk": "low",
      "affected_keywords": ["keyword1", "keyword2"],
      "estimated_impact": {"ats_score": "+6", "keyword_match": "+8"}
    },
    "about": {
      "section_name": "about",
      "current_data": {"summary": "Summary"},
      "optimized_data": {"summary": "Optimized Summary"},
      "reason": "Enhances domain positioning.",
      "category": "Keyword Alignment",
      "confidence": 0.92,
      "risk": "low",
      "affected_keywords": ["keyword1"],
      "estimated_impact": {"ats_score": "+5", "keyword_match": "+5"}
    },
    "skills": {
      "section_name": "skills",
      "current_data": [{"name": "Skill1"}],
      "optimized_data": [{"name": "Skill1"}, {"name": "Skill2"}],
      "reason": "Includes missing core job skills.",
      "category": "Technical Accuracy",
      "confidence": 0.95,
      "risk": "low",
      "affected_keywords": ["skill2"],
      "estimated_impact": {"ats_score": "+10", "keyword_match": "+12"}
    }
  }
}

Important: Do NOT wrap output in markdown codeblocks. Return valid JSON only.
""",
    required_variables=["job_requirements", "portfolio_data", "user_instruction"],
    schema={
        "type": "object",
        "required": ["optimizations"]
    }
))


# 11. Register AI Cover Letter Generation Template
PromptLibrary.register(PromptTemplate(
    key="cover_letter_generation",
    category="cover_letter",
    version="1.0",
    description="Generates a tailored, persuasive cover letter aligning portfolio evidence and resume data with job description requirements.",
    system_prompt="You are an elite Executive Career Strategist and Professional Copywriter.",
    user_template="""
Generate a highly persuasive, tailored cover letter by synthesizing the applicant's Portfolio evidence and Resume data to match the target Job Description requirements.

TONE PREFERENCE: {{tone}}
LENGTH PREFERENCE: {{length}}
TEMPLATE VARIANT: {{template_variant}}

TARGET JOB REQUIREMENTS:
{{job_requirements}}

APPLICANT PORTFOLIO EVIDENCE:
{{portfolio_data}}

APPLICANT RESUME DATA:
{{resume_data}}

USER SPECIAL INSTRUCTION:
{{user_instruction}}

Return ONLY a valid JSON object matching this schema:
{
  "title": "Cover Letter - [Job Title]",
  "greeting": "Dear Hiring Manager,",
  "introduction": "Introductory paragraph engaging the reader and stating the target role.",
  "body": "Main body paragraphs demonstrating core competencies and domain achievements.",
  "closing": "Closing paragraph reiterating value proposition and call to action.",
  "signature": "Sincerely,\n[Applicant Name]",
  "evidence_map": [
    "Project: AI Portfolio Builder Engine",
    "Experience: Lead Architect at Cloud Solutions"
  ],
  "coverage": {
    "covered": ["Python", "Django", "System Architecture"],
    "not_covered": ["Docker"]
  }
}

Important: Do NOT wrap output in markdown codeblocks. Return valid JSON only.
""",
    required_variables=["portfolio_data", "resume_data", "job_requirements", "tone", "length", "template_variant", "user_instruction"],
    schema={
        "type": "object",
        "required": ["greeting", "introduction", "body", "closing", "signature"]
    }
))


# 12. Register ATS Resume Optimization Template
PromptLibrary.register(PromptTemplate(
    key="resume_optimization",
    category="resume_optimization",
    version="1.0",
    description="Optimizes resume professional summary, skills, projects, and experience to match target job requirements while leaving contact and education intact.",
    system_prompt="You are an expert ATS Resume Optimization Architect.",
    user_template="""
Optimize the applicant's resume to maximize ATS match score and keyword alignment for the target job description.

STRICT INSTRUCTION:
Optimize ONLY the following 4 sections:
1. Professional Summary
2. Skills
3. Projects
4. Experience

DO NOT modify Name, Email, Phone, or Education.

TARGET JOB REQUIREMENTS:
{{job_requirements}}

CURRENT RESUME DATA:
{{resume_data}}

USER INSTRUCTION:
{{user_instruction}}

Return ONLY a valid JSON object matching this schema:
{
  "summary": "Optimized professional summary incorporating target job keywords.",
  "skills": [
    {"name": "Python", "category": "technical", "level": "Expert"}
  ],
  "projects": [
    {
      "title": "Optimized Project Title",
      "description": "Optimized project description with target action verbs and metrics.",
      "technologies": ["Python", "Django"]
    }
  ],
  "experience": [
    {
      "company": "Company Name",
      "position": "Optimized Role Title",
      "duration": "2021 - Present",
      "description": "Optimized bullet points emphasizing achievements and ATS keywords."
    }
  ]
}

Important: Do NOT wrap output in markdown codeblocks. Return valid JSON only.
""",
    required_variables=["resume_data", "job_requirements", "user_instruction"],
    schema={
        "type": "object",
        "required": ["summary", "skills", "projects", "experience"]
    }
))
