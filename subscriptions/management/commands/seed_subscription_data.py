"""
subscriptions/management/commands/seed_subscription_data.py

Management command to automatically seed initial Subscription Plans, Plan Features, and Plan Feature Access rules.
Execution is 100% idempotent and production safe.
"""

from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan, PlanFeature, PlanFeatureAccess


class Command(BaseCommand):
    help = "Seeds default Subscription Plans, Features, and Feature Access rules idempotently."

    DEFAULT_FEATURES = [
        ("AI Portfolio Generation", "ai-portfolio-generation", "Automated AI portfolio creation engine."),
        ("Resume Import", "resume-import", "Import resume PDF/DOCX into portfolio."),
        ("AI Regeneration", "ai-regeneration", "AI section regeneration and smart editing."),
        ("Cover Letter Generator", "cover-letter-generator", "AI-powered cover letter generator."),
        ("ATS Resume Optimizer", "ats-resume-optimizer", "Optimize resume sections for ATS systems."),
        ("Portfolio Export", "portfolio-export", "Export portfolio in PDF, DOCX, HTML, ZIP."),
        ("Backup & Restore", "backup-restore", "JSON portfolio backup export and import."),
        ("Portfolio Templates", "portfolio-templates", "Switch visual theme layout presets."),
        ("Portfolio SEO", "portfolio-seo", "Generate SEO meta tags, Open Graph, robots.txt, sitemap.xml."),
        ("GitHub Deployment", "github-deployment", "One-click deployment to GitHub Pages."),
    ]

    DEFAULT_PLANS = [
        {
            "name": "Free",
            "slug": "free",
            "description": "Basic free tier for starting portfolios.",
            "price": "0.00",
            "billing_cycle": SubscriptionPlan.BillingCycle.MONTHLY,
            "is_active": True,
            "is_featured": False,
            "display_order": 1,
            "features": {
                "ai-portfolio-generation": (True, 1),
                "resume-import": (True, 1),
                "ai-regeneration": (True, 3),
                "cover-letter-generator": (False, 0),
                "ats-resume-optimizer": (False, 0),
                "portfolio-export": (True, 2),
                "backup-restore": (True, 1),
                "portfolio-templates": (True, None),
                "portfolio-seo": (True, None),
                "github-deployment": (False, 0),
            }
        },
        {
            "name": "Starter",
            "slug": "starter",
            "description": "Essential toolkit for active job seekers.",
            "price": "9.99",
            "billing_cycle": SubscriptionPlan.BillingCycle.MONTHLY,
            "is_active": True,
            "is_featured": False,
            "display_order": 2,
            "features": {
                "ai-portfolio-generation": (True, 5),
                "resume-import": (True, 5),
                "ai-regeneration": (True, 20),
                "cover-letter-generator": (True, 5),
                "ats-resume-optimizer": (True, 5),
                "portfolio-export": (True, 10),
                "backup-restore": (True, 5),
                "portfolio-templates": (True, None),
                "portfolio-seo": (True, None),
                "github-deployment": (True, 1),
            }
        },
        {
            "name": "Professional",
            "slug": "professional",
            "description": "Full-featured professional suite with unlimited generation.",
            "price": "29.99",
            "billing_cycle": SubscriptionPlan.BillingCycle.MONTHLY,
            "is_active": True,
            "is_featured": True,
            "display_order": 3,
            "features": {
                "ai-portfolio-generation": (True, None),
                "resume-import": (True, None),
                "ai-regeneration": (True, None),
                "cover-letter-generator": (True, None),
                "ats-resume-optimizer": (True, None),
                "portfolio-export": (True, None),
                "backup-restore": (True, None),
                "portfolio-templates": (True, None),
                "portfolio-seo": (True, None),
                "github-deployment": (True, None),
            }
        },
        {
            "name": "Enterprise",
            "slug": "enterprise",
            "description": "Enterprise-grade lifetime suite for organization teams.",
            "price": "99.99",
            "billing_cycle": SubscriptionPlan.BillingCycle.YEARLY,
            "is_active": True,
            "is_featured": False,
            "display_order": 4,
            "features": {
                "ai-portfolio-generation": (True, None),
                "resume-import": (True, None),
                "ai-regeneration": (True, None),
                "cover-letter-generator": (True, None),
                "ats-resume-optimizer": (True, None),
                "portfolio-export": (True, None),
                "backup-restore": (True, None),
                "portfolio-templates": (True, None),
                "portfolio-seo": (True, None),
                "github-deployment": (True, None),
            }
        },
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting subscription data seeding..."))

        # 1. Seed PlanFeatures
        feature_map = {}
        for name, slug, desc in self.DEFAULT_FEATURES:
            feat, created = PlanFeature.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "description": desc}
            )
            if not created and feat.name != name:
                feat.name = name
                feat.save(update_fields=["name"])
            feature_map[slug] = feat
            status = "Created" if created else "Exists"
            self.stdout.write(f"  Feature '{name}' ({slug}): {status}")

        # 2. Seed SubscriptionPlans & FeatureAccesses
        for pdata in self.DEFAULT_PLANS:
            plan_features = pdata.pop("features")
            plan, created = SubscriptionPlan.objects.get_or_create(
                slug=pdata["slug"],
                defaults=pdata
            )
            status = "Created" if created else "Exists"
            self.stdout.write(self.style.SUCCESS(f"  Plan '{plan.name}' ({plan.slug}): {status}"))

            for fslug, (enabled, limit) in plan_features.items():
                if fslug in feature_map:
                    PlanFeatureAccess.objects.update_or_create(
                        plan=plan,
                        feature=feature_map[fslug],
                        defaults={"enabled": enabled, "usage_limit": limit}
                    )

        self.stdout.write(self.style.SUCCESS("Successfully seeded subscription plans and features!"))
