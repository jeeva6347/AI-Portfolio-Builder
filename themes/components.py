"""
themes/components.py — Component Registry Engine (Phase 5)

Centralized registry for portfolio components, managing component schemas,
default dataset configurations, category classifications, and editable fields.
"""

from typing import Dict, List, Optional


class ComponentDefinition:
    """Represents a registered portfolio component definition."""
    def __init__(
        self,
        component_id: str,
        name: str,
        category: str,
        icon: str,
        template: str,
        description: str = "",
        editable_fields: Optional[List[str]] = None,
        default_data: Optional[Dict] = None,
        supports_animation: bool = True,
        responsive_support: bool = True
    ):
        self.component_id = component_id
        self.name = name
        self.category = category
        self.icon = icon
        self.template = template
        self.description = description
        self.editable_fields = editable_fields or []
        self.default_data = default_data or {}
        self.supports_animation = supports_animation
        self.responsive_support = responsive_support

    def to_dict(self) -> Dict:
        return {
            "id": self.component_id,
            "name": self.name,
            "category": self.category,
            "icon": self.icon,
            "template": self.template,
            "description": self.description,
            "editable_fields": self.editable_fields,
            "default_data": self.default_data,
            "supports_animation": self.supports_animation,
            "responsive_support": self.responsive_support
        }


class ThemeComponentRegistry:
    """Registry class managing all available portfolio component presets."""

    def __init__(self):
        self._components: Dict[str, ComponentDefinition] = {}
        self._register_default_components()

    def register(self, definition: ComponentDefinition):
        self._components[definition.component_id] = definition

    def get(self, component_id: str) -> Optional[ComponentDefinition]:
        return self._components.get(component_id)

    def get_all(self) -> List[ComponentDefinition]:
        return list(self._components.values())

    def filter_by_category(self, category: str) -> List[ComponentDefinition]:
        if category.lower() == "all":
            return self.get_all()
        return [c for c in self._components.values() if c.category.lower() == category.lower()]

    def _register_default_components(self):
        defaults = [
            ComponentDefinition(
                component_id="hero",
                name="Hero Header",
                category="Layout",
                icon="bi-person-badge-fill",
                template="themes/components/hero.html",
                description="Introductory hero banner with name, title, tagline, and CTA buttons.",
                editable_fields=["name", "title", "tagline", "photo", "resume"]
            ),
            ComponentDefinition(
                component_id="about",
                name="About Biography",
                category="Content",
                icon="bi-card-text",
                template="themes/components/about.html",
                description="Rich text biography card with profile photo and key highlights.",
                editable_fields=["about", "address", "email", "phone"]
            ),
            ComponentDefinition(
                component_id="projects",
                name="Projects Grid",
                category="Portfolio",
                icon="bi-folder-fill",
                template="themes/components/projects.html",
                description="Showcase portfolio project cards with repo links and live demo buttons.",
                editable_fields=["title", "description", "technologies", "github_url", "live_url"]
            ),
            ComponentDefinition(
                component_id="experience",
                name="Work Experience",
                category="Content",
                icon="bi-briefcase-fill",
                template="themes/components/experience.html",
                description="Chronological work experience history with position and company details.",
                editable_fields=["company", "position", "duration", "description"]
            ),
            ComponentDefinition(
                component_id="education",
                name="Education & Degrees",
                category="Content",
                icon="bi-mortarboard-fill",
                template="themes/components/education.html",
                description="Academic history displaying degrees, colleges, and graduation years.",
                editable_fields=["degree", "college", "university", "year"]
            ),
            ComponentDefinition(
                component_id="skills",
                name="Skills & Stack",
                category="Portfolio",
                icon="bi-tools",
                template="themes/components/skills.html",
                description="Technical skills and programming language badges grid.",
                editable_fields=["name", "skill_type", "level"]
            ),
            ComponentDefinition(
                component_id="services",
                name="Services & Offerings",
                category="Marketing",
                icon="bi-gear-fill",
                template="themes/components/services.html",
                description="Professional service cards with icons and descriptions.",
                editable_fields=["title", "description", "icon"]
            ),
            ComponentDefinition(
                component_id="timeline",
                name="Career Timeline",
                category="Content",
                icon="bi-hourglass-split",
                template="themes/components/timeline.html",
                description="Vertical timeline graph combining education and career milestones.",
                editable_fields=["company", "duration", "description"]
            ),
            ComponentDefinition(
                component_id="testimonials",
                name="Testimonials & Reviews",
                category="Marketing",
                icon="bi-star-fill",
                template="themes/components/testimonials.html",
                description="Client and manager recommendation quotes and review badges.",
                editable_fields=["reviewer_name", "reviewer_role", "text"]
            ),
            ComponentDefinition(
                component_id="gallery",
                name="Media Gallery",
                category="Media",
                icon="bi-images",
                template="themes/components/gallery.html",
                description="Grid layout showcasing design shots, certificates, or screenshots.",
                editable_fields=["image", "title"]
            ),
            ComponentDefinition(
                component_id="statistics",
                name="Impact Stats",
                category="Marketing",
                icon="bi-graph-up-arrow",
                template="themes/components/statistics.html",
                description="Metric counter boxes highlighting years of experience and completed projects.",
                editable_fields=["title", "value"]
            ),
            ComponentDefinition(
                component_id="blog",
                name="Blog / Articles",
                category="Content",
                icon="bi-journal-richtext",
                template="themes/components/blog.html",
                description="List or grid of technical articles and published posts.",
                editable_fields=["title", "url", "date"]
            ),
            ComponentDefinition(
                component_id="pricing",
                name="Pricing Plans",
                category="Marketing",
                icon="bi-credit-card-fill",
                template="themes/components/pricing.html",
                description="Freelance rate plans and consulting package tiers.",
                editable_fields=["title", "price", "features"]
            ),
            ComponentDefinition(
                component_id="faq",
                name="FAQ Accordion",
                category="Content",
                icon="bi-question-circle-fill",
                template="themes/components/faq.html",
                description="Frequently asked questions accordion for clients.",
                editable_fields=["question", "answer"]
            ),
            ComponentDefinition(
                component_id="contact",
                name="Contact Form",
                category="Contact",
                icon="bi-envelope-fill",
                template="themes/components/contact.html",
                description="Direct email, phone, location details, and active contact form.",
                editable_fields=["contact_email", "contact_phone", "contact_address", "contact_form_action"]
            ),
            ComponentDefinition(
                component_id="map",
                name="Location Map",
                category="Contact",
                icon="bi-geo-alt-fill",
                template="themes/components/map.html",
                description="Embedded map view displaying general location.",
                editable_fields=["address"]
            ),
            ComponentDefinition(
                component_id="footer",
                name="Footer & Copyright",
                category="Layout",
                icon="bi-layout-south",
                template="themes/components/footer.html",
                description="Page footer containing copyright text, social links, and back-to-top button.",
                editable_fields=["footer_copyright", "footer_tagline"]
            ),
        ]
        for comp in defaults:
            self.register(comp)


# Global registry instance singleton
component_registry = ThemeComponentRegistry()
