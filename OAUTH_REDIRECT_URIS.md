# OAuth Redirect URIs Configuration

## Google Cloud Console

**CRITICAL:** Verify these redirect URIs are configured in your Google Cloud Console OAuth app.

1. Go to: https://console.cloud.google.com/apis/credentials
2. Find your OAuth 2.0 Client ID: `1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com`
3. Click "Edit" on the OAuth client
4. Under "Authorized redirect URIs", ensure these exist:

   ```
   https://swarmsync.ai/api/auth/callback/google
   http://localhost:3000/api/auth/callback/google (for local dev)
   ```

5. Save changes

## GitHub OAuth App

**CRITICAL:** Verify redirect URI in GitHub OAuth app settings.

1. Go to: https://github.com/settings/developers
2. Find your OAuth App with Client ID: `Ov23lijhlbg5GGBJZyqp`
3. Edit the app
4. Set "Authorization callback URL" to:

   ```
   https://swarmsync.ai/api/auth/callback/github
   ```

5. For local development, create a second OAuth app with:
   ```
   http://localhost:3000/api/auth/callback/github
   ```

## How to Verify After Setting Netlify Env Vars

1. **Open browser dev tools (F12)**
2. **Go to Network tab**
3. **Navigate to:** https://swarmsync.ai/login
4. **Click "Continue with Google"**
5. **Watch for redirect:**
   - Should see request to `/api/auth/signin/google`
   - Should get 302 redirect to `accounts.google.com`
   - URL should contain `client_id=1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr`

If you see `error=google` in the URL, the OAuth configuration is still wrong.

## Testing Checklist

- [ ] Netlify environment variables set (all 7 variables)
- [ ] New deploy triggered and completed
- [ ] Google OAuth redirect URIs configured
- [ ] GitHub OAuth redirect URI configured
- [ ] Browser redirects to accounts.google.com when clicking "Continue with Google"
- [ ] Can complete full OAuth flow
- [ ] Can log in successfully
- [ ] Invite links work with OAuth
