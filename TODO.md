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

## Next: Module 5-8 — Theme Engine & Marketplace
- [ ] Support uploading `theme.zip` (index.html, style.css, script.js, assets)
- [ ] Extract, validate, and store theme files
- [ ] Visual Theme Mapper (map sections to dynamic data)
- [ ] Theme Marketplace for users to browse and select

## Then: Modules 5-9 — Theme Engine, Marketplace, Categories, Preview, DB polish
## Then: Module 10 — UI pass (dark mode, animations, toasts, skeletons)

## Explicitly excluded from this phase (per brief)
- Portfolio Builder logic, GitHub Auto Publish, Payments, Premium
  feature-gating, AI, Analytics, Resume Import
