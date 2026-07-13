# Continue Prompt

You are continuing work on **AI Portfolio Builder** (Django + MySQL SaaS).

**Modules 1, 2, and 5 (Authentication, Dashboard System, Theme Engine) are 100% COMPLETE.**
Do NOT regenerate them.

---

## Current State

- Authentication: `accounts` app — complete
- Dashboard System: `dashboard` app — complete (Super Admin, Admin, User dashboards)
- Theme Engine: `themes` app — complete (upload, validate, extract, marketplace, preview)
- GitHub repository: `https://github.com/jeeva6347/AI-Portfolio-Builder.git` (branch: `main`)

---

## Before Coding

1. Run `python manage.py migrate` to apply all pending migrations.
2. Run `python manage.py check` to verify no system issues.
3. Confirm there are no merge conflicts.

---

## Next: Module 6 — Theme Mapper

Build out the Theme Mapper inside the `themes` app.

### Requirements
- Parse the uploaded theme's `index.html` to discover template placeholders.
- Support custom placeholder syntax: `{{name}}`, `{{bio}}`, `{{tagline}}`, `{{projects}}`, `{{skills}}`, `{{contact}}`, etc.
- Create a `ThemeMapping` model that stores the mapping between placeholder keys and portfolio data fields.
- Allow Admins to define mappings for each theme via a visual form UI.
- Store mappings in the database, linked to each `Theme`.
- On preview, inject real user data from the portfolio (once Portfolio Builder module exists) — for now, inject mock/placeholder data.
- Use existing dashboard components (breadcrumb, stat_card, table_card) for all admin UIs.
- Never duplicate existing templates or views.

### Rules to Keep Following
- Reuse existing dashboard components — never write duplicate HTML.
- Update CHANGELOG.md / TODO.md / PROJECT_STATUS.md / DEVELOPMENT_REPORT.md as you go.
- Stop and ask for permission before modifying completed Modules 1, 2, or 5.
- Generate a new CONTINUE_PROMPT.md when done.
