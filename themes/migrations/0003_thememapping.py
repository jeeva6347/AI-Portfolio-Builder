"""
Migration: Add ThemeMapping and ThemeMappingField — Module 6.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("themes", "0002_seed_categories"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── ThemeMapping ───────────────────────────────────────────────────────
        migrations.CreateModel(
            name="ThemeMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(help_text="Human-readable name, e.g. 'v1 Default' or 'Dark Variant'.", max_length=100)),
                ("version", models.PositiveSmallIntegerField(default=1)),
                ("is_active", models.BooleanField(default=False, help_text="Only one mapping per theme should be active at a time.")),
                ("notes", models.TextField(blank=True, help_text="Optional admin notes about this mapping.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("theme", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="mappings",
                    to="themes.theme",
                )),
                ("created_by", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_mappings",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Theme Mapping",
                "verbose_name_plural": "Theme Mappings",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="thememapping",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=["theme"],
                name="unique_active_mapping_per_theme",
            ),
        ),

        # ── ThemeMappingField ──────────────────────────────────────────────────
        migrations.CreateModel(
            name="ThemeMappingField",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("field_key", models.CharField(max_length=100)),
                ("selector", models.CharField(max_length=500)),
                ("attribute", models.CharField(
                    choices=[
                        ("text", "Inner Text"),
                        ("html", "Inner HTML"),
                        ("src", "src attribute (img)"),
                        ("href", "href attribute (link)"),
                        ("alt", "alt attribute (img)"),
                        ("placeholder", "Placeholder text"),
                        ("custom", "Custom attribute"),
                    ],
                    default="text",
                    max_length=20,
                )),
                ("custom_attribute", models.CharField(blank=True, max_length=100)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("is_required", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True)),
                ("mapping", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="fields",
                    to="themes.thememapping",
                )),
            ],
            options={
                "verbose_name": "Mapping Field",
                "verbose_name_plural": "Mapping Fields",
                "ordering": ["order", "field_key"],
            },
        ),
    ]
