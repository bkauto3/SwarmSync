# URGENT: Authentication Fix for swarmsync.ai

## CRITICAL ISSUE IDENTIFIED

**Root Cause**: OAuth client secrets are NOT deployed to Netlify production environment because `.env` files are gitignored.

The `.env` file in `apps/web/.env` contains all the OAuth secrets, but it's excluded by the root `.gitignore` file, so Netlify never receives these credentials.

When NextAuth runs in production without these secrets, it falls back to placeholder values:

- `'missing-google-client-secret'`
- `'missing-github-client-secret'`

This causes **ALL OAuth logins to fail silently**.

---

## SYMPTOMS

1. ❌ Google OAuth button - clicking does NOTHING
2. ❌ GitHub OAuth button - clicking does NOTHING
3. ⚠️ Email/password login - backend API works, but there may be client-side issues

---

## SOLUTION (Choose One)

### Option 1: Netlify Dashboard (RECOMMENDED - Most Secure & Manual)

1. Go to https://app.netlify.com
2. Select your site: **swarmsync.ai** (or agent-market-web)
3. Navigate to: **Site Settings → Environment Variables**
4. Click **Add a variable** and add ALL of these:

```bash
# OAuth Secrets (Server-Side Only)
GOOGLE_CLIENT_ID=1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
GITHUB_CLIENT_ID=Ov23lijhlbg5GGBJZyqp
GITHUB_CLIENT_SECRET=9970089f7d6588f60ed8c47b4251840137c6eb73

# NextAuth Configuration
NEXTAUTH_SECRET=HNT0jWSyAGYkf3DAaUgpIUgfJdY7jwMW
NEXTAUTH_URL=https://swarmsync.ai

# Public Variables (Client-Side)
NEXT_PUBLIC_GOOGLE_CLIENT_ID=1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com
NEXT_PUBLIC_GITHUB_CLIENT_ID=Ov23lijhlbg5GGBJZyqp
NEXT_PUBLIC_APP_URL=https://swarmsync.ai
NEXT_PUBLIC_API_URL=https://swarmsync-api.up.railway.app
NEXT_PUBLIC_DEFAULT_ORG_SLUG=swarmsync
```

5. **Trigger a redeploy**:
   - Go to **Deploys** tab
   - Click **Trigger deploy → Clear cache and deploy site**

6. **Wait for deployment** (~3-5 minutes)

7. **Test the fix**: Go to https://swarmsync.ai/login and try:
   - Google OAuth login
   - GitHub OAuth login
   - Email/password login

---

### Option 2: Netlify CLI (FASTEST - Automated)

**Prerequisites**: Run `netlify login` first to authenticate

```bash
cd C:\Users\Ben\Desktop\Github\Agent-Market
chmod +x set-netlify-env.sh
./set-netlify-env.sh
```

This will:

- Set all environment variables in Netlify
- Trigger a production deployment automatically
- Complete in ~5-7 minutes total

---

## VERIFICATION STEPS

After deployment completes:

1. **Check environment variables are set**:

   ```bash
   netlify env:list --context production
   ```

2. **Test OAuth endpoints**:

   ```bash
   curl -s "https://swarmsync.ai/api/auth/providers" | python -m json.tool
   ```

   Should return Google and GitHub providers.

3. **Test live site manually**:
   - Navigate to https://swarmsync.ai/login
   - Open browser DevTools (F12) → Console tab
   - Click "Google" button
   - Should redirect to Google OAuth consent screen
   - After authentication, should redirect back to /dashboard

4. **Check for errors**:
   - If OAuth fails, check browser console for errors
   - Check Netlify function logs: https://app.netlify.com → Functions → View logs

---

## SECURITY NOTE

**DO NOT commit `.env` files to git!**

The proper way to handle secrets in production:

- ✅ Use Netlify dashboard environment variables
- ✅ Use Netlify CLI `env:set` commands
- ❌ NEVER commit `.env` files with real secrets to the repository

Current setup is correct: `.env` is gitignored, but we must manually set the variables in Netlify.

---

## ADDITIONAL ISSUES FOUND

### 1. GitHub Client ID Mismatch

There are **different GitHub OAuth client IDs** in different files:

- `apps/web/.env`: `Ov23lijhlbg5GGBJZyqp`
- `apps/web/.env.local`: `Ov23li9tCaHQdRC8yrno` ⚠️ DIFFERENT!

**Fix**: Use the same client ID everywhere. The `.env` file is the source of truth.

**Action Required**:

```bash
# Update .env.local to match .env
cd apps/web
# Edit .env.local manually and change NEXT_PUBLIC_GITHUB_CLIENT_ID to: Ov23lijhlbg5GGBJZyqp
```

### 2. OAuth Redirect URIs Must Be Configured

Ensure these redirect URIs are configured in your OAuth provider settings:

**Google OAuth** (https://console.cloud.google.com):

- Authorized redirect URI: `https://swarmsync.ai/api/auth/callback/google`

**GitHub OAuth** (https://github.com/settings/developers):

- Authorization callback URL: `https://swarmsync.ai/api/auth/callback/github`

---

## TIMELINE TO FIX

- **Option 1 (Manual)**: ~10-15 minutes (5 min to set vars + 3-5 min deployment)
- **Option 2 (CLI)**: ~5-7 minutes (automated)

---

## TEST CHECKLIST

After deployment, verify:

- [ ] Google OAuth login works (redirects to Google, then back to dashboard)
- [ ] GitHub OAuth login works (redirects to GitHub, then back to dashboard)
- [ ] Email/password login works (submits form, logs in, redirects to dashboard)
- [ ] No JavaScript errors in browser console
- [ ] No failed network requests in Network tab
- [ ] User can access protected pages (like /dashboard) after login
- [ ] User session persists after page reload

---

## CONTACT FOR ISSUES

If authentication still fails after this fix:

1. Check Netlify function logs for NextAuth errors
2. Check browser console for client-side JavaScript errors
3. Verify OAuth provider redirect URIs are correct
4. Test with a different browser/incognito mode
5. Check if NEXTAUTH_URL matches the actual domain (https://swarmsync.ai)

---

**Generated**: 2026-01-05
**Urgency**: CRITICAL - Site authentication is completely broken
**Impact**: Users cannot log in at all - site effectively down for authenticated features
