"""
payments/management/commands/unlock_all_free.py

Sets all payments.SubscriptionPlan limits to unlimited on every plan,
and updates the subscriptions Free plan feature accesses to all-enabled/unlimited.
Safe to run multiple times (idempotent).
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Unlocks all features for all users by setting unlimited limits on every plan."

    def handle(self, *args, **options):
        # 1. Fix payments.SubscriptionPlan limits for Free plan
        try:
            from payments.models import SubscriptionPlan as Paymentsplan
            updated = Paymentsplan.objects.update(
                portfolio_limit=9999,
                ai_usage_limit=9999,
                github_publish_limit=9999,
                premium_themes_enabled=True,
                custom_branding_removal=True,
                team_access=True,
            )
            self.stdout.write(self.style.SUCCESS(
                f"Updated {updated} payments.SubscriptionPlan record(s) to unlimited limits."
            ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"payments.SubscriptionPlan update skipped: {e}"))

        # 2. Re-seed subscriptions plan features with all enabled + unlimited
        try:
            call_command("seed_subscription_data", verbosity=1)
            self.stdout.write(self.style.SUCCESS("Subscription feature accesses re-seeded: all features unlimited."))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"seed_subscription_data skipped: {e}"))

        # 3. Fix any existing PlanFeatureAccess records: enable all + remove limits
        try:
            from subscriptions.models import PlanFeatureAccess
            count = PlanFeatureAccess.objects.update(enabled=True, usage_limit=None)
            self.stdout.write(self.style.SUCCESS(
                f"Updated {count} PlanFeatureAccess record(s) to enabled=True, usage_limit=Unlimited."
            ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"PlanFeatureAccess update skipped: {e}"))

        self.stdout.write(self.style.SUCCESS("\n[DONE] All features are now FREE and UNLIMITED for every user!"))
