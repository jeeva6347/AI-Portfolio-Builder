# Project Status

**Completion:** Module 14 (Team Collaboration & Organization Workspace) — complete. ~63% overall (14 of ~22 modules).

## Completed
- Module 1: Authentication (Custom User model, Email/Social Auth)
- Module 2: Dashboard System (Super Admin, Admin, and User dashboards)
- Module 5: Theme Engine (Upload, Validate, Extract, Marketplace, Preview, Admin)
- Module 6: Theme Mapper (Visual element mapping workspace, HTML scanner & auto-suggest, compiled live iframe preview, duplication, XSS sanitization, tests)
- Module 7: Portfolio Builder (User portfolio database models, CRUD builder tab subviews, theme activation panel, dynamic list compiler list replication, base-href resolution, tests)
- Module 6 (AI): AI Resume Import & AI Portfolio Generation (PDF/DOCX file extractors, heuristic fallback regex schemas, Gemini JSON parses, content enrichers, verification editor workspace, merge/overwrite builder population)
- Module 8: Live Preview & Visual Portfolio Editor (Multi-portfolios dashboard, ForeignKey refactoring, side-by-side editing sidebar panel, responsive viewports zoom, debounced autosave, non-blink dynamic iframe reloading, duplication clone actions, tests)
- Module 9: GitHub Auto Publish & GitHub Pages Deployment (Reusable service layer oauth/repos/exporter/deployment/pages, repo configuration models, in-memory Git Data API commit pushes, Pages activator, layout media link absolute-to-relative converter, templates dashboard)
- Module 10: SaaS Subscription & Payments (Database SubscriptionPlan, UserSubscription, UsageMetrics, and PaymentTransaction models, mock Stripe checkout simulator redirect flow, decorators/CBV mixins premium limits checks, user and admin dashboards templates)
- Module 11: Analytics, SEO & Performance (Database models tracking visitors, device types, referrers, and pages, BeautifulSoup filter injecting custom meta titles, descriptions, OG social cards, and favicons, performance analyzer suggestions, sitemap.xml, robots.txt, Chart.js views history line charts)
- Module 12: Production Stabilization & Code Quality (51 tests passing, security hardening, query optimization, code audit, documentation)
- Module 13: Custom Domains (CustomDomain database model, CNAME/TXT DNS verification lookups, mock SSL status validation, custom domain resolution routing middleware, management dashboard list/add/instructions UIs, 11 automated unit tests)
- Module 14: Team Collaboration & Organization Workspace (Organization, OrganizationMember, Invitation, and ActivityLog models, role-based collaborator permissions checks for shared portfolios, link/unlink portfolios, accept invites, transfer ownerships, and leave workspaces views, 13 automated unit tests)

## Not Started
- Modules 15-22 (PDF Export, etc.)

## Folder Structure
```
aiportfoliobuilder/
├── accounts/            <- Module 1, complete
├── dashboard/           <- Module 2-4, complete
├── themes/              <- Module 5, complete
├── portfolio/           <- Module 6-8, complete
├── github_integration/  <- Module 9, complete
├── ai/                  <- Module 6 (AI), complete
├── payments/            <- Module 10, complete
├── analytics/           <- Module 11, complete
├── domains/             <- Module 13, complete
├── organizations/       <- Module 14, complete
├── notifications/       <- empty scaffold (reserved for future)
├── api/                 <- empty scaffold (reserved for future)
├── core/                <- empty scaffold (reserved for future)
├── templates/base.html
└── aiportfoliobuilder/ (project settings/urls)
```

## Database Schema (so far)
### accounts.User (extends AbstractUser)
| Field | Type | Notes |
|---|---|---|
| role | CharField | SUPER_ADMIN / ADMIN / PREMIUM_USER / FREE_USER, default FREE_USER |
| avatar | ImageField | optional |
| github_username | CharField | optional |
| email_verified | BooleanField | default False |

### domains.CustomDomain
| Field | Type | Notes |
|---|---|---|
| user | ForeignKey | User owner |
| portfolio | ForeignKey | Target portfolio |
| domain_name | CharField | Root domain |
| subdomain | CharField | Optional subdomain |
| provider | CharField | DNS provider choice |
| status | CharField | pending, verifying, active, failed |
| ssl_status | CharField | pending, issued, failed |

### organizations.Organization
| Field | Type | Notes |
|---|---|---|
| name | CharField | Organization name |
| slug | SlugField | Unique workspace identifier |
| owner | ForeignKey | User owner |
| logo | ImageField | Workspace avatar |
| description | TextField | Description text |
| plan | ForeignKey | Subscription plan ForeignKey |

### organizations.OrganizationMember
| Field | Type | Notes |
|---|---|---|
| organization | ForeignKey | Parent Organization |
| user | ForeignKey | User member |
| role | CharField | OWNER, ADMIN, EDITOR, VIEWER |
| joined_at | DateTimeField | Creation date |
| invited_by | ForeignKey | User who invited them |
| active | BooleanField | Is membership active |

## Test Count
- 75 automated tests across all modules (exceeds 70+ target)
- accounts: 4, ai: 4, analytics: 7, dashboard: 4, domains: 11, github_integration: 4, organizations: 13, payments: 7, portfolio: 12, themes: 9

## Security Settings
Production security settings are gated behind `DEBUG=False`:
- SECURE_SSL_REDIRECT
- SESSION_COOKIE_SECURE
- CSRF_COOKIE_SECURE
- SECURE_HSTS_SECONDS
- SECURE_HSTS_INCLUDE_SUBDOMAINS
- SECURE_HSTS_PRELOAD

## Installed Packages
Django, django-allauth, python-decouple, Pillow, BeautifulSoup4, python-docx

## Environment Variables
See `.env.example` — DB switch (mysql/sqlite), Django secret/debug/hosts, email backend, OAuth client IDs/secrets.

## Next Steps (Module 15+)
1. PDF Portfolio Export
2. Team Collaboration features
