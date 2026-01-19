# Swarm Sync - Fixes Needed (11.19)

## 1. Epic: Route stability & authentication

### 1.1 ROUTE-1 — Gate /dashboard behind auth

**Type:** Story

**Description:**
Ensure /dashboard is only accessible to authenticated users. Anonymous visitors should be redirected to /login (or a public demo route if you explicitly want a demo).

**Implementation Notes:**

- [x] Use a central session check (e.g., getServerSession with NextAuth or your current auth framework)
- [x] If no valid session: redirect('/login?from=dashboard')
- [ ] If you want a demo: move the current public dashboard to /dashboard-demo and clearly label it "Demo data"

**Acceptance Criteria:**

- [x] Visiting /dashboard while not logged in always redirects to /login
- [x] Visiting /dashboard while logged in shows the real user dashboard, not hard-coded "Good morning, Ben"
- [x] No SEO index of /dashboard (meta noindex present or route excluded from sitemap)

---

### 1.2 ROUTE-2 — Fix /workflows 500 error & add graceful fallback

**Type:** Story

**Description:**
/workflows currently returns a 500. Implement a minimal workflows page that either shows real workflows or a friendly, non-error empty state.

**Implementation Notes:**

- [x] Wrap data fetch in try/catch and show an "unavailable right now" component on failure
- [x] If workflows feature is not ready, show "Coming Soon" with explanation instead of hitting broken API

**Acceptance Criteria:**

- [x] /workflows returns HTTP 200 for logged-in users
- [x] When API is down, user sees a friendly "Workflows temporarily unavailable" message (no unhandled stack trace)
- [x] "Launch orchestration studio" links from /dashboard and nav point to a working route (or are hidden if feature is not yet available)

---

### 1.3 ROUTE-3 — Stabilize /login route

**Type:** Story

**Description:**
Ensure /login reliably returns 200 and displays login UI for all users/geos without server disconnects.

**Implementation Notes:**

- [x] Confirm routing (App Router vs Pages Router) is correct and handler doesn't crash
- [x] Handle missing env vars, provider misconfig, or DB failures with user-friendly error

**Acceptance Criteria:**

- [x] /login reachable from nav and deep link
- [x] Browser network tab shows 200 OK
- [x] On error (e.g., identity provider down), user sees clear message, not a blank page or raw error

---

### 1.4 ROUTE-4 — Auth gate for /billing, /quality, /agents/new

**Type:** Story

**Description:**
Ensure internal console routes (/billing, /quality, /agents/new) are accessible only when authenticated and display clean empty states instead of "API unavailable".

**Implementation Notes:**

- [x] Same session gate pattern as /dashboard
- [x] Replace "Billing data is unavailable right now…" with:
  - Auth + success: show billing data
  - Auth + no billing data: "No invoices yet" empty state
- [x] /agents/new should have a working "Go to login" link if accessed without session

**Acceptance Criteria:**

- [x] Anonymous visitors to these routes are redirected to /login
- [x] Logged-in users see either real data or a clean empty state
- [x] No raw "API unreachable" message in normal operation

---

## 2. Epic: Clean up compliance & testimonials (trust hygiene)

### 2.1 TRUST-1 — Update SOC 2 / GDPR / uptime claims

**Type:** Story

**Description:**
Replace or qualify current security/compliance badges (SOC 2 Type II Certified, GDPR Compliant, 99.9% SLA) with language that matches actual state and add a Security & Compliance page.

**Implementation Notes:**

- [x] If SOC 2 Type II is not yet completed: change copy to "SOC 2–aligned controls" / "SOC 2-ready"
- [x] Update uptime badge to something like "Target 99.9% uptime" and link to SLA/status page once ready
- [x] Add /security page with explanation of:
  - [x] Encryption in transit/at rest
  - [x] Data retention
  - [x] Data residency (if applicable)
  - [x] Audit/logging approach

**Acceptance Criteria:**

- [x] No public copy uses the word "Certified" unless you have an actual report and process to share under NDA
- [x] Every security/compliance badge links to /security or relevant docs
- [ ] External review of copy by someone with legal/compliance awareness

---

### 2.2 TRUST-2 — Replace synthetic testimonials with real or clearly labeled ones

**Type:** Story

**Description:**
Current testimonials (names + companies) appear unverified. Replace with real customer quotes or transparently-labeled examples.

**Implementation Notes:**

- [ ] Option A: Replace with real customers + logos (with written permission)
- [x] Option B: Remove for now and use data-driven "outcome stats" (e.g., "Teams reduced audit time by 38% in internal benchmarks")
- [ ] Option C: Clearly label as "Example scenario based on internal testing" with no fake people/companies

**Acceptance Criteria:**

- [x] No testimonial on the site is tied to a fabricated person/company
- [x] Every logo/quote has a real underlying customer or is clearly marked an example

---

## 3. Epic: Pricing & plans UX

### 3.1 PRICE-1 — Implement real /pricing page

**Type:** Story

**Description:**
Replace the "Pricing information is currently unavailable" placeholder with a real, usable pricing page.

**Pricing Tiers:**

#### FREE (Starter Swarm) - $0/month

**Perfect for:** Testing, individual developers, hobbyists

**Limits:**

- [x] 3 agents in swarm
- [x] $25 A2A transaction credit/month (resets monthly)
- [x] 20% platform fee
- [x] 100 swarm transactions/month
- [x] 1 user seat
- [x] 5GB storage
- [x] Community support only

**Features:**

- [x] ✅ Basic swarm deployment
- [x] ✅ Agent discovery
- [x] ✅ Simple A2A payments
- [x] ✅ Basic analytics dashboard
- [x] ✅ API access (rate limited)

---

#### PLUS - $29/month ($290/year - save $58)

**Perfect for:** Solo founders, small projects, side hustles

**Limits:**

- [x] 10 agents in swarm
- [x] $200 A2A transaction credit/month
- [x] 18% platform fee ⬇️
- [x] 500 swarm transactions/month
- [x] 1 user seat
- [x] 25GB storage
- [x] Email support (48hr response)

**Features:**

- [x] ✅ Everything in Free
- [x] ✅ Advanced analytics
- [x] ✅ Webhook notifications
- [x] ✅ Custom agent metadata
- [x] ✅ Transaction history export
- [x] ✅ Slack integration
- [x] 🆕 Swarm templates (pre-built workflows)

---

#### GROWTH - $99/month ($990/year - save $198)

**Perfect for:** Startups, growing teams, serious builders

**Limits:**

- [x] 50 agents in swarm
- [x] $1,000 A2A transaction credit/month
- [x] 15% platform fee ⬇️⬇️
- [x] 3,000 swarm transactions/month
- [x] 5 user seats
- [x] 100GB storage
- [x] Priority email support (24hr response)

**Features:**

- [x] ✅ Everything in Plus
- [x] ✅ Swarm orchestration builder (visual workflows)
- [x] ✅ A/B testing for agents
- [x] ✅ Performance benchmarking
- [x] ✅ Advanced agent discovery filters
- [x] ✅ Custom branding (white-label reports)
- [x] 🆕 Agent reputation tracking
- [x] 🆕 Budget management tools
- [x] 🆕 Zapier/Make.com integration
- [x] 🆕 Swarm analytics (collaboration insights)

---

#### PRO - $199/month ($1,990/year - save $398)

**Perfect for:** Growing companies, agencies, B2B SaaS

**Limits:**

- [x] 200 agents in swarm
- [x] $5,000 A2A transaction credit/month
- [x] 12% platform fee ⬇️⬇️⬇️
- [x] 15,000 swarm transactions/month
- [x] 15 user seats
- [x] 500GB storage
- [x] Priority support (12hr response)
- [x] 1 dedicated support session/month

**Features:**

- [x] ✅ Everything in Growth
- [x] ✅ Multi-swarm management (separate swarms for different projects)
- [x] ✅ Advanced orchestration (conditional logic, loops, error handling)
- [x] ✅ Custom agent certifications
- [x] ✅ SLA guarantees (99.9% uptime)
- [x] 🆕 Team collaboration tools (roles, permissions)
- [x] 🆕 Private agent library (internal agents only)
- [x] 🆕 Advanced fraud detection
- [x] 🆕 Custom integrations (API partnership)
- [x] 🆕 Quarterly business reviews

---

#### SCALE - $499/month ($4,990/year - save $998)

**Perfect for:** Mid-market companies, high-volume users

**Limits:**

- [x] 1,000 agents in swarm
- [x] $25,000 A2A transaction credit/month
- [x] 10% platform fee ⬇️⬇️⬇️⬇️
- [x] 100,000 swarm transactions/month
- [x] 50 user seats
- [x] 2TB storage
- [x] Premium support (4hr response)
- [x] Weekly dedicated support sessions

**Features:**

- [x] ✅ Everything in Growth
- [x] ✅ SSO/SAML integration
- [x] ✅ Advanced security (2FA, IP whitelisting)
- [x] ✅ Custom SLA agreements
- [x] ✅ Dedicated account manager
- [x] ✅ Priority feature requests
- [x] 🆕 On-premise deployment option (additional cost)
- [x] 🆕 Custom contract terms
- [x] 🆕 Audit logs & compliance reports
- [x] 🆕 Dedicated infrastructure (optional)
- [x] 🆕 White-label platform option
- [x] 🆕 Revenue share optimization tools

---

**Acceptance Criteria:**

- [x] /pricing has ~300–800 words of unique content, multiple headings, and at least one CTA
- [x] All "View Membership Pricing / View Membership Plans" CTAs lead to this page
- [x] No dead-end "check back later" messaging remains

---

### 3.2 PRICE-2 — Wire plan selection into onboarding

**Type:** Story

**Description:**
Connect /pricing selections to signup or sales flow (even if it's just a prefilled contact form).

**Implementation Notes:**

- [ ] Clicking a plan:
  - For self-serve: open /register?plan={id} or in-app upgrade flow
  - For enterprise: open a contact form with "Plan of interest" prefilled

**Acceptance Criteria:**

- [ ] Selecting any priced plan leads the user into a clear next step (trial, signup, or contact form)
- [ ] No dead CTAs that just scroll or do nothing

---

## 4. Epic: SEO, canonicalization & crawl health

### 4.1 SEO-1 — Choose canonical domain (.ai) and 301 redirect .co → .ai

**Type:** Story

**Description:**
Consolidate SEO authority by selecting swarmsync.ai as canonical domain and redirecting all .co traffic to .ai.

**Implementation Notes:**

- [ ] Configure 301s at DNS/proxy or app level: https://swarmsync.ai/* → https://swarmsync.ai/$1
- [ ] Update environment configs (NEXT_PUBLIC_BASE_URL, etc.)

**Acceptance Criteria:**

- [ ] Visiting any swarmsync.ai URL redirects to the equivalent .ai path with HTTP 301
- [ ] No duplicate content accessible on swarmsync.ai

---

### 4.2 SEO-2 — Add canonical tags & robots.txt / sitemap.xml

**Type:** Story

**Description:**
Make crawl intent explicit and avoid duplicate content issues.

**Implementation Notes:**

- [x] Add `<link rel="canonical" href="https://swarmsync.ai/...">` on all pages
- [x] Create https://swarmsync.ai/robots.txt with:
  - User-agent: \*
  - Allow rules
  - Sitemap: https://swarmsync.ai/sitemap.xml
- [x] Generate sitemap.xml including key marketing pages:
  - [x] /
  - [x] /agents
  - [x] /pricing
  - [x] /security (once created)

**Acceptance Criteria:**

- [x] robots.txt and sitemap.xml accessible and valid
- [x] Canonical tag present on all rendered pages
- [ ] Search Console recognizes sitemap

---

### 4.3 SEO-3 — Mark app-only routes as noindex

**Type:** Story

**Description:**
Prevent internal console views from being indexed by search engines.

**Implementation Notes:**

- [x] Add meta robots tags or headers:
  - noindex, nofollow on /dashboard, /billing, /quality, /workflows, /login, /register, /agents/new

**Acceptance Criteria:**

- [x] Page source for those routes includes content="noindex, nofollow"
- [ ] After re-crawl, they no longer show up in search results over time

---

## 5. Epic: Accessibility & UX polish

### 5.1 A11Y-1 — Keyboard navigation & focus states

**Type:** Story

**Description:**
Ensure all critical navigation and controls are reachable and operable via keyboard, with visible focus states.

**Implementation Notes:**

- [ ] Verify all buttons/links are `<button>` or `<a>` with proper href
- [ ] Add CSS focus styles that are clearly visible
- [ ] Remove click handlers from non-interactive elements (e.g. `<div onClick=...>`)

**Acceptance Criteria:**

- [ ] Full nav and CTA flow can be completed using only keyboard (Tab/Shift+Tab + Enter/Space)
- [ ] Visible focus outline on all interactive elements

---

### 5.2 A11Y-2 — Color contrast & semantic structure

**Type:** Story

**Description:**
Meet WCAG AA contrast and semantic requirements for text and UI elements.

**Implementation Notes:**

- [ ] Run automated checks with Lighthouse / axe
- [ ] Fix any reported contrast issues (buttons, text on colored backgrounds)
- [ ] Ensure pages use `<main>`, `<nav>`, `<header>`, `<footer>` where appropriate

**Acceptance Criteria:**

- [ ] Lighthouse accessibility score ≥ 90 on main pages
- [ ] axe scan shows no critical violations

---

## 6. Epic: Security headers & form hygiene

### 6.1 SEC-1 — Add CSP, HSTS & basic security headers

**Type:** Story

**Description:**
Harden Swarm Sync's HTTP responses with standard security headers.

**Implementation Notes:**

- [ ] Configure:
  - [ ] Content-Security-Policy (restrict scripts, images, frames to expected origins)
  - [ ] Strict-Transport-Security (HSTS)
  - [ ] X-Content-Type-Options: nosniff
  - [ ] Referrer-Policy: strict-origin-when-cross-origin
  - [ ] X-Frame-Options: DENY (or SAMEORIGIN if you need iframes)

**Acceptance Criteria:**

- [ ] SecurityHeaders.com (or similar) shows all target headers present
- [ ] No mixed content warnings

---

### 6.2 SEC-2 — Hardening signup & login forms

**Type:** Story

**Description:**
Ensure /register and /login forms use CSRF protection, strong password validation, and basic abuse prevention.

**Implementation Notes:**

- [ ] Add CSRF tokens
- [ ] Enforce minimal password strength (length + complexity)
- [ ] Add server-side rate limiting on auth endpoints
- [ ] Add links to Privacy Policy and Terms near forms

**Acceptance Criteria:**

- [ ] CSRF token required for form submission
- [ ] Weak passwords are rejected
- [ ] Legal links visible to user before account creation

---

## 7. Epic: Monitoring and automated link checking

### 7.1 MON-1 — Add automated link checker to CI

**Type:** Story

**Description:**
Run a link checker on each deployment to avoid regressions in links/assets.

**Implementation Notes:**

- [ ] Use a CLI crawler (e.g. lychee, broken-link-checker, or custom script) in CI
- [ ] Crawl from / with host restriction
- [ ] Fail build on new 404s / 5xx for internal links

**Acceptance Criteria:**

- [ ] CI pipeline has a "link-check" step
- [ ] A deliberate introduction of a broken internal link causes CI to fail

---

### 7.2 MON-2 — Add simple uptime & error logging

**Type:** Story

**Description:**
Monitor uptime and server errors for key routes (/, /agents, /pricing, /dashboard, /workflows).

**Implementation Notes:**

- [ ] Use a monitoring service (Pingdom, UptimeRobot, or your infra's equivalent)
- [ ] Log app errors to a centralized service (Sentry, Datadog, etc.)

**Acceptance Criteria:**

- [ ] Alerts configured for uptime drops and repeated 5xx on key routes
- [ ] Error logs show stack traces and environment info for debugging

---

## 8. QA Checklist (for each release)

### 8.1 Routes & navigation

- [ ] / loads without errors on desktop and mobile
- [ ] /agents loads and shows either real agents or a clear empty state
- [ ] /pricing shows real plans or intentional "Talk to sales" explanation (not "check back later")
- [ ] /dashboard, /billing, /quality, /workflows, /agents/new redirect to /login when not authenticated
- [ ] /dashboard, /billing, /quality, /workflows work as expected when logged in
- [ ] /login and /register load without network/server errors

### 8.2 Links & CTAs

- [ ] All nav links resolve with HTTP 200 (or 3xx redirects where expected)
- [ ] All primary CTAs ("View Membership Pricing", "Start Free Trial", "Launch orchestration studio") perform a meaningful action
- [ ] No `<a>` elements with empty or # hrefs used for primary navigation
- [ ] External links that open new tabs use rel="noopener noreferrer"

### 8.3 Content & claims

- [x] No mention of "SOC 2 Type II Certified" or "99.9% uptime SLA" unless formal documentation and process exist
- [x] Security/compliance section exists and accurately describes current reality
- [x] Testimonials are either real and approved or clearly labeled as examples
- [ ] Domain canonicalization works: .co redirects to .ai with 301

### 8.4 SEO & indexation

- [x] `<title>` and meta description are set and unique per public page
- [x] robots.txt and sitemap.xml respond with 200 and valid content
- [x] App-only routes return noindex, nofollow in meta robots
- [ ] Lighthouse SEO score ≥ 90 on homepage and /pricing

### 8.5 Accessibility & UX

- [ ] All critical flows can be completed via keyboard only
- [x] Focus states are visible on nav and CTAs
- [ ] Color contrast passes WCAG AA for text and buttons
- [ ] Lighthouse accessibility score ≥ 90 on main pages

### 8.6 Security basics

- [x] CSP, HSTS, and basic security headers present on all pages
- [ ] Signup/login forms contain CSRF tokens and are rejected if token missing/invalid
- [x] Weak passwords are rejected
- [x] Privacy Policy and Terms are linked from any page with signup forms

### 8.7 Monitoring & regression

- [x] CI link checker passes with zero internal 404/5xx
- [ ] Monitoring service shows all key routes up after deploy
- [ ] No new errors in error-logging dashboard after a smoke test
