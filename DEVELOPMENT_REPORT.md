# Module 13 Development Report: Custom Domains

This report covers the design, implementation, testing, and verification of **Module 13: Custom Domains**.

---

## 1. Objectives & Requirements
Premium and Enterprise users are permitted to link their custom domains or subdomains to their published portfolios.
- **Plan Limits**: Free users cannot link domains. Premium users get up to 5 domains. Enterprise/Admins get unlimited (999) domains.
- **Verification Modes**: Support TXT and CNAME ownership verification methods.
- **SSL Security**: Automate white-label SSL generation status tracking (Pending → Issued → Failed).
- **Domain Middleware**: Resolves incoming HTTP requests on active custom domains and serves the compiled mapped portfolio preview seamlessly.
- **UI Panels**: List, Add, DNS setup instructions UIs matching the SaaS visual layout.
- **Tests**: Targets 60+ total passing automated tests.

---

## 2. Architecture & Design

### Models (`domains/models.py`)
- `CustomDomain`: Tracks target portfolio, domain name, subdomain prefix, provider (Namecheap, Cloudflare, GoDaddy, etc.), verification token, verification method, status choices (Pending, Verifying, Active, Failed), SSL status choices, and primary marker flag.
- `DomainVerificationLog`: Captures check history, success status, timestamp, and raw resolver responses.

### Services (`domains/services/`)
- `dns_service.py`: Provides TXT lookup (`_mock_txt_lookup`) and CNAME lookup (`_mock_cname_lookup`) functions. Uses a mock resolver for local development settings (`DOMAIN_DNS_MOCK=True`) and has hooks for real Resolver clients.
- `domain_service.py`: Handles high-level logic (validations, domain creations, primary switches, deletes, quota limits queries).

### Middleware (`domains/middleware.py`)
- `CustomDomainMiddleware`: Intercepts requests on custom domains, looks up active `CustomDomain` records matching the HTTP host, maps parameters, compiles theme templates via BeautifulSoup auto-mapping, logs traffic visits, and returns raw compiled HTML directly.

---

## 3. UI Implementation
Created templates in `templates/domains/`:
- `list.html`: Interactive list with status badges, primary toggles, SSL status indicators, disconnect confirmation modals, and limits check warning banners.
- `add.html`: Form to associate domains to portfolios, enter subdomain/root details, choose provider, and select verification method.
- `instructions.html`: Copy-to-clipboard DNS instructions with Toast notifications and logs history table.

---

## 4. Test Coverage & Verification

Added 11 comprehensive unit and integration tests in `domains/tests.py`:
1. `test_domain_validation_and_creation` — Validates structural generation and hex token sizes.
2. `test_invalid_domain_name_rejected` — Rejects bad domain formats (missing dots, double-dots).
3. `test_domain_plan_limits` — Validates role-based limits (Free=0, Premium=5, Admin=999).
4. `test_txt_verification_workflow` — Verifies successful TXT checks transition state to Active, logs entries, and auto-issues SSL.
5. `test_cname_verification_workflow` — Validates CNAME matches and status mappings.
6. `test_primary_domain_switching` — Assures setting primary clears flags on other domains.
7. `test_primary_promotion_on_deletion` — Promotes next active domain as primary if current primary is deleted.
8. `test_get_portfolio_primary_url` — Checks resolution priority chain (Custom Domain > GitHub Pages > Platform URL).
9. `test_anonymous_redirect_on_dashboard` — Restricts anonymous access.
10. `test_free_user_gated_billing` — Redirects Free tier requests to payments billing.
11. `test_premium_user_access_dashboard` — Grants access to subscribers.

### Automated Test Output
All 62 automated unit tests across all modules pass:
```
Ran 62 tests in 69.870s
OK
```

---

## 5. Deployment Gating & Security Checks
- Gated behind standard checks.
- `py manage.py check` returns `0 issues`.
- Gated security settings (SSL redirect, HSTS, secure cookies) automatically enable when `DEBUG=False`.
