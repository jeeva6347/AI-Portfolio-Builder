# Architecture

## Overview

AI Portfolio Builder is a Django-based SaaS application for creating, managing, and publishing professional portfolio websites. Users can import their resume via AI, customize themes, preview in real time, and publish directly to GitHub Pages.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend Framework | Django 4.x |
| Authentication | django-allauth (email + Google + GitHub OAuth) |
| Database | SQLite (development) / MySQL (production) |
| Frontend | Bootstrap 5 + Tailwind CSS utilities |
| Charts | Chart.js |
| AI Integration | Google Gemini API |
| File Parsing | python-docx, PyPDF2 / pdfminer |
| HTML Manipulation | BeautifulSoup4 |
| Image Processing | Pillow |
| Config Management | python-decouple |

---

## Application Architecture

The project follows a Django multi-app architecture where each feature domain is encapsulated in its own app:

```
aiportfoliobuilder/
├── accounts/         # Authentication, User model, roles
├── dashboard/        # Role-based dashboards, navigation
├── themes/           # Theme Engine (upload, validation, marketplace)
├── portfolio/        # Portfolio Builder (CRUD, live preview)
├── ai/               # AI Resume Import, content enrichment
├── github_integration/ # GitHub OAuth, publish, GitHub Pages
├── payments/         # Subscription plans, billing, usage limits
├── analytics/        # Traffic tracking, SEO, performance
├── core/             # (Reserved: future shared utilities)
├── api/              # (Reserved: future DRF REST API)
├── notifications/    # (Reserved: future email/push notifications)
└── aiportfoliobuilder/ # Django project settings, URL configuration
```

---

## Key Design Patterns

### 1. Service Layer Pattern
Business logic is placed in dedicated service modules, not views:
- `themes/services.py` — theme processing pipeline, XSS sanitization, mapping compiler
- `ai/services.py` — resume parsing, Gemini API calls, content enrichment
- `github_integration/services/` — OAuth, repository, exporter, deployment, pages services
- `payments/services.py` — payment provider abstraction
- `analytics/services/` — tracking service, SEO service, performance service

Views remain thin coordinators that delegate to services.

### 2. Permission Mixins
Reusable permission guards as Django CBV mixins:
- `dashboard/mixins.py` — `SuperAdminRequiredMixin`, `AdminRequiredMixin`
- `payments/permissions.py` — `PortfolioLimitMixin`, `AILimitMixin`, `GitHubPublishLimitMixin`

### 3. Signal-Based Auto-Provisioning
Django signals ensure automatic creation of related records:
- `payments/signals.py` — creates `UserSubscription` + `UsageMetrics` on user creation
- `analytics/signals.py` — creates `PortfolioMetric` + `PortfolioSEO` on portfolio creation

### 4. Query Optimization
- `select_related()` used for ForeignKey traversals
- `prefetch_related()` used for reverse OneToOne and ManyToMany
- Aggregation via `annotate()` and `.aggregate()` instead of Python-side loops

---

## Data Flow

### Portfolio Preview Flow
```
User → PortfolioBuilderView → get_fields_dict() → apply_theme_mapping()
     → inject_seo_metadata() → Base64 HTML response → iframe preview
```

### GitHub Publish Flow
```
User → GitHubPublishView → oauth_service.get_token()
     → exporter_service.export_portfolio() → repository_service.push_to_github()
     → pages_service.enable_pages() → deployment_service.log_deployment()
```

### Payment Flow
```
User → CheckoutView → MockPaymentProvider.initiate_checkout()
     → PaymentTransaction(PENDING) → checkout_mock redirect
     → success_callback → transaction(SUCCESS) → subscription upgrade
```

---

## Security Model

### Authentication
- Email/Password via django-allauth
- Google OAuth, GitHub OAuth
- CSRF protection on all POST endpoints
- Login required on all authenticated views

### Authorization
- Role-based: `SUPER_ADMIN > ADMIN > PREMIUM_USER > FREE_USER`
- Permission checks via mixins and view-level guards
- Portfolio access restricted to owner (returns 403 on unauthorized access)

### File Upload Security
- ZIP uploads: 6-layer validation (format, size, zip-slip, whitelist, count, index.html required)
- Resume uploads: PDF/DOCX whitelist, size limit
- File uploads served from `MEDIA_ROOT` not user-controlled paths

### XSS Protection
- `sanitize_html_string()` in `themes/services.py` strips `<script>` and inline event handlers
- Django template auto-escaping enabled
- Content Security Policy via `X-Frame-Options: DENY`

### Production Security (DEBUG=False)
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

---

## Database Models Overview

### accounts
- `User` — extended AbstractUser with role field, avatar, github_username

### themes
- `ThemeCategory` — browsable categories
- `Theme` — uploaded ZIP themes with status workflow
- `ThemeAsset` — individual files inside themes
- `ThemeMapping` — visual field mapping profiles
- `ThemeMappingField` — individual CSS selector → portfolio field mappings

### portfolio
- `Portfolio` — user portfolio with status (draft/published/archived)
- `PortfolioSkill`, `PortfolioProject`, `PortfolioExperience`, `PortfolioEducation`
- `PortfolioCertificate`, `PortfolioService`, `PortfolioTestimonial`

### ai
- `ResumeUpload` — uploaded resume files

### github_integration
- `GitHubRepoConfig` — connected repository configuration
- `GitHubDeployment` — deployment history and logs

### payments
- `SubscriptionPlan` — plan definitions with limits
- `UserSubscription` — user's current plan
- `UsageMetrics` — per-user usage tracking
- `PaymentTransaction` — payment history

### analytics
- `PortfolioMetric` — aggregated visit totals, SEO/performance scores
- `PortfolioVisit` — individual visit records (browser, device, country, referrer)
- `PortfolioSEO` — custom meta tags, Open Graph, Twitter Card, robots.txt

---

## URL Structure

| Prefix | App | Description |
|---|---|---|
| `/accounts/` | accounts + allauth | Login, signup, OAuth, profile |
| `/dashboard/` | dashboard | Super Admin, Admin, User dashboards |
| `/themes/` | themes | Theme marketplace, admin, mapper |
| `/portfolio/` | portfolio | Builder, preview, list, CRUD |
| `/ai/` | ai | Resume import, review |
| `/github/` | github_integration | Connect, publish, deploy |
| `/billing/` | payments | Subscription, billing, checkout |
| `/analytics/` | analytics | Traffic, SEO, performance |
| `/sitemap.xml` | analytics | Dynamic sitemap |
| `/robots.txt` | analytics | Crawler configuration |
| `/admin/` | Django admin | Backend admin panel |
