"""
Initial migration for the themes app — Module 5.
Creates ThemeCategory, Theme, and ThemeAsset tables.
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── ThemeCategory ──────────────────────────────────────────
        migrations.CreateModel(
            name='ThemeCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('icon', models.CharField(default='bi-grid-fill', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Theme Category',
                'verbose_name_plural': 'Theme Categories',
                'ordering': ['name'],
            },
        ),

        # ── Theme ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='Theme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(blank=True, max_length=220, unique=True)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(
                    choices=[('draft', 'Draft'), ('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                    db_index=True,
                    default='draft',
                    max_length=10,
                )),
                ('is_premium', models.BooleanField(default=False)),
                ('price', models.DecimalField(decimal_places=2, default=0.0, help_text='Price in USD. 0 = free.', max_digits=8)),
                ('zip_file', models.FileField(blank=True, null=True, upload_to='themes/zips/')),
                ('extracted_path', models.CharField(blank=True, help_text='Path relative to MEDIA_ROOT where zip was extracted.', max_length=500)),
                ('thumbnail', models.ImageField(blank=True, help_text='Auto-generated or manually uploaded preview image.', null=True, upload_to='themes/thumbnails/')),
                ('tags', models.CharField(blank=True, help_text="Comma-separated tags, e.g. 'dark, minimal, portfolio'.", max_length=500)),
                ('version', models.CharField(default='1.0.0', max_length=20)),
                ('downloads', models.PositiveIntegerField(default=0)),
                ('rejection_reason', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='themes',
                    to='themes.themecategory',
                )),
                ('uploaded_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='uploaded_themes',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Theme',
                'verbose_name_plural': 'Themes',
                'ordering': ['-created_at'],
            },
        ),

        # ── ThemeAsset ─────────────────────────────────────────────
        migrations.CreateModel(
            name='ThemeAsset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset_type', models.CharField(
                    choices=[('html', 'HTML'), ('css', 'CSS'), ('js', 'JavaScript'), ('image', 'Image'), ('font', 'Font'), ('other', 'Other')],
                    default='other',
                    max_length=10,
                )),
                ('file_path', models.CharField(help_text='Path relative to theme extracted_path.', max_length=500)),
                ('file_name', models.CharField(max_length=255)),
                ('file_size', models.PositiveIntegerField(default=0, help_text='Size in bytes.')),
                ('mime_type', models.CharField(blank=True, max_length=100)),
                ('theme', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assets',
                    to='themes.theme',
                )),
            ],
            options={
                'verbose_name': 'Theme Asset',
                'verbose_name_plural': 'Theme Assets',
                'ordering': ['asset_type', 'file_name'],
            },
        ),
    ]
