# OAuth Setup Guide - Fixing Google & GitHub Login

> **Status:** Deprecated (2025-11-22). Social login support was removed from the product, so this guide is retained only for historical reference.

## Current Issue

The OAuth login buttons show but fail with "redirect_uri_mismatch" errors because the redirect URIs aren't configured in your Google and GitHub OAuth apps.

## Production URLs

- **Frontend**: `https://agent-market.fly.dev` (or `https://www.swarmsync.ai` if configured)
- **GitHub Callback**: `https://agent-market.fly.dev/auth/github/callback`
- **Google OAuth**: Uses implicit flow, needs authorized JavaScript origins

## Fix Steps

### 1. Google OAuth Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** > **Credentials**
3. Find your OAuth 2.0 Client ID (the one matching `NEXT_PUBLIC_GOOGLE_CLIENT_ID`)
4. Click **Edit**

5. Under **Authorized JavaScript origins**, add:

   ```
   https://agent-market.fly.dev
   https://www.swarmsync.ai
   https://swarmsync.ai
   ```

6. Under **Authorized redirect URIs** (for implicit flow), add:

   ```
   https://agent-market.fly.dev
   https://www.swarmsync.ai
   https://swarmsync.ai
   ```

7. Click **Save**

### 2. GitHub OAuth Configuration

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click on your OAuth App (the one matching `NEXT_PUBLIC_GITHUB_CLIENT_ID`)
3. Find the **Authorization callback URL** field
4. Add:

   ```
   https://agent-market.fly.dev/auth/github/callback
   ```

   (Also add `https://www.swarmsync.ai/auth/github/callback` if you use that domain)

5. Click **Update application**

### 3. Verify Secrets Are Set

The following secrets should already be set in Fly.io (verified):

- ✅ `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- ✅ `GOOGLE_OAUTH_CLIENT_ID`
- ✅ `NEXT_PUBLIC_GITHUB_CLIENT_ID`
- ✅ `GITHUB_CLIENT_ID`
- ✅ `GITHUB_CLIENT_SECRET`

### 4. Test After Configuration

1. Wait 1-2 minutes for OAuth provider changes to propagate
2. Visit `https://agent-market.fly.dev/login`
3. Try clicking "Continue with Google" - should redirect to Google login
4. Try clicking "Continue with GitHub" - should redirect to GitHub login

## Troubleshooting

### Still getting redirect_uri_mismatch?

1. **Check the exact error**: The error message will show what redirect URI was attempted
2. **Verify domain matches**: Make sure you're using `agent-market.fly.dev` (not `agent-market-api-divine-star-3849.fly.dev`)
3. **Check for typos**: Redirect URIs are case-sensitive and must match exactly
4. **Wait for propagation**: OAuth provider changes can take 1-5 minutes to propagate

### Google OAuth still not working?

- Make sure you're using the **same Client ID** in both:
  - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (frontend)
  - `GOOGLE_OAUTH_CLIENT_ID` (backend)
- For implicit flow, the **Authorized JavaScript origins** is critical
- Check browser console for specific error messages

### GitHub OAuth still not working?

- Verify the callback URL matches exactly: `/auth/github/callback`
- Check that `GITHUB_CLIENT_SECRET` is set correctly
- Verify the GitHub OAuth app is not in "Development" mode if you need it to work for all users

## Additional Notes

- The app uses `@react-oauth/google` which handles the OAuth flow client-side
- GitHub uses a server-side callback route at `/api/auth/github/callback`
- Both flows eventually call the backend API to create/login users
