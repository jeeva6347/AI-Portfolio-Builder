# AI Portfolio Builder

A full-stack Django SaaS application for building, customizing, and publishing professional portfolio websites powered by AI resume parsing, live theme previews, GitHub Pages deployment, and comprehensive analytics.

---

## Features

### ✅ Completed Modules (1–12)

| Module | Feature |
|---|---|
| 1 | Authentication (Email + Google + GitHub OAuth, role-based users) |
| 2-4 | Role-based Dashboards (Super Admin, Admin, User) |
| 5 | Theme Engine (ZIP upload, validation, marketplace, preview) |
| 6 | Theme Mapper (Visual CSS selector mapping, XSS sanitization) |
| 7 | Portfolio Builder (CRUD, multi-tab editor, dynamic list compilation) |
| AI | AI Resume Import (PDF/DOCX parsing, Gemini LLM enrichment) |
| 8 | Live Preview & Visual Editor (real-time iframe, autosave) |
| 9 | GitHub Auto Publish & GitHub Pages Deployment |
| 10 | SaaS Subscriptions & Payments (plans, usage limits, mock Stripe) |
| 11 | Analytics, SEO & Performance (traffic tracking, meta injection, sitemap) |
| 12 | Production Stabilization (51 tests passing, query optimization, security) |

---

## Quick Start

```bash
# Clone
git clone https://github.com/your-username/aiportfoliobuilder.git
cd aiportfoliobuilder/aiportfoliobuilder

# Setup virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Visit `http://localhost:8000` to access the application.

---

## Technology Stack

- **Backend**: Django 4.x
- **Authentication**: django-allauth (Email + Google + GitHub OAuth)
- **Frontend**: Bootstrap 5 + Tailwind CSS utilities + Chart.js
- **AI**: Google Gemini API
- **HTML Processing**: BeautifulSoup4
- **Config**: python-decouple
- **Database**: SQLite (dev) / MySQL (production)

---

## Testing

```bash
python manage.py test
```

**51 automated tests** covering authentication, dashboard, themes, portfolio builder, AI import, GitHub integration, payments, and analytics.

---

## Documentation

| Document | Description |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, design patterns, data flow |
| [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) | Internal AJAX endpoints and data schemas |
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | Production deployment with Nginx + SSL |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Development setup, standards, and git workflow |
| [CHANGELOG.md](./CHANGELOG.md) | Module-by-module development history |
| [PROJECT_STATUS.md](./PROJECT_STATUS.md) | Current completion status |

---

## Project Structure

```
aiportfoliobuilder/
├── accounts/           # Authentication & User model
├── dashboard/          # Role-based dashboards
├── themes/             # Theme Engine & Marketplace
├── portfolio/          # Portfolio Builder & Live Preview
├── ai/                 # AI Resume Import
├── github_integration/ # GitHub Publish & Pages
├── payments/           # Subscriptions & Billing
├── analytics/          # Traffic, SEO, Performance
├── core/               # (Reserved: future shared utilities)
├── api/                # (Reserved: future DRF REST API)
├── notifications/      # (Reserved: future notifications)
└── templates/          # Shared HTML templates
```

---

## Security

- All production security settings gated behind `DEBUG=False`
- XSS protection via HTML sanitization in theme uploads
- CSRF, clickjacking, and session security configured
- ZIP upload validated against zip-slip, file type whitelist, and size limits

---

## License

This project is for demonstration and educational purposes.
