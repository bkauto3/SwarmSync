# CRITICAL FIX: Set Netlify Environment Variables

## Problem

Google/GitHub OAuth is failing because **NO environment variables are set in Netlify production**.

## ROOT CAUSE

The NextAuth configuration needs server-side secrets (GOOGLE_CLIENT_SECRET, GITHUB_CLIENT_SECRET, etc.) but they're not configured in Netlify, causing OAuth to fail with "missing-google-client-secret".

## IMMEDIATE FIX - Choose ONE method:

---

### METHOD 1: Netlify Web Dashboard (FASTEST - 5 minutes)

1. **Go to Netlify Dashboard:**
   - Open: https://app.netlify.com/sites/swarmsync/configuration/env

2. **Add each variable below:**
   Click "Add a variable" for each:

   ```
   Key: NEXTAUTH_SECRET
   Value: HNT0jWSyAGYkf3DAaUgpIUgfJdY7jwMW
   Scopes: ✅ All scopes (builds, functions, runtime, post-processing)
   Deploy contexts: ✅ Production
   ```

   ```
   Key: NEXTAUTH_URL
   Value: https://swarmsync.ai
   Scopes: ✅ All scopes
   Deploy contexts: ✅ Production
   ```

   ```
   Key: GOOGLE_CLIENT_ID
   Value: 1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com
   Scopes: ✅ All scopes
   Deploy contexts: ✅ Production
   ```

   ```
   Key: GOOGLE_CLIENT_SECRET
   Value: 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
   Scopes: ✅ All scopes
   Deploy contexts: ✅ Production
   Mark as secret: ✅ Yes
   ```

   ```
   Key: GITHUB_CLIENT_ID
   Value: Ov23lijhlbg5GGBJZyqp
   Scopes: ✅ All scopes
   Deploy contexts: ✅ Production
   ```

   ```
   Key: GITHUB_CLIENT_SECRET
   Value: 9970089f7d6588f60ed8c47b4251840137c6eb73
   Scopes: ✅ All scopes
   Deploy contexts: ✅ Production
   Mark as secret: ✅ Yes
   ```

   ```
   Key: DATABASE_URL
   Value: postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-aenonb7s.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require
   Scopes: ✅ All scopes
   Deploy contexts: ✅ Production
   Mark as secret: ✅ Yes
   ```

3. **Trigger New Deploy:**
   - Go to: https://app.netlify.com/sites/swarmsync/deploys
   - Click "Trigger deploy" > "Clear cache and deploy site"
   - Wait for deploy to complete (~3-5 minutes)

4. **Test:**
   - Go to: https://swarmsync.ai/login
   - Click "Continue with Google"
   - **VERIFY:** Browser redirects to accounts.google.com (NOT stays on same page)

---

### METHOD 2: Python Script (AUTOMATED - 2 minutes)

1. **Get Netlify Personal Access Token:**
   - Go to: https://app.netlify.com/user/applications/personal
   - Click "New access token"
   - Name it: "Environment Variable Setup"
   - Copy the token (starts with `nfp_...`)

2. **Run the script:**

   ```bash
   cd C:/Users/Ben/Desktop/Github/Agent-Market
   python set-netlify-env.py <YOUR_NETLIFY_TOKEN>
   ```

3. **Trigger New Deploy:**
   - Go to: https://app.netlify.com/sites/swarmsync/deploys
   - Click "Trigger deploy" > "Clear cache and deploy site"

4. **Test the login**

---

### METHOD 3: Netlify CLI (if you re-authenticate)

```bash
# Re-authenticate
netlify logout
netlify login

# Set variables
cd apps/web
netlify env:set NEXTAUTH_SECRET "HNT0jWSyAGYkf3DAaUgpIUgfJdY7jwMW" --context production
netlify env:set NEXTAUTH_URL "https://swarmsync.ai" --context production
netlify env:set GOOGLE_CLIENT_ID "1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com" --context production
netlify env:set GOOGLE_CLIENT_SECRET "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" --context production --secret
netlify env:set GITHUB_CLIENT_ID "Ov23lijhlbg5GGBJZyqp" --context production
netlify env:set GITHUB_CLIENT_SECRET "9970089f7d6588f60ed8c47b4251840137c6eb73" --context production --secret
netlify env:set DATABASE_URL "postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-aenonb7s.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require" --context production --secret

# Trigger deploy
netlify deploy --prod
```

---

## VERIFICATION CHECKLIST

After setting variables and deploying:

1. ✅ **Check env vars are set:**
   - Go to: https://app.netlify.com/sites/swarmsync/configuration/env
   - Verify all 7 variables exist

2. ✅ **Check deploy succeeded:**
   - Go to: https://app.netlify.com/sites/swarmsync/deploys
   - Latest deploy should be "Published"

3. ✅ **Test OAuth redirect:**
   - Open: https://swarmsync.ai/login
   - Click "Continue with Google"
   - Browser MUST redirect to `accounts.google.com`
   - NOT stay on same page

4. ✅ **Test full auth flow:**
   - Complete Google OAuth
   - Should redirect back to site
   - Should be logged in

5. ✅ **Test invite link:**
   - Open: https://swarmsync.ai/invite/4db223a6-93a2-4561-92e5-8561b32a72d5
   - Click "Continue with Google"
   - Complete OAuth
   - Should handle invite properly

---

## WHY THIS WAS FAILING

1. **Netlify had ZERO environment variables set** (verified with `netlify env:list`)
2. **NextAuth was using fallback values:**
   - `GOOGLE_CLIENT_SECRET` → "missing-google-client-secret"
   - This caused Google OAuth to reject the request
3. **The signin endpoint returned error:**
   - `Location: /login?error=google`
   - This is why clicking the button did nothing

## FILES CREATED

1. `apps/web/.env.production` - Template with all required variables
2. `set-netlify-env.py` - Automated script to set variables via API
3. This instruction file

## NEXT STEPS

**RECOMMENDED: Use METHOD 1 (Netlify Dashboard) - it's the fastest and most reliable.**

After variables are set and deployed, the OAuth redirect should work immediately.
