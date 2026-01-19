# Deploy to Railway - Step by Step Guide

**Time Required**: 10 minutes
**Result**: Fully working login system

---

## Why Railway Will Fix Everything:

1. ✅ **No build-time API connection issues** - Builds correctly
2. ✅ **Environment variables work properly** - OAuth buttons will show
3. ✅ **Monorepo support** - Handles your workspace structure
4. ✅ **Auto-deploys** - Push to GitHub = instant deploy
5. ✅ **Free $5 credit** - Covers initial testing
6. ✅ **One platform** - Can run both frontend AND backend

---

## Step 1: Push Your Code to GitHub (if not already)

```powershell
cd C:\Users\Ben\Desktop\Github\Agent-Market
git add .
git commit -m "Add Railway configuration files"
git push origin main
```

---

## Step 2: Create Railway Project

1. Go to: **https://railway.app/**
2. Click **"Login"** (top right)
3. Sign in with GitHub
4. Click **"New Project"**
5. Select **"Deploy from GitHub repo"**
6. Choose your repository: **Agent-Market**
7. Railway will detect it's a monorepo

---

## Step 3: Configure Web Service (Frontend)

### 3.1 Add Service for Web App

1. In your Railway project, click **"+ New"**
2. Select **"Service"** → **"GitHub Repo"**
3. Choose **Agent-Market** repo
4. Railway will start building

### 3.2 Configure Build Settings

1. Click on the web service
2. Go to **"Settings"** tab
3. Set these values:

   **Root Directory**: `apps/web`
   **Build Command**: `npm run build`
   **Start Command**: `npm run start`
   **Watch Paths**: `apps/web/**`

### 3.3 Add Environment Variables

Click **"Variables"** tab and add these:

```
NEXT_PUBLIC_API_URL=https://api.swarmsync.ai
NEXT_PUBLIC_APP_URL=https://www.swarmsync.ai
NEXT_PUBLIC_GOOGLE_CLIENT_ID=613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com
NEXT_PUBLIC_GITHUB_CLIENT_ID=Ov23lifZqAEEJxZmMD84
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_51RyJPcPQdMywmVkHwdLQtTRV8YV9fXjdJtrxEwnYCFTn3Wqt4q82g0o1UMhP4Nr3GchadbVvUKXAMkKvxijlRRoF00Zm32Fgms
```

### 3.4 Get Your Railway URL

1. Go to **"Settings"** → **"Networking"**
2. Click **"Generate Domain"**
3. Copy the URL (e.g., `your-app.up.railway.app`)

---

## Step 4: Update Your Domain

### Option A: Use Railway Domain Temporarily

Just use the `your-app.up.railway.app` URL for now.

### Option B: Point swarmsync.ai to Railway

1. Go to your DNS provider (Cloudflare, GoDaddy, etc.)
2. Update the CNAME for `www.swarmsync.ai`:
   - **Type**: CNAME
   - **Name**: www
   - **Value**: your-app.up.railway.app
3. Add custom domain in Railway:
   - Go to **Settings** → **Networking**
   - Click **"Custom Domain"**
   - Enter: `www.swarmsync.ai`

---

## Step 5: Deploy API Service (Backend)

### 5.1 Add API Service

1. In Railway project, click **"+ New"**
2. Select **"Service"** → **"GitHub Repo"**
3. Choose **Agent-Market** repo again
4. Name it: **"api"**

### 5.2 Configure API Build

1. Click on the API service
2. Go to **"Settings"**
3. Set:

   **Root Directory**: `apps/api`
   **Build Command**: `npm run build`
   **Start Command**: `npm run start:prod`
   **Watch Paths**: `apps/api/**`

### 5.3 Add API Environment Variables

Click **"Variables"** tab:

```
NODE_ENV=production
DATABASE_URL=postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-aenonb7s.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require
JWT_SECRET=NYs0Ts_M8XDa0hBgjELcA4i_FfqLlP_eapMQUbKeaoA
GOOGLE_OAUTH_CLIENT_ID=613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com
GOOGLE_CLIENT_ID=613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
GITHUB_CLIENT_ID=Ov23lifZqAEEJxZmMD84
GITHUB_CLIENT_SECRET=b01b7afd70fa78e382c57565fb41898d0ddc9157
STRIPE_SECRET_KEY=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
CORS_ALLOWED_ORIGINS=https://www.swarmsync.ai,https://swarmsync.ai
```

### 5.4 Get API Railway URL

1. Generate domain for API service
2. Copy the URL (e.g., `api-production.up.railway.app`)
3. Update DNS CNAME for `api.swarmsync.ai` to point to this URL

---

## Step 6: Update Frontend to Use Railway API

Go back to the **web service** → **Variables** and update:

```
NEXT_PUBLIC_API_URL=https://api-production.up.railway.app
```

(Use the actual Railway URL you got in Step 5.4)

---

## Step 7: Redeploy

1. Both services will auto-redeploy when you update variables
2. Wait 2-3 minutes for builds to complete
3. Check deployment logs in Railway UI

---

## Step 8: Update OAuth Providers

### Google OAuth

1. Go to: https://console.cloud.google.com/apis/credentials
2. Edit your OAuth Client
3. Add to **Authorized JavaScript origins**:
   - `https://www.swarmsync.ai`
   - `https://your-app.up.railway.app` (if using Railway domain)
4. Add to **Authorized redirect URIs** (same URLs)
5. Save

### GitHub OAuth

1. Go to: https://github.com/settings/developers
2. Edit your OAuth App
3. Set **Authorization callback URL**:
   - `https://www.swarmsync.ai/auth/github/callback`
4. Update

---

## Step 9: Test Everything

1. Wait 2-5 minutes for OAuth changes to propagate
2. Visit your Railway URL or `https://www.swarmsync.ai`
3. Go to `/login`
4. Check:
   - ✅ Google button says "Continue with Google" (not unavailable)
   - ✅ GitHub button says "Continue with GitHub" (not unavailable)
   - ✅ Can register with email/password
   - ✅ Can login with Google
   - ✅ Can login with GitHub

---

## Troubleshooting

### Build fails with "Cannot find module"

**Fix**: Check that Root Directory is set correctly:

- Web: `apps/web`
- API: `apps/api`

### OAuth buttons still say "unavailable"

**Fix**:

1. Check environment variables are set in Railway
2. Make sure they start with `NEXT_PUBLIC_` for frontend
3. Redeploy the service

### API connection refused

**Fix**:

1. Make sure API service is running (check logs)
2. Verify `NEXT_PUBLIC_API_URL` points to your API Railway URL
3. Check CORS settings in API allow your frontend domain

### "Unauthorized" errors

**Fix**:

1. Verify all OAuth secrets are set in API service
2. Check JWT_SECRET is set
3. Restart API service

---

## Railway vs Fly.io - Why It's Better

| Feature         | Railway            | Fly.io (Current)  |
| --------------- | ------------------ | ----------------- |
| Next.js Support | ✅ Native          | ⚠️ Complex Docker |
| Monorepo        | ✅ Easy            | ❌ Difficult      |
| Env Variables   | ✅ Build + Runtime | ⚠️ Only Runtime   |
| Deploy Speed    | ✅ 2-3 min         | ⚠️ 5-10 min       |
| Free Tier       | ✅ $5 credit       | ✅ Limited        |
| Dashboard       | ✅ Beautiful       | ⚠️ Basic          |
| Logs            | ✅ Real-time UI    | ⚠️ CLI only       |
| Auto-deploy     | ✅ Git push        | ❌ Manual CLI     |

---

## Next Steps After Deployment

1. **Remove Fly.io** (optional):

   ```powershell
   flyctl apps destroy agent-market
   flyctl apps destroy agent-market-api-divine-star-3849
   ```

2. **Set up auto-deploys**:
   - Railway automatically deploys on git push to main
   - No CI/CD setup needed

3. **Monitor your app**:
   - Check logs in Railway dashboard
   - Set up notifications for failures

4. **Configure custom domain permanently**:
   - Add `www.swarmsync.ai` as custom domain in Railway
   - Update DNS CNAME records

---

## Cost Estimate

**Railway Pricing**:

- **Free**: $5 credit (lasts ~1 month for your traffic)
- **Hobby Plan**: $5/month per service
  - Web service: $5/month
  - API service: $5/month
  - **Total**: $10/month

**What You Get**:

- Unlimited deployments
- Custom domains
- 8GB RAM per service
- Shared CPU
- 100GB outbound bandwidth

**Compare to Fly.io**:

- Similar pricing but Railway is easier
- No Docker complexity
- Better developer experience

---

## Summary

Railway will fix your login issues because:

1. ✅ **Proper build environment** - Environment variables available during build
2. ✅ **No localhost API calls** - Uses production API URL during build
3. ✅ **Monorepo support** - Handles workspaces correctly
4. ✅ **Simpler deployment** - No Dockerfile needed

**Estimated time**: 10-15 minutes to fully deploy and test

**Result**: Working login with Google, GitHub, and email/password 🎉
