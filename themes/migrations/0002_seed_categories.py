"""
Seed default ThemeCategories.
Safe to run multiple times — uses get_or_create.
"""
from django.db import migrations

DEFAULT_CATEGORIES = [
    {"name": "Developer",     "icon": "bi-code-slash",           "description": "Themes for software developers and engineers."},
    {"name": "Portfolio",     "icon": "bi-briefcase-fill",       "description": "General purpose portfolio themes."},
    {"name": "Resume",        "icon": "bi-file-earmark-person-fill", "description": "Resume / CV style themes."},
    {"name": "Minimal",       "icon": "bi-square",               "description": "Clean, minimal design themes."},
    {"name": "Corporate",     "icon": "bi-building-fill",        "description": "Professional corporate themes."},
    {"name": "Creative",      "icon": "bi-brush-fill",           "description": "Bold, creative and artistic themes."},
    {"name": "Business",      "icon": "bi-bar-chart-fill",       "description": "Business and consulting themes."},
    {"name": "Landing Page",  "icon": "bi-rocket-takeoff-fill",  "description": "Single-page landing themes."},
    {"name": "Dark",          "icon": "bi-moon-stars-fill",      "description": "Dark mode themes."},
    {"name": "Light",         "icon": "bi-sun-fill",             "description": "Light and bright themes."},
]


def seed_categories(apps, schema_editor):
    ThemeCategory = apps.get_model("themes", "ThemeCategory")
    from django.utils.text import slugify
    for cat in DEFAULT_CATEGORIES:
        ThemeCategory.objects.get_or_create(
            name=cat["name"],
            defaults={
                "slug": slugify(cat["name"]),
                "description": cat["description"],
                "icon": cat["icon"],
            },
        )


def unseed_categories(apps, schema_editor):
    """Reverse: remove only the seeded categories (those that have no themes attached)."""
    ThemeCategory = apps.get_model("themes", "ThemeCategory")
    names = [c["name"] for c in DEFAULT_CATEGORIES]
    ThemeCategory.objects.filter(name__in=names, themes__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("themes", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_code=unseed_categories),
    ]
