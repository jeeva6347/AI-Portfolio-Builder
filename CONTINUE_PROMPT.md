# Continue Prompt

You are continuing the visual resume/portfolio builder Django SaaS project called **AI Portfolio Builder**.

**Modules 1, 2, 5, 6, 7, and the AI Resume Import & Content Generation module are 100% COMPLETE.**
Do NOT regenerate them.

---

## Current State

- Authentication: `accounts` app — complete
- Dashboard: `dashboard` app — complete
- Theme Engine: `themes` app — complete
- Theme Mapper: `themes` app — complete
- Portfolio Builder: `portfolio` app — complete
- AI Resume Import: `ai` app (ResumeUpload models, ResumeParserService extracting text/sections/Gemini JSONs, content enrichers, drag-and-drop uploads view, visual JSON review editor workspace) — complete
- GitHub repository: `https://github.com/jeeva6347/AI-Portfolio-Builder.git` (branch: `main`)

---

## Before Coding

1. Run `python manage.py test` to verify that all 14 unit test cases pass.
2. Run `python manage.py runserver` to launch the development environment.

---

## Next: Module 8 — Live Preview

Build out the Live Preview serving system under the `portfolio` app or custom core handlers.

### Requirements
- **Dynamic Routing**:
  - Map users' published portfolios to custom URLs (e.g. `/show/<username>/` or custom subdomains if supported by middleware).
- **Asset Resolution**:
  - Ensure that when a public user accesses a portfolio, all relative assets in the theme (CSS stylesheets, JavaScript scripts, template graphics) resolve to the theme's extracted directory under `/media/themes/extracted/<slug>/` correctly.
  - Make sure user uploaded images (project screenshot, cover image, profile picture) load correctly.
- **Dynamic Compilation**:
  - Pull the user's active theme mapping profile.
  - Retrieve the user's portfolio database records.
  - Compile the template in real-time, sanitize the HTML string against XSS, and serve the final page.
- **Verify Accessibility and Responsiveness**:
  - Check the output layout resolves perfectly in both desktop, tablet, and mobile viewports.
