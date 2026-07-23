# Generated to repair production databases where 0001_initial was already
# recorded before these fields were added to that migration file.

from django.db import migrations


def add_missing_theme_columns(apps, schema_editor):
    """Repair databases that recorded the older version of 0001_initial."""
    Theme = apps.get_model("themes", "Theme")
    table_name = Theme._meta.db_table
    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(), table_name
        )
    }

    for field_name in (
        "css_variables",
        "custom_css",
        "html_structure",
        "is_featured",
        "rating",
        "review_count",
    ):
        field = Theme._meta.get_field(field_name)
        if field.column not in existing_columns:
            schema_editor.add_field(Theme, field)


class Migration(migrations.Migration):

    dependencies = [
        ("themes", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(add_missing_theme_columns)],
            state_operations=[],
        ),
    ]
