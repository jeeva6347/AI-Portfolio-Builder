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

## Next: Module 6 — Theme Mapper
- [ ] Visual section mapper: connect theme HTML sections to portfolio data fields
- [ ] Map `{{name}}`, `{{bio}}`, `{{projects}}` etc. to user profile fields
- [ ] Store mapping config per theme in DB
- [ ] Preview with real user data injected

## Then: Modules 7-9

## Explicitly excluded from this phase (per brief)
- Portfolio Builder logic, GitHub Auto Publish, Payments, Premium
  feature-gating, AI, Analytics, Resume Import
