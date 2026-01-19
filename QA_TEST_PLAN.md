# Swarm Sync - Release QA Test Plan

**Version:** 1.0  
**Last Updated:** November 19, 2025  
**Scope:** Release Candidate Validation

This document outlines the manual and automated verification steps required before deploying Swarm Sync to production. It corresponds to Section 8 of the implementation checklist.

## 🛠 Automated Checks

Run these commands first to catch basic issues early.

```bash
# 1. Run Linting & Link Checking
npm run qa

# 2. Verify Build
npm run build
```

---

## 🧪 Manual Verification Checklist

### 1. Routes & Navigation

_Verify that all pages load and routing logic works as expected._

| ID  | Test Case              | Pre-conditions | Steps              | Expected Result                                       | Status   |
| --- | ---------------------- | -------------- | ------------------ | ----------------------------------------------------- | -------- |
| 1.1 | Homepage Load          | None           | Visit `/`          | Loads < 2s, no console errors                         | 🟡       |
| 1.2 | Agents Page            | None           | Visit `/agents`    | Shows agent grid or "No agents found" (not 500 error) | 🟡       |
| 1.3 | Pricing Page           | None           | Visit `/pricing`   | Shows 5 tiers, all prices correct                     | ✅ Ready |
| 1.4 | Auth Guard (Dashboard) | **Logged OUT** | Visit `/dashboard` | Redirects to `/login`                                 | ✅ Ready |
| 1.5 | Auth Guard (Workflows) | **Logged OUT** | Visit `/workflows` | Redirects to `/login`                                 | ✅ Ready |
| 1.6 | Auth Guard (Billing)   | **Logged OUT** | Visit `/billing`   | Redirects to `/login`                                 | ✅ Ready |
| 1.7 | Console Access         | **Logged IN**  | Visit `/dashboard` | Shows dashboard with user greeting                    | 🟡       |

### 2. Links & CTAs

_Verify that all buttons and links lead to the correct destinations._

| ID  | Test Case            | Pre-conditions | Steps                                    | Expected Result                                | Status   |
| --- | -------------------- | -------------- | ---------------------------------------- | ---------------------------------------------- | -------- |
| 2.1 | Pricing: Starter     | None           | Click "Get Started Free" on Starter plan | Goes to `/register?plan=starter`               | ✅ Ready |
| 2.2 | Pricing: Plus        | None           | Click "Start Plus Plan"                  | Goes to `/register?plan=plus`                  | ✅ Ready |
| 2.3 | Pricing: Scale       | None           | Click "Contact Sales" on Scale plan      | Opens mailto with subject "Scale Plan Inquiry" | ✅ Ready |
| 2.4 | Register: Plan Badge | None           | Visit `/register?plan=pro`               | Shows "Selected Plan: Pro" badge               | ✅ Ready |
| 2.5 | Legal Links          | None           | Visit `/register`                        | "Terms" and "Privacy" links are present        | ✅ Ready |
| 2.6 | Navbar Links         | None           | Click all navbar items                   | All resolve (no 404s)                          | 🟡       |

### 3. Content & Claims

_Verify accuracy of marketing claims and compliance language._

| ID  | Test Case         | Pre-conditions | Steps                      | Expected Result                                  | Status   |
| --- | ----------------- | -------------- | -------------------------- | ------------------------------------------------ | -------- |
| 3.1 | Compliance Claims | None           | Check Footer/Security page | "SOC 2 Ready" (not Certified), "GDPR Aligned"    | ✅ Ready |
| 3.2 | Testimonials      | None           | Check Homepage/Agents      | No fake personas (Sarah Chen, etc.). Only stats. | ✅ Ready |
| 3.3 | Security Badges   | None           | Check Homepage             | Badges link to `/security`                       | ✅ Ready |

### 4. SEO & Indexation

_Verify search engine visibility settings._

| ID  | Test Case       | Pre-conditions | Steps                       | Expected Result                                            | Status   |
| --- | --------------- | -------------- | --------------------------- | ---------------------------------------------------------- | -------- |
| 4.1 | Public Indexing | None           | View source of `/`          | `meta name="robots" content="index, follow"`               | ✅ Ready |
| 4.2 | Private Noindex | None           | View source of `/dashboard` | `meta name="robots" content="noindex, nofollow"`           | ✅ Ready |
| 4.3 | Auth Noindex    | None           | View source of `/login`     | `meta name="robots" content="noindex, nofollow"`           | ✅ Ready |
| 4.4 | Sitemap         | None           | Visit `/sitemap.xml`        | Includes `/pricing`, excludes `/dashboard`                 | ✅ Ready |
| 4.5 | Canonical URL   | None           | View source of `/pricing`   | `link rel="canonical" href="https://swarmsync.ai/pricing"` | ✅ Ready |

### 5. Accessibility & UX

_Verify usability for all users._

| ID  | Test Case    | Pre-conditions | Steps                            | Expected Result                         | Status   |
| --- | ------------ | -------------- | -------------------------------- | --------------------------------------- | -------- |
| 5.1 | Keyboard Nav | None           | Press Tab repeatedly             | Focus ring visible on all links/buttons | ✅ Ready |
| 5.2 | Skip Link    | None           | Press Tab immediately after load | "Skip to main content" appears          | ✅ Ready |
| 5.3 | Form Labels  | None           | Inspect Register form            | All inputs have associated labels       | ✅ Ready |

### 6. Security Basics

_Verify fundamental security protections._

| ID  | Test Case        | Pre-conditions | Steps                       | Expected Result                                        | Status   |
| --- | ---------------- | -------------- | --------------------------- | ------------------------------------------------------ | -------- |
| 6.1 | Security Headers | None           | Inspect Network Response    | `Strict-Transport-Security`, `X-Frame-Options` present | ✅ Ready |
| 6.2 | HTTPS Redirect   | None           | Visit `http://swarmsync.ai` | Redirects to `https://`                                | 🟡 Infra |
| 6.3 | Weak Password    | None           | Try registering with "123"  | Form error: "Password must be at least 8 characters"   | ✅ Ready |

---

## 🚦 Release Decision

**GO / NO-GO Criteria:**

- [ ] All "Ready" items pass manual verification
- [ ] `npm run qa` passes with no critical errors
- [ ] Environment variables (`.env`) are configured in production
- [ ] DNS redirects for `.co` -> `.ai` are active

**Sign-off:**

- **QA Lead:** **\*\*\*\***\_\_\_\_**\*\*\*\***
- **Eng Lead:** **\*\*\*\***\_\_\_\_**\*\*\*\***
- **Date:** **\*\*\*\***\_\_\_\_**\*\*\*\***
