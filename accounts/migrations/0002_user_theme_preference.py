"""
Migration: Add theme_preference field to accounts.User.

This is an ADDITIVE migration — it does not touch 0001_initial.py.
Safe to apply to both fresh databases (after 0001) and existing
databases that already have the users table.

Default is 'system' so existing users get system-preferred theming
automatically without any data loss.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='theme_preference',
            field=models.CharField(
                choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'System')],
                default='system',
                max_length=10,
                help_text='User preferred theme. Stored in DB for future cross-device sync.',
            ),
        ),
    ]
