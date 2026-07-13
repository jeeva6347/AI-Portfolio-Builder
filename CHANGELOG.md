# Changelog

## [Completed] - Module 11: Analytics, SEO & Performance
### Added
- Complete traffic tracker schema logging visits `PortfolioVisit` (browsers, devices types, countries, referrers, page sections) and metrics totals `PortfolioMetric`.
- Dynamic SEO tag override profiles `PortfolioSEO` supporting custom meta titles, keywords list, canonical links, OG Facebook sharing tags, and Twitter Cards descriptors.
- Modular BeautifulSoup filter parser injecting head meta tags and icon favicon links into compiled compiled portfolio layouts preview output.
- Performance diagnostics service layer (`performance_service.py`) aggregating css, js, image bytes, and suggestion listings (compression prompts, minification alerts).
- High-fidelity traffic analytics charts (`templates/analytics/dashboard.html`) displaying past 30 days line graphs, referrers tables, devices breakdowns, and admin system statistics.
- Interactive SEO form metadata editor panel (`templates/analytics/seo_config.html`) including custom crawler robots directives and dynamic Google/Social share SERP snippet previews.
- Page Speed diagnostic gauges display (`templates/analytics/performance.html`) containing speedometers and files category progress bars.
- Dynamic sitemaps generation route serving published locating tags `/sitemap.xml` and plain text robot rules `/robots.txt`.
- Multi-portfolio metrics overview cards and trend lines graphs added to User Dashboard (`user.html`) and Super Admin dashboard.
- Active visual builder action links inside visual workspace toolbar (`builder.html`) and grid listing templates.
- Expanded automated unit tests suite inside `analytics/tests.py` testing signals, tracking logs, SEO tags injection, sitemaps XML, robots directives, and premium tier gates (7 new tests, 36 total passing OK).

## [Completed] - Module 10: SaaS Subscription & Payments
### Added
- Reusable `SubscriptionPlan` model tracking pricing tiers, portfolio limits, premium themes access, AI upload counts, and GitHub publishes caps.
- `UserSubscription` model recording auto-renew state, renewal dates, and status fields (active, canceled, expired).
- `UsageMetrics` model aggregating active user stats (portfolios, parses, publishes, and disk space usage sizes).
- Modular payment provider service layer (`BasePaymentProvider`, `MockPaymentProvider`) managing sessions and simulating checkout URL routing.
- Custom decorators and CBV mixins enforcing limits checks: `PortfolioLimitMixin`, `AILimitMixin`, `GitHubPublishLimitMixin` blocking premium options for Free tiers.
- High-fidelity billing templates (`templates/payments/billing.html`, `checkout_mock.html`, `success.html`, `failure.html`) for usage tracking and transaction history logs.
- Admin revenue summary template (`templates/payments/admin_billing.html`) showing aggregate subscribers splits, plans metrics, and sales transaction tables.
- Provision signals auto-creating default Free tier subscription and metrics profile on account signup.
- Expanded mock unit tests inside `payments/tests.py` testing auto creation, limit blocks, upgrades, cancellations, and admin checks (7 new tests, 29 total passing OK).

## [Completed] - Module 9: GitHub Auto Publish & GitHub Pages Deployment
### Added
- Reusable service layer under `github_integration/services/` decoupled from views (`oauth_service.py`, `repository_service.py`, `exporter_service.py`, `deployment_service.py`, `pages_service.py`).
- Active connected repository configurations model `GitHubRepoConfig` and deployment publication logs history model `GitHubDeployment` under migrations `0001`.
- Synchronous or background publish compile-and-push Git Data REST API (blobs creation, parent tree references, commits base mappings, and heads refs updates).
- Automatic Pages setup enablement triggers on the mapped repository's main branch.
- HTML relative media converter scans compiled soup resources, copies referenced local media files to the Git package, and rewrites path links dynamically to run offline.
- Deployment dashboard template (`templates/github/dashboard.html`) mapping active configurations, status indicators, live page links, build logs error checklists, and logs tables.
- Sidebar menu triggers linked dynamically to route connected portfolios or fall back to listings.
- Mock integrations unit tests inside `github_integration/tests.py` testing auth retrieval, export converters, API ref configurations, and Pages configs.

## [Completed] - Module 8: Live Preview & Visual Portfolio Editor
### Added
- Multi-portfolio management listing dashboard (`templates/portfolio/list.html`) partitioning Drafts, Published, and Archived states.
- Database relationship refactoring: updated `Portfolio.user` to ForeignKey and added a text-choice `status` field with migration `0003`.
- Side-by-side split-screen editing visual workspace (`templates/portfolio/builder.html`) with Left Editing Panel and Right Live Preview viewport.
- Viewport size responsive controllers (Desktop, Laptop, Tablet, Mobile) and CSS transform-based zoom scale managers (50% - 150%).
- Debounced (800ms) autosave script (`static/js/portfolio_builder.js`) asynchronously committing updates via `PortfolioUpdateAPI` AJAX endpoint.
- Smooth dynamic iframe refreshing by fetching fresh compiled HTML layouts and document-writing without browser reload blinks.
- Duplicate portfolio action cloned properties and deep-copied child list items (skills, projects, educations, experiences).
- Security controls: restricted visual editor workspace access and unpublished preview iframe access to the owner of the portfolio (403 Forbidden).
- Expanded automated tests suite by adding 4 comprehensive unit tests in `portfolio/tests.py`.

## [Completed] - Module 6: AI Resume Import & AI Portfolio Generation
### Added
- Resume parser service (`ai/services.py`) extracting personal details, contact coordinates, social profile links, skills, experiences, educations, and projects.
- Gemini LLM parser connector integration with structured JSON outputs.
- Robust Regex/Heuristics parsing fallback supporting indented heading divisions and protocol-optional links.
- AI Content Enrichment pipeline enhancing about descriptions, experience/project summaries, and compiling SEO metadata.
- Drag-and-drop resume upload portal (`templates/ai/import.html`) with file size validation, extension Whitelisting (PDF/DOCX), and corruption scanning.
- Review and edit workspace panel (`templates/ai/review.html`) displaying extracted data in editable formats.
- Integration views: saves the reviewed characteristics, deletes/overwrites legacy profiles, and builds new child records.
- Active "AI Content" link integrated into sidebar navigation.
- Comprehensive Unit Test Suite (`ai/tests.py`) covering all Module 6 features.

## [Completed] - Module 7: Portfolio Builder
### Added
- Portfolio database models (`Portfolio`, `PortfolioSkill`, `PortfolioProject`, `PortfolioExperience`, `PortfolioEducation`, `PortfolioCertificate`, `PortfolioService`, `PortfolioTestimonial`) with migrations `0001` and `0002`.
- Integrated tabular inline sections inside Django Admin for easy model management.
- Multi-tab configuration dashboard panel (`templates/portfolio/builder.html`) allowing users to edit personal, contact, socials, and footer details.
- Clean CRUD POST sub-views for related lists (skills, experiences, education, projects, certificates, services, testimonials) supporting inline additions and deletes.
- Dynamic list replication support inside `apply_theme_mapping` to clone template items and inject dynamic portfolio values into templates (like projects.list, experience.list).
- Auto base-href tag injection resolving relative paths for CSS, JS, and images automatically during theme compilation previews.
- Theme Selection Dashboard View (`templates/portfolio/select_theme.html`) allowing users to browse and activate templates.
- Interactive user portfolio preview viewport with viewport switching controls.
- Comprehensive Unit Test Suite (`portfolio/tests.py`) covering all Module 7 features.
- Dynamic portfolio statistics wired into the User Dashboard welcome panel.

## [Completed] - Module 6: Theme Mapper
### Added
- Visual mapping interface (`templates/themes/admin/mapper.html`) allowing admins to visually map elements in theme templates.
- Dotted portfolio mapping keys registry (`themes/fields.py`) containing 50+ normalized fields (Personal Info, Skills, Projects, Experience, Education, Socials, Footer, Contact, etc.).
- Safe HTML scanner and parsing helper (`themes/scanner.py`) to auto-suggest element selectors using custom heuristics and detect curly-bracket template placeholders.
- Real-time mapping compilation and injection (`apply_theme_mapping` inside `themes/services.py`).
- Security Layer: HTML sanitization (`sanitize_html_string`) decomposing unsafe tags (e.g. `<script>`, inline event handlers) to prevent XSS.
- Versioning and management actions: Create, duplicate/clone, delete, activate, list mappings.
- Preview Page (`templates/themes/admin/mapper_preview.html`) containing desktop, tablet, and mobile viewport controls.
- API endpoints: `ThemeScannerAPI` for recommendations, `MappingSaveAPI` for bulk mapping saving.
- Mapping persistence: added `ThemeMapping` and `ThemeMappingField` models with migration `0003_thememapping`.
- Comprehensive Unit Test Suite (`themes/tests.py`) covering all Module 6 features.
- "Mappings" action trigger added to the Theme details view.

## [Completed] - Module 5: Theme Engine + Pre-flight Fixes
### Fixed
- Added `accounts/migrations/0002_user_theme_preference.py` — additive migration for the `theme_preference` field that was missing from `0001_initial.py`. Safe for both fresh and existing databases.
- Fixed root URL `/` returning 404. Now redirects to `/accounts/login/`.

### Added
- Full Theme Engine in the `themes` app:
  - Models: `ThemeCategory`, `Theme`, `ThemeAsset` with proper migrations.
  - Data migration seeding 10 default categories (Developer, Portfolio, Resume, Minimal, Corporate, Creative, Business, Landing Page, Dark, Light).
  - ZIP upload pipeline with 6-layer validation: format, 50MB size limit, zip-slip protection, file type whitelist, 500-file count limit, required `index.html`.
  - Atomic transaction — any processing failure rolls back DB and removes extracted files.
  - Asset scanner: classifies HTML, CSS, JS, images, fonts, and stores per-file records.
  - Placeholder thumbnail generator using Pillow.
  - Admin views: theme list (with status filter), upload, detail, approve, reject, submit for review, delete.
  - Category management: list + add + delete categories.
  - Public Marketplace with search, category filter, pricing filter, and sort.
  - Theme preview via sandboxed iframe with desktop/tablet/mobile viewport toggles.
  - Django Admin integration for all three models.
- Connected real theme counts to Super Admin Dashboard stats.
- Replaced sidebar Themes and Marketplace placeholder links with live URLs.
- `static/js/theme_upload.js` — drag-and-drop UX with client-side validation and progress bar.
- `static/css/themes.css` — marketplace cards, drop zone, and preview styling.

## [Completed] - Module 2: Dashboard System
### Added
- Dashboard architecture with reusable components (`sidebar`, `navbar`, `cards`, `toast`, `breadcrumb`, `footer`).
- Implemented Super Admin Dashboard, Admin Dashboard, and User Dashboard templates.
- Strict separation of Bootstrap 5 (Layout) and Tailwind CSS (Utilities).
- Dark/Light mode theme toggle using LocalStorage and Tailwind classes.
- Responsive collapsing sidebar with LocalStorage persistence.
- Reusable Chart.js initialization logic (`static/js/charts.js`).
- `SuperAdminRequiredMixin` and `AdminRequiredMixin` security classes.
- Custom 403 Access Denied template matching the dashboard styling.
- `theme_preference` field added to the `User` model.
- Centralized `dashboard/navigation.py` to manage sidebar routes.

## [Completed] - Module 1: Authentication
- Full app structure: `accounts`, `dashboard`, `themes`, `portfolio`,
  `analytics`, `payments`, `github_integration`, `ai`, `notifications`,
  `api`, `core` (all but `accounts` are empty scaffolds for later phases).
- Custom `accounts.User` model: role field (SUPER_ADMIN / ADMIN /
  PREMIUM_USER / FREE_USER, default FREE_USER), `is_premium` derived
  property, `upgrade_to_premium()` / `downgrade_to_free()` helpers for
  the future payments module, avatar, github_username, email_verified.
- Email signup (with optional profile picture) and login (with Remember
  Me — persists session per SESSION_COOKIE_AGE, or ends at browser close).
- Google OAuth and GitHub OAuth via django-allauth.
- Forgot / reset password flow (Django's built-in views, custom
  Bootstrap templates, console email backend for dev).
- Profile page (update avatar + GitHub username).
- Session management page (list active sessions, sign out of all others).
- Role-based dashboard redirect stub (real dashboards are Module 2).
- Env-driven settings: DB (MySQL/SQLite switch), email backend, session
  age — nothing hardcoded per the Development Rules.

### Fixed (caught via live smoke-testing, not just code review)
- Signup crashed on login() due to multiple AUTHENTICATION_BACKENDS
  being configured without specifying which one — now explicit.
- Profile page 500'd for anonymous users — added LoginRequiredMixin.
- Templates were missing `{% load socialaccount %}` for the OAuth
  buttons.
