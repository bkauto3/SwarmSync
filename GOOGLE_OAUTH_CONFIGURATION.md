# 🔐 Google Cloud OAuth Configuration

**Complete guide to configuring Google OAuth for SwarmSync**

---

## 📋 Current Configuration Review

Based on your Google Cloud Console screenshot, here's what needs to be verified/updated:

---

## ✅ Required Configuration

### **1. Authorized JavaScript Origins**

These domains are allowed to initiate OAuth requests:

```
https://swarmsync.ai
https://www.swarmsync.ai
http://localhost:3000 (for local development)
```

**How to Add**:

1. Go to https://console.cloud.google.com
2. Select your project
3. Navigate to: APIs & Services → Credentials
4. Click on your OAuth 2.0 Client ID
5. Scroll to "Authorized JavaScript origins"
6. Click "ADD URI"
7. Add each origin above
8. Click "Save"

---

### **2. Authorized Redirect URIs**

These are the callback URLs where Google sends users after authentication:

```
https://swarmsync.ai/api/auth/callback/google
https://swarmsync.ai/callback
https://www.swarmsync.ai/api/auth/callback/google
https://www.swarmsync.ai/callback
http://localhost:3000/api/auth/callback/google (for local development)
http://localhost:3000/callback (for local development)
```

**How to Add**:

1. In the same OAuth 2.0 Client ID settings
2. Scroll to "Authorized redirect URIs"
3. Click "ADD URI"
4. Add each redirect URI above
5. Click "Save"

---

## 🔍 Verification Checklist

### **Check Your Current Settings**

Based on the screenshot you provided, verify these are configured:

- [ ] **Client ID**: Starts with `*.apps.googleusercontent.com`
- [ ] **Client Secret**: Stored securely (never commit to git)
- [ ] **Application Type**: Web application
- [ ] **JavaScript Origins**: Includes `https://swarmsync.ai`
- [ ] **Redirect URIs**: Includes `https://swarmsync.ai/api/auth/callback/google`

---

## 🚨 Common Issues & Fixes

### **Issue 1: "redirect_uri_mismatch" Error**

**Symptom**: After clicking "Continue with Google", you see an error page saying the redirect URI doesn't match.

**Cause**: The redirect URI in your code doesn't match what's configured in Google Cloud Console.

**Fix**:

1. Check the error message for the exact redirect URI being used
2. Add that exact URI to "Authorized redirect URIs" in Google Cloud Console
3. Make sure there are no trailing slashes or typos
4. Wait 5 minutes for changes to propagate
5. Try again

---

### **Issue 2: "origin_mismatch" Error**

**Symptom**: OAuth popup is blocked or shows origin error.

**Cause**: The JavaScript origin isn't authorized.

**Fix**:

1. Add `https://swarmsync.ai` to "Authorized JavaScript origins"
2. Make sure protocol (https) matches exactly
3. No trailing slashes in origins
4. Save and wait 5 minutes

---

### **Issue 3: OAuth Consent Screen Not Configured**

**Symptom**: Users see "This app isn't verified" warning.

**Fix**:

1. Go to: APIs & Services → OAuth consent screen
2. Fill in required fields:
   - App name: SwarmSync
   - User support email: support@swarmsync.ai
   - Developer contact: your-email@example.com
3. Add scopes:
   - `userinfo.email`
   - `userinfo.profile`
4. Add test users (for testing mode)
5. Save

---

## 🔧 Environment Variables

Make sure these are set in your frontend environment:

### **Netlify (Production)**

```bash
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
NEXTAUTH_URL=https://swarmsync.ai
NEXTAUTH_SECRET=your-nextauth-secret
```

### **Local Development**

```bash
# apps/web/.env.local
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret
```

---

## 🧪 Testing OAuth Flow

### **Test Locally**

1. Start dev server: `npm run dev`
2. Visit http://localhost:3000/login
3. Click "Continue with Google"
4. Should redirect to Google login
5. After login, should redirect back to http://localhost:3000
6. Should be logged in

### **Test Production**

1. Visit https://swarmsync.ai/login
2. Click "Continue with Google"
3. Should redirect to Google login
4. After login, should redirect back to https://swarmsync.ai
5. Should be logged in
6. Check browser console for errors

---

## 📊 OAuth Flow Diagram

```
User clicks "Continue with Google"
    ↓
Frontend redirects to Google OAuth
    ↓
User logs in with Google
    ↓
Google redirects to: https://swarmsync.ai/api/auth/callback/google?code=...
    ↓
NextAuth exchanges code for tokens
    ↓
NextAuth creates session
    ↓
User redirected to dashboard
```

---

## 🔐 Security Best Practices

1. **Never commit secrets to git**
   - Use `.env.local` for local development
   - Use Netlify environment variables for production

2. **Use HTTPS in production**
   - All redirect URIs should use `https://`
   - Never use `http://` in production

3. **Restrict origins**
   - Only add domains you control
   - Don't use wildcards

4. **Rotate secrets regularly**
   - Change client secret every 6-12 months
   - Update in all environments

5. **Monitor OAuth usage**
   - Check Google Cloud Console for usage stats
   - Set up alerts for unusual activity

---

## 📝 Configuration Checklist

Before going live, verify:

- [ ] OAuth 2.0 Client ID created
- [ ] Client ID and Secret stored in environment variables
- [ ] JavaScript origins include `https://swarmsync.ai`
- [ ] Redirect URIs include `https://swarmsync.ai/api/auth/callback/google`
- [ ] OAuth consent screen configured
- [ ] App name and logo set
- [ ] Support email configured
- [ ] Scopes added (email, profile)
- [ ] Test users added (if in testing mode)
- [ ] Tested OAuth flow locally
- [ ] Tested OAuth flow in production
- [ ] No errors in browser console
- [ ] User can log in successfully
- [ ] User session persists after refresh

---

## 🆘 Troubleshooting

### **Still Getting Errors?**

1. **Check browser console**
   - Look for error messages
   - Check network tab for failed requests

2. **Check server logs**
   - Railway logs for API errors
   - Netlify logs for frontend errors

3. **Verify environment variables**
   - Make sure all variables are set
   - No typos in variable names
   - Values are correct (no extra spaces)

4. **Clear browser cache**
   - OAuth tokens may be cached
   - Try incognito mode

5. **Wait 5-10 minutes**
   - Google Cloud changes take time to propagate
   - Don't test immediately after saving

---

## 📞 Support

If you're still having issues:

1. Check Google Cloud Console error logs
2. Review NextAuth.js documentation: https://next-auth.js.org/providers/google
3. Check SwarmSync documentation
4. Contact support@swarmsync.ai

---

**See Also**:

- `IMMEDIATE_FIXES_GUIDE.md` - Step-by-step fixes
- `FIXES_SUMMARY.md` - Summary of all fixes
