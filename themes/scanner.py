"""
themes/scanner.py — Module 6: Theme Mapper

Two responsibilities:
  1. scan_html_elements(html_content)
     Parses an HTML file and returns a structured list of discoverable
     elements (headings, paragraphs, images, links, sections, etc.)
     with their suggested CSS selectors.

  2. detect_placeholders(html_content)
     Finds any existing {{key}} placeholder tokens in the HTML and maps
     them to known PORTFOLIO_FIELDS keys.

  3. suggest_mappings(elements)
     Heuristically suggests field_key → selector pairs based on element
     tag names, class names, id values, and text patterns.

Uses Python's built-in html.parser — no external dependency required.
"""

import html as html_module
import re
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

from .fields import MOCK_DATA, _FIELD_MAP, get_field_label

# ── Placeholder pattern — matches {{ key }} or {{key}} ─────────────────────────
PLACEHOLDER_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")

# ── Elements worth surfacing to the mapper UI ───────────────────────────────────
SCANNABLE_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "span", "a", "img", "li",
    "section", "div", "header", "footer", "nav",
    "button",
}

# Confidence threshold: a suggestion must score ≥ this to be included
MIN_CONFIDENCE = 0.3


# ── Data class ─────────────────────────────────────────────────────────────────

class ScannedElement:
    """Represents one HTML element surfaced by the scanner."""
    __slots__ = ("tag", "selector", "text_preview", "attrs", "element_index")

    def __init__(self, tag, selector, text_preview="", attrs=None, element_index=0):
        self.tag = tag
        self.selector = selector        # Best CSS selector we can derive
        self.text_preview = text_preview[:80]
        self.attrs = attrs or {}
        self.element_index = element_index

    def to_dict(self):
        return {
            "tag": self.tag,
            "selector": self.selector,
            "text_preview": self.text_preview,
            "attrs": self.attrs,
            "element_index": self.element_index,
        }


class MappingSuggestion:
    """A heuristic suggestion: this selector might map to this field_key."""
    __slots__ = ("field_key", "field_label", "selector", "confidence", "reason")

    def __init__(self, field_key, selector, confidence, reason=""):
        self.field_key = field_key
        self.field_label = get_field_label(field_key)
        self.selector = selector
        self.confidence = round(confidence, 2)
        self.reason = reason

    def to_dict(self):
        return {
            "field_key": self.field_key,
            "field_label": self.field_label,
            "selector": self.selector,
            "confidence": self.confidence,
            "reason": self.reason,
        }


# ── HTML Parser ─────────────────────────────────────────────────────────────────

class _ElementCollector(HTMLParser):
    """
    Single-pass HTML parser that collects tag metadata.
    We don't build a full DOM — just record opening tags with attributes
    and the text that immediately follows them.
    """

    def __init__(self):
        super().__init__()
        self._elements: List[dict] = []
        self._stack: List[dict] = []   # open tags
        self._counter: int = 0

    def handle_starttag(self, tag, attrs):
        if tag not in SCANNABLE_TAGS:
            return
        attr_dict = dict(attrs)
        el = {
            "tag": tag,
            "attrs": attr_dict,
            "text": "",
            "index": self._counter,
        }
        self._counter += 1
        self._stack.append(el)
        self._elements.append(el)

    def handle_endtag(self, tag):
        # Pop the most recent matching tag
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i]["tag"] == tag:
                self._stack.pop(i)
                break

    def handle_data(self, data):
        data = data.strip()
        if data and self._stack:
            # Append text to the innermost open tag
            self._stack[-1]["text"] += data + " "

    @property
    def elements(self):
        return self._elements


# ── CSS selector builder ────────────────────────────────────────────────────────

def _build_selector(tag: str, attrs: dict, index: int) -> str:
    """
    Build the most specific CSS selector we can from tag + attributes.
    Priority: #id > .class > tag:nth-of-type(n)
    """
    el_id = attrs.get("id", "").strip()
    if el_id:
        return f"#{el_id}"

    classes = attrs.get("class", "").split()
    # Take up to 2 classes for specificity without being too fragile
    if classes:
        cls_part = ".".join(classes[:2])
        return f"{tag}.{cls_part}"

    return f"{tag}:nth-of-type({index + 1})"


# ── Heuristic scorer ────────────────────────────────────────────────────────────

# Keyword → (field_key, bonus_score) mapping
_KEYWORD_RULES: List[Tuple[re.Pattern, str, float]] = [
    # Personal
    (re.compile(r"\b(full[- ]?name|hero[- ]?name|your[- ]?name)\b", re.I), "personal.name", 0.9),
    (re.compile(r"\b(name|username)\b", re.I),                              "personal.name", 0.5),
    (re.compile(r"\b(title|subtitle|profession|role|job[- ]?title)\b", re.I), "personal.title", 0.7),
    (re.compile(r"\b(tagline|headline|slogan|motto)\b", re.I),              "personal.tagline", 0.7),
    (re.compile(r"\b(about|bio|description|summary|intro)\b", re.I),        "personal.about", 0.6),
    (re.compile(r"\b(profile[- ]?photo|avatar|photo)\b", re.I),             "personal.photo", 0.7),
    (re.compile(r"\b(cover|hero[- ]?image|banner)\b", re.I),                "personal.cover", 0.7),
    (re.compile(r"\b(email|mail)\b", re.I),                                 "personal.email", 0.8),
    (re.compile(r"\b(phone|mobile|telephone|tel)\b", re.I),                 "personal.phone", 0.8),
    (re.compile(r"\b(address|location|city|country)\b", re.I),              "personal.address", 0.7),
    (re.compile(r"\b(resume|cv|curriculum)\b", re.I),                       "personal.resume_url", 0.8),

    # Skills
    (re.compile(r"\b(technical[- ]?skills?|hard[- ]?skills?)\b", re.I),    "skills.technical", 0.9),
    (re.compile(r"\b(soft[- ]?skills?)\b", re.I),                          "skills.soft", 0.9),
    (re.compile(r"\b(skills?|expertise|proficiency)\b", re.I),             "skills.technical", 0.4),
    (re.compile(r"\b(languages?|programming)\b", re.I),                    "skills.languages", 0.6),
    (re.compile(r"\b(frameworks?|libraries)\b", re.I),                     "skills.frameworks", 0.7),
    (re.compile(r"\b(tools?|devops|cloud)\b", re.I),                       "skills.tools", 0.6),

    # Projects
    (re.compile(r"\b(projects?|work|portfolio[- ]?item)\b", re.I),         "projects.title", 0.5),
    (re.compile(r"\b(project[- ]?title|work[- ]?title)\b", re.I),          "projects.title", 0.9),
    (re.compile(r"\b(project[- ]?desc|project[- ]?detail)\b", re.I),       "projects.description", 0.8),
    (re.compile(r"\b(live|demo|launch|view[- ]?project)\b", re.I),         "projects.live_url", 0.7),
    (re.compile(r"\b(source|code|github|repo)\b", re.I),                   "projects.github_url", 0.7),

    # Experience
    (re.compile(r"\b(experience|career|work[- ]?history)\b", re.I),        "experience.list", 0.5),
    (re.compile(r"\b(company|employer|organization)\b", re.I),             "experience.company", 0.8),
    (re.compile(r"\b(position|job[- ]?title|designation)\b", re.I),        "experience.position", 0.8),
    (re.compile(r"\b(duration|period|from[- ]?to|date)\b", re.I),          "experience.duration", 0.7),

    # Education
    (re.compile(r"\b(education|degree|academic)\b", re.I),                 "education.list", 0.5),
    (re.compile(r"\b(degree|qualification|bachelor|master|phd)\b", re.I),  "education.degree", 0.8),
    (re.compile(r"\b(college|school|institute)\b", re.I),                  "education.college", 0.8),
    (re.compile(r"\b(university)\b", re.I),                                "education.university", 0.9),
    (re.compile(r"\b(graduation|year|batch)\b", re.I),                     "education.year", 0.7),

    # Social
    (re.compile(r"\bgithub\b", re.I),   "social.github",   0.95),
    (re.compile(r"\blinkedin\b", re.I), "social.linkedin",  0.95),
    (re.compile(r"\btwitter\b", re.I),  "social.twitter",   0.95),
    (re.compile(r"\binstagram\b", re.I),"social.instagram",  0.95),
    (re.compile(r"\byoutube\b", re.I),  "social.youtube",   0.95),
    (re.compile(r"\bfacebook\b", re.I), "social.facebook",  0.95),

    # Footer
    (re.compile(r"\b(copyright|©|footer[- ]?text)\b", re.I), "footer.copyright", 0.8),
    (re.compile(r"\bfooter\b", re.I),                         "footer.tagline",   0.4),

    # Contact
    (re.compile(r"\b(contact|get[- ]?in[- ]?touch|reach)\b", re.I), "contact.email", 0.4),

    # Testimonials
    (re.compile(r"\b(testimonial|review|feedback|client)\b", re.I), "testimonials.list", 0.7),

    # Services
    (re.compile(r"\b(services?|what[- ]?i[- ]?do|offer)\b", re.I), "services.list", 0.6),

    # Achievements / Certificates
    (re.compile(r"\b(achievement|accomplishment|milestone)\b", re.I), "achievements.list", 0.7),
    (re.compile(r"\b(certificate|certification|license)\b", re.I),    "certificates.list", 0.8),
    (re.compile(r"\b(award|honour|honor)\b", re.I),                   "awards.list",       0.8),
]


def _score_element(tag: str, attrs: dict, text: str) -> List[Tuple[str, float, str]]:
    """
    Score an element against all keyword rules.
    Returns a list of (field_key, score, reason) sorted by score desc.
    """
    # Combine searchable text sources
    search_text = " ".join([
        attrs.get("id", ""),
        attrs.get("class", ""),
        attrs.get("name", ""),
        attrs.get("placeholder", ""),
        attrs.get("alt", ""),
        attrs.get("title", ""),
        text,
    ])

    scores: Dict[str, Tuple[float, str]] = {}
    for pattern, field_key, base_score in _KEYWORD_RULES:
        if pattern.search(search_text):
            # Boost score if the tag type makes sense for this field
            boost = 0.0
            if field_key.endswith("_url") and tag == "a":
                boost = 0.1
            elif field_key.endswith(".photo") or field_key.endswith(".cover") or field_key.endswith(".image"):
                if tag == "img":
                    boost = 0.15
            elif tag in ("h1", "h2") and "name" in field_key:
                boost = 0.15
            elif tag == "p" and "about" in field_key:
                boost = 0.1

            score = min(base_score + boost, 1.0)
            if field_key not in scores or score > scores[field_key][0]:
                scores[field_key] = (score, pattern.pattern)

    return sorted(
        [(k, v[0], v[1]) for k, v in scores.items()],
        key=lambda x: -x[1],
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def scan_html_elements(html_content: str) -> List[ScannedElement]:
    """
    Parse the HTML and return a flat list of ScannedElement objects
    for all tags in SCANNABLE_TAGS.

    Only elements that have meaningful content (text, id, class, or src)
    are included.
    """
    collector = _ElementCollector()
    try:
        collector.feed(html_content)
    except Exception:
        pass  # best-effort

    elements = []
    tag_counters: Dict[str, int] = {}

    for el in collector.elements:
        tag = el["tag"]
        attrs = el["attrs"]
        text = el["text"].strip()

        # Skip completely empty elements with no useful attributes
        has_attrs = any(attrs.get(k) for k in ("id", "class", "src", "href", "alt", "placeholder"))
        if not text and not has_attrs:
            continue

        n = tag_counters.get(tag, 0)
        tag_counters[tag] = n + 1

        selector = _build_selector(tag, attrs, n)
        elements.append(ScannedElement(
            tag=tag,
            selector=selector,
            text_preview=text[:80],
            attrs={k: v for k, v in attrs.items() if k in ("id", "class", "src", "href", "alt", "placeholder", "name")},
            element_index=el["index"],
        ))

    return elements


def detect_placeholders(html_content: str) -> List[Dict]:
    """
    Find all {{key}} tokens in the HTML.
    Returns list of {key, field_label, count} dicts for recognised keys.
    """
    found: Dict[str, int] = {}
    for match in PLACEHOLDER_RE.finditer(html_content):
        key = match.group(1)
        found[key] = found.get(key, 0) + 1

    result = []
    for key, count in found.items():
        label = get_field_label(key)
        is_known = key in _FIELD_MAP
        result.append({
            "key": key,
            "field_label": label,
            "count": count,
            "is_known": is_known,
        })
    return result


def suggest_mappings(elements: List[ScannedElement]) -> List[MappingSuggestion]:
    """
    Run heuristic scoring across all scanned elements and return
    the best suggestions (one per field_key, highest confidence wins).
    """
    # field_key → best suggestion so far
    best: Dict[str, MappingSuggestion] = {}

    for el in elements:
        scored = _score_element(el.tag, el.attrs, el.text_preview)
        for field_key, score, reason in scored:
            if score < MIN_CONFIDENCE:
                continue
            if field_key not in best or score > best[field_key].confidence:
                best[field_key] = MappingSuggestion(
                    field_key=field_key,
                    selector=el.selector,
                    confidence=score,
                    reason=f"Matched '{reason}' in {el.tag} [{el.selector}]",
                )

    return sorted(best.values(), key=lambda s: -s.confidence)


def apply_placeholder_data(html_content: str, data: dict) -> str:
    """
    Replace all {{key}} tokens in the HTML with values from `data`.
    Values are HTML-escaped to prevent XSS.

    Args:
        html_content: Raw HTML string.
        data: {key: value} mapping (use MOCK_DATA or real user data).
    Returns:
        HTML string with placeholders replaced.
    """
    def replacer(match):
        key = match.group(1)
        value = data.get(key, match.group(0))  # keep original token if key not found
        return html_module.escape(str(value)) if value else match.group(0)

    return PLACEHOLDER_RE.sub(replacer, html_content)
