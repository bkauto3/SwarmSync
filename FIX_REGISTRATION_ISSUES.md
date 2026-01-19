# Fix Registration Issues - Step by Step

> **Status:** Updated (2025-11-22). Google/GitHub login has been removed — ignore any references to social providers below; the remaining steps apply only to email/password flows.

## Problem 1: API Not Running (Why Google Login Fails After OAuth)

Your backend API isn't deployed, so when Google login tries to register you, it can't connect to the server.

## Problem 2: GitHub Redirect URI Mismatch

The app uses the exact URL you're visiting. If you're on `swarmsync.ai`, it needs that exact URL in GitHub settings. If you're on `www.swarmsync.ai`, it needs that one.

---

## FIX 1: Deploy the API (This is why registration fails)

The API deployment failed earlier. We need to finish deploying it.

### Step 1: Check if the build is still running

1. Open PowerShell or Command Prompt
2. Navigate to your project folder:
   ```
   cd C:\Users\Ben\Desktop\Github\Agent-Market
   ```
3. Check the deployment status:
   ```
   flyctl releases --app agent-market-api-divine-star-3849
   ```

### Step 2: If no releases exist, deploy the API

1. Make sure you're in the project root folder
2. Run this command:
   ```
   flyctl deploy --config apps/api/fly.toml --app agent-market-api-divine-star-3849
   ```
3. This will take 5-10 minutes. Watch for any errors.
4. If it fails, let me know the error message.

---

## FIX 2: Fix GitHub Redirect URI (Make sure BOTH URLs are added)

The app uses whatever URL you're visiting. You need to add BOTH versions to GitHub.

### Step 1: Go to GitHub OAuth Settings

1. Go to: **https://github.com/settings/developers**
2. Click **"OAuth Apps"**
3. Click on your OAuth app name

### Step 2: Edit the Callback URL

1. Click **"Edit"** or **"Update application"**
2. Find **"Authorization callback URL"**
3. Make sure you have BOTH of these URLs (each on its own line):
   ```
   https://www.swarmsync.ai/auth/github/callback
   https://swarmsync.ai/auth/github/callback
   ```
4. **IMPORTANT:**
   - If you're visiting `www.swarmsync.ai`, GitHub needs that exact URL
   - If you're visiting `swarmsync.ai` (without www), GitHub needs that exact URL
   - Add BOTH to be safe
5. Click **"Update application"**

### Step 3: Test

1. Wait 1-2 minutes
2. Go to: **https://www.swarmsync.ai/login** (try with www)
3. Try GitHub login
4. If it still fails, try: **https://swarmsync.ai/login** (without www)
5. The one that works is the one you need to make sure is in GitHub settings

---

## Quick Checklist

- [ ] API is deployed (check with `flyctl machines list --app agent-market-api-divine-star-3849` - should show at least 1 machine)
- [ ] GitHub OAuth has BOTH callback URLs:
  - `https://www.swarmsync.ai/auth/github/callback`
  - `https://swarmsync.ai/auth/github/callback`
- [ ] Google OAuth has BOTH origins:
  - `https://www.swarmsync.ai`
  - `https://swarmsync.ai`

---

## After Fixing

1. Wait 2-3 minutes for changes to take effect
2. Try Google login again - should work now that API is running
3. Try GitHub login - should work now that both URLs are configured
4. If still having issues, check browser console (F12) for error messages
