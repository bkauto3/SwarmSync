# SwarmSync.ai Login Issues - Complete Diagnosis & Fix

**Date**: November 21, 2025
**Issue**: New users cannot register or login using Google/GitHub OAuth
**Status**: Issues Identified - Fixes Required

---

## 🔍 Root Causes Identified

### 1. **API Backend is Not Running** ⚠️ CRITICAL

- **Status**: `agent-market-api-divine-star-3849` is **SUSPENDED** on Fly.io
- **Impact**: All authentication requests (email/password, Google, GitHub) fail because the backend API is unreachable
- **API URL Expected**: `https://api.swarmsync.ai`
- **Current State**: Returns 404 errors

### 2. **OAuth Environment Variables Not Deployed** ⚠️ CRITICAL

- The frontend code checks for `process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID` and `process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID`
- If these are missing in production, the OAuth buttons show as "unavailable"
- Local `.env` files have these values, but they need to be set in Fly.io secrets

### 3. **OAuth Redirect URI Configuration** ⚠️ WARNING

- The app is deployed to `agent-market.fly.dev` but DNS points to `swarmsync.ai` and `www.swarmsync.ai`
- OAuth providers need to have the correct callback URLs registered
- GitHub callback is hardcoded to: `https://www.swarmsync.ai/auth/github/callback`

---

## 📊 Current Deployment Status

### Frontend (Web)

- **Deployed As**: `agent-market` on Fly.io
- **URL**: `agent-market.fly.dev` (DNS points to `www.swarmsync.ai`)
- **Status**: ✅ Running (1 machine started)
- **Last Deploy**: 1h54m ago

### Backend (API)

- **Deployed As**: `agent-market-api-divine-star-3849` on Fly.io
- **URL**: Should be `api.swarmsync.ai`
- **Status**: ❌ SUSPENDED (stopped 3h42m ago)
- **Issue**: Machine is stopped, needs to be started/deployed

---

## 🔧 Required Fixes

### Fix 1: Start/Deploy the Backend API

**Option A: Start Existing Machine**

```powershell
flyctl machine start 91850912c36518 --app agent-market-api-divine-star-3849
```

**Option B: Full Redeploy (Recommended)**

```powershell
cd C:\Users\Ben\Desktop\Github\Agent-Market
flyctl deploy --config apps/api/fly.toml --app agent-market-api-divine-star-3849
```

**Verify API is Running:**

```powershell
flyctl status --app agent-market-api-divine-star-3849
# Should show machine state as "started"

# Test API endpoint:
curl https://api.swarmsync.ai/health
# or visit in browser
```

---

### Fix 2: Set OAuth Environment Variables in Fly.io

The OAuth credentials exist in the local `.env` files but need to be set as Fly.io secrets for production.

**Set Secrets for Frontend (agent-market):**

```powershell
flyctl secrets set \
  NEXT_PUBLIC_GOOGLE_CLIENT_ID="613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com" \
  NEXT_PUBLIC_GITHUB_CLIENT_ID="Ov23lifZqAEEJxZmMD84" \
  --app agent-market
```

**Set Secrets for Backend (agent-market-api-divine-star-3849):**

```powershell
flyctl secrets set \
  GOOGLE_OAUTH_CLIENT_ID="613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com" \
  GOOGLE_CLIENT_ID="613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com" \
  GOOGLE_CLIENT_SECRET="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" \
  GITHUB_CLIENT_ID="Ov23lifZqAEEJxZmMD84" \
  GITHUB_CLIENT_SECRET="b01b7afd70fa78e382c57565fb41898d0ddc9157" \
  --app agent-market-api-divine-star-3849
```

**Verify Secrets Are Set:**

```powershell
# Check frontend secrets
flyctl secrets list --app agent-market

# Check backend secrets
flyctl secrets list --app agent-market-api-divine-star-3849
```

---

### Fix 3: Configure OAuth Providers

#### Google OAuth Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Find OAuth 2.0 Client ID: `613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c`
4. Click **Edit**

5. **Add Authorized JavaScript Origins:**

   ```
   https://www.swarmsync.ai
   https://swarmsync.ai
   https://agent-market.fly.dev
   ```

6. **Add Authorized Redirect URIs:**

   ```
   https://www.swarmsync.ai
   https://swarmsync.ai
   https://agent-market.fly.dev
   ```

7. Click **Save**

#### GitHub OAuth Configuration

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click on **OAuth Apps**
3. Find your app with Client ID: `Ov23lifZqAEEJxZmMD84`
4. Click **Edit**

5. **Set Authorization Callback URL:**

   ```
   https://www.swarmsync.ai/auth/github/callback
   ```

   **Note**: GitHub only allows ONE callback URL. The code is hardcoded to use `www.swarmsync.ai`, so this must match exactly.

6. Click **Update Application**

---

## 🧪 Testing Steps (After Fixes)

### 1. Verify API is Running

```powershell
# Check machine status
flyctl status --app agent-market-api-divine-star-3849

# Test health endpoint
curl https://api.swarmsync.ai/health
```

### 2. Test Regular Registration

1. Go to `https://www.swarmsync.ai/register`
2. Fill in name, email, password
3. Click "Create account"
4. **Expected**: Should create account and redirect to dashboard
5. **Previously Failed**: Would fail because API was down

### 3. Test Google Login

1. Go to `https://www.swarmsync.ai/login`
2. Click "Continue with Google"
3. **Expected**:
   - Button should NOT say "Google login unavailable"
   - Should redirect to Google login page
   - After Google auth, should create account and redirect to dashboard

### 4. Test GitHub Login

1. Go to `https://www.swarmsync.ai/login` (use www)
2. Click "Continue with GitHub"
3. **Expected**:
   - Button should NOT say "GitHub login unavailable"
   - Should redirect to GitHub authorization page
   - After GitHub auth, should redirect back to callback
   - Should create account and redirect to dashboard

---

## 🐛 Troubleshooting

### Issue: OAuth buttons still say "unavailable"

**Cause**: Environment variables not set in Fly.io
**Fix**: Run the `flyctl secrets set` commands from Fix 2 above
**Verify**: After setting secrets, the app will auto-redeploy. Wait 2-3 minutes and refresh the page.

### Issue: "redirect_uri_mismatch" error from Google

**Cause**: The redirect URI used by the app doesn't match what's configured in Google Cloud Console
**Check**: Look at the error message to see what URI was attempted
**Fix**: Add that exact URI to Google Cloud Console → Authorized JavaScript Origins and Redirect URIs

### Issue: GitHub callback error

**Cause**: The callback URL doesn't match what's registered in GitHub
**Check**: The code uses `https://www.swarmsync.ai/auth/github/callback`
**Fix**: Make sure this EXACT URL is in your GitHub OAuth app settings
**Important**: Always use `www.swarmsync.ai` (not `swarmsync.ai` without www)

### Issue: Registration succeeds but can't login

**Cause**: Backend is using in-memory storage (Map) which resets when the machine restarts
**Impact**: Users created before a restart will be lost
**Long-term Fix**: Implement proper database storage (this is planned Phase 1 work)

### Issue: API returns 404

**Cause**: API machine is stopped or not deployed
**Fix**: Start the machine or redeploy using commands from Fix 1

---

## 📝 Quick Command Reference

```powershell
# Navigate to project
cd C:\Users\Ben\Desktop\Github\Agent-Market

# Check deployments
flyctl apps list
flyctl status --app agent-market
flyctl status --app agent-market-api-divine-star-3849

# Start API machine
flyctl machine start 91850912c36518 --app agent-market-api-divine-star-3849

# Or redeploy API
flyctl deploy --config apps/api/fly.toml --app agent-market-api-divine-star-3849

# Redeploy frontend
flyctl deploy --config apps/web/fly.toml --app agent-market

# View logs
flyctl logs --app agent-market
flyctl logs --app agent-market-api-divine-star-3849

# Manage secrets
flyctl secrets list --app agent-market
flyctl secrets set KEY=value --app agent-market
```

---

## ✅ Success Criteria

After all fixes are applied, the following should work:

- [ ] Regular email/password registration creates account
- [ ] Regular email/password login works
- [ ] Google OAuth button is visible and clickable (not "unavailable")
- [ ] Google OAuth flow completes successfully
- [ ] GitHub OAuth button is visible and clickable (not "unavailable")
- [ ] GitHub OAuth flow completes successfully
- [ ] All login methods redirect to `/dashboard` after success
- [ ] API health endpoint returns 200 OK

---

## 🚀 Next Steps After Fixing

1. **Monitor for 24 hours** - Check logs for any authentication errors
2. **Test from different browsers** - Chrome, Firefox, Safari
3. **Test on mobile devices** - Both iOS and Android
4. **Implement database persistence** - Replace in-memory storage with PostgreSQL
5. **Add error logging** - Better visibility into authentication failures
6. **Set up monitoring** - Alerts for API downtime

---

## 📚 Related Documentation

- `GITHUB_OAUTH_FIX.md` - Specific GitHub OAuth callback URL fix
- `OAUTH_SETUP.md` - Original OAuth configuration guide
- `FIX_REGISTRATION_ISSUES.md` - Previous troubleshooting attempts
- `OAUTH_SETUP_STEP_BY_STEP.md` - Detailed OAuth provider setup

---

**Priority**: 🔴 CRITICAL - Blocks all user registration and login
**Estimated Fix Time**: 15-30 minutes
**Impact**: Once fixed, all login methods should work for new and existing users
