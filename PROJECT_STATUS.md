# Project Status

**Completion:** Module 7 (Portfolio Builder) — complete. ~22% overall (5 of ~22 modules).

## Completed
- Module 1: Authentication (Custom User model, Email/Social Auth)
- Module 2: Dashboard System (Super Admin, Admin, and User dashboards)
- Module 5: Theme Engine (Upload, Validate, Extract, Marketplace, Preview, Admin)
- Module 6: Theme Mapper (Visual element mapping workspace, HTML scanner & auto-suggest, compiled live iframe preview, duplication, XSS sanitization, tests)
- Module 7: Portfolio Builder (User portfolio database models, CRUD builder tab subviews, theme activation panel, dynamic list compiler list replication, base-href resolution, tests)

## Not Started
- Modules 8-22 (Live Preview, Portfolio Export, Resume Import, AI Content, GitHub integration, Payments, Analytics, etc.)

## Folder Structure
```
aiportfoliobuilder/
├── accounts/            <- Module 1, complete
├── dashboard/            <- Module 2-4, empty scaffold
├── themes/               <- Module 5-8, empty scaffold
├── portfolio/             <- future phase, empty scaffold
├── analytics/             <- future phase, empty scaffold
├── payments/              <- future phase, empty scaffold
├── github_integration/    <- future phase, empty scaffold (named to
│                             avoid colliding with the PyGithub import)
├── ai/                    <- future phase, empty scaffold
├── notifications/         <- empty scaffold
├── api/                   <- empty scaffold
├── core/                  <- empty scaffold
├── templates/base.html
└── aiportfoliobuilder/ (project settings/urls)
```

## Database Schema (so far)
### accounts.User (extends AbstractUser)
| Field | Type | Notes |
|---|---|---|
| role | CharField | SUPER_ADMIN / ADMIN / PREMIUM_USER / FREE_USER, default FREE_USER |
| avatar | ImageField | optional, uploaded at signup or via profile |
| github_username | CharField | optional, reused by GitHub Publish module later |
| email_verified | BooleanField | default False |
| created_at / updated_at | DateTimeField | auto |

`is_premium` is a derived property (`role == PREMIUM_USER`), not a DB
column — avoids the two fields going out of sync.

## Installed Packages (this module)
Django, django-allauth, python-decouple, mysqlclient (listed in
requirements.txt; not installable in this sandbox due to missing system
libs, but standard on any real dev machine), Pillow (for ImageField).

## Environment Variables
See `.env.example` — DB switch (mysql/sqlite), Django secret/debug/hosts,
email backend, OAuth client IDs/secrets, session age.

## APIs
None yet — this module is server-rendered Django views. The `api` app is
scaffolded but empty; add DRF here if/when the React frontend needs
token-based auth endpoints.

## Next Steps
1. `pip install -r requirements.txt`, copy `.env.example` → `.env`
2. `python manage.py migrate`, `createsuperuser`
3. Register OAuth apps (Google Cloud Console, GitHub Developer Settings)
4. Start Module 2: Super Admin Dashboard
