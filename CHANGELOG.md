# Changelog

## [Unreleased] - Module 7: Portfolio Builder
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
