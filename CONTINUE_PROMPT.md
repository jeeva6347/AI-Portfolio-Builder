# Continue Prompt

You are continuing work on "AI Portfolio Builder" (Django + MySQL SaaS).

**Modules 1 and 2 (Authentication & Dashboards) are 100% COMPLETE.** Do NOT regenerate them.

## Start here: Module 5 — Theme Engine
Build out the core Theme Engine in the `themes` app.

Requirements:
- Support uploading `theme.zip` files (containing `index.html`, `style.css`, `script.js`, `assets/`).
- Automatically extract, validate structure, and store the files.
- Read metadata from the theme (if applicable).
- Generate a preview for the theme.
- Create models: `Theme`, `ThemeAsset`, etc.

## Rules to keep following
- Reuse the existing Dashboard UI components (cards, tables, breadcrumbs) for any admin interfaces you build in the `themes` app.
- Never write duplicate HTML if a component exists in `templates/dashboard/components/`.
- Test every view live before calling it done.
- Update CHANGELOG.md / TODO.md / PROJECT_STATUS.md as you go.
- Stop and ask for permission before modifying completed Modules 1 and 2.
