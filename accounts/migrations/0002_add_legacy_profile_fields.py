# Repair production databases where 0001_initial was recorded before these
# profile fields were added to that migration file.

from django.db import migrations


def add_missing_profile_columns(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    table_name = User._meta.db_table
    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(), table_name
        )
    }

    for field_name in (
        "bio",
        "company",
        "location",
        "website",
        "phone_number",
        "timezone",
    ):
        field = User._meta.get_field(field_name)
        if field.column not in existing_columns:
            schema_editor.add_field(User, field)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(add_missing_profile_columns)],
            state_operations=[],
        ),
    ]
