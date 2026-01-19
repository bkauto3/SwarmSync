# 🔧 Fix Stripe Checkout - Step by Step

**Stripe checkout still returning 401 error - here's how to fix it**

---

## 🎯 Current Status

- ✅ Code fixed (publicApi client created)
- ✅ Database connected (53 agents working)
- ❌ Stripe checkout still fails with 401

---

## 🔍 Diagnosis

The 401 error means one of these:

1. Stripe Price IDs not set in Railway
2. Stripe Secret Key not set in Railway
3. Backend authentication issue

---

## ✅ Step 1: Verify Railway Stripe Variables

```powershell
# Check all Railway variables
railway variables
```

**Look for these variables** (should all be set):

### **Required Stripe Variables**

```bash
# Stripe API Keys
STRIPE_SECRET_KEY=sk_test_... or sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_test_... or pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Price IDs (8 total)
PLUS_SWARM_SYNC_TIER_PRICE_ID=price_1SVKKGPQdMywmVkHgz2Wk5gD
PLUS_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKUFPQdMywmVkH5Codud0o
GROWTH_SWARM_SYNC_TIER_PRICE_ID=price_1SSlzkPQdMywmVkHXJSPjysl
GROWTH_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKV0PQdMywmVkHP471mt4C
PRO_SWARM_SYNC_TIER_PRICE_ID=price_1SSm0GPQdMywmVkHAb9V3Ct7
PRO_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKVePQdMywmVkHbnolmqiG
SCALE_SWARM_SYNC_TIER_PRICE_ID=price_1SSm3XPQdMywmVkH0Umdoehb
SCALE_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKWFPQdMywmVkHqwrToHAv
```

---

## ✅ Step 2: Add Missing Variables

If any are missing, add them:

```powershell
# Add Stripe Secret Key (if missing)
railway variables set STRIPE_SECRET_KEY="sk_test_YOUR_KEY_HERE"

# Add Stripe Price IDs (if missing)
railway variables set PLUS_SWARM_SYNC_TIER_PRICE_ID="price_1SVKKGPQdMywmVkHgz2Wk5gD"
railway variables set PLUS_SWARM_SYNC_YEARLY_PRICE_ID="price_1SVKUFPQdMywmVkH5Codud0o"
railway variables set GROWTH_SWARM_SYNC_TIER_PRICE_ID="price_1SSlzkPQdMywmVkHXJSPjysl"
railway variables set GROWTH_SWARM_SYNC_YEARLY_PRICE_ID="price_1SVKV0PQdMywmVkHP471mt4C"
railway variables set PRO_SWARM_SYNC_TIER_PRICE_ID="price_1SSm0GPQdMywmVkHAb9V3Ct7"
railway variables set PRO_SWARM_SYNC_YEARLY_PRICE_ID="price_1SVKVePQdMywmVkHbnolmqiG"
railway variables set SCALE_SWARM_SYNC_TIER_PRICE_ID="price_1SSm3XPQdMywmVkH0Umdoehb"
railway variables set SCALE_SWARM_SYNC_YEARLY_PRICE_ID="price_1SVKWFPQdMywmVkHqwrToHAv"
```

---

## ✅ Step 3: Check if Endpoint is Actually Public

Let me verify the billing controller doesn't have auth guards:

```powershell
# Test the public endpoint directly
Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/billing/subscription/checkout/public" -Method POST -ContentType "application/json" -Body '{"planSlug":"plus"}' | Select-Object StatusCode, Content
```

**Expected**: Should return 200 or redirect, NOT 401

**If 401**: The endpoint has an auth guard we need to remove

---

## ✅ Step 4: Deploy Code Changes

The code fix (publicApi client) was made locally. We need to deploy it:

```powershell
# Commit and push changes
git add apps/web/src/lib/api.ts
git commit -m "Fix: Use publicApi for Stripe checkout to avoid 401 error"
git push origin main
```

**Wait for Netlify to redeploy** (~2 minutes)

---

## ✅ Step 5: Test Stripe Checkout

After Railway and Netlify redeploy:

1. **Open incognito window** (to test as unauthenticated user)
2. Visit: https://swarmsync.ai/pricing
3. Click **"Checkout with Stripe"** on Plus plan
4. Should redirect to Stripe checkout page

**If still 401**: Check browser console for error details

---

## 🐛 Alternative: Test with Authenticated User

The 401 might be because the endpoint requires authentication. Let's test:

1. **Login** to https://swarmsync.ai
2. Visit: https://swarmsync.ai/pricing
3. Click **"Checkout with Stripe"**
4. Should work if endpoint requires auth

**If this works**: The endpoint is NOT public, we need to make it public

---

## 🔧 Fix: Make Endpoint Truly Public

If the endpoint requires auth, we need to add `@Public()` decorator:

**File**: `apps/api/src/modules/billing/billing.controller.ts`

```typescript
import { Public } from '../auth/decorators/public.decorator';

@Controller('billing')
export class BillingController {
  @Public() // Add this decorator
  @Post('subscription/checkout/public')
  async createPublicCheckoutSession(@Body() dto: CreateCheckoutSessionDto) {
    // ... existing code
  }
}
```

**Then redeploy**:

```powershell
git add apps/api/src/modules/billing/billing.controller.ts
git commit -m "Fix: Add @Public() decorator to public checkout endpoint"
git push origin main
```

---

## 📊 Verification Checklist

- [ ] Railway variables checked (all Stripe vars present)
- [ ] Code changes committed and pushed
- [ ] Netlify redeployed (frontend)
- [ ] Railway redeployed (backend)
- [ ] Tested in incognito window
- [ ] Stripe checkout redirects successfully
- [ ] Can complete test payment

---

## 🎯 Quick Test Script

```powershell
# Test the endpoint directly
$body = @{
    planSlug = "plus"
    successUrl = "https://swarmsync.ai/success"
    cancelUrl = "https://swarmsync.ai/pricing"
} | ConvertTo-Json

Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/billing/subscription/checkout/public" -Method POST -ContentType "application/json" -Body $body
```

**Expected Response**:

```json
{
  "checkoutUrl": "https://checkout.stripe.com/c/pay/cs_test_..."
}
```

---

## 📞 Next Steps

1. Run `railway variables` to check Stripe vars
2. Add any missing variables
3. Commit and push code changes
4. Wait for redeploy
5. Test checkout flow
6. Report results

---

**Let me know what `railway variables` shows and I'll help you fix it!** 🎯
