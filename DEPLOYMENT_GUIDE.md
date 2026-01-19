# 🚀 Deployment Guide - Critical Bug Fixes

**Date**: December 4, 2025  
**Status**: Code fixes complete, ready for deployment

---

## 📋 Changes Summary

### Files Modified

1. `apps/web/.env.local` - Fixed API URL configuration
2. `apps/api/.env` - Added missing Stripe Price IDs
3. `apps/web/src/app/pricing/page.tsx` - Removed test Stripe links

---

## 🔧 Step 1: Deploy Backend (Railway)

### 1.1 Set Environment Variables in Railway Dashboard

Navigate to your Railway project → API service → Variables tab and ensure these are set:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=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
STRIPE_WEBHOOK_SECRET=whsec_XWfHm4jPyYYhT089B0oR54qqS5sOIrUN
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_51RyJPcPQdMywmVkHwdLQtTRV8YV9fXjdJtrxEwnYCFTn3Wqt4q82g0o1UMhP4Nr3GchadbVvUKXAMkKvxijlRRoF00Zm32Fgms

# Stripe Price IDs (CRITICAL - NEWLY ADDED)
PLUS_SWARM_SYNC_TIER_PRICE_ID=price_1SSlyTPQdMywmVkHgz2Wk5gD
PLUS_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbBXYZ123ABC
GROWTH_SWARM_SYNC_TIER_PRICE_ID=price_1SSlzkPQdMywmVkHXJSPjysl
GROWTH_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbCgvrkT8zgem
SCALE_SWARM_SYNC_TIER_PRICE_ID=price_1SSm0GPQdMywmVkHAb9V3Ct7
SCALE_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbCXg63wEQ5oE
PRO_SWARM_SYNC_TIER_PRICE_ID=price_1SSm3XPQdMywmVkH0Umdoehb
PRO_SWARM_SYNC_TIER_PRODUCT_ID=prod_TPbGlQTQ8dQY9G

# Database
DATABASE_URL=postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-a7s.us-east-2.aws.neon.tech/neondb?sslmode=require

# API Configuration
API_URL=https://api.swarmsync.ai
WEB_URL=https://swarmsync.ai
NODE_ENV=production
```

### 1.2 Deploy Backend

```bash
# Option A: Push to trigger auto-deploy
git add apps/api/.env
git commit -m "fix: Add missing Stripe Price IDs for Plus plan"
git push origin main

# Option B: Manual redeploy in Railway dashboard
# Click "Deploy" button in Railway dashboard
```

### 1.3 Verify Backend Deployment

```bash
# Test API health
curl https://swarmsync-api.up.railway.app/health

# Test billing plans endpoint
curl https://swarmsync-api.up.railway.app/billing/plans
```

---

## 🌐 Step 2: Deploy Frontend (Netlify)

### 2.1 Set Environment Variables in Netlify

Navigate to Netlify dashboard → Site settings → Environment variables:

```bash
# API Configuration (CRITICAL - CHANGED)
NEXT_PUBLIC_API_URL=https://swarmsync-api.up.railway.app

# App Configuration
NEXT_PUBLIC_APP_URL=https://swarmsync.ai
NEXT_PUBLIC_DEFAULT_ORG_SLUG=swarmsync

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_51RyJPcPQdMywmVkHwdLQtTRV8YV9fXjdJtrxEwnYCFTn3Wqt4q82g0o1UMhP4Nr3GchadbVvUKXAMkKvxijlRRoF00Zm32Fgms

# OAuth
NEXT_PUBLIC_GOOGLE_CLIENT_ID=1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com
NEXT_PUBLIC_GITHUB_CLIENT_ID=Ov23li9tCaHQdRC8yrno

# NextAuth
NEXTAUTH_SECRET=HNT0jWSyAGYkf3DAaUgpIUgfJdY7jwMW
NEXTAUTH_URL=https://swarmsync.ai
```

### 2.2 Deploy Frontend

```bash
# Push changes to trigger Netlify build
git add apps/web/.env.local apps/web/src/app/pricing/page.tsx
git commit -m "fix: Update API URL and remove test Stripe links"
git push origin main

# Netlify will auto-deploy from main branch
```

### 2.3 Clear Netlify Cache (if needed)

```bash
# In Netlify dashboard:
# Deploys → Trigger deploy → Clear cache and deploy site
```

---

## ✅ Step 3: Verify Fixes

### 3.1 Test Agent Profile Links

1. Visit https://swarmsync.ai/agents
2. Click "View Profile" on any agent card
3. ✅ Should load agent detail page with full information
4. ✅ Should NOT show 404 error

### 3.2 Test Stripe Checkout

1. Visit https://swarmsync.ai/pricing
2. Click "Checkout with Stripe" on Plus plan ($29/month)
3. ✅ Should redirect to Stripe checkout page
4. ✅ Should show correct price ($29.00)
5. Use test card: `4242 4242 4242 4242`, any future date, any CVC
6. ✅ Should complete checkout successfully
7. ✅ Should redirect to `/billing?status=success`

### 3.3 Test Other Plans

Repeat Stripe checkout test for:

- Growth plan ($99/month)
- Pro plan ($199/month)
- Scale plan ($499/month)

---

## 🔍 Troubleshooting

### Issue: Agent profiles still 404

**Solution**: Check browser console for API errors. Verify:

```bash
# In browser console, check:
localStorage.getItem('NEXT_PUBLIC_API_URL')
# Should be: https://swarmsync-api.up.railway.app
```

### Issue: Stripe checkout fails

**Solution**: Check Railway logs for errors:

```bash
# In Railway dashboard → API service → Logs
# Look for errors like "Stripe price ID missing"
```

### Issue: Environment variables not updating

**Solution**: Hard refresh browser cache:

- Chrome/Edge: Ctrl + Shift + R (Windows) or Cmd + Shift + R (Mac)
- Clear Netlify cache and redeploy

---

## 📊 Post-Deployment Checklist

- [ ] Backend deployed to Railway
- [ ] Frontend deployed to Netlify
- [ ] Agent profile links working
- [ ] Stripe checkout working for all plans
- [ ] No console errors on homepage
- [ ] No console errors on pricing page
- [ ] No console errors on agents page
- [ ] Test transaction completes successfully

---

## 🎯 Success Criteria

✅ **Bug #1 Fixed**: Clicking "View Profile" loads agent detail page  
✅ **Bug #2 Fixed**: Clicking "Checkout with Stripe" initiates Stripe checkout  
✅ **No Regressions**: All other site functionality still works

---

## 📞 Support

If issues persist after deployment:

1. Check Railway logs for backend errors
2. Check Netlify build logs for frontend errors
3. Check browser console for client-side errors
4. Verify all environment variables are set correctly
