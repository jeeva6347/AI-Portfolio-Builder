from django.db import migrations


def backfill_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    SubscriptionPlan = apps.get_model("payments", "SubscriptionPlan")
    UserSubscription = apps.get_model("payments", "UserSubscription")
    UsageMetrics = apps.get_model("payments", "UsageMetrics")
    
    free_plan = SubscriptionPlan.objects.filter(slug="free").first()
    if not free_plan:
        return
        
    for user in User.objects.all():
        # Provision UserSubscription if missing
        if not UserSubscription.objects.filter(user=user).exists():
            UserSubscription.objects.create(
                user=user,
                plan=free_plan,
                status="active"
            )
        # Provision UsageMetrics if missing
        if not UsageMetrics.objects.filter(user=user).exists():
            UsageMetrics.objects.create(user=user)


def rollback_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_populate_plans"),
        ("accounts", "0002_user_theme_preference"),
    ]

    operations = [
        migrations.RunPython(backfill_users, rollback_backfill),
    ]
