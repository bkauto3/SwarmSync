\# WEEK 3: LAUNCH READINESS



\## 🎉 INCREDIBLE WORK ON AP2 PROTOCOL!



The A2A transaction layer is COMPLETE. Agents can now autonomously discover, negotiate, and transact with each other. This is the core differentiator - we're the ONLY platform where agents buy from agents.



\## MISSION: PRODUCTION-READY FOR ALPHA LAUNCH



We have the engine. Now we polish it for real users (design partners).



\*\*Timeline\*\*: 5-7 days  

\*\*Goal\*\*: Production-ready platform that 10 companies can use



---



\## BUILD PRIORITIES (In Order)



\### \*\*Priority 1: Enable Full Authentication (1 day)\*\*



\*\*Task\*\*: Turn on JWT authentication for all AP2 endpoints



\*\*Steps\*\*:

1\. Set in `.env`:

```bash

&nbsp;  AP2\_REQUIRE\_AUTH=true

```



2\. Test these flows:

&nbsp;  - All AP2 endpoints require valid JWT tokens

&nbsp;  - Agents can authenticate using API keys

&nbsp;  - Dashboard login/logout works correctly

&nbsp;  - User sessions persist across page refreshes

&nbsp;  - Token refresh works (if implemented)



3\. Fix any issues:

&nbsp;  - If endpoints return 401 when they shouldn't

&nbsp;  - If valid tokens are rejected

&nbsp;  - If CurrentUser decorator fails



\*\*Success Criteria\*\*:

\- \[ ] All AP2 endpoints require authentication when AP2\_REQUIRE\_AUTH=true

\- \[ ] Agents using SDK can authenticate with API keys

\- \[ ] Dashboard auth flow works end-to-end

\- \[ ] No 401 errors for valid requests



---



\### \*\*Priority 2: Agent Onboarding Flow (2 days)\*\*



\*\*Task\*\*: Build UI for users to deploy agents (currently only possible via API)



\*\*Create\*\*: `apps/web/src/app/(marketplace)/(console)/agents/new/page.tsx`



\*\*Design\*\*: Multi-step form wizard



\*\*Step 1: Agent Details\*\*

```typescript

\- Name (required)

\- Description (required, markdown support)

\- Capabilities (multi-select tags: lead\_generation, email\_verification, content\_writing, etc.)

\- Category (dropdown: sales, marketing, development, data, etc.)

\- Icon/Avatar (optional, upload or select from library)

```



\*\*Step 2: Pricing Model\*\*

```typescript

\- Pay-per-use: $X per execution

\- OR Monthly subscription: $Y unlimited

\- OR Both options available

\- Currency: USD (default)

```



\*\*Step 3: Technical Configuration\*\*

```typescript

\- Input schema (JSON schema editor or form builder)

\- Output schema (JSON schema editor)

\- Estimated execution time (seconds)

\- SLA guarantees (uptime %, max latency)

\- API endpoint (if external agent)

```



\*\*Step 4: Budget \& Limits\*\*

```typescript

\- Monthly spending limit (for A2A purchases this agent makes)

\- Per-transaction limit

\- Approval required for transactions > $X

\- Auto-reload settings (on/off, threshold, amount)

```



\*\*Step 5: Review \& Deploy\*\*

```typescript

\- Preview agent card (how it appears in marketplace)

\- Summary of all settings

\- "Deploy Agent" button

\- Confirmation message with agent ID

```



\*\*Components to create\*\*:

\- `AgentOnboardingWizard.tsx` (main container)

\- `AgentDetailsStep.tsx`

\- `PricingStep.tsx`

\- `ConfigurationStep.tsx`

\- `BudgetStep.tsx`

\- `ReviewStep.tsx`



\*\*API Integration\*\*:

```typescript

// Should call existing endpoint

POST /agents

{

&nbsp; name: string;

&nbsp; description: string;

&nbsp; capabilities: string\[];

&nbsp; category: string;

&nbsp; pricing: { perUse?: number; monthly?: number; currency: string };

&nbsp; inputSchema: object;

&nbsp; outputSchema: object;

&nbsp; estimatedLatency: number;

&nbsp; sla: { uptime: number; maxLatency: number };

}



// Then create budget

POST /agents/:id/budget

{

&nbsp; monthlyLimit: number;

&nbsp; perTransactionLimit: number;

&nbsp; approvalThreshold: number;

&nbsp; autoReload: boolean;

}

```



\*\*Success Criteria\*\*:

\- \[ ] Users can deploy agents via UI (no API calls needed)

\- \[ ] All form validation works

\- \[ ] Agent appears in dashboard after deployment

\- \[ ] Budget settings are applied correctly

\- \[ ] Mobile responsive



---



\### \*\*Priority 3: Public Marketplace Page (2 days)\*\*



\*\*Task\*\*: Make `/agents` page show REAL agents from database (not demo data)



\*\*File\*\*: `apps/web/src/app/(marketplace)/agents/page.tsx`



\*\*Ensure these work\*\*:

1\. \*\*Data fetching\*\*: 

&nbsp;  - Pulls agents from `GET /agents`

&nbsp;  - Shows only approved/certified agents

&nbsp;  - Includes pagination or infinite scroll



2\. \*\*Filters\*\*:

&nbsp;  - Category (sales, marketing, development, etc.)

&nbsp;  - Price range (free, <$1, $1-$10, >$10)

&nbsp;  - Certification status (certified only)

&nbsp;  - Rating (4+ stars, 5 stars)



3\. \*\*Search\*\*:

&nbsp;  - Search by agent name

&nbsp;  - Search by capabilities

&nbsp;  - Real-time filtering (as you type)



4\. \*\*Agent cards show\*\*:

&nbsp;  - Agent name

&nbsp;  - Short description (truncated)

&nbsp;  - Category badge

&nbsp;  - Price (from $X)

&nbsp;  - Rating (★★★★★ 4.8)

&nbsp;  - Number of runs

&nbsp;  - Certification badge (if certified)



\*\*Agent Detail Page\*\*: `apps/web/src/app/(marketplace)/agents/\[id]/page.tsx`



\*\*Must include\*\*:

1\. \*\*Hero section\*\*:

&nbsp;  - Agent name

&nbsp;  - Created by @username

&nbsp;  - Rating + review count

&nbsp;  - Total runs

&nbsp;  - Certification badge

&nbsp;  - "Deploy This Agent" button (primary CTA)

&nbsp;  - "Try Demo" button (if available)



2\. \*\*Tabs\*\*:

&nbsp;  - Overview (description, what it does, use cases)

&nbsp;  - Pricing (plans, what's included)

&nbsp;  - Technical (input/output schemas, SLA)

&nbsp;  - Reviews (ratings distribution, recent reviews)

&nbsp;  - Stats (performance metrics, success rate)



3\. \*\*Related agents sidebar\*\*:

&nbsp;  - "Similar agents" (same category)

&nbsp;  - "Often used together" (from A2A network data)



\*\*"Deploy This Agent" Flow\*\*:

```typescript

// When clicked:

1\. Check if user is authenticated (if not, redirect to /login)

2\. Show modal: "Deploy \[Agent Name]"

&nbsp;  - Set budget for this agent

&nbsp;  - Set spending limits

&nbsp;  - Review permissions

3\. Call: POST /agents/:id/deploy-copy (creates instance for user)

4\. Redirect to /dashboard with success message

```



\*\*Success Criteria\*\*:

\- \[ ] Marketplace page shows real agents from database

\- \[ ] Filters and search work correctly

\- \[ ] Agent detail pages have all required information

\- \[ ] "Deploy This Agent" flow works end-to-end

\- \[ ] Mobile responsive

\- \[ ] Fast loading (<2s)



---



\### \*\*Priority 4: Stripe Integration (1-2 days)\*\*



\*\*Task\*\*: Complete wallet funding via Stripe



\*\*What exists\*\*: Database tables, some endpoints  

\*\*What's needed\*\*: Frontend integration + Stripe Elements



\*\*Wallet Funding Flow\*\*:



\*\*Page\*\*: `apps/web/src/app/(marketplace)/(console)/wallet/page.tsx`



\*\*Add component\*\*: `AddFundsModal.tsx`

```typescript

// User clicks "Add Funds"

// Modal appears with:



1\. Amount selector

&nbsp;  - Quick buttons: $50, $100, $250, $500

&nbsp;  - Custom amount input



2\. Stripe Payment Element

&nbsp;  - Card details (Stripe Elements iframe)

&nbsp;  - Save card for future use (checkbox)



3\. Summary

&nbsp;  - Amount to add: $100.00

&nbsp;  - Processing fee: $3.00 (3%)

&nbsp;  - Total charge: $103.00



4\. "Add Funds" button

&nbsp;  - Processes payment via Stripe

&nbsp;  - Credits wallet on success

&nbsp;  - Shows confirmation message

```



\*\*Backend endpoints needed\*\* (check if exist, create if not):

```typescript

// Create payment intent

POST /wallets/my/fund

{

&nbsp; amount: number; // in dollars

}

Response: {

&nbsp; clientSecret: string; // for Stripe Elements

}



// Confirm payment (webhook)

POST /webhooks/stripe

// Stripe calls this when payment succeeds

// Credits the wallet automatically

```



\*\*Stripe Setup\*\*:

1\. Get Stripe API keys (test mode for now)

2\. Add to `.env`:

```bash

&nbsp;  STRIPE\_SECRET\_KEY=sk\_test\_...

&nbsp;  STRIPE\_PUBLISHABLE\_KEY=pk\_test\_...

&nbsp;  STRIPE\_WEBHOOK\_SECRET=whsec\_...

```

3\. Install Stripe in web app:

```bash

&nbsp;  npm install --workspace @agent-market/web @stripe/stripe-js @stripe/react-stripe-js

```



\*\*Implementation\*\*:

```typescript

// apps/web/src/components/wallet/add-funds-modal.tsx



import { Elements } from '@stripe/react-stripe-js';

import { loadStripe } from '@stripe/stripe-js';



const stripePromise = loadStripe(process.env.NEXT\_PUBLIC\_STRIPE\_PUBLISHABLE\_KEY!);



export function AddFundsModal() {

&nbsp; const \[amount, setAmount] = useState(100);

&nbsp; const \[clientSecret, setClientSecret] = useState('');



&nbsp; const createPaymentIntent = async () => {

&nbsp;   const response = await api.post('wallets/my/fund', {

&nbsp;     json: { amount },

&nbsp;   }).json();

&nbsp;   setClientSecret(response.clientSecret);

&nbsp; };



&nbsp; return (

&nbsp;   <Dialog>

&nbsp;     <DialogContent>

&nbsp;       {!clientSecret ? (

&nbsp;         // Amount selection

&nbsp;         <AmountSelector amount={amount} onChange={setAmount} />

&nbsp;         <Button onClick={createPaymentIntent}>Continue</Button>

&nbsp;       ) : (

&nbsp;         // Stripe payment form

&nbsp;         <Elements stripe={stripePromise} options={{ clientSecret }}>

&nbsp;           <PaymentForm />

&nbsp;         </Elements>

&nbsp;       )}

&nbsp;     </DialogContent>

&nbsp;   </Dialog>

&nbsp; );

}

```



\*\*Test Flow\*\*:

1\. User has $0 balance

2\. Click "Add Funds"

3\. Select $100

4\. Enter test card: 4242 4242 4242 4242

5\. Submit payment

6\. See success message

7\. Balance shows $100

8\. Transaction appears in history



\*\*Success Criteria\*\*:

\- \[ ] Add funds modal works

\- \[ ] Stripe payment form appears

\- \[ ] Test payments succeed

\- \[ ] Wallet balance updates immediately

\- \[ ] Transaction appears in history

\- \[ ] Webhook handler processes payments

\- \[ ] Error handling (declined cards, etc.)



---



\### \*\*Priority 5: Documentation (1 day)\*\*



\*\*Task\*\*: Create essential docs for developers and users



\*\*For Agent Developers\*\* (in `docs/` folder):



\*\*File\*\*: `docs/agent-sdk-guide.md`

```markdown

\# Agent SDK Guide



\## Installation

npm install @agent-market/agent-sdk



\## Quick Start

\[Copy from examples/autonomous-agent/README.md]



\## API Reference

\- AgentMarketSDK class

\- discover() method

\- requestService() method

\- waitForCompletion() method



\## Examples

\- Lead generation agent

\- Email verification agent

\- Content writing agent

```



\*\*File\*\*: `docs/ap2-protocol.md`

```markdown

\# AP2 Protocol Specification



\## Overview

Agent Payment Protocol v2 enables autonomous agent-to-agent transactions



\## Transaction Flow

1\. Discovery

2\. Negotiation

3\. Escrow

4\. Execution

5\. Verification

6\. Settlement



\## API Endpoints

\[Document the AP2 endpoints]

```



\*\*File\*\*: `docs/agent-examples.md`

```markdown

\# Agent Examples



\## Example 1: Autonomous Lead Generation

\[Code from examples/autonomous-agent]



\## Example 2: Email Verification Chain

\[Create new example]



\## Example 3: Multi-Agent Workflow

\[Create new example]

```



\*\*For Platform Users\*\*:



\*\*File\*\*: `docs/getting-started.md`

```markdown

\# Getting Started



\## Create an Account

\## Deploy Your First Agent

\## Set Budget Limits

\## Monitor Transactions

\## View ROI Metrics

```



\*\*File\*\*: `docs/budgets-and-limits.md`

```markdown

\# Budget Controls



\## Monthly Limits

\## Per-Transaction Limits

\## Approval Workflows

\## Auto-Reload Settings

```



\*\*File\*\*: `docs/a2a-transactions.md`

```markdown

\# Understanding Agent-to-Agent Commerce



\## What is A2A?

\## How Agents Discover Each Other

\## Negotiation Process

\## Escrow \& Settlement

\## Outcome Verification

```



\*\*Also create\*\*:

\- `README.md` in repo root (overview, quick start)

\- API reference using Swagger/OpenAPI (NestJS can auto-generate with `@nestjs/swagger`)



\*\*Success Criteria\*\*:

\- \[ ] Agent SDK guide complete

\- \[ ] AP2 protocol documented

\- \[ ] Code examples work

\- \[ ] User guides written

\- \[ ] API reference generated



---



\## TESTING CHECKLIST



\*\*Run through these flows before considering Week 3 complete:\*\*



\### \*\*Flow 1: User Signup \& Agent Deployment\*\*

1\. \[ ] Sign up with new email

2\. \[ ] Verify email (if required)

3\. \[ ] Log in

4\. \[ ] Navigate to "Deploy Agent"

5\. \[ ] Fill out onboarding wizard

6\. \[ ] Set budget: $100 monthly, $10 per transaction

7\. \[ ] Deploy agent

8\. \[ ] See agent in dashboard

9\. \[ ] Wallet shows $0, needs funding



\### \*\*Flow 2: Add Funds \& Budget\*\*

1\. \[ ] Click "Add Funds" in wallet

2\. \[ ] Enter $100

3\. \[ ] Complete Stripe payment (test card)

4\. \[ ] See $100 balance

5\. \[ ] Transaction appears in history



\### \*\*Flow 3: A2A Transaction (End-to-End)\*\*

1\. \[ ] Use `examples/autonomous-agent` to trigger transaction

2\. \[ ] Watch negotiation appear in AP2 monitor (dashboard)

3\. \[ ] Verify escrow locks ($X from wallet)

4\. \[ ] Wait for service delivery

5\. \[ ] Verify outcome verification happens

6\. \[ ] Verify payment settles to recipient

7\. \[ ] Check wallet balance decreased by transaction amount

8\. \[ ] Check A2A metrics updated (network graph, ROI)

9\. \[ ] Check agent engagement metrics incremented



\### \*\*Flow 4: Budget Limits Work\*\*

1\. \[ ] Set agent monthly limit to $50

2\. \[ ] Set per-transaction limit to $10

3\. \[ ] Try transaction that exceeds per-transaction limit

4\. \[ ] Verify transaction blocked with clear error

5\. \[ ] Try multiple transactions that exceed monthly limit

6\. \[ ] Verify blocked after hitting limit

7\. \[ ] See errors in dashboard



\### \*\*Flow 5: Marketplace Discovery\*\*

1\. \[ ] Browse `/agents` page

2\. \[ ] Apply filters (category, price, certification)

3\. \[ ] Search for agent by name

4\. \[ ] Click agent to see detail page

5\. \[ ] Review tabs (overview, pricing, technical, reviews)

6\. \[ ] Click "Deploy This Agent"

7\. \[ ] See agent copy deployed to user's account



\### \*\*Flow 6: Dashboard Monitoring\*\*

1\. \[ ] View all deployed agents

2\. \[ ] See A2A transaction monitor (live updates)

3\. \[ ] View agent network graph (ReactFlow)

4\. \[ ] Check ROI metrics (spend vs. value)

5\. \[ ] Adjust budget controls

6\. \[ ] View negotiation details

7\. \[ ] Cancel pending negotiation (if applicable)



\*\*Fix any bugs found during testing.\*\*



---



\## SUCCESS CRITERIA (Week 3 Complete)



By Friday, you should have:



\*\*Backend:\*\*

\- \[x] AP2 protocol complete (DONE)

\- \[ ] Authentication fully enabled and tested

\- \[ ] All endpoints secured with JWT

\- \[ ] Stripe webhook handler working



\*\*Frontend:\*\*

\- \[ ] Agent onboarding wizard complete

\- \[ ] Public marketplace working (real data)

\- \[ ] Agent detail pages with full info

\- \[ ] Wallet funding via Stripe working

\- \[ ] All dashboards showing real-time data



\*\*Documentation:\*\*

\- \[ ] Agent SDK guide written

\- \[ ] AP2 protocol documented

\- \[ ] User guides complete

\- \[ ] API reference generated



\*\*Testing:\*\*

\- \[ ] All 6 test flows passing

\- \[ ] No critical bugs

\- \[ ] Mobile responsive

\- \[ ] <2s page load times



---



\## WHAT HAPPENS AFTER WEEK 3



\*\*Week 4: Alpha Launch with Design Partners\*\*



1\. \*\*Recruit 10 design partner companies\*\*

&nbsp;  - AI agent developers

&nbsp;  - Companies building automation

&nbsp;  - Free Pro tier for 6 months



2\. \*\*Seed marketplace with 20 agents\*\*

&nbsp;  - 10 template agents (you build)

&nbsp;  - 10 from design partners



3\. \*\*Target: 100 A2A transactions\*\*

&nbsp;  - Real autonomous trades

&nbsp;  - Prove the platform works



4\. \*\*Gather feedback\*\*

&nbsp;  - Weekly calls with design partners

&nbsp;  - Iterate on critical issues

&nbsp;  - Build roadmap for beta



---



\## NOTES



\- Focus on \*\*working end-to-end flows\*\* over perfect UI

\- \*\*Document as you build\*\* (don't save for later)

\- \*\*Test frequently\*\* (after each priority)

\- \*\*Ask questions\*\* if anything is unclear

\- \*\*Ship daily\*\* (merge to main, deploy to staging)



The AP2 protocol is incredible work. Now we polish it for real users.



Let's make this launch-ready. 🚀

