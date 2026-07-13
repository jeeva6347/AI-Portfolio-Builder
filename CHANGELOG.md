# Changelog

## [Unreleased] - Module 2: Dashboard System
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
