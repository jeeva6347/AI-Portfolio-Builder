# TODO

## Module 1 — Authentication (COMPLETE)
- [x] Custom User model with 4 roles (Super Admin/Admin/Premium/Free)
- [x] Email signup + login, with Remember Me
- [x] Google OAuth, GitHub OAuth
- [x] Forgot / reset password
- [x] Email verification (via allauth, ACCOUNT_EMAIL_VERIFICATION=optional by default — set to "mandatory" in .env for production)
- [x] Profile picture
- [x] Session management (list + revoke-others)
- [x] Role-based dashboard redirect stub
- [x] End-to-end tested: signup, login, logout, password reset round trip, profile access, session listing — all verified live, not just read through.

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

## Module 8 — Live Preview & Visual Portfolio Editor (COMPLETE)
- [x] Multi-portfolio database relationship refactoring (ForeignKey + status migration)
- [x] Multi-portfolio management dashboard listing panel (Drafts, Published, Archived)
- [x] Visual editor workspace: Left Editing Panel and Right Live Preview viewport
- [x] Viewport size responsive controllers (Desktop, Laptop, Tablet, Mobile) and CSS transform-based zoom scale managers
- [x] Debounced autosave script asynchronously committing updates via PortfolioUpdateAPI AJAX
- [x] Seamless iframe refreshing by fetching fresh compiled HTML layouts and document-writing
- [x] Duplicate portfolio action deep-copying properties and child list records
- [x] Security permissions: restricted visual editor and unpublished previews to portfolio owner
- [x] Expanded automated test suite by adding 4 comprehensive tests (18 tests total)

## Module 9 — GitHub Auto Publish & GitHub Pages Deployment (COMPLETE)
- [x] Reusable service layer under `github_integration/services/` (oauth, repository, exporter, deployment, pages)
- [x] Mapped database configs `GitHubRepoConfig` and deployment history records `GitHubDeployment`
- [x] Static site package exporter converter (copies media assets to package and rewrites references dynamically)
- [x] In-memory Git Data REST API pushes (blobs uploads, parent trees referencing, commit creations, branch ref updates)
- [x] Enable and verify GitHub Pages hosting
- [x] Connect/disconnect OAuth profile integrations and unlinking repos without deleting files
- [x] Visual deployment management dashboard panel (status badge, build log warning checklist, version tracking)
- [x] Mock integrations unit tests inside tests.py (22 tests total passing OK)

## Module 10 — SaaS Subscription & Payments (COMPLETE)
- [x] Reusable `SubscriptionPlan` model with dynamic database admin editable limits
- [x] Provisioned automatic Free subscription and UsageMetrics profile on account creations
- [x] Modular provider services (`BasePaymentProvider`, `MockPaymentProvider`) initiating checkouts
- [x] Reusable permission checks (`PortfolioLimitMixin`, `AILimitMixin`, `GitHubPublishLimitMixin`) gating views
- [x] High-fidelity user billing dashboard template tracking limits usage percentages and disk size occupied
- [x] Mock Stripe checkout session screen simulating Paid upgrade activations
- [x] Admin console summaries card panel displaying subscribers count splits and revenues
- [x] Added 7 payments mock unit tests (29 tests total passing OK)

## Module 11 — Analytics, SEO & Performance (COMPLETE)
- [x] Mapped `PortfolioVisit`, `PortfolioMetric`, and `PortfolioSEO` database models with automatic signals
- [x] Parsed browser user-agents, device categories, referrers, and geography in `tracking_service.py`
- [x] Created BeautifulSoup filter parser injecting dynamic meta descriptors, titles overrides, Open Graph, and favicons
- [x] Written `performance_service.py` calculating theme css, js, and images size weight penalty suggestions
- [x] Designed premium traffic analytics metrics dashboard including 30-day Chart.js line charts
- [x] Implemented interactive SEO editor form featuring robots crawler rules and SERP Google/Social share mock cards
- [x] Implemented speedometer gauges scorecards on speed diagnostics templates
- [x] Mounted dynamic XML sitemaps generator at `/sitemap.xml` and plain text robot parameters at `/robots.txt`
- [x] Expanded tests suite by adding 7 comprehensive tests (36 unit tests total passing OK)

## Module 12 — Production Stabilization & Code Quality (COMPLETE)
- [x] Fixed 3 failing test assertions (login page text, dashboard heading, 403 vs 404 permission check)
- [x] Fixed `PortfolioUpdateAPI` to return `403 Forbidden` instead of `404 Not Found` for unauthorized access
- [x] Eliminated N+1 query in `AnalyticsDashboardView` (used `prefetch_related("metric", "seo")`)
- [x] Eliminated N+1 aggregation in `UserDashboardView` (used Django `.aggregate()`)
- [x] Configured production security settings (HSTS, SSL redirect, secure cookies)
- [x] Set up API, Architecture, deployment, and contributing guidelines documentation

## Module 13 — Custom Domains (COMPLETE)
- [x] Created CustomDomain and DomainVerificationLog models and applied migrations
- [x] Built TXT and CNAME DNS lookup service checkers with mock resolvers for local dev environments
- [x] Set up SSL check hook simulators (auto transitions active domains to HTTPS SSL issued status)
- [x] Created CustomDomainMiddleware handling routing and compiling resolved portfolio pages
- [x] Mapped domains list, adding form, instructions instructions setup guides, verify retry checks, make primary and deletion actions
- [x] Increased test coverage to 62 passing automated tests (added 11 tests)

## Module 14 — Team Collaboration & Organization Workspace (COMPLETE)
- [x] Implemented Organization, OrganizationMember, Invitation, and ActivityLog database models
- [x] Developed modular `org_service.py` orchestrating team actions (creations, role changes, leaves, invites, deletes, transfers)
- [x] Refactored all portfolio views and sub-item actions to use custom permission checker helper (`get_portfolio_for_user`)
- [x] Designed organizational listings, setup create form, multi-tab dashboard workspace, and accept invite review panels
- [x] Injected activity logging and mock email notifications support triggers
- [x] Added 13 automated tests inside `organizations/tests.py` bringing the total passing tests count to 75 tests

## Next: Module 15 — PDF Portfolio Export
- [ ] Mapped PDF renderer service configuration
- [ ] Export portfolio layout template as compiled static PDF download
