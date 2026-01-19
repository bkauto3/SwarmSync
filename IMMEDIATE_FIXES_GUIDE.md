# 🚨 Immediate Fixes Guide

**Step-by-step instructions to fix critical issues**

---

## ✅ COMPLETED FIXES

### **1. Stripe Checkout 401 Error** ✅ FIXED

**Problem**: Public checkout endpoint was receiving Authorization header, causing 401 error

**Solution**: Created separate `publicApi` client without auth headers

**Files Changed**:

- `apps/web/src/lib/api.ts` - Added `publicApi` client
- `apps/web/src/lib/api.ts` - Updated `createPublicCheckoutSession` to use `publicApi`

**Status**: ✅ Code fixed, needs testing

---

## ⚠️ REMAINING CRITICAL FIXES

### **2. Verify Railway Environment Variables**

**Problem**: Stripe Price IDs may not be set in Railway production environment

**Steps to Fix**:

1. **Login to Railway**
   - Go to https://railway.app
   - Use project token: `c5617b21-1704-46c3-bf94-410d17440c83`

2. **Navigate to API Service**
   - Select the API project (swarmsync-api)
   - Click "Variables" tab

3. **Add/Verify These 8 Variables**:

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

4. **Redeploy**
   - Railway will auto-redeploy (takes ~2 minutes)
   - Or click "Deploy" button manually

5. **Test**
   - Visit https://swarmsync.ai/pricing
   - Click "Checkout with Stripe" on Plus plan
   - Should redirect to Stripe checkout (NOT 500 error)

---

### **3. Fix Agent Profile Pages (View Profile 404)**

**Problem**: Clicking "View Profile" on agent cards may return 404

**Possible Causes**:

1. No agents in production database
2. API endpoint not working
3. Routing issue

**Steps to Diagnose**:

1. **Check if agents exist in database**

   ```bash
   # Connect to Neon database
   # Run query:
   SELECT id, slug, name, status FROM "Agent" LIMIT 10;
   ```

2. **Test API endpoint directly**

   ```bash
   curl https://swarmsync-api.up.railway.app/agents
   ```

   - Should return array of agents
   - If empty, database needs seeding

3. **Test agent detail endpoint**
   ```bash
   curl https://swarmsync-api.up.railway.app/agents/slug/[agent-slug]
   ```

   - Replace `[agent-slug]` with actual slug from database
   - Should return agent details

**Steps to Fix**:

**Option A: Seed Database with Demo Agents**

```bash
# Create seed script
cd apps/api
npm run seed:agents
```

**Option B: Create Agents Manually**

1. Visit https://swarmsync.ai/agents/new
2. Create 5-10 demo agents
3. Set status to APPROVED
4. Test "View Profile" links

**Option C: Use Prisma Studio**

```bash
cd apps/api
npx prisma studio
# Opens at http://localhost:5555
# Manually create agents in UI
```

---

### **4. Configure Google Cloud OAuth**

**Problem**: OAuth redirect URIs may not be configured correctly

**Steps to Fix**:

1. **Go to Google Cloud Console**
   - Visit https://console.cloud.google.com
   - Select your project

2. **Navigate to OAuth Consent Screen**
   - APIs & Services → OAuth consent screen
   - Verify app is configured

3. **Navigate to Credentials**
   - APIs & Services → Credentials
   - Click on your OAuth 2.0 Client ID

4. **Add Authorized Redirect URIs**

   ```
   https://swarmsync.ai/api/auth/callback/google
   https://swarmsync.ai/callback
   http://localhost:3000/api/auth/callback/google (for local dev)
   http://localhost:3000/callback (for local dev)
   ```

5. **Add Authorized JavaScript Origins**

   ```
   https://swarmsync.ai
   http://localhost:3000 (for local dev)
   ```

6. **Save Changes**
   - Click "Save"
   - Changes take effect immediately

7. **Test OAuth Flow**
   - Visit https://swarmsync.ai/login
   - Click "Continue with Google"
   - Should redirect to Google login
   - Should redirect back to swarmsync.ai after auth

**GitHub OAuth** (Similar Steps):

1. Go to https://github.com/settings/developers
2. Click on your OAuth App
3. Update "Authorization callback URL":
   ```
   https://swarmsync.ai/api/auth/callback/github
   ```
4. Save changes
5. Test GitHub login

---

### **5. Implement Agent Pricing**

**Problem**: Agents don't have realistic pricing set

**Steps to Fix**:

1. **Review Pricing Guide**
   - See `AGENT_PRICING_GUIDE.md` for recommended pricing

2. **Update Existing Agents**

   ```sql
   -- Example: Update lead generation agents
   UPDATE "Agent"
   SET "basePriceCents" = 2000
   WHERE categories @> ARRAY['lead-generation']
   AND "basePriceCents" IS NULL;
   ```

3. **Set Category-Specific Pricing**
   - Lead Generation: $20-50 per 100 leads (2000-5000 cents)
   - Content Creation: $10-20 per piece (1000-2000 cents)
   - Data Analysis: $50-150 per report (5000-15000 cents)
   - Customer Support: $0.10-1.00 per conversation (10-100 cents)
   - Development: $25-500 per task (2500-50000 cents)
   - Marketing: $20-150 per campaign (2000-15000 cents)

4. **Create Pricing Tiers**
   - Add `pricingTier` field to Agent model
   - Values: FREE, BASIC, STANDARD, PREMIUM, ENTERPRISE
   - Display tier badge on agent cards

---

### **6. Update Star Rating Formula**

**Problem**: Current formula is too simplistic

**Steps to Fix**:

1. **Review Improved Formula**
   - See `IMPROVED_RATING_FORMULA.md` for new formula

2. **Update Rating Calculation**
   - File: `apps/web/src/components/agents/agent-card.tsx`
   - File: `apps/web/src/app/(marketplace)/agents/[slug]/page.tsx`
   - Replace `calculateRating()` function with improved version

3. **Add Database Fields**

   ```prisma
   model Agent {
     // ... existing fields
     recentSuccessRate Float?
     reviewScore       Float?
     reviewCount       Int     @default(0)
     ratingConfidence  Float?
   }
   ```

4. **Run Migration**

   ```bash
   cd apps/api
   npx prisma migrate dev --name add_rating_fields
   ```

5. **Create Background Job**
   - Calculate `recentSuccessRate` from last 30 days
   - Run daily via cron job or scheduled task

---

## 🧪 Testing Checklist

After making fixes, test these critical flows:

### **Stripe Checkout**

- [ ] Visit https://swarmsync.ai/pricing
- [ ] Click "Checkout with Stripe" (unauthenticated)
- [ ] Should redirect to Stripe checkout
- [ ] Should show correct price ($29 for Plus)
- [ ] Complete test payment with card: `4242 4242 4242 4242`
- [ ] Should redirect back to success page

### **Agent Profile Pages**

- [ ] Visit https://swarmsync.ai/agents
- [ ] Should see list of agents
- [ ] Click "View Profile" on any agent
- [ ] Should load agent detail page (NOT 404)
- [ ] Should show agent stats, pricing, description
- [ ] "Request Service" button should work

### **OAuth Login**

- [ ] Visit https://swarmsync.ai/login
- [ ] Click "Continue with Google"
- [ ] Should redirect to Google login
- [ ] After login, should redirect back to swarmsync.ai
- [ ] Should be logged in (see user menu)
- [ ] Repeat for GitHub OAuth

---

## 📊 Success Criteria

All fixes are complete when:

- ✅ Stripe checkout works for unauthenticated users
- ✅ All 4 pricing tiers redirect to Stripe correctly
- ✅ Agent profile pages load without 404 errors
- ✅ At least 10 demo agents exist in production
- ✅ Google OAuth login works end-to-end
- ✅ GitHub OAuth login works end-to-end
- ✅ All agents have realistic pricing set
- ✅ Star ratings show confidence levels

---

**Estimated Time**: 2-4 hours total

- Railway env vars: 10 minutes
- Agent seeding: 30-60 minutes
- OAuth configuration: 20 minutes
- Pricing updates: 30-60 minutes
- Rating formula: 60-90 minutes
- Testing: 30 minutes

---

**See Also**:

- `COMPLETE_TODO_LIST.md` - Full task list
- `AGENT_PRICING_GUIDE.md` - Pricing recommendations
- `IMPROVED_RATING_FORMULA.md` - New rating formula
