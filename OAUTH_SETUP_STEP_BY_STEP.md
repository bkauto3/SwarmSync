# OAuth Setup - Complete Step-by-Step Guide

> **Status:** Deprecated (2025-11-22). Google/GitHub OAuth have been removed from the live stack; keep this walkthrough only for historical tracing.

## What We're Fixing

Your login buttons (Google and GitHub) don't work because the websites need to know your production website URL is allowed. We're going to add your website URL to both Google and GitHub's settings.

---

## PART 1: Fix Google Login

### Step 1: Open Google Cloud Console

1. Open your web browser (Chrome, Firefox, Edge, etc.)
2. Go to this website: **https://console.cloud.google.com/**
3. If you're not logged in, sign in with your Google account (the same one you used to create the OAuth app)

### Step 2: Find Your Project

1. At the very top of the page, you'll see a dropdown that says something like "Select a project" or shows a project name
2. Click on that dropdown
3. Select the project that contains your OAuth app (if you're not sure which one, try each one until you find the right one)

### Step 3: Navigate to Credentials

1. On the left side of the page, you'll see a menu. Look for **"APIs & Services"**
2. Click on **"APIs & Services"**
3. A submenu will appear. Click on **"Credentials"** (it's usually the first option)

### Step 4: Find Your OAuth Client

1. You'll see a list of credentials. Look for one that says **"OAuth 2.0 Client IDs"** in the "Type" column
2. You might see multiple - that's okay, we'll check them one by one
3. Click on the name of the OAuth client (it might be called something like "Web client" or "Client 1" or have a custom name)

### Step 5: Edit the OAuth Client

1. You'll see a page with details about your OAuth client
2. Look for a button that says **"EDIT"** or **"EDIT OAuth CLIENT"** - it's usually at the top right
3. Click that button

### Step 6: Add Authorized JavaScript Origins

1. Scroll down until you see a section called **"Authorized JavaScript origins"**
2. You'll see a list (it might be empty or have some URLs already)
3. Click the **"+ ADD URI"** button (or if the list is empty, you'll see a text box)
4. Type this EXACTLY (copy and paste to avoid typos):
   ```
   https://www.swarmsync.ai
   ```
5. Press Enter or click outside the box
6. Click **"+ ADD URI"** again and add:
   ```
   https://swarmsync.ai
   ```
7. (Optional) If you also use the Fly.io default domain for testing, add:
   ```
   https://agent-market.fly.dev
   ```

### Step 7: Add Authorized Redirect URIs

1. Scroll down a bit more to find **"Authorized redirect URIs"**
2. Click **"+ ADD URI"**
3. Type this EXACTLY:
   ```
   https://www.swarmsync.ai
   ```
4. Press Enter
5. Click **"+ ADD URI"** again and add:
   ```
   https://swarmsync.ai
   ```
6. (Optional) If you also use the Fly.io default domain for testing, add:
   ```
   https://agent-market.fly.dev
   ```

### Step 8: Save Your Changes

1. Scroll all the way to the bottom of the page
2. Look for a button that says **"SAVE"** (usually blue, on the right side)
3. Click **"SAVE"**
4. You should see a message saying it was saved successfully

**✅ Google OAuth is now configured!**

---

## PART 2: Fix GitHub Login

### Step 1: Open GitHub Developer Settings

1. Open your web browser
2. Go to: **https://github.com/settings/developers**
3. If you're not logged in, sign in with your GitHub account

### Step 2: Find Your OAuth App

1. You'll see a page with different sections. Look for **"OAuth Apps"** (it might be in a list on the left or as a card on the page)
2. Click on **"OAuth Apps"**
3. You'll see a list of your OAuth applications
4. Click on the name of the app you're using (it might be called "Agent Market" or something similar)

### Step 3: Edit the OAuth App

1. You'll see a page with your app's details
2. Look for a button that says **"Edit"** or **"Update application"** - usually at the top right
3. Click that button

### Step 4: Add the Callback URL

1. Scroll down to find a field called **"Authorization callback URL"**
2. You might see a text box with some URL already in it (like `http://localhost:3000/auth/github/callback`)
3. Click in that text box
4. Add a new line (press Enter) or replace it with:

   ```
   https://www.swarmsync.ai/auth/github/callback
   ```

   **IMPORTANT:** Make sure you include `/auth/github/callback` at the end - that's the exact path your app uses

5. Add another line for the non-www version:

   ```
   https://swarmsync.ai/auth/github/callback
   ```

6. If you have multiple URLs (like localhost for development), you can keep both - just put each on its own line:
   ```
   http://localhost:3000/auth/github/callback
   https://www.swarmsync.ai/auth/github/callback
   https://swarmsync.ai/auth/github/callback
   ```
   (Optional: If you also use the Fly.io default domain, add: `https://agent-market.fly.dev/auth/github/callback`)

### Step 5: Save Your Changes

1. Scroll to the bottom of the page
2. Look for a button that says **"Update application"** or **"Save"** (usually green)
3. Click that button
4. You should see a confirmation message

**✅ GitHub OAuth is now configured!**

---

## PART 3: Test It Out

### Wait a Moment

1. OAuth changes can take 1-2 minutes to take effect
2. Wait about 2 minutes after saving both changes

### Test Google Login

1. Go to: **https://www.swarmsync.ai/login** (or **https://swarmsync.ai/login**)
2. Click the **"Continue with Google"** button
3. You should be redirected to Google's login page (not see an error)
4. If you see an error, wait another minute and try again

### Test GitHub Login

1. Still on the login page: **https://www.swarmsync.ai/login** (or **https://swarmsync.ai/login**)
2. Click the **"Continue with GitHub"** button
3. You should be redirected to GitHub's login page (not see an error)
4. If you see an error, wait another minute and try again

---

## Troubleshooting

### "I can't find my OAuth app in Google Cloud Console"

- Make sure you're logged into the correct Google account
- Check if you have multiple Google accounts - try switching accounts
- Look in the project dropdown at the top - you might have created it in a different project

### "I can't find my OAuth app in GitHub"

- Make sure you're logged into the correct GitHub account
- Check if you're looking at "OAuth Apps" (not "GitHub Apps" - those are different)
- If you created it under an organization, you might need to go to that organization's settings

### "The buttons still don't work after 5 minutes"

- Double-check that you typed the URLs EXACTLY as shown (no extra spaces, correct spelling)
- Make sure you clicked "Save" or "Update" on both sites
- Try clearing your browser cache (Ctrl+Shift+Delete, then clear cached images and files)
- Try opening the login page in an incognito/private window

### "I see a different error message"

- Take a screenshot of the error
- The error message will tell us what's wrong - common issues:
  - "redirect_uri_mismatch" = The URL you added doesn't match what the app is trying to use
  - "invalid_client" = The Client ID might be wrong
  - "access_denied" = You might have denied permissions

---

## What Each URL Does

- **`https://www.swarmsync.ai`** = Your main production website URL (with www)
- **`https://swarmsync.ai`** = Your main production website URL (without www)
- **`/auth/github/callback`** = The specific page GitHub sends users back to after they log in
- **Authorized JavaScript origins** = Where your website is allowed to run from (for Google)
- **Authorization callback URL** = Where GitHub sends users after they approve login (for GitHub)

**Note:** `agent-market.fly.dev` is just the default Fly.io domain. Your actual website that users visit is `swarmsync.ai`, so that's what needs to be in the OAuth settings.

---

## Need More Help?

If you get stuck at any step:

1. Take a screenshot of what you're seeing
2. Note which step number you're on
3. Describe what happens when you try to proceed

The most common mistake is typos in the URLs - make sure to copy and paste them exactly as shown above!
