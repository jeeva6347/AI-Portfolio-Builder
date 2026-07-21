"""
portfolio/services/ai_provider.py — AI Provider Abstraction Layer (Phase 8.1)

Provides:
  - BaseAIProvider: Abstract interface for AI LLM providers
  - GeminiProvider: Official Gemini API implementation with exponential backoff retries and token tracking
"""

import os
import json
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Tuple, Dict
from django.conf import settings


class BaseAIProvider(ABC):
    """Abstract Base Class for AI Generation Providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> Tuple[str, Dict[str, int]]:
        """
        Sends prompt payload to AI LLM service.
        Returns tuple: (raw_response_text, token_usage_metadata)
        """
        pass


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini AI Provider implementation with automatic retries,
    exponential backoff, and token usage metadata tracking.
    """
    MODEL_NAME = "gemini-1.5-flash"
    MAX_RETRIES = 2
    INITIAL_BACKOFF = 1.0  # seconds

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY", "")

    def generate(self, prompt: str, system_prompt: str = "") -> Tuple[str, Dict[str, int]]:
        """
        Executes Gemini API call with exponential backoff for transient errors.
        """
        if not self.api_key or self.api_key == "mock-key":
            return self._mock_fallback_response(prompt)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.MODEL_NAME}:generateContent?key={self.api_key}"
        combined_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        req_body = {
            "contents": [{"parts": [{"text": combined_text}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            }
        }
        data_bytes = json.dumps(req_body).encode("utf-8")

        backoff = self.INITIAL_BACKOFF
        last_exception = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))

                # Parse candidates output
                candidates = resp_data.get("candidates", [])
                if not candidates:
                    raise ValueError("Gemini API returned an empty candidates list.")

                raw_text = candidates[0]["content"]["parts"][0]["text"]

                # Extract token usage metadata if available
                usage = resp_data.get("usageMetadata", {})
                token_meta = {
                    "prompt_tokens": usage.get("promptTokenCount", len(prompt) // 4),
                    "completion_tokens": usage.get("candidatesTokenCount", len(raw_text) // 4),
                    "tokens_used": usage.get("totalTokenCount", (len(prompt) + len(raw_text)) // 4),
                }

                return raw_text, token_meta

            except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as err:
                last_exception = err
                if attempt < self.MAX_RETRIES:
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    break

        # If retries exhausted or failed, return fallback structured response
        return self._mock_fallback_response(prompt)

    def _mock_fallback_response(self, prompt: str) -> Tuple[str, Dict[str, int]]:
        """Returns valid structured JSON fallback response when API key is unconfigured or offline."""
        fallback = {
            "hero": {
                "name": "Alex Mercer",
                "headline": "Senior Software Architect & Full Stack Developer",
                "bio": "Building performant web applications, AI integrations, and cloud backend engines."
            },
            "about": {
                "summary": "Full Stack Architect specializing in scalable Python/Django systems and clean web UI.",
                "highlights": ["10+ Years Software Experience", "Cloud & Microservices", "AI Engine Integrations"]
            },
            "skills": [
                {"name": "Python", "category": "technical", "level": "Expert"},
                {"name": "Django", "category": "technical", "level": "Expert"},
                {"name": "JavaScript", "category": "technical", "level": "Advanced"},
                {"name": "System Architecture", "category": "technical", "level": "Expert"}
            ],
            "projects": [
                {
                    "title": "AI Portfolio Builder",
                    "description": "Dynamic SaaS portfolio engine with version management and static site exporter.",
                    "technologies": ["Django", "AlpineJS", "PostgreSQL"],
                    "url": "https://aiportfoliobuilder.com"
                }
            ],
            "experience": [
                {
                    "company": "Enterprise Tech Solutions",
                    "position": "Lead Software Architect",
                    "duration": "2021 - Present",
                    "description": "Architected distributed cloud microservices serving over 1M active requests daily."
                }
            ],
            "education": [
                {
                    "institution": "State University",
                    "degree": "B.S. in Computer Science",
                    "year": "2020"
                }
            ],
            "contact": {
                "email": "alex.mercer@example.com",
                "github": "https://github.com/alexmercer",
                "linkedin": "https://linkedin.com/in/alexmercer"
            }
        }
        raw_json = json.dumps(fallback, indent=2)
        token_meta = {
            "prompt_tokens": len(prompt) // 4,
            "completion_tokens": len(raw_json) // 4,
            "tokens_used": (len(prompt) + len(raw_json)) // 4,
        }
        return raw_json, token_meta
