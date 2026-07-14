# AI Portfolio Builder — Version 2.0 (Product Polish & Production Ready)

A full-stack Django SaaS application for building, customizing, and publishing professional portfolio websites powered by AI resume parsing, live theme previews, custom domains, GitHub Pages deployment, team collaboration workspaces, and comprehensive traffic analytics.

---

## Features

### ✅ Completed Modules (1–14)

| Module | Feature |
|---|---|
| 1 | Authentication (Email + Google + GitHub OAuth, role-based users) |
| 2-4 | Role-based Dashboards (Super Admin, Admin, User) |
| 5 | Theme Engine (ZIP upload, validation, marketplace, preview) |
| 6 | Theme Mapper (Visual CSS selector mapping, XSS sanitization) |
| 7 | Portfolio Builder (CRUD, multi-tab editor, dynamic list compilation) |
| AI | AI Resume Import (PDF/DOCX parsing, Gemini LLM enrichment) |
| 8 | Live Preview & Visual Editor (real-time iframe, autosave, viewport responsive controls) |
| 9 | GitHub Auto Publish & GitHub Pages Deployment |
| 10 | SaaS Subscriptions & Payments (plans, usage limits, mock Stripe billing) |
| 11 | Analytics, SEO & Performance (traffic tracking, meta tag injection, sitemap/robots) |
| 12 | Production Stabilization (Code audits, prefetch optimization, security) |
| 13 | Custom Domains (CNAME/TXT verification DNS check, SSL issued status routing middleware) |
| 14 | Team Collaboration Workspaces (Organizations, invites, roles-based portfolios link/unlink permissions, audit feeds logs) |
| 2.0 | Version 2.0 Polish (Tailwind SaaS landing page, password strength meter, forms loaders, empty states, 75 passing unit tests) |

---

## Quick Start

```bash
# Clone
git clone https://github.com/jeeva6347/AI-Portfolio-Builder.git
cd aiportfoliobuilder

# Setup virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (Stripe keys, GitHub app details, Gemini API keys)

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run dev server
python manage.py runserver
```

Visit `http://localhost:8000` to access the premium landing page.

---

## Running Automated Tests

To run the complete automated test suite (75 passing tests):
```bash
python manage.py test
```

---

## Documentation Registry

We provide detailed documentation manuals:
- **[USER_GUIDE.md](file:///d:/aiportfoliobuilder-module1-auth-v2/aiportfoliobuilder/USER_GUIDE.md)**: User handbook to generate portfolios, hook GitHub, and map domains.
- **[ADMIN_GUIDE.md](file:///d:/aiportfoliobuilder-module1-auth-v2/aiportfoliobuilder/ADMIN_GUIDE.md)**: Admin guide to approve themes and manage subscription plans.
- **[DEPLOYMENT_GUIDE.md](file:///d:/aiportfoliobuilder-module1-auth-v2/aiportfoliobuilder/DEPLOYMENT_GUIDE.md)**: Steps to launch on production servers with Nginx & Gunicorn.
- **[SCREENSHOTS.md](file:///d:/aiportfoliobuilder-module1-auth-v2/aiportfoliobuilder/SCREENSHOTS.md)**: Page-by-page visual interface gallery references.
- **[PROJECT_STATUS.md](file:///d:/aiportfoliobuilder-module1-auth-v2/aiportfoliobuilder/PROJECT_STATUS.md)**: Detailed project module breakdown.
- **[DEVELOPMENT_REPORT.md](file:///d:/aiportfoliobuilder-module1-auth-v2/aiportfoliobuilder/DEVELOPMENT_REPORT.md)**: Design architectural decisions.
- **[CHANGELOG.md](file:///d:/aiportfoliobuilder-module1-auth-v2/aiportfoliobuilder/CHANGELOG.md)**: Version history timeline entries.
