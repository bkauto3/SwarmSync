# Railway Deployment - 5 Minute Quick Start

## 🚀 Why Railway Fixes Your Login Issues

The problem with Fly.io is that during the Next.js build, it tries to connect to `localhost:4000` (the API), but the API isn't running during build time. This causes:

- ❌ Build errors with "ECONNREFUSED"
- ❌ OAuth buttons showing as "unavailable"
- ❌ Pages that fetch data failing to build

**Railway solves this** by properly handling environment variables at build time AND runtime.

---

## 🎯 Quick Deploy Steps (5 Minutes)

### 1. Go to Railway

Visit: **https://railway.app/new**

### 2. Sign in with GitHub

Click "Login with GitHub"

### 3. Create New Project

1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your repo: **Rainking6693/Agent-Market**
4. Railway will detect it's a monorepo and ask which service

### 4. Deploy Frontend First

1. Select **"apps/web"** as the root directory
2. Railway will automatically:
   - Detect Next.js
   - Run `npm install`
   - Run `npm run build`
   - Start the app

### 5. Add Environment Variables (Frontend)

Click on the service → "Variables" tab → "Raw Editor":

```env
NEXT_PUBLIC_API_URL=https://api.swarmsync.ai
NEXT_PUBLIC_APP_URL=https://www.swarmsync.ai
NEXT_PUBLIC_GOOGLE_CLIENT_ID=613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com
NEXT_PUBLIC_GITHUB_CLIENT_ID=Ov23lifZqAEEJxZmMD84
```

Click "Deploy" after adding variables.

### 6. Get Your URL

1. Go to "Settings" → "Networking"
2. Click "Generate Domain"
3. You'll get: `something.up.railway.app`

### 7. Test It!

Visit your Railway URL → go to `/login`

**Expected Result:**

- ✅ OAuth buttons say "Continue with Google/GitHub"
- ✅ Not "unavailable" anymore
- ✅ Can register with email/password
- ✅ Page loads without build errors

---

## ✅ What Railway Does Differently

| Issue                | Fly.io               | Railway                   |
| -------------------- | -------------------- | ------------------------- |
| Build-time API calls | ❌ Fails (localhost) | ✅ Uses production URL    |
| Env variables        | ⚠️ Runtime only      | ✅ Build + Runtime        |
| Next.js support      | ⚠️ Docker required   | ✅ Native detection       |
| Monorepo             | ❌ Complex           | ✅ Root directory setting |

---

## 🔄 Deploy API Service (Optional)

If you want to move API to Railway too:

1. In same project, click "+ New"
2. Select "Service" → "GitHub Repo" → "Agent-Market"
3. Set Root Directory: `apps/api`
4. Add environment variables (see full guide)
5. Generate domain
6. Update frontend's `NEXT_PUBLIC_API_URL` to point to new API domain

---

## 🎉 That's It!

Your login should now work! The OAuth buttons will show correctly because Railway:

1. ✅ Properly injects `NEXT_PUBLIC_*` variables during build
2. ✅ Doesn't try to connect to localhost API during build
3. ✅ Handles Next.js SSR/SSG correctly
4. ✅ Deploys fast (2-3 minutes vs 10+ on Fly.io)

---

## 📚 Full Documentation

See **RAILWAY_DEPLOYMENT_GUIDE.md** for:

- Complete API deployment
- Custom domain setup
- OAuth provider configuration
- Troubleshooting guide
- Cost breakdown

---

## 💡 Pro Tip

Once deployed on Railway:

- Every git push to `main` = automatic deployment
- Check logs in real-time in Railway dashboard
- Rollback to previous deploys with 1 click
- Free $5 credit = ~1 month of hosting

---

**Questions?** Check the full guide or Railway's excellent docs at https://docs.railway.app
