from django.db import migrations


def create_default_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("payments", "SubscriptionPlan")
    
    # 1. Free Plan
    SubscriptionPlan.objects.get_or_create(
        slug="free",
        defaults={
            "name": "Free Plan",
            "price": 0.00,
            "portfolio_limit": 1,
            "premium_themes_enabled": False,
            "ai_usage_limit": 3,
            "github_publish_limit": 3,
            "custom_branding_removal": False,
            "team_access": False,
        }
    )
    
    # 2. Premium Plan
    SubscriptionPlan.objects.get_or_create(
        slug="premium",
        defaults={
            "name": "Premium Plan",
            "price": 19.00,
            "portfolio_limit": 9999,
            "premium_themes_enabled": True,
            "ai_usage_limit": 50,
            "github_publish_limit": 9999,
            "custom_branding_removal": True,
            "team_access": False,
        }
    )
    
    # 3. Enterprise Plan
    SubscriptionPlan.objects.get_or_create(
        slug="enterprise",
        defaults={
            "name": "Enterprise Plan",
            "price": 99.00,
            "portfolio_limit": 9999,
            "premium_themes_enabled": True,
            "ai_usage_limit": 9999,
            "github_publish_limit": 9999,
            "custom_branding_removal": True,
            "team_access": True,
        }
    )


def remove_default_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("payments", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(slug__in=["free", "premium", "enterprise"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_plans, remove_default_plans),
    ]
