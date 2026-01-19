# 🚨 URGENT: Fix Stripe 500 Error

**Error**: `Request failed with status code 500: POST https://swarmsync-api.up.railway.app/billing/subscription/checkout/public`

**Root Cause**: Stripe Price ID environment variables are NOT set in Railway production environment.

---

## 🔧 IMMEDIATE FIX (2 minutes)

### Step 1: Add Environment Variables to Railway

1. Go to https://railway.app
2. Select your API project
3. Click "Variables" tab
4. Add these 8 variables:

```bash
PLUS_SWARM_SYNC_TIER_PRICE_ID=price_1SVKKGPQdMywmVkHgz2Wk5gD
PLUS_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKUFPQdMywmVkH5Codud0o
GROWTH_SWARM_SYNC_TIER_PRICE_ID=price_1SSlzkPQdMywmVkHXJSPjysl
GROWTH_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKV0PQdMywmVkHP471mt4C
PRO_SWARM_SYNC_TIER_PRICE_ID=price_1SSm0GPQdMywmVkHAb9V3Ct7
PRO_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKVePQdMywmVkHbnolmqiG
SCALE_SWARM_SYNC_TIER_PRICE_ID=price_1SSm3XPQdMywmVkH0Umdoehb
SCALE_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKWFPQdMywmVkHqwrToHAv
```

5. Click "Deploy" or wait for auto-redeploy (takes ~2 minutes)

### Step 2: Test

1. Open incognito window
2. Visit https://swarmsync.ai/pricing
3. Click "Checkout with Stripe" on Plus plan
4. Should now redirect to Stripe checkout (NOT 500 error)

---

## 📋 Why This Happened

The billing service reads Stripe Price IDs from environment variables:

```typescript
// packages/config/src/billing.ts
const plusPlan = {
  slug: 'plus',
  name: 'Plus',
  priceCents: 2900,
  stripePriceId: process.env.PLUS_SWARM_SYNC_TIER_PRICE_ID ?? '', // ← This is empty in Railway!
};
```

When `stripePriceId` is empty, the backend throws:

```typescript
if (!stripePriceId) {
  throw new Error(`Stripe price ID missing for plan ${plan.slug}`); // ← 500 error
}
```

---

## ✅ Verification

After adding environment variables to Railway:

1. Check Railway logs for successful deployment
2. Test checkout flow:
   - Visit https://swarmsync.ai/pricing
   - Click "Checkout with Stripe"
   - Should redirect to Stripe checkout page
   - Should show correct price ($29 for Plus)

---

## 🎯 Alternative Quick Fix (If Railway is slow)

If you need an immediate fix while waiting for Railway deployment, use Stripe Payment Links:

### Create Payment Links in Stripe Dashboard

1. Go to https://dashboard.stripe.com/payment-links
2. Click "New payment link"
3. Select the price (e.g., Plus_Swarm_Sync_Tier)
4. Set success URL: `https://swarmsync.ai/register?status=success&plan=plus`
5. Set cancel URL: `https://swarmsync.ai/pricing?status=cancel`
6. Copy the payment link URL

### Update Pricing Page

Replace the `stripeLink` values with actual Stripe Payment Links:

```typescript
// apps/web/src/app/pricing/page.tsx
{
  name: 'Plus',
  stripeLink: 'https://buy.stripe.com/YOUR_PAYMENT_LINK_HERE',
}
```

Then update the CheckoutButton to use the link directly:

```typescript
// apps/web/src/components/pricing/checkout-button.tsx
if (stripeLink && stripeLink.startsWith('https://buy.stripe.com/')) {
  // Direct Stripe Payment Link
  return (
    <Button asChild className="w-full" variant={popular ? 'default' : 'outline'}>
      <a href={stripeLink}>Checkout with Stripe</a>
    </Button>
  );
}
```

---

## 📊 Status

- [x] Identified root cause (missing env vars in Railway)
- [x] Documented fix
- [ ] Add env vars to Railway
- [ ] Test checkout flow
- [ ] Verify all 4 plans work

---

## 🚀 Next Steps After Fix

1. Test all 4 pricing tiers (Plus, Growth, Pro, Scale)
2. Test both monthly and yearly pricing (if implemented)
3. Complete a test transaction with test card: `4242 4242 4242 4242`
4. Verify webhook receives payment confirmation
5. Check that subscription is created in database

---

**TLDR**: Add the 8 Stripe Price ID environment variables to Railway, wait 2 minutes for redeploy, then test.
