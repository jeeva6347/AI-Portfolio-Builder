# TODO

## Module 1 — Authentication (COMPLETE)
- [x] Custom User model with 4 roles (Super Admin/Admin/Premium/Free)
- [x] Email signup + login, with Remember Me
- [x] Google OAuth, GitHub OAuth
- [x] Forgot / reset password
- [x] Email verification (via allauth, ACCOUNT_EMAIL_VERIFICATION=optional
      by default — set to "mandatory" in .env for production)
- [x] Profile picture
- [x] Session management (list + revoke-others)
- [x] Role-based dashboard redirect stub
- [x] End-to-end tested: signup, login, logout, password reset round
      trip, profile access, session listing — all verified live, not
      just read through.

## Module 2-4 — Dashboard System (COMPLETE)
- [x] Shared Dashboard Layouts (Sidebar, Navbar, Components)
- [x] Super Admin Dashboard (Stats, Charts, User tables)
- [x] Admin Dashboard (Theme management placeholders)
- [x] User Dashboard (Portfolio management placeholders)
- [x] Theme Toggle (Light/Dark) & Responsive Collapsible Sidebar
- [x] Security Mixins and Custom 403 Page

## Module 5 — Theme Engine (COMPLETE)
- [x] ThemeCategory, Theme, ThemeAsset models + migrations
- [x] 10 default categories seeded via data migration
- [x] ZIP upload with 6-layer validation (format, size, zip-slip, whitelist, count, index.html)
- [x] Atomic processing pipeline (extract → scan → thumbnail → rollback on failure)
- [x] Admin: theme list, upload, detail, approve, reject, submit, delete
- [x] Admin: category list, add, delete
- [x] Public Marketplace: search, filter, sort
- [x] Theme preview: sandboxed iframe + desktop/tablet/mobile viewport toggle
- [x] Django Admin registration for all models
- [x] Sidebar navigation updated (Themes & Marketplace live)
- [x] Super Admin Dashboard now shows real theme counts
- [x] Fixed: `theme_preference` migration gap (0002_user_theme_preference.py)
- [x] Fixed: Root URL / returning 404 (redirects to login)

## Module 6 — Theme Mapper (COMPLETE)
- [x] ThemeMapping and ThemeMappingField models + migrations
- [x] Dotted portfolio fields registry (50+ fields defined)
- [x] Visual click-to-map HTML element selector editing in iframe
- [x] Auto-suggest mapping recommendations using HTML scanner
- [x] Dotted placeholder curly-braces regex rendering
- [x] Secure XSS injection filter (strips unsafe script elements/event handlers)
- [x] Versioning actions: create, duplicate/clone, toggle active status, delete mappings
- [x] Preview tool with viewport controls (Desktop, Tablet, Mobile)
- [x] Core scanner and compiler unit tests (6 passing test cases)

## Module 7 — Portfolio Builder (COMPLETE)
- [x] User Portfolio database schemas (Portfolio, Skill, Project, Experience, Education models)
- [x] Multi-tab configuration dashboard panel for personal details, contact, socials, and footers
- [x] CRUD views for inline sub-items (skills, projects, experiences, educations, certificates, services, testimonials)
- [x] Theme Selection activation and de-activation view
- [x] Dynamic template compiler list replication support and base-href tag injection
- [x] Comprehensive tests (4 passing test cases covering preview compilation, permissions and CRUD)

## Module 6 (AI Extra) — AI Resume Import & Portfolio Generation (COMPLETE)
- [x] ResumeUpload model + initial migrations and admin registrations
- [x] PDF/DOCX file text parser reading structure securely
- [x] Heuristic regex section-divider mapping and protocol-optional links parser
- [x] Content Enrichment generating professional summaries and SEO metadata
- [x] Drag-drop resume upload page with validation checks
- [x] JSON list review/edit editor workspace
- [x] Overwrite/merge db portfolio updates
- [x] Unit test suite containing 4 test cases

## Next: Module 8 — Live Preview
- [ ] Implement routing and serving of compiled portfolio HTML under user subdomain or custom slug
- [ ] Connect public CSS, JS, and image assets resolution pipeline
- [ ] Verify accessibility, responsive rendering, and custom fonts load on compile


## Explicitly excluded from this phase (per brief)
- GitHub Auto Publish, Payments, Premium feature-gating, Analytics

