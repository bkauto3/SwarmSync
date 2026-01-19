# Configure OAuth Providers - Step-by-Step Guide

> **Status:** Deprecated (2025-11-22). Google and GitHub sign-in have been removed from SwarmSync/Agent Market; keep this doc for historical reference only.

---

## 🔐 Part 1: Configure Google OAuth

### What "Authorized Origins" Means:

Google needs to know which websites are allowed to use your OAuth app. Think of it as a security whitelist - you're telling Google "these are my legitimate websites that can ask users to login with Google."

### Steps:

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/
   - Sign in with your Google account

2. **Navigate to Credentials**
   - In the left sidebar, click **"APIs & Services"**
   - Click **"Credentials"**

3. **Find Your OAuth Client**
   - Look for the OAuth 2.0 Client ID with this ID:
     ```
     613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com
     ```
   - Click on the name to edit it

4. **Add Authorized JavaScript Origins**

   You'll see a section called **"Authorized JavaScript origins"**

   Click **"+ ADD URI"** and add each of these URLs (one at a time):

   ```
   https://www.swarmsync.ai
   https://swarmsync.ai
   https://agent-market.fly.dev
   ```

   **Why all three?**
   - `www.swarmsync.ai` - Your main website with www
   - `swarmsync.ai` - Your website without www (in case users visit this way)
   - `agent-market.fly.dev` - Your Fly.io deployment URL (backup)

5. **Add Authorized Redirect URIs**

   Scroll down to **"Authorized redirect URIs"**

   Click **"+ ADD URI"** and add each of these URLs:

   ```
   https://www.swarmsync.ai
   https://swarmsync.ai
   https://agent-market.fly.dev
   ```

   **Note**: For the implicit OAuth flow used by Google, these should match the origins.

6. **Save Changes**
   - Click the **"SAVE"** button at the bottom
   - You should see a success message

7. **Wait for Changes to Propagate**
   - Google's changes typically take 1-5 minutes to take effect
   - Sometimes it can take up to 10 minutes

---

## 🐙 Part 2: Configure GitHub OAuth

### What "Callback URL" Means:

When a user clicks "Login with GitHub", they're sent to GitHub's website to authorize. After they approve, GitHub needs to know where to send them back to. That's the "callback URL" - it's the return address.

### Steps:

1. **Go to GitHub Developer Settings**
   - Visit: https://github.com/settings/developers
   - Sign in with your GitHub account if needed

2. **Navigate to OAuth Apps**
   - Click on **"OAuth Apps"** in the left sidebar
   - You should see your app in the list

3. **Find Your OAuth App**
   - Look for the app with Client ID: `Ov23lifZqAEEJxZmMD84`
   - Click on the app name to edit it

4. **Update Authorization Callback URL**

   You'll see a field called **"Authorization callback URL"**

   **IMPORTANT**: GitHub only allows ONE callback URL (unlike Google which allows multiple)

   Enter this EXACT URL:

   ```
   https://www.swarmsync.ai/auth/github/callback
   ```

   **Why this specific URL?**
   - Your code is hardcoded to always use `www.swarmsync.ai` for GitHub callbacks
   - This ensures consistency regardless of how users access your site
   - GitHub redirects users to this URL after they authorize

5. **Update Application**
   - Click the **"Update application"** button
   - You should see a success message

6. **Verify the Homepage URL (Optional)**

   While you're here, make sure these fields are correct:
   - **Homepage URL**: `https://www.swarmsync.ai`
   - **Application description**: (whatever you want to show users)

7. **Wait for Changes to Take Effect**
   - GitHub's changes are usually instant
   - But allow 1-2 minutes to be safe

---

## ✅ Verification Steps

### After Configuring Both Providers:

**Wait 2-5 minutes** for all changes to propagate, then:

### 1. Test Google Login

1. Open a **NEW incognito/private browser window**
2. Go to: `https://www.swarmsync.ai/login`
3. Look at the Google button:
   - ✅ **GOOD**: Shows "Continue with Google" (clickable)
   - ❌ **BAD**: Shows "Google login unavailable" (grayed out)
4. Click the Google button
5. You should be redirected to Google's login page
6. Sign in with your Google account
7. You should be redirected back to your dashboard

**If it fails:**

- Check the browser console (F12) for error messages
- Look for "redirect_uri_mismatch" or similar errors
- Make sure you added ALL the URLs to Google Cloud Console
- Wait another 2-3 minutes and try again

### 2. Test GitHub Login

1. Open a **NEW incognito/private browser window**
2. Go to: `https://www.swarmsync.ai/login` (use www!)
3. Look at the GitHub button:
   - ✅ **GOOD**: Shows "Continue with GitHub" (clickable)
   - ❌ **BAD**: Shows "GitHub login unavailable" (grayed out)
4. Click the GitHub button
5. You should be redirected to GitHub's authorization page
6. Click "Authorize" to give permission
7. You should be redirected back to your dashboard

**If it fails:**

- Check the URL in the error message
- Make sure the callback URL in GitHub settings is EXACTLY:
  `https://www.swarmsync.ai/auth/github/callback`
- Make sure you're visiting `www.swarmsync.ai` (with www)
- Check browser console for errors

### 3. Test Regular Registration

1. Go to: `https://www.swarmsync.ai/register`
2. Fill in:
   - Full name: `Test User`
   - Email: `test@example.com`
   - Password: `TestPassword123`
3. Click "Create account"
4. You should be redirected to the dashboard

---

## 🐛 Troubleshooting

### Google OAuth Issues

**Error: "redirect_uri_mismatch"**

- **Cause**: The URL you're visiting isn't in the authorized list
- **Solution**:
  1. Look at the error message - it shows the exact URL that was attempted
  2. Add that URL to Google Cloud Console → Authorized JavaScript Origins
  3. Wait 2-3 minutes and try again

**Button says "Google login unavailable"**

- **Cause**: Environment variables not set or not loaded
- **Solution**:
  1. Run: `flyctl secrets list --app agent-market`
  2. Verify `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is in the list
  3. If not, run the command from the main fix document
  4. Wait 2-3 minutes for the app to reload

**Can login but immediately logged out**

- **Cause**: Backend API not accepting the token
- **Solution**:
  1. Check API is running: `flyctl status --app agent-market-api-divine-star-3849`
  2. Check API logs: `flyctl logs --app agent-market-api-divine-star-3849`
  3. Look for error messages about Google token validation

### GitHub OAuth Issues

**Error: "The redirect_uri MUST match the registered callback URL"**

- **Cause**: Callback URL in GitHub doesn't match what the app is using
- **Solution**:
  1. Go to GitHub OAuth app settings
  2. Make sure callback URL is EXACTLY: `https://www.swarmsync.ai/auth/github/callback`
  3. No trailing slashes, must use `www`, must be HTTPS

**Button says "GitHub login unavailable"**

- **Cause**: Environment variables not set
- **Solution**:
  1. Run: `flyctl secrets list --app agent-market`
  2. Verify `NEXT_PUBLIC_GITHUB_CLIENT_ID` is in the list
  3. If not, run the command from the main fix document

**Callback completes but shows error**

- **Cause**: Backend API can't validate GitHub token
- **Solution**:
  1. Check API logs: `flyctl logs --app agent-market-api-divine-star-3849`
  2. Look for errors about GitHub token validation
  3. Verify `GITHUB_CLIENT_SECRET` is set correctly in the backend

### Registration Issues

**Registration succeeds but can't login later**

- **Cause**: Backend is using in-memory storage which resets on restart
- **Impact**: This is a known limitation - users are lost on API restart
- **Long-term Fix**: Implement proper database storage (Phase 1 work)
- **Workaround**: Keep the API running, or users need to re-register after restarts

---

## 📝 Quick Reference

### Your OAuth Credentials:

**Google:**

- Client ID: `613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com`
- Configure at: https://console.cloud.google.com/apis/credentials

**GitHub:**

- Client ID: `Ov23lifZqAEEJxZmMD84`
- Callback URL: `https://www.swarmsync.ai/auth/github/callback`
- Configure at: https://github.com/settings/developers

### Your Deployment URLs:

- **Website**: `https://www.swarmsync.ai`
- **API**: `https://api.swarmsync.ai` (points to agent-market-api-divine-star-3849.fly.dev)
- **Fly.io Apps**:
  - Frontend: `agent-market`
  - Backend: `agent-market-api-divine-star-3849`

### Useful Commands:

```powershell
# Check if services are running
flyctl status --app agent-market
flyctl status --app agent-market-api-divine-star-3849

# View logs
flyctl logs --app agent-market
flyctl logs --app agent-market-api-divine-star-3849

# Check environment variables
flyctl secrets list --app agent-market
flyctl secrets list --app agent-market-api-divine-star-3849
```

---

## ✨ Success Checklist

After completing all steps, verify:

- [ ] Google Cloud Console has all 3 URLs in authorized origins
- [ ] Google Cloud Console has all 3 URLs in redirect URIs
- [ ] GitHub OAuth app has callback URL set to `https://www.swarmsync.ai/auth/github/callback`
- [ ] Wait 2-5 minutes for changes to propagate
- [ ] Visit `https://www.swarmsync.ai/login` in incognito mode
- [ ] Google button shows "Continue with Google" (not "unavailable")
- [ ] GitHub button shows "Continue with GitHub" (not "unavailable")
- [ ] Google login works and redirects to dashboard
- [ ] GitHub login works and redirects to dashboard
- [ ] Regular registration works

---

**Need Help?**

- Check the browser console (F12) for error messages
- Check API logs: `flyctl logs --app agent-market-api-divine-star-3849`
- Refer to `LOGIN_ISSUES_DIAGNOSIS_AND_FIX.md` for detailed troubleshooting
