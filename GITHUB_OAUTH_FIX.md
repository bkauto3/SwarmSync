# GitHub OAuth Fix - Simple Instructions

> **Status:** Deprecated (2025-11-22). GitHub OAuth was removed from SwarmSync/Agent Market — keep this doc for history only.

## The Problem

GitHub only allows **ONE** callback URL, but your app was trying to use different URLs depending on whether you visit `www.swarmsync.ai` or `swarmsync.ai`.

## The Fix

I've updated the code to **always use** `https://www.swarmsync.ai/auth/github/callback` no matter which URL you visit.

## What You Need to Do

### Step 1: Update GitHub OAuth Settings

1. Go to: **https://github.com/settings/developers**
2. Click **"OAuth Apps"**
3. Click on your OAuth app name
4. Click **"Edit"** or **"Update application"**
5. Find **"Authorization callback URL"**
6. Make sure it says EXACTLY this (and nothing else):
   ```
   https://www.swarmsync.ai/auth/github/callback
   ```
7. Click **"Update application"**

### Step 2: Redeploy the Frontend

The code change needs to be deployed. Run this command:

```powershell
cd C:\Users\Ben\Desktop\Github\Agent-Market
flyctl deploy --app agent-market
```

This will take about 5 minutes.

### Step 3: Test

1. Wait 2-3 minutes after deployment
2. Go to: **https://www.swarmsync.ai/login** (use www)
3. Try GitHub login - should work now!

---

## Why This Works

- Before: App used whatever URL you visited (`www` or non-`www`)
- Now: App always uses `www.swarmsync.ai`
- GitHub: Only needs one URL registered (the `www` one)

This way, no matter which domain you visit, GitHub login will always use the same callback URL that's registered in GitHub.
