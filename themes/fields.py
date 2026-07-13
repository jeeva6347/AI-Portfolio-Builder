"""
themes/fields.py — Module 6: Theme Mapper

Centralized registry of all portfolio data fields that can be
mapped onto a theme's HTML elements.

Structure:
  PORTFOLIO_FIELDS  — ordered list of FieldGroup objects
  FIELD_CHOICES     — flat (key, label) tuples for form selects
  MOCK_DATA         — sample values used in the mapper live-preview
  get_field_label() — look up a human label from a dotted key
"""

from typing import List, Tuple

# ── Field group definition ─────────────────────────────────────────────────────

class PortfolioField:
    """A single mappable portfolio data field."""
    def __init__(self, key: str, label: str, description: str = "", field_type: str = "text"):
        self.key = key                   # e.g. "personal.name"
        self.label = label               # e.g. "Full Name"
        self.description = description   # shown in mapper tooltip
        self.field_type = field_type     # text | image | url | list | richtext


class FieldGroup:
    """A logical grouping of portfolio fields (e.g. Personal, Skills)."""
    def __init__(self, group_key: str, group_label: str, icon: str, fields: List[PortfolioField]):
        self.group_key = group_key
        self.group_label = group_label
        self.icon = icon        # Bootstrap Icons class
        self.fields = fields


# ── Registry ───────────────────────────────────────────────────────────────────

PORTFOLIO_FIELDS: List[FieldGroup] = [

    FieldGroup("personal", "Personal Information", "bi-person-fill", [
        PortfolioField("personal.name",        "Full Name",       "The user's full name"),
        PortfolioField("personal.title",       "Professional Title", "e.g. 'Full-Stack Developer'"),
        PortfolioField("personal.tagline",     "Tagline",         "Short one-liner bio"),
        PortfolioField("personal.about",       "About Me",        "Longer bio paragraph", "richtext"),
        PortfolioField("personal.photo",       "Profile Photo",   "Avatar/profile image URL", "image"),
        PortfolioField("personal.cover",       "Cover Image",     "Hero/banner background image", "image"),
        PortfolioField("personal.email",       "Email Address",   "Primary contact email"),
        PortfolioField("personal.phone",       "Phone Number",    "Contact phone"),
        PortfolioField("personal.address",     "Location / Address", "City, Country"),
        PortfolioField("personal.resume_url",  "Resume URL",      "Link to downloadable resume PDF", "url"),
    ]),

    FieldGroup("skills", "Skills", "bi-tools", [
        PortfolioField("skills.technical",     "Technical Skills",  "List of technical skills",   "list"),
        PortfolioField("skills.soft",          "Soft Skills",       "List of soft skills",        "list"),
        PortfolioField("skills.languages",     "Languages",         "Programming languages",      "list"),
        PortfolioField("skills.frameworks",    "Frameworks",        "Frameworks & libraries",     "list"),
        PortfolioField("skills.tools",         "Tools & DevOps",    "Tools, CI/CD, cloud, etc.",  "list"),
    ]),

    FieldGroup("projects", "Projects", "bi-folder-fill", [
        PortfolioField("projects.list",        "Projects List",   "All projects (dynamic list)", "list"),
        PortfolioField("projects.title",       "Project Title",   "Title of a single project"),
        PortfolioField("projects.description", "Project Description", "Description of a project", "richtext"),
        PortfolioField("projects.tech",        "Technologies Used", "Tech stack for project",    "list"),
        PortfolioField("projects.github_url",  "GitHub URL",      "GitHub repo link",           "url"),
        PortfolioField("projects.live_url",    "Live Demo URL",   "Live deployment URL",        "url"),
        PortfolioField("projects.image",       "Project Image",   "Screenshot of the project",  "image"),
    ]),

    FieldGroup("experience", "Work Experience", "bi-briefcase-fill", [
        PortfolioField("experience.list",      "Experience List", "All jobs (dynamic list)",    "list"),
        PortfolioField("experience.company",   "Company Name",    "Employer name"),
        PortfolioField("experience.position",  "Job Title",       "Role/position held"),
        PortfolioField("experience.duration",  "Duration",        "e.g. 'Jan 2020 – Mar 2022'"),
        PortfolioField("experience.description", "Job Description", "Responsibilities and achievements", "richtext"),
    ]),

    FieldGroup("education", "Education", "bi-mortarboard-fill", [
        PortfolioField("education.list",       "Education List",  "All degrees (dynamic list)", "list"),
        PortfolioField("education.degree",     "Degree",          "Degree name"),
        PortfolioField("education.college",    "College / School","Institution name"),
        PortfolioField("education.university", "University",      "University affiliation"),
        PortfolioField("education.year",       "Graduation Year", "Year of graduation"),
    ]),

    FieldGroup("achievements", "Achievements & Awards", "bi-trophy-fill", [
        PortfolioField("achievements.list",    "Achievements List", "All achievements",         "list"),
        PortfolioField("awards.list",          "Awards List",     "All awards",                "list"),
        PortfolioField("certificates.list",    "Certificates List", "Certifications earned",   "list"),
    ]),

    FieldGroup("services", "Services", "bi-star-fill", [
        PortfolioField("services.list",        "Services List",   "Services offered (dynamic)", "list"),
        PortfolioField("services.title",       "Service Title",   "Name of one service"),
        PortfolioField("services.description", "Service Description", "What the service includes", "richtext"),
    ]),

    FieldGroup("testimonials", "Testimonials", "bi-chat-quote-fill", [
        PortfolioField("testimonials.list",    "Testimonials List", "All testimonials (dynamic)", "list"),
        PortfolioField("testimonials.name",    "Reviewer Name",   "Name of the testimonial author"),
        PortfolioField("testimonials.text",    "Review Text",     "The testimonial body",       "richtext"),
        PortfolioField("testimonials.role",    "Reviewer Role",   "Title/company of reviewer"),
    ]),

    FieldGroup("social", "Social Links", "bi-share-fill", [
        PortfolioField("social.github",        "GitHub URL",       "https://github.com/username",    "url"),
        PortfolioField("social.linkedin",      "LinkedIn URL",     "https://linkedin.com/in/...",    "url"),
        PortfolioField("social.twitter",       "Twitter / X URL",  "https://twitter.com/username",   "url"),
        PortfolioField("social.instagram",     "Instagram URL",    "https://instagram.com/...",      "url"),
        PortfolioField("social.youtube",       "YouTube URL",      "https://youtube.com/...",        "url"),
        PortfolioField("social.facebook",      "Facebook URL",     "https://facebook.com/...",       "url"),
        PortfolioField("social.portfolio",     "Personal Website", "https://yourportfolio.com",      "url"),
    ]),

    FieldGroup("contact", "Contact", "bi-envelope-fill", [
        PortfolioField("contact.email",        "Contact Email",    "Displayed contact email"),
        PortfolioField("contact.phone",        "Contact Phone",    "Displayed phone number"),
        PortfolioField("contact.address",      "Contact Address",  "City, Country"),
        PortfolioField("contact.form_action",  "Form Action URL",  "POST target for contact form", "url"),
    ]),

    FieldGroup("footer", "Footer", "bi-layout-text-window", [
        PortfolioField("footer.copyright",     "Copyright Text",   "e.g. '© 2024 John Doe'"),
        PortfolioField("footer.tagline",       "Footer Tagline",   "Short footer text"),
    ]),
]


# ── Derived helpers ─────────────────────────────────────────────────────────────

def _build_flat_map():
    result = {}
    for group in PORTFOLIO_FIELDS:
        for field in group.fields:
            result[field.key] = field
    return result

_FIELD_MAP = _build_flat_map()


def get_field(key: str) -> PortfolioField | None:
    """Return a PortfolioField by its dotted key, or None if not found."""
    return _FIELD_MAP.get(key)


def get_field_label(key: str) -> str:
    """Return a human label for a field key, or the key itself as fallback."""
    f = _FIELD_MAP.get(key)
    return f.label if f else key


def get_field_choices() -> List[Tuple[str, str]]:
    """Return grouped choices for a Django select widget."""
    choices = []
    for group in PORTFOLIO_FIELDS:
        group_choices = [(f.key, f.label) for f in group.fields]
        choices.append((group.group_label, group_choices))
    return choices


# ── Mock data for live preview ─────────────────────────────────────────────────

MOCK_DATA: dict = {
    "personal.name":        "Alex Johnson",
    "personal.title":       "Full-Stack Developer",
    "personal.tagline":     "Building elegant solutions to complex problems.",
    "personal.about":       "I'm a passionate developer with 5+ years of experience crafting scalable web applications. I love open source and clean code.",
    "personal.photo":       "",   # empty = no replacement
    "personal.cover":       "",
    "personal.email":       "alex@example.com",
    "personal.phone":       "+1 (555) 000-0000",
    "personal.address":     "San Francisco, CA",
    "personal.resume_url":  "#",

    "skills.technical":     "Python, Django, JavaScript, React, PostgreSQL",
    "skills.soft":          "Leadership, Communication, Problem Solving",
    "skills.languages":     "Python, JavaScript, TypeScript, Go",
    "skills.frameworks":    "Django, FastAPI, React, Next.js, Tailwind CSS",
    "skills.tools":         "Docker, GitHub Actions, AWS, Nginx",

    "projects.title":       "AI Portfolio Builder",
    "projects.description": "A SaaS platform that lets developers build and publish stunning portfolios using AI.",
    "projects.tech":        "Django, Python, JavaScript",
    "projects.github_url":  "https://github.com/example",
    "projects.live_url":    "https://example.com",

    "experience.company":   "Acme Corp",
    "experience.position":  "Senior Software Engineer",
    "experience.duration":  "Jan 2021 – Present",
    "experience.description": "Led the backend team in building microservices architecture serving 1M+ users.",

    "education.degree":     "B.Sc. Computer Science",
    "education.college":    "MIT",
    "education.university": "Massachusetts Institute of Technology",
    "education.year":       "2019",

    "social.github":        "https://github.com/alexjohnson",
    "social.linkedin":      "https://linkedin.com/in/alexjohnson",
    "social.twitter":       "https://twitter.com/alexjohnson",
    "social.instagram":     "",
    "social.youtube":       "",
    "social.facebook":      "",
    "social.portfolio":     "https://alexjohnson.dev",

    "contact.email":        "hello@alexjohnson.dev",
    "contact.phone":        "+1 (555) 000-0000",
    "contact.address":      "San Francisco, CA, USA",
    "contact.form_action":  "#",

    "footer.copyright":     "© 2024 Alex Johnson. All rights reserved.",
    "footer.tagline":       "Designed & built with ❤️",

    "services.title":       "Web Development",
    "services.description": "Full-stack web development from design to deployment.",
    "testimonials.name":    "Jane Smith",
    "testimonials.text":    "Alex delivered outstanding work on time. Highly recommended!",
    "testimonials.role":    "CEO, TechStartup",
}
