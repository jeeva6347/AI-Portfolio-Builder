# API Documentation

> **Note**: The `api` app is scaffolded and reserved for a future DRF REST API module. Current functionality uses server-rendered Django views with JSON AJAX endpoints.

---

## Internal AJAX Endpoints

These endpoints are used internally by the JavaScript frontend (no authentication token required — uses session cookies).

---

### Portfolio Update API

**Endpoint**: `POST /portfolio/update/<pk>/`

**Description**: Auto-saves individual portfolio fields from the visual editor workspace.

**Authentication**: Session cookie (login required)

**Authorization**: Returns `403 Forbidden` if the portfolio does not belong to the authenticated user.

**Request Body** (form-encoded):
```
name=My Portfolio
title=Software Engineer
about=I am a developer...
tagline=Building things that matter
email=john@example.com
phone=+1-555-0100
location=San Francisco, CA
```

**Success Response** `200 OK`:
```json
{
  "success": true,
  "message": "Draft saved."
}
```

**Validation Error** `400 Bad Request`:
```json
{
  "success": false,
  "errors": {
    "email": ["Enter a valid email address."]
  }
}
```

**Unauthorized** `403 Forbidden`:
```
You do not have permission to edit this portfolio.
```

---

### Theme Scanner API

**Endpoint**: `POST /themes/admin/mapper/<pk>/scan/`

**Description**: Scans a theme's HTML and returns auto-suggested field mapping recommendations.

**Authentication**: Session cookie (admin required)

**Request Body** (JSON):
```json
{}
```

**Success Response** `200 OK`:
```json
{
  "suggestions": [
    {
      "field_key": "personal.name",
      "selector": "#main-name",
      "attribute": "text",
      "confidence": 0.95,
      "reason": "h1 element with hero-name class"
    },
    {
      "field_key": "social.github",
      "selector": ".github-link",
      "attribute": "href",
      "confidence": 0.88,
      "reason": "anchor with github.com href"
    }
  ]
}
```

---

### Theme Mapping Save API

**Endpoint**: `POST /themes/admin/mapper/<pk>/save/`

**Description**: Bulk-saves field mapping definitions for a theme mapping profile.

**Authentication**: Session cookie (admin required)

**Request Body** (JSON):
```json
{
  "fields": [
    {
      "field_key": "personal.name",
      "selector": "#main-name",
      "attribute": "text"
    },
    {
      "field_key": "social.github",
      "selector": ".github-link",
      "attribute": "href"
    }
  ]
}
```

**Success Response** `200 OK`:
```json
{
  "success": true,
  "saved": 2
}
```

---

## Portfolio Preview Endpoint

**Endpoint**: `GET /portfolio/preview/<pk>/`

**Description**: Returns compiled HTML of the portfolio with the active theme applied. Used by the iframe live preview.

**Authentication**: Login required (owner only for drafts; public for published)

**Authorization**:
- Unpublished portfolios: owner only (403 for others)
- Published portfolios: public access

**Response**: Raw HTML document (content-type: `text/html`)

---

## Sitemap Endpoint

**Endpoint**: `GET /sitemap.xml`

**Description**: Returns a dynamically generated XML sitemap listing all published portfolio URLs.

**Authentication**: None (public)

**Response**: `application/xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://yourdomain.com/portfolio/preview/1/</loc>
    <lastmod>2026-07-14</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
```

---

## Robots.txt Endpoint

**Endpoint**: `GET /robots.txt`

**Description**: Returns crawler configuration directives.

**Authentication**: None (public)

**Response**: `text/plain`
```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /billing/

Sitemap: https://yourdomain.com/sitemap.xml
```

---

## Payment Checkout Flow

> The payment system uses a mock provider in development. In production, replace with a real Stripe integration.

### 1. Initiate Checkout

**Endpoint**: `POST /billing/checkout/`

**Request Body** (form-encoded):
```
plan_slug=premium
```

**Response**: Redirect to mock checkout page with `session_id` parameter.

### 2. Complete Checkout (Mock)

**Endpoint**: `POST /billing/checkout/mock/`

**Request Body** (form-encoded):
```
session_id=<uuid>
action=success|failure
```

**Success**: Redirects to `/billing/success/` — upgrades subscription  
**Failure**: Redirects to `/billing/failure/` — leaves subscription unchanged

---

## GitHub Integration Flow

### Connect GitHub Account

**Endpoint**: `GET /github/connect/` → OAuth flow → `GET /github/callback/`

Authenticates via GitHub OAuth and stores the access token in the `GitHubRepoConfig` model.

### Publish Portfolio

**Endpoint**: `POST /github/publish/<portfolio_pk>/`

Triggers the full publish pipeline:
1. Export portfolio to static HTML package
2. Upload to GitHub repository via Git Data API
3. Enable GitHub Pages
4. Log deployment record

**Response**: Redirect to GitHub dashboard with success/error message.

---

## Portfolio Data Schema

Portfolio fields available for theme mapping:

| Field Key | Description |
|---|---|
| `personal.name` | Full name |
| `personal.title` | Job title |
| `personal.tagline` | Short tagline |
| `personal.about` | Bio/about section |
| `personal.email` | Email address |
| `personal.phone` | Phone number |
| `personal.location` | City, Country |
| `personal.avatar` | Profile photo URL |
| `social.github` | GitHub profile URL |
| `social.linkedin` | LinkedIn profile URL |
| `social.twitter` | Twitter profile URL |
| `social.website` | Personal website URL |
| `skills.list` | Skills list container |
| `skills.name` | Individual skill name |
| `skills.level` | Skill level |
| `projects.list` | Projects list container |
| `projects.title` | Project title |
| `projects.description` | Project description |
| `projects.technologies` | Technologies used |
| `projects.github_url` | Project GitHub URL |
| `projects.live_url` | Project live URL |
| `experience.list` | Experience list container |
| `experience.company` | Company name |
| `experience.position` | Job position |
| `experience.duration` | Employment period |
| `experience.description` | Role description |
| `education.list` | Education list container |
| `education.institution` | School/university name |
| `education.degree` | Degree name |
| `education.field` | Field of study |
| `education.year` | Graduation year |
| `footer.copyright` | Copyright text |
| `footer.contact_email` | Footer contact email |
