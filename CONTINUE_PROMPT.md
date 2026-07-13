# Continue Prompt

You are continuing the visual resume/portfolio builder Django SaaS project called **AI Portfolio Builder**.

**Modules 1, 2, 5, and 6 (Authentication, Dashboard, Theme Engine, Theme Mapper) are 100% COMPLETE.**
Do NOT regenerate them.

---

## Current State

- Authentication: `accounts` app — complete
- Dashboard: `dashboard` app — complete
- Theme Engine: `themes` app — complete
- Theme Mapper: `themes` app (ThemeMapping / ThemeMappingField models, visual mapper workspace, HTML scanner suggestions, iframe compiled previews) — complete
- GitHub repository: `https://github.com/jeeva6347/AI-Portfolio-Builder.git` (branch: `main`)

---

## Before Coding

1. Run `python manage.py test themes` to verify that the core mapper scanner, parser, and sanitization compiler tests pass.
2. Run `python manage.py runserver` to launch the development environment.

---

## Next: Module 7 — Portfolio Builder

Build out the Portfolio Builder inside the `portfolio` app.

### Requirements
- Create database models for the user portfolio data:
  - `Portfolio`: linked to a User, has fields matching `personal.*` (Name, Title, Bio, Photo, Contact, etc.).
  - `PortfolioSection`: dynamic sections like Skills, Experience, Education, Projects, Testimonials.
  - `PortfolioItem`: individual rows inside sections (e.g. one Project, one Job Experience).
- Build a user-facing form wizard or tabbed builder interface:
  - Let users enter their personal information, choose social links, select a resume PDF file.
  - Let users dynamically add/edit/delete skills (technical, soft), experiences, projects, education entries.
- Integrate Theme Mapping selection:
  - When the user selects an approved theme from the Marketplace, automatically bind that theme's `active` `ThemeMapping` profile.
  - Compile the live portfolio by querying the user's saved portfolio data models and feeding them into `apply_theme_mapping` to generate the HTML.
- Protect against XSS and sanitize any rich-text inputs.
- Ensure only the owner can edit their portfolio data.

### Rules to Keep Following
- Reuse existing dashboard layouts and components (sidebar, navbar, toast, breadcrumbs).
- Comment important business logic.
- Avoid duplicate code.
- Update documentation files (`CHANGELOG.md`, `TODO.md`, `PROJECT_STATUS.md`, `DEVELOPMENT_REPORT.md`) after completing the module.
