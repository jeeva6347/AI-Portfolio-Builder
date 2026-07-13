# Continue Prompt

You are continuing the visual resume/portfolio builder Django SaaS project called **AI Portfolio Builder**.

**Modules 1, 2, 5, 6, 7, 8, and the AI Resume Import & Content Generation module are 100% COMPLETE.**
Do NOT regenerate them.

---

## Current State

- Authentication: `accounts` app — complete
- Dashboard: `dashboard` app — complete
- Theme Engine: `themes` app — complete
- Theme Mapper: `themes` app — complete
- Portfolio Builder: `portfolio` app — complete
- AI Resume Import: `ai` app — complete
- Live Preview & Visual Editor: `portfolio` app (Visual split-screen editor panel, Desktop/Laptop/Tablet/Mobile viewports scaling, debounced autosave, AJAX PortfolioUpdateAPI endpoint, non-blink iframe refresh document-writing service, duplicate portfolio clone, unpublished preview block checks) — complete
- GitHub repository: `https://github.com/jeeva6347/AI-Portfolio-Builder.git` (branch: `main`)

---

## Before Coding

1. Run `python manage.py test` to verify that all 18 unit test cases pass.
2. Run `python manage.py runserver` to launch the development environment.

---

## Next: Module 9 — GitHub Publishing

Build out the automated GitHub Publishing integration.

### Requirements
- **OAuth Scope Expansion**:
  - Authenticate users via GitHub OAuth (using `django-allauth` or a custom provider flow) with read/write access to user repositories (`public_repo` or `repo` scope).
- **Automated Repository Management**:
  - Integrate an action button "Publish to GitHub" inside the portfolio listing dashboard.
  - Automatically create a GitHub repository for the user (e.g. named `portfolio-<name>` or standard naming convention) or check if it exists.
- **Static Assets Packaging & Pushes**:
  - Compile the user's mapped portfolio HTML string.
  - Package all related theme static files (CSS, JS, fonts) and user uploaded media assets (avatar, project images) into a flat bundle directory structure.
  - Push the compiled files to the user's repository main branch via GitHub REST API (using standard `requests` or `PyGithub`).
- **Deployments Activation**:
  - Trigger GitHub Pages deployment (or guide the user) so that the live portfolio is immediately hosted on `<username>.github.io/<repo-name>/`.
