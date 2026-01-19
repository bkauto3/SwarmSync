# SwarmSync Routing & Auth Map

## Authentication System

- **Framework**: NextAuth.js + Custom JWT
- **Methods**:
  - Email/Password (JWT token in `auth_token` cookie)
  - OAuth (Google/GitHub via NextAuth session)
- **Guard Function**: `requireAuth()` from `/lib/auth-guard.ts`
- **Redirect Behavior**: Unauthenticated users → `/login?from={originalPath}`

---

## Route Map

### 🔓 PUBLIC ROUTES (No Auth Required)

| Route                        | Purpose                   | Type      | Notes                                                       |
| ---------------------------- | ------------------------- | --------- | ----------------------------------------------------------- |
| `/`                          | Landing page              | Marketing | Main homepage with CTAs                                     |
| `/demo/a2a`                  | Live A2A Transaction Demo | Demo      | **PRIMARY NO-LOGIN A2A DEMO** - Fully functional, no signup |
| `/demo/workflows`            | Workflow Builder Demo     | Demo      | Read-only workflow designer, can export JSON                |
| `/login`                     | Sign in page              | Auth      | Email/password + OAuth options                              |
| `/register`                  | Sign up page              | Auth      | Create new account                                          |
| `/pricing`                   | Pricing page              | Marketing | Subscription tiers                                          |
| `/platform`                  | Platform overview         | Marketing | Feature showcase                                            |
| `/agent-orchestration-guide` | Documentation             | Docs      | How-to guide                                                |
| `/security`                  | Security info             | Marketing | Security features                                           |
| `/use-cases`                 | Use cases                 | Marketing | Example scenarios                                           |
| `/faq`                       | FAQ                       | Marketing | Common questions                                            |
| `/privacy`                   | Privacy policy            | Legal     | Privacy terms                                               |
| `/terms`                     | Terms of service          | Legal     | ToS                                                         |

### 🔒 AUTHENTICATED ROUTES (Auth Required)

| Route                           | Purpose                   | Redirect Target | Notes                                       |
| ------------------------------- | ------------------------- | --------------- | ------------------------------------------- |
| `/console/overview`             | User dashboard home       | `/overview`     | Main authenticated landing page             |
| `/console/agents/*`             | Agent management          | `/overview`     | Create, view, edit agents                   |
| `/console/workflows`            | Workflow management       | `/overview`     | Create and run workflows                    |
| `/console/quality/test-library` | Test library              | `/overview`     | Agent testing suite                         |
| `/console/quality/outcomes`     | Outcomes tracking         | `/overview`     | Verification results                        |
| `/console/analytics/logs`       | System logs               | `/overview`     | Activity logs                               |
| `/console/settings/api-keys`    | API key management        | `/overview`     | Manage API keys                             |
| `/console/settings/limits`      | Rate limits               | `/overview`     | Usage limits                                |
| `/console/settings/profile`     | User profile              | `/overview`     | Account settings                            |
| `/console/test-a2a`             | Authenticated A2A test    | `/overview`     | Full A2A testing with real agents           |
| `/console/transactions`         | Transaction history       | `/overview`     | Payment history                             |
| `/console/billing`              | Billing                   | `/overview`     | Subscription management                     |
| `/console/wallet`               | Wallet                    | `/overview`     | Agent wallet management                     |
| `/agents`                       | Public agent marketplace  | N/A             | Browse public agents (may be auth-optional) |
| `/dashboard`                    | Legacy dashboard redirect | N/A             | Redirects to `/console/overview`            |
| `/overview`                     | Overview redirect         | N/A             | Redirects to `/console/overview`            |

---

## CTA Wiring Table

### Homepage CTAs (Current State)

| CTA Button Text                         | Current Link      | Should Link To    | Auth Required? | Notes                                       |
| --------------------------------------- | ----------------- | ----------------- | -------------- | ------------------------------------------- |
| "Run a Live A2A Transaction (No Login)" | `/demo/a2a`       | `/demo/a2a`       | ❌ No          | ✅ **CORRECT** - Fully functional demo      |
| "Explore Workflow Builder Demo"         | `/demo/workflows` | `/demo/workflows` | ❌ No          | ✅ **CORRECT** - Read-only workflow builder |
| "Start Free Trial"                      | `/register`       | `/register`       | ❌ No          | ✅ **CORRECT** - Sign up page               |

### Navigation Links (Navbar)

| Nav Link                       | Current Link | Should Link To      | Auth Required? | Notes                                                 |
| ------------------------------ | ------------ | ------------------- | -------------- | ----------------------------------------------------- |
| "Agents"                       | `/agents`    | `/agents`           | ⚠️ Optional    | Public marketplace (may require auth for full access) |
| "Dashboard"                    | `/dashboard` | `/console/overview` | ✅ Yes         | Redirects to console overview                         |
| "Log in"                       | `/login`     | `/login`            | ❌ No          | Sign in page                                          |
| "Get started"                  | `/register`  | `/register`         | ❌ No          | Sign up page                                          |
| "Console" (when authenticated) | `/dashboard` | `/console/overview` | ✅ Yes         | Main dashboard                                        |

---

## Demo Routes Deep Dive

### `/demo/a2a` - Live A2A Transaction Demo

- **Auth**: ❌ Not required
- **Type**: Fully functional demo
- **Features**:
  - Select requester & responder agents from demo pool
  - Configure service request and budget
  - Watch real-time negotiation, escrow, and payout
  - Transaction storyboard with timeline
  - Shareable demo runs via `?runId=` parameter
  - Session expires after 1 hour
- **API Endpoints**:
  - `GET /demo/a2a/agents` - Fetch demo agents
  - `POST /demo/a2a/run` - Create demo negotiation
  - `GET /demo/a2a/run/{runId}/logs` - Fetch demo logs and status
- **Fallback**: If API fails, shows sample successful run with mock data

### `/demo/workflows` - Workflow Builder Demo

- **Auth**: ❌ Not required
- **Type**: Read-only demo
- **Features**:
  - Browse workflow templates (Research→Summary, Support Triage, SEO Audit)
  - View/edit workflow JSON
  - Export workflow JSON for later import
  - Cannot execute workflows (requires signup)
- **CTA**: Prompts to create account to run workflows

---

## Recommended CTA Updates

### ✅ No Changes Needed

All current CTAs are correctly wired:

1. **"Run a Live A2A Transaction (No Login)"** → `/demo/a2a` ✅
2. **"Explore Workflow Builder Demo"** → `/demo/workflows` ✅
3. **"Start Free Trial"** → `/register` ✅

### Optional Enhancements

If you want to add more CTAs, consider:

| New CTA                           | Link To                      | Purpose                   |
| --------------------------------- | ---------------------------- | ------------------------- |
| "View Agent Marketplace"          | `/agents`                    | Browse public agents      |
| "Read Documentation"              | `/agent-orchestration-guide` | Learn how to use platform |
| "See Pricing"                     | `/pricing`                   | View subscription tiers   |
| "Go to Dashboard" (authenticated) | `/console/overview`          | Access user console       |

---

## Auth Flow Summary

```
Unauthenticated User
│
├─ Visits public route (/, /demo/*, /pricing, etc.)
│  └─ ✅ Access granted
│
├─ Visits /login or /register
│  └─ ✅ Access granted (auth pages)
│
└─ Visits /console/* or other protected route
   └─ ❌ Redirected to /login?from={originalPath}
      │
      └─ After successful login
         └─ ✅ Redirected to original path or /console/overview
```

---

## API Integration Notes

### Demo A2A Endpoints

- **Base URL**: Configured in `@/lib/api.ts` as `API_BASE_URL`
- **Demo Agent Pool**: Backend enforces `DEMO_AGENT_IDS` allowlist
- **Fallback Strategy**: If `/demo/a2a/agents` fails, falls back to `/agents?status=APPROVED&visibility=PUBLIC&limit=8`
- **Session Management**: Demo runs expire after 1 hour, tracked by `runId`

### Authentication Endpoints

- **Login**: `POST /auth/login` (email/password)
- **Register**: `POST /auth/register`
- **OAuth**: Handled by NextAuth.js (`/api/auth/*`)

---

## Copy/Paste Ready: Current CTA Configuration

```tsx
// Homepage CTAs (apps/web/src/app/page.tsx)
<Button size="lg" className="hover-lift" asChild>
  <Link href="/demo/a2a">Run a Live A2A Transaction (No Login)</Link>
</Button>

<Button size="lg" variant="outline" className="hover-lift" asChild>
  <Link href="/demo/workflows">Explore Workflow Builder Demo</Link>
</Button>

<Button size="lg" className="hover-lift" asChild>
  <Link href="/register">Start Free Trial</Link>
</Button>
```

```tsx
// Navbar Links (apps/web/src/components/layout/navbar.tsx)
const navLinks = [
  { href: '/agents', label: 'Agents' },
  { href: '/dashboard', label: 'Dashboard' }, // Redirects to /console/overview
];

// Auth buttons
{
  isAuthenticated ? (
    <>
      <Button variant="ghost" onClick={logout}>
        Sign out
      </Button>
      <Button asChild>
        <Link href="/dashboard">Console</Link>
      </Button>
    </>
  ) : (
    <>
      <Button variant="ghost" asChild>
        <Link href="/login">Log in</Link>
      </Button>
      <Button asChild>
        <Link href="/register">Get started</Link>
      </Button>
    </>
  );
}
```

---

## Summary

✅ **All CTAs are correctly wired** - No changes needed
✅ **Demo routes are fully functional** - `/demo/a2a` and `/demo/workflows` work without auth
✅ **Auth flow is clear** - Protected routes redirect to login with return path
✅ **API endpoints are documented** - Demo and auth endpoints identified

**Recommendation**: Keep current CTA configuration. The routing is production-ready.
