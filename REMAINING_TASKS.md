# Remaining Implementation Tasks - Infrastructure & Configuration

This document outlines the remaining tasks from the FixesNEEDED11.19.md checklist that require infrastructure configuration, deployment setup, or manual testing.

## Epic 4.1: SEO-1 — Domain Canonicalization (.co → .ai)

### Task: Configure 301 Redirects

**Status:** Requires DNS/Proxy Configuration

**Implementation Steps:**

1. **Choose Canonical Domain:** `swarmsync.ai`

2. **Configure 301 Redirects:**
   - **Option A: Vercel/Netlify Configuration**

     ```json
     // vercel.json or netlify.toml
     {
       "redirects": [
         {
           "source": "https://swarmsync.co/:path*",
           "destination": "https://swarmsync.ai/:path*",
           "permanent": true
         }
       ]
     }
     ```

   - **Option B: Next.js Middleware**

     ```typescript
     // middleware.ts
     import { NextResponse } from 'next/server';
     import type { NextRequest } from 'next/server';

     export function middleware(request: NextRequest) {
       const hostname = request.headers.get('host');

       if (hostname?.includes('swarmsync.co')) {
         const url = request.nextUrl.clone();
         url.host = 'swarmsync.ai';
         return NextResponse.redirect(url, 301);
       }

       return NextResponse.next();
     }
     ```

3. **Update Environment Variables:**

   ```bash
   # .env.production
   NEXT_PUBLIC_APP_URL=https://swarmsync.ai
   NEXT_PUBLIC_BASE_URL=https://swarmsync.ai
   ```

4. **Update DNS:**
   - Ensure both domains point to the same deployment
   - Configure SSL certificates for both domains

**Acceptance Criteria:**

- ✅ Visiting `https://swarmsync.co/pricing` redirects to `https://swarmsync.ai/pricing` with HTTP 301
- ✅ No duplicate content accessible on .co domain
- ✅ All internal links use .ai domain

---

## Epic 5: Accessibility & UX Polish

### 5.1 A11Y-1 — Keyboard Navigation & Focus States

**Status:** Requires Manual Testing & CSS Updates

**Implementation Steps:**

1. **Add Focus Styles to Global CSS:**

   ```css
   /* apps/web/src/app/globals.css */

   /* Enhanced focus styles for better visibility */
   *:focus-visible {
     outline: 2px solid var(--brass);
     outline-offset: 2px;
     border-radius: 4px;
   }

   /* Button focus states */
   button:focus-visible,
   a:focus-visible {
     outline: 2px solid var(--brass);
     outline-offset: 2px;
     box-shadow: 0 0 0 4px rgba(var(--brass-rgb), 0.1);
   }

   /* Skip to main content link */
   .skip-to-main {
     position: absolute;
     left: -9999px;
     z-index: 999;
   }

   .skip-to-main:focus {
     left: 50%;
     transform: translateX(-50%);
     top: 1rem;
     background: var(--brass);
     color: white;
     padding: 0.5rem 1rem;
     border-radius: 0.5rem;
   }
   ```

2. **Add Skip to Main Content Link:**

   ```tsx
   // In layout.tsx or navbar.tsx
   <a href="#main-content" className="skip-to-main">
     Skip to main content
   </a>
   ```

3. **Manual Testing Checklist:**
   - [ ] Tab through entire homepage - all interactive elements reachable
   - [ ] Tab through pricing page - all plan CTAs reachable
   - [ ] Tab through navigation menu - all links accessible
   - [ ] Test with screen reader (NVDA/JAWS/VoiceOver)
   - [ ] Ensure no keyboard traps
   - [ ] Verify Escape key closes modals/dropdowns

**Acceptance Criteria:**

- [ ] Full navigation flow completable with keyboard only
- [ ] Visible focus outline on all interactive elements
- [ ] No `<div onClick>` without proper role/tabindex

---

### 5.2 A11Y-2 — Color Contrast & Semantic Structure

**Status:** Requires Automated Testing & Fixes

**Implementation Steps:**

1. **Run Lighthouse Audit:**

   ```bash
   # Install Lighthouse CLI
   npm install -g lighthouse

   # Run audit
   lighthouse https://swarmsync.ai --view --only-categories=accessibility
   ```

2. **Run axe DevTools:**
   - Install axe DevTools browser extension
   - Run scan on each major page
   - Fix reported violations

3. **Common Contrast Issues to Check:**
   - Text on brass background (ensure sufficient contrast)
   - Muted text colors (ensure at least 4.5:1 ratio for body text)
   - Button text on colored backgrounds
   - Link colors in different states

4. **Semantic HTML Checklist:**
   - ✅ `<main>` wraps primary content
   - ✅ `<nav>` for navigation
   - ✅ `<header>` for page headers
   - ✅ `<footer>` for footers
   - ✅ Proper heading hierarchy (h1 → h2 → h3, no skipping)
   - [ ] `<article>` for blog posts/content
   - [ ] `<section>` for thematic groupings
   - [ ] ARIA labels where needed

**Acceptance Criteria:**

- [ ] Lighthouse accessibility score ≥ 90 on all major pages
- [ ] axe scan shows 0 critical violations
- [ ] All text meets WCAG AA contrast requirements (4.5:1 for normal text, 3:1 for large text)

---

## Epic 6: Security Headers & Form Hygiene

### 6.1 SEC-1 — Add Security Headers

**Status:** Requires Next.js Configuration

**Implementation:**

Create or update `next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains; preload',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://js.stripe.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "img-src 'self' data: https: blob:",
              "font-src 'self' https://fonts.gstatic.com",
              "connect-src 'self' https://api.swarmsync.ai https://*.stripe.com",
              "frame-src 'self' https://js.stripe.com https://hooks.stripe.com",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'self'",
              'upgrade-insecure-requests',
            ].join('; '),
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

**Testing:**

```bash
# Test security headers
curl -I https://swarmsync.ai | grep -i "strict-transport\|x-frame\|x-content\|referrer\|content-security"

# Or use online tool
# Visit: https://securityheaders.com/?q=https://swarmsync.ai
```

**Acceptance Criteria:**

- [ ] SecurityHeaders.com shows A or A+ rating
- [ ] All target headers present in response
- [ ] No mixed content warnings in browser console
- [ ] Stripe integration still works with CSP

---

### 6.2 SEC-2 — Hardening Signup & Login Forms

**Status:** Partially Implemented (needs backend work)

**Frontend Implementation:**

1. **Add Privacy Policy & Terms Links:**

   ```tsx
   // In RegisterForm component
   <p className="text-xs text-muted-foreground text-center mt-4">
     By creating an account, you agree to our{' '}
     <Link href="/terms" className="text-brass hover:underline">
       Terms of Service
     </Link>{' '}
     and{' '}
     <Link href="/privacy" className="text-brass hover:underline">
       Privacy Policy
     </Link>
   </p>
   ```

2. **Enhanced Password Validation:**
   ```typescript
   // Already implemented in schema, but ensure it's enforced
   password: z.string()
     .min(8, 'Password must be at least 8 characters')
     .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
     .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
     .regex(/[0-9]/, 'Password must contain at least one number')
     .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character'),
   ```

**Backend Requirements (API team):**

- [ ] Implement CSRF token generation and validation
- [ ] Add rate limiting on `/api/auth/register` and `/api/auth/login`
- [ ] Implement account lockout after failed attempts
- [ ] Add email verification flow
- [ ] Log authentication attempts

**Acceptance Criteria:**

- [ ] CSRF protection active on auth forms
- [ ] Weak passwords rejected (< 8 chars, no complexity)
- [ ] Rate limiting prevents brute force (max 5 attempts per 15 min)
- [ ] Privacy Policy and Terms links visible on register page

---

## Epic 7: Monitoring & Automated Checks

### 7.1 MON-1 — Add Automated Link Checker to CI

**Status:** Requires CI/CD Configuration

**Implementation:**

1. **Install Link Checker:**

   ```bash
   npm install --save-dev broken-link-checker
   ```

2. **Create Link Check Script:**

   ```javascript
   // scripts/check-links.js
   const { SiteChecker } = require('broken-link-checker');

   const siteChecker = new SiteChecker(
     {
       excludeExternalLinks: false,
       filterLevel: 3,
       honorRobotExclusions: false,
     },
     {
       error: (error) => {
         console.error('Error:', error);
         process.exit(1);
       },
       link: (result) => {
         if (result.broken) {
           console.error(`Broken link found: ${result.url.original}`);
           console.error(`  On page: ${result.base.original}`);
           console.error(`  Reason: ${result.brokenReason}`);
           process.exitCode = 1;
         }
       },
       end: () => {
         console.log('Link check complete');
         if (process.exitCode === 1) {
           process.exit(1);
         }
       },
     },
   );

   const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
   siteChecker.enqueue(baseUrl);
   ```

3. **Add to package.json:**

   ```json
   {
     "scripts": {
       "check-links": "node scripts/check-links.js"
     }
   }
   ```

4. **Add to CI Pipeline:**
   ```yaml
   # .github/workflows/ci.yml
   - name: Check for broken links
     run: |
       npm run build
       npm run start &
       sleep 10
       npm run check-links
   ```

**Acceptance Criteria:**

- [ ] CI has link-check step
- [ ] Broken internal link causes build failure
- [ ] External links are checked but don't fail build

---

### 7.2 MON-2 — Add Uptime & Error Logging

**Status:** Requires Third-Party Service Setup

**Recommended Services:**

1. **Uptime Monitoring:**
   - **UptimeRobot** (Free tier available)
     - Monitor: `/`, `/agents`, `/pricing`, `/dashboard`, `/api/health`
     - Check interval: 5 minutes
     - Alert via email/Slack on downtime

   - **Pingdom** (Paid)
     - More advanced monitoring
     - Performance metrics
     - Real user monitoring

2. **Error Logging:**
   - **Sentry** (Recommended)

     ```bash
     npm install @sentry/nextjs
     npx @sentry/wizard -i nextjs
     ```

     ```typescript
     // sentry.client.config.ts
     import * as Sentry from '@sentry/nextjs';

     Sentry.init({
       dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
       environment: process.env.NODE_ENV,
       tracesSampleRate: 0.1,
       beforeSend(event) {
         // Filter out sensitive data
         if (event.request) {
           delete event.request.cookies;
         }
         return event;
       },
     });
     ```

   - **Alternative: Datadog, LogRocket, or built-in cloud logging**

**Setup Steps:**

1. **UptimeRobot:**
   - Sign up at uptimerobot.com
   - Add monitors for key URLs
   - Configure alert contacts
   - Set up status page (optional)

2. **Sentry:**
   - Create Sentry project
   - Install SDK
   - Add DSN to environment variables
   - Configure error boundaries in React components

**Acceptance Criteria:**

- [ ] Uptime monitoring active for 5+ key routes
- [ ] Alerts configured for downtime (email/Slack)
- [ ] Error logging captures stack traces
- [ ] Error logs include user context (non-PII)
- [ ] Dashboard shows uptime % and error rates

---

## Summary of Required Actions

### Immediate (Can be done now):

1. ✅ Update environment variables for canonical domain
2. ✅ Add security headers to next.config.js
3. ✅ Add Terms & Privacy links to register form
4. ✅ Create link checker script

### Requires Deployment:

1. Configure 301 redirects at DNS/proxy level
2. Deploy with updated next.config.js
3. Verify security headers in production

### Requires Manual Testing:

1. Keyboard navigation audit
2. Screen reader testing
3. Lighthouse accessibility audit
4. axe DevTools scan

### Requires Third-Party Setup:

1. UptimeRobot or Pingdom account
2. Sentry account and configuration
3. CI/CD pipeline updates

### Requires Backend Work:

1. CSRF token implementation
2. Rate limiting on auth endpoints
3. Email verification flow

---

## Next Steps

1. **Review this document** with the team
2. **Prioritize tasks** based on impact and effort
3. **Assign owners** for each epic
4. **Set deadlines** for completion
5. **Schedule testing** sessions for accessibility
6. **Configure monitoring** services
7. **Update deployment** pipeline with security headers

All code-level implementations that could be done have been completed. The remaining tasks require infrastructure access, deployment configuration, or manual testing that cannot be automated through code changes alone.
