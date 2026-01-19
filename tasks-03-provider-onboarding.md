# SwarmSync Tasks: Provider Onboarding Flow

**Priority:** P1 — Ship This Sprint  
**Estimated Effort:** 6-10 hours  
**Files Affected:** `app/get-started/page.tsx`, `app/dashboard/provider/*` (new), `app/docs/providers/page.tsx` (new)

---

## Overview

Build the provider signup and onboarding flow. When providers click "List Your Agent" from the homepage, they should land on a tailored experience that gets them from signup to listed agent.

---

## Get Started Page Updates

- [x] **Add role detection via URL param**
  - Check for `?role=provider` on `/get-started`
  - If present: Show provider-specific flow
  - If absent: Show role selector

- [x] **Create role selector (if no param)**

  ```
  What brings you to SwarmSync?

  ┌─────────────────────────┐    ┌─────────────────────────┐
  │                         │    │                         │
  │   I want to hire        │    │   I want to list        │
  │   AI agents             │    │   my AI agent           │
  │                         │    │                         │
  │   [Browse Marketplace]  │    │   [Become a Provider]   │
  │                         │    │                         │
  └─────────────────────────┘    └─────────────────────────┘
  ```

  - "Browse Marketplace" → existing buyer flow
  - "Become a Provider" → sets `?role=provider` and shows provider form

---

## Provider Signup Form

- [x] **Create provider-specific form fields**

  | Field                    | Type     | Required | Validation                                         |
  | ------------------------ | -------- | -------- | -------------------------------------------------- |
  | Agent Name               | text     | Yes      | 3-50 chars                                         |
  | Category                 | dropdown | Yes      | Research, Content, Code, Finance, Marketing, Other |
  | What does it do?         | textarea | Yes      | 10-150 chars                                       |
  | Pricing Model            | radio    | Yes      | Subscription, Per-task, Custom                     |
  | API Endpoint or Docs URL | url      | No       | Valid URL format                                   |
  | Your Email               | email    | Yes      | Valid email                                        |
  | Terms checkbox           | checkbox | Yes      | Must be checked                                    |

- [x] **Add provider-specific headline on form**

  ```
  List Your Agent
  Tell us about your agent and we'll review it within 48 hours.
  ```

- [x] **Add terms checkbox copy**

  ```
  ☐ I agree to the Provider Terms and verification process
  ```

  - Link "Provider Terms" to `/docs/providers/terms`

- [x] **Add submit button**
  - Text: "Submit for Review"
  - On success: Redirect to `/dashboard/provider` with success toast

---

## Provider Dashboard Pages

### Main Dashboard (`/dashboard/provider`)

- [x] **Create provider dashboard landing**
  - Show welcome message for new providers
  - Show earnings summary for active providers
  - Quick links: "Add Agent", "View Earnings", "Payout Settings"

- [x] **Show listing status**
  ```
  Your Agents
  ┌──────────────────────────────────────────┐
  │  DataCleanerBot          [Under Review]  │
  │  Submitted 2 hours ago                    │
  └──────────────────────────────────────────┘
  ```

### Agent Management (`/dashboard/provider/agents`)

- [x] **Create agent listing page**
  - Table/grid of all submitted agents
  - Status badges: Under Review, Live, Rejected, Paused
  - Edit/View actions per agent

### Create Agent (`/dashboard/provider/agents/new`)

- [x] **Create full agent profile form**
  - All fields from quick signup PLUS:
  - Full description (500 chars)
  - Capability tags (multi-select)
  - Pricing tiers configuration
  - API/webhook endpoint
  - Authentication method
  - Sample outputs (file upload, optional)
  - Response time SLA

### Payout Settings (`/dashboard/provider/payouts`)

- [x] **Integrate Stripe Connect onboarding**
  - "Connect Stripe" button for new providers
  - Show connected account status
  - Bank/card on file indicator

- [x] **Add withdrawal interface**
  - Current balance display
  - "Withdraw" button (available balance)
  - Withdrawal history

### Earnings History (`/dashboard/provider/earnings`)

- [x] **Create transaction history table**
  - Columns: Date, Buyer, Agent, Amount, Fee, Net, Status
  - Filter by date range, agent, status
  - Export to CSV

---

## Provider Documentation (`/docs/providers`)

- [x] **Create provider docs landing page**
  - Overview of being a provider
  - Link to sub-pages

- [x] **Create requirements page (`/docs/providers/requirements`)**
  - What agents are accepted
  - Quality standards
  - Prohibited content

- [x] **Create API/webhook docs (`/docs/providers/integration`)**
  - How to connect your agent
  - Authentication setup
  - Request/response formats

- [x] **Create payouts FAQ (`/docs/providers/payouts`)**
  - How escrow works
  - Payout timing (48h)
  - Fee structure (12-20%)
  - Dispute resolution

- [x] **Create terms page (`/docs/providers/terms`)**
  - Provider agreement
  - Liability
  - Termination conditions

---

## Provider Journey Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PROVIDER JOURNEY                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. HOMEPAGE                                                         │
│     └─→ Sees Provider Section                                        │
│         └─→ Clicks "List Your Agent"                                 │
│                                                                      │
│  2. /get-started?role=provider                                       │
│     └─→ Fills quick signup form (6 fields)                          │
│         └─→ Creates account OR logs in                               │
│             └─→ Submits agent for review                             │
│                                                                      │
│  3. /dashboard/provider                                              │
│     └─→ Sees "Under Review" status                                   │
│         └─→ Completes full profile (optional)                        │
│             └─→ Connects Stripe for payouts                          │
│                                                                      │
│  4. REVIEW (SwarmSync internal)                                      │
│     └─→ Team reviews within 48h                                      │
│         └─→ APPROVED: Agent goes live                                │
│         └─→ REJECTED: Feedback sent, can revise                      │
│                                                                      │
│  5. LIVE IN MARKETPLACE                                              │
│     └─→ Agent appears in /agents                                     │
│         └─→ Gets discovered by buyers                                │
│             └─→ Receives hire requests                               │
│                                                                      │
│  6. TRANSACTION                                                      │
│     └─→ Buyer funds escrow                                           │
│         └─→ Provider executes work                                   │
│             └─→ Verification passes                                  │
│                 └─→ Escrow releases                                  │
│                     └─→ Funds in provider account (48h)              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Email Notifications (If Applicable)

- [ ] **Agent submitted confirmation**
  - "We received your agent submission. Review takes up to 48 hours."

- [ ] **Agent approved notification**
  - "Your agent is now live! View your listing →"

- [ ] **Agent rejected notification**
  - "Your agent needs changes. Here's the feedback: [...]"

- [ ] **First hire notification**
  - "Congratulations! Your agent just got its first job."

- [ ] **Payout notification**
  - "You earned $X from [Agent Name]. Funds available in 48h."

---

## QA Checklist

- [x] `/get-started?role=provider` shows provider form
- [x] `/get-started` without param shows role selector
- [x] Form validation works (required fields, email format, URL format)
- [x] Successful submission creates account + agent record
- [x] Provider dashboard shows submitted agents
- [x] Stripe Connect flow works end-to-end
- [x] Provider docs pages are accessible and linked correctly

---

_Part 3 of 4 — Provider Onboarding Flow_
