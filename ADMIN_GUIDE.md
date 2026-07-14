# AI Portfolio Builder — Administrator Guide

Welcome to the **Administrator Guide**. This guide details platform management operations for Super Admins and Platform Admins.

---

## 1. Role-Based Access Controls
- **Super Admin**: Full database access, user roles promotions/demotions, revenue reports, systems configurations.
- **Admin (Platform Admin)**: Manage templates marketplace, review theme uploads, delete spam portfolios, support tickets.

---

## 2. Managing the Theme Marketplace
Admins and Super Admins manage public themes:
1. Navigate to **Admin Dashboard** -> **Manage Themes**.
2. **Review Uploads**:
   - Platform designers upload ZIP archives.
   - Click **Review** to check layout contents in a sandboxed preview iframe.
   - Select **Approve** (marks theme as active and publishes to marketplace) or **Reject** (returns feedback to designer).
3. **Category Management**:
   - Create design categories (e.g. Modern, Minimal, Creative, Corporate) with slugs.

---

## 3. Subscription & Billing Plans Setup
Super Admins configure plan limits inside the Django Admin panel:
1. Open the Django Admin at `/admin/` and navigate to **Subscription Plans**.
2. Define Plan Tiers (e.g., Free, Premium, Enterprise):
   - **Portfolio Limit**: Max portfolios a user can create.
   - **AI Usage Limit**: Max resume uploads.
   - **GitHub Publish Limit**: Max publishing actions.
   - **Custom Branding Removal**: Toggle if footer branding is hidden.
   - **Team Access**: Toggle organization creation.
   - **Price**: Decimal monthly amount.

---

## 4. User and Organization Audits
To inspect and manage platform signups:
1. Go to the **Super Admin Dashboard** to view total user registrations growth and theme usage distribution.
2. Search user tables by username or email.
3. Manage organizations list, audit activity logs, or check linked domains.
4. Escalate roles safely via the Django Admin panel under user accounts.
