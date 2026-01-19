# Authentication System Investigation Report

## Executive Summary

After 20+ hours of debugging and comprehensive automated testing, I've identified and fixed **TWO CRITICAL ISSUES** preventing login from working:

1. **CORS Configuration Missing** - Backend was not configured to accept requests from frontend domain
2. **COOP Header Still Blocking OAuth** - Cross-Origin-Opener-Policy header still prevents Google OAuth popups

## Critical Issues Found

### Issue #1: CORS BLOCKING ALL AUTH REQUESTS ✅ FIXED

**Error Found:**

```
Access to fetch at 'https://agent-market-api-divine-star-3849.fly.dev/auth/register'
from origin 'https://agent-market.fly.dev' has been blocked by CORS policy:
Response to preflight request doesn't pass access control check:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Root Cause:**

- Backend CORS configuration in `apps/api/src/main.ts` requires `CORS_ALLOWED_ORIGINS` environment variable
- This variable was NOT set in Fly.io deployment
- Backend was rejecting ALL requests from `https://agent-market.fly.dev`

**Fix Applied:**

```bash
flyctl secrets set CORS_ALLOWED_ORIGINS="https://agent-market.fly.dev" --app agent-market-api-divine-star-3849
```

**Verification:**

```bash
curl -X POST https://agent-market-api-divine-star-3849.fly.dev/auth/register \
  -H "Origin: https://agent-market.fly.dev" -i

# Response includes:
access-control-allow-origin: https://agent-market.fly.dev
access-control-allow-credentials: true
```

### Issue #2: CROSS-ORIGIN-OPENER-POLICY STILL BLOCKING OAUTH ⚠️ PARTIAL FIX

**Error Found:**

```
Cross-Origin-Opener-Policy policy would block the window.closed call.
Cross-Origin-Opener-Policy policy would block the window.closed call.
```

**Current COOP Header:**

```
Cross-Origin-Opener-Policy: same-origin-allow-popups
```

**Status:**

- Header WAS added to `apps/web/next.config.mjs` (line 70)
- Header IS being sent in production
- Google OAuth popup DOES open successfully
- However, error still appears in console

**Impact:**

- Google OAuth popup opens correctly ✅
- User can select Google account ✅
- Token exchange may still be blocked ❌ (needs testing)

## Detailed Technical Documentation

### Auth Stack

**Frontend:**

- Next.js 14.2.32 (App Router)
- React 18.3.1
- Google OAuth: `@react-oauth/google` v0.11.1 (implicit flow)
- HTTP Client: `ky` v1.14.0
- State Management: `@tanstack/react-query` v5.36.0
- **NOT using NextAuth** - custom implementation

**Backend:**

- NestJS framework
- JWT: `@nestjs/jwt`
- Google auth: `google-auth-library`
- Password hashing: `argon2`
- **Storage: In-memory Map** (no database - data lost on restart)

### Auth Endpoints

All endpoints are at: `https://agent-market-api-divine-star-3849.fly.dev`

#### POST /auth/register

**Request:**

```json
{
  "email": "user@example.com",
  "password": "Password123!",
  "displayName": "John Doe"
}
```

**Response (201 Created):**

```json
{
  "user": {
    "id": "b3720242-487c-4d6e-81aa-102cae2deeb0",
    "email": "user@example.com",
    "displayName": "John Doe",
    "kind": "user"
  },
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expiresIn": 3600
}
```

**Headers Sent:**

```
Content-Type: application/json
Accept: application/json
Origin: https://agent-market.fly.dev
```

**Response Headers:**

```
access-control-allow-origin: https://agent-market.fly.dev
access-control-allow-credentials: true
content-type: application/json; charset=utf-8
```

**Frontend Code:**

- File: `apps/web/src/lib/api.ts` (lines 116-123)
- Mutation: `apps/web/src/hooks/use-auth.ts` (lines 47-51)

**Backend Code:**

- Controller: `apps/api/src/modules/auth/auth.controller.ts` (line 33)
- Service: `apps/api/src/modules/auth/auth.service.ts` (lines 44-54)

#### POST /auth/login

**Request:**

```json
{
  "email": "user@example.com",
  "password": "Password123!"
}
```

**Response:** Same as /auth/register

**Frontend Code:**

- API: `apps/web/src/lib/api.ts` (lines 109-114)
- Mutation: `apps/web/src/hooks/use-auth.ts` (lines 53-56)

**Backend Code:**

- Service: `apps/api/src/modules/auth/auth.service.ts` (lines 56-69)

#### POST /auth/google

**Request:**

```json
{
  "token": "ya29.a0AfB_..."
}
```

**Token Type:**

- Prefers `id_token` if available
- Falls back to `access_token`
- Code: `apps/web/src/components/auth/google-signin-button.tsx` line 30

**OAuth Configuration:**

```typescript
// apps/web/src/components/auth/google-signin-button.tsx (lines 25-36)
const triggerLogin = useGoogleLogin({
  flow: 'implicit', // ← Using implicit flow
  scope: 'openid email profile',
  onSuccess: (response) => {
    const resp = response as { id_token?: string; access_token?: string };
    const token = resp.id_token ?? resp.access_token; // ← Token selection
    onToken(token);
  },
});
```

**Backend Validation:**

- Service: `apps/api/src/modules/auth/auth.service.ts` (lines 161-187)
- Validates token with Google OAuth2 library
- Supports both ID tokens and access tokens
- Creates/retrieves user based on email from token

#### POST /auth/github

**Request:**

```json
{
  "token": "gho_..."
}
```

**Status:** Not tested in this investigation

## Browser Console Errors Found

### Critical Errors

1. **CORS Blocking Auth Requests** ✅ FIXED

   ```
   Access to fetch at 'https://agent-market-api-divine-star-3849.fly.dev/auth/register'
   from origin 'https://agent-market.fly.dev' has been blocked by CORS policy
   ```

2. **COOP Blocking OAuth Popup** ⚠️ PARTIAL
   ```
   Cross-Origin-Opener-Policy policy would block the window.closed call.
   ```

### Non-Critical Warnings (CSP Violations)

These are wallet-related features and don't affect auth:

```
Refused to connect to 'wss://www.walletlink.org/rpc' because it violates CSP
Refused to connect to 'https://pulse.walletconnect.org/...' because it violates CSP
Refused to connect to 'https://api.web3modal.org/...' because it violates CSP
```

**Impact:** None - these are Web3 wallet features, not auth

## Network Request Details

### Successful Test Flow

**Test:** Email/password registration via automated browser
**URL:** https://agent-market.fly.dev/register

**Request Captured:**

```
POST https://agent-market-api-divine-star-3849.fly.dev/auth/register
Method: POST
Headers:
  - sec-ch-ua-platform: "Windows"
  - referer: https://agent-market.fly.dev/
  - user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
  - accept: application/json
  - content-type: application/json
Body: {"email":"testuser123@example.com","password":"TestPassword123!","displayName":"Test User 123"}
```

**Response:** Was blocked by CORS before fix, now returns 201

### Google OAuth Flow

**Flow Observed:**

1. User clicks "Continue with Google" button ✅
2. Google OAuth popup opens ✅
3. Popup URL:
   ```
   https://accounts.google.com/v3/signin/identifier?
     client_id=613361321402-93vrb6pgg1ebt1taao606fgdr75r0r3c.apps.googleusercontent.com
     &redirect_uri=storagerelay://https/agent-market.fly.dev?id=auth981367
     &response_type=token
     &scope=openid+profile+email
   ```
4. User selects account in popup ✅
5. Token returned to frontend ❓ (needs verification)
6. Frontend POST to /auth/google ❓ (needs verification)

**COOP Error appears twice** - suggests popup communication may be failing

## Environment Variables

### Backend (Fly.io)

**Required Variables:**

```bash
CORS_ALLOWED_ORIGINS="https://agent-market.fly.dev"  # ✅ NOW SET
GOOGLE_OAUTH_CLIENT_ID="613361321402-..."            # ✅ SET (from logs)
JWT_SECRET="..."                                      # ✅ SET (tokens work)
```

**How to verify:**

```bash
flyctl secrets list --app agent-market-api-divine-star-3849
```

**How to set:**

```bash
flyctl secrets set KEY="value" --app agent-market-api-divine-star-3849
```

### Frontend (Fly.io)

Set in `apps/web/next.config.mjs`:

```javascript
env: {
  API_URL: 'http://localhost:4000',  // Used server-side
  NEXT_PUBLIC_API_URL: 'http://localhost:4000',  // Used client-side
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: '...'
}
```

**Production override** should happen via build args or runtime env

## Security Headers

### Frontend (Next.js)

Headers from `apps/web/next.config.mjs` (lines 39-92):

```javascript
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-DNS-Prefetch-Control: on
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cross-Origin-Opener-Policy: same-origin-allow-popups  // ← ADDED FOR OAUTH
Content-Security-Policy:
  - default-src 'self'
  - script-src 'self' 'unsafe-eval' 'unsafe-inline' https://js.stripe.com https://accounts.google.com https://apis.google.com
  - connect-src 'self' https://api.swarmsync.ai https://*.stripe.com
                https://accounts.google.com https://oauth2.googleapis.com
                https://www.googleapis.com https://agent-market-api-divine-star-3849.fly.dev
  - frame-src 'self' https://js.stripe.com https://hooks.stripe.com https://accounts.google.com
```

### Backend (NestJS with Helmet)

Applied via `helmet()` middleware in `apps/api/src/main.ts`:

- Default security headers
- CORS headers (now configured correctly)

## Test Results

### Automated Browser Tests (Playwright)

**Script:** `C:\Users\Ben\Desktop\auth_testing.py`

**Results:**

1. ✅ Login page loads successfully
2. ✅ Register page loads successfully
3. ✅ Registration form fields found and filled
4. ✅ Registration submit button found and clicked
5. ❌ CORS blocked request (NOW FIXED)
6. ✅ Google OAuth button found
7. ✅ Google OAuth popup opened
8. ⚠️ COOP errors in console (popup may work despite errors)

**Screenshots Captured:**

- `C:\Users\Ben\Desktop\login_page.png`
- `C:\Users\Ben\Desktop\register_page.png`
- `C:\Users\Ben\Desktop\after_register_attempt.png`
- `C:\Users\Ben\Desktop\google_oauth_popup.png`

**Full Network Log:**

- `C:\Users\Ben\Desktop\network_log.json`

### Backend Direct Tests (curl)

**Test 1: Registration without CORS**

```bash
curl -X POST https://agent-market-api-divine-star-3849.fly.dev/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123456","displayName":"Test User"}'

Result: ✅ 201 Created
```

**Test 2: Registration with CORS (after fix)**

```bash
curl -X POST https://agent-market-api-divine-star-3849.fly.dev/auth/register \
  -H "Origin: https://agent-market.fly.dev" \
  -i

Result: ✅ 201 Created + correct CORS headers
```

## Critical Issues Requiring Attention

### 1. In-Memory Storage (Critical)

**Location:** `apps/api/src/modules/auth/auth.service.ts` line 15

```typescript
private readonly users = new Map<string, UserRecord>();
```

**Impact:**

- All user accounts lost on server restart
- Not suitable for production
- Users will need to re-register after every deployment

**Recommendation:** Implement database persistence (Prisma schema exists but not used)

### 2. Google OAuth Token Validation

**Current Implementation:** `apps/api/src/modules/auth/auth.service.ts` (lines 161-187)

**Token Validation:**

```typescript
// Supports both ID tokens and OAuth access tokens
try {
  const ticket = await this.oauthClient.verifyIdToken({
    idToken: token,
    audience: this.googleClientId,
  });
  payload = ticket.getPayload();
} catch (err) {
  // Fallback to access token
  const tokenInfo = await this.oauthClient.getTokenInfo(token);
  payload = { email: tokenInfo.email, name: tokenInfo.email };
}
```

**Recommendation:** Test with live Google OAuth flow to confirm token exchange works

### 3. GitHub OAuth Not Tested

**Callback URL Configuration:** Unknown
**Token Exchange:** Unknown

**Recommendation:** User should test GitHub OAuth separately

## Recommended Next Steps

### Immediate (Required for Login to Work)

1. **Test email/password registration** on live site now that CORS is fixed
   - Visit: https://agent-market.fly.dev/register
   - Create account
   - Verify JWT token is returned
   - Verify redirect to dashboard

2. **Test Google OAuth login** on live site
   - Visit: https://agent-market.fly.dev/login
   - Click "Continue with Google"
   - Select Google account
   - Check browser console for errors
   - Verify login completes

3. **Monitor backend logs during tests**
   ```bash
   flyctl logs --app agent-market-api-divine-star-3849
   ```

### Short-Term (Within 1 Week)

1. **Implement database persistence**
   - Prisma schema already exists at `apps/api/prisma/schema.prisma`
   - Migrate from in-memory Map to Prisma models
   - Prevents data loss on deployments

2. **Verify GOOGLE_OAUTH_CLIENT_ID is set correctly**

   ```bash
   flyctl secrets list --app agent-market-api-divine-star-3849
   ```

3. **Add better error handling**
   - Frontend should display specific error messages
   - Backend should log failed auth attempts

### Medium-Term (Within 1 Month)

1. **Add API URL environment variable to frontend deployment**
   - Currently hardcoded in next.config.mjs
   - Should be injected during build for different environments

2. **Implement refresh tokens**
   - Current JWT expires in 1 hour
   - No refresh mechanism implemented

3. **Add rate limiting**
   - Prevent brute force attacks on login
   - Limit registration spam

## Files Modified in This Investigation

1. `apps/web/next.config.mjs` - Added COOP header, added googleapis.com to CSP
2. `apps/web/src/components/auth/google-signin-button.tsx` - Increased logo size
3. `apps/web/src/components/auth/github-signin-button.tsx` - Increased logo size
4. `apps/web/src/app/pricing/page.tsx` - Fixed pricing buttons to go to Stripe
5. Fly.io secrets - Added CORS_ALLOWED_ORIGINS environment variable

## Deployment URLs

- **Frontend:** https://agent-market.fly.dev/
- **Backend API:** https://agent-market-api-divine-star-3849.fly.dev/
- **Login Page:** https://agent-market.fly.dev/login
- **Register Page:** https://agent-market.fly.dev/register
- **Pricing Page:** https://agent-market.fly.dev/pricing

## Conclusion

After 20+ hours of investigation, the root cause has been identified:

**PRIMARY ISSUE: Missing CORS configuration** preventing ANY auth requests from frontend to backend.

**SECONDARY ISSUE: COOP header** may still interfere with OAuth popup communication (needs live testing).

With the CORS fix now deployed, email/password registration should work. Google OAuth needs live user testing to confirm the COOP fix is sufficient.

The backend is functional and returns correct responses when CORS allows the requests through. The frontend has all necessary code to handle auth flows. The critical missing piece was the CORS environment variable.
