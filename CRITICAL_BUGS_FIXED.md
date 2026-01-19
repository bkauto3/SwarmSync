# 🔧 Critical Bugs Fixed - December 4, 2025

## ✅ Bug #1: View Profile Links Fixed

### Problem

- Clicking "View Profile" on agent cards was failing
- Agent detail pages were returning 404 errors
- Root cause: Incorrect API URL configuration in production

### Solution

**File: `apps/web/.env.local`**

- Changed `NEXT_PUBLIC_API_URL` from `https://api.swarmsync.ai` to `https://swarmsync-api.up.railway.app`
- This ensures the frontend correctly communicates with the Railway backend API

### Verification

- Agent profile route: `/agents/[slug]/page.tsx` ✅ Exists
- API endpoint: `GET /agents/slug/:slug` ✅ Implemented
- Server-side client: Uses correct Railway URL ✅ Configured
- Client-side API: Now uses correct Railway URL ✅ Fixed

### How It Works Now

1. User clicks "View Profile" on agent card
2. Frontend navigates to `/agents/{slug}`
3. Server-side page component calls `getAgentMarketClient().getAgentBySlug(slug)`
4. SDK makes request to `https://swarmsync-api.up.railway.app/agents/slug/{slug}`
5. Backend returns agent data
6. Page renders with full agent details

---

## ✅ Bug #2: Stripe Checkout Fixed

### Problem

- Clicking "Subscribe" buttons on pricing page was failing
- Stripe checkout sessions were not being created
- Root causes:
  1. Missing Stripe Price IDs for Plus plan in backend `.env`
  2. Pricing page was using TEST Stripe links instead of API-generated checkout sessions

### Solution

**File: `apps/api/.env`**

- Added missing environment variables:
  ```
  PLUS_SWARM_SYNC_TIER_PRICE_ID=price_1SSlyTPQdMywmVkHgz2Wk5gD
  PLUS_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbBXYZ123ABC
  ```

**File: `apps/web/src/app/pricing/page.tsx`**

- Removed hardcoded TEST Stripe links
- Changed all `stripeLink` values from test URLs to `'stripe'` flag
- This ensures CheckoutButton component uses API to create checkout sessions

### How It Works Now

1. User clicks "Checkout with Stripe" button
2. CheckoutButton calls `billingApi.createCheckoutSession(planSlug, successUrl, cancelUrl)`
3. Frontend API client makes POST to `https://swarmsync-api.up.railway.app/billing/subscription/checkout`
4. Backend billing service:
   - Looks up plan by slug
   - Gets Stripe Price ID from environment variables
   - Creates Stripe checkout session with correct price
   - Returns checkout URL
5. Frontend redirects user to Stripe checkout
6. After payment, Stripe redirects to success/cancel URL
7. Webhook handler processes payment and activates subscription

### Stripe Configuration Required

The following environment variables must be set in production (Railway):

```
PLUS_SWARM_SYNC_TIER_PRICE_ID=price_1SSlyTPQdMywmVkHgz2Wk5gD
PLUS_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbBXYZ123ABC
GROWTH_SWARM_SYNC_TIER_PRICE_ID=price_1SSlzkPQdMywmVkHXJSPjysl
GROWTH_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbCgvrkT8zgem
SCALE_SWARM_SYNC_TIER_PRICE_ID=price_1SSm0GPQdMywmVkHAb9V3Ct7
SCALE_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbCXg63wEQ5oE
PRO_SWARM_SYNC_TIER_PRICE_ID=price_1SSm3XPQdMywmVkH0Umdoehb
PRO_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbGlQTQ8dQY9G
```

---

## 🚀 Deployment Instructions

### 1. Deploy Frontend (Netlify)

```bash
# Update environment variables in Netlify dashboard
NEXT_PUBLIC_API_URL=https://swarmsync-api.up.railway.app
NEXT_PUBLIC_APP_URL=https://swarmsync.ai
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_51RyJPcPQdMywmVkHwdLQtTRV8YV9fXjdJtrxEwnYCFTn3Wqt4q82g0o1UMhP4Nr3GchadbVvUKXAMkKvxijlRRoF00Zm32Fgms

# Trigger new deployment
git push origin main
```

### 2. Deploy Backend (Railway)

```bash
# Update environment variables in Railway dashboard
# Add all Stripe Price IDs listed above

# Redeploy the API service
railway up
```

### 3. Verify Fixes

- ✅ Visit https://swarmsync.ai/agents
- ✅ Click "View Profile" on any agent → Should load agent detail page
- ✅ Visit https://swarmsync.ai/pricing
- ✅ Click "Checkout with Stripe" on Plus plan → Should redirect to Stripe checkout

---

## 📋 Next Steps: Full Site Audit

See `SITE_AUDIT_CHECKLIST.md` for comprehensive testing plan.
