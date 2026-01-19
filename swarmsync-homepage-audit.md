# SwarmSync.ai Homepage UX/Conversion Audit

## Senior B2B SaaS Marketplace Analysis

---

## A. Homepage Map (Current Structure)

### Section Order & Analysis

| #   | Section                                 | Purpose                                        | Primary CTA                                            | Target Persona                  |
| --- | --------------------------------------- | ---------------------------------------------- | ------------------------------------------------------ | ------------------------------- |
| 1   | **Hero**                                | Establish value prop + differentiation         | "Run Live A2A Demo" / "Explore Workflow Builder Demo"  | Buyers (technical operators)    |
| 2   | **A2A Transaction Flow** (right panel)  | Show how agent transactions work               | None (informational)                                   | Buyers + Finance                |
| 3   | **Transaction Storyboard**              | Real-time demo feed showing transaction states | None (live feed)                                       | Buyers (technical)              |
| 4   | **The Velocity Gap**                    | Problem statement—enterprises are slow         | Tab toggle (Workflow Comparison / Quantified Benefits) | Buyers (exec/manager)           |
| 5   | **Traditional vs SwarmSync Comparison** | Side-by-side time savings                      | None                                                   | Buyers (exec decision-makers)   |
| 6   | **Enterprise-Grade Governance**         | Security/compliance messaging                  | Tab toggle (Safety / Data / Audit)                     | Finance / Compliance / Security |
| 7   | **Compliance Badges**                   | SOC 2, GDPR, CCPA, HIPAA, ISO                  | None (trust signals)                                   | Finance / Compliance            |
| 8   | **Technical Architecture**              | Protocol/infra details                         | Tab toggle (A2A Protocol / Design Patterns / MCP+RAG)  | Buyers (technical)              |
| 9   | **How It Works**                        | 3-step getting started flow                    | None explicitly (implied next section)                 | All buyers                      |
| 10  | **Why SwarmSync**                       | 4 key differentiators                          | None                                                   | All buyers                      |
| 11  | **Feature Comparison Table**            | vs LangChain, CrewAI, AutoGPT                  | None                                                   | Technical buyers                |
| 12  | **Integration Logos**                   | Shows supported stack                          | None                                                   | Technical buyers                |
| 13  | **Mid-page CTA**                        | Demo call-to-action                            | "Try Live Demo" / "Why Not Build Your Own?"            | All buyers                      |
| 14  | **Final CTA**                           | Trial conversion                               | "Start Free Trial" / "Checkout With Stripe"            | All buyers                      |
| 15  | **Footer**                              | Navigation + "List your agent" link            | "List your agent" (buried)                             | **Providers** (barely visible)  |

### Critical Observation

**Provider persona has ZERO dedicated homepage real estate.** The only provider-facing CTA is a tiny footer link that says "List your agent."

---

## B. Top Issues & Fixes (Ranked by Impact)

### 🔴 HIGH IMPACT Issues

#### Issue #1: No Provider Section on Homepage

**What's wrong:** The entire homepage speaks to buyers. Providers (the supply side of your marketplace) have no dedicated section or value prop.

**Why it matters:** A two-sided marketplace dies without supply. If providers don't understand how they earn, you won't have agents for buyers to hire.

**Exact change:** Add a dedicated "Register Your Agent & Earn" section (see Section C for full spec).

**Impact:** HIGH | **Effort:** Moderate

---

#### Issue #2: Hero Headline Alienates Non-Technical Buyers

**What's wrong:** "Remove Humans From the Loop for Unmatched Agent-to-Agent Autonomy" is abstract and slightly dystopian ("remove humans").

**Why it matters:** Decision-makers who aren't AI-native won't immediately grasp the value. The phrasing triggers sci-fi concerns rather than business outcomes.

**Exact change:**

- Option A: "Let Your AI Agents Hire, Negotiate, and Pay Each Other—Automatically"
- Option B: "The Marketplace Where AI Agents Do Business With Each Other"

**Impact:** HIGH | **Effort:** Quick

---

#### Issue #3: Too Many CTAs in Hero (Cognitive Overload)

**What's wrong:** Hero has 4 competing actions: "Run Live A2A Demo," "Explore Workflow Builder Demo," a copyable URL, and "View pricing."

**Why it matters:** Paradox of choice. Users don't know which action matters most. Conversion suffers.

**Exact change:**

- Primary CTA: "See It in Action" (single demo)
- Secondary (text link): "View pricing"
- Kill the copy URL box—too early, too technical

**Impact:** HIGH | **Effort:** Quick

---

#### Issue #4: "Why Not Build Your Own?" CTA is Self-Sabotaging

**What's wrong:** This button invites users to leave and build a competitor.

**Why it matters:** You're literally suggesting they don't need you.

**Exact change:** Replace with "See How It Works" or "Compare Build vs. Buy" (with a page showing why building is harder).

**Impact:** HIGH | **Effort:** Quick

---

#### Issue #5: Navigation Lacks "Marketplace" Entry Point

**What's wrong:** Nav says "Agents" not "Marketplace." Users expect "Marketplace" for a marketplace product.

**Why it matters:** "Agents" is ambiguous (could mean docs about agents, agent types, etc.). Marketplace is standard IA for this model.

**Exact change:** Rename "Agents" → "Marketplace" in nav. Keep URL as /agents if needed, but label should be "Marketplace."

**Impact:** HIGH | **Effort:** Quick

---

#### Issue #6: No Social Proof / Testimonials

**What's wrong:** Zero customer logos, quotes, case studies, or usage stats anywhere on the homepage.

**Why it matters:** B2B buyers need proof this works before they trust autonomous financial transactions.

**Exact change:** Add a "Trusted By" section with 3-5 logos OR add a single testimonial quote from an early adopter OR show aggregate stats ("$X in transactions processed, X agents on marketplace").

**Impact:** HIGH | **Effort:** Moderate

---

### 🟡 MEDIUM IMPACT Issues

#### Issue #7: "Escrow" Mentioned But Not Explained

**What's wrong:** Escrow appears multiple times without explaining how it protects users.

**Why it matters:** Escrow is your key trust differentiator. Buyers and providers need to understand funds are safe.

**Exact change:** Add a micro-explainer: "Funds held securely until work is verified and approved. If there's a dispute, escrow protects both parties."

**Impact:** Medium | **Effort:** Quick

---

#### Issue #8: Compliance Badges Are Confusing

**What's wrong:** "HIPAA Ready" and "ISO 27001 In Progress" undermine the certified ones.

**Why it matters:** "Ready" and "In Progress" suggest you're not actually compliant yet—raises doubt.

**Exact change:** Only show achieved certifications (SOC 2, GDPR, CCPA). Add "HIPAA and ISO 27001 coming Q2" as small text below if needed.

**Impact:** Medium | **Effort:** Quick

---

#### Issue #9: The "Velocity Gap" Section is Too Far Down

**What's wrong:** The problem statement ("AI Generates in Seconds. Enterprises Decide in Days.") appears after the live demo feed.

**Why it matters:** You should agitate the problem BEFORE showing the solution. Currently, visitors see solution details before understanding why it matters.

**Exact change:** Move "Velocity Gap" section immediately after hero OR integrate the problem statement into the hero subheadline.

**Impact:** Medium | **Effort:** Quick

---

#### Issue #10: Feature Comparison Table Has No CTA

**What's wrong:** After seeing SwarmSync beats LangChain/CrewAI/AutoGPT, there's no immediate next step.

**Why it matters:** You've convinced them you're better—now capture that momentum.

**Exact change:** Add "Start Free Trial" button directly below the comparison table.

**Impact:** Medium | **Effort:** Quick

---

#### Issue #11: "How It Works" Titles Are Vague

**What's wrong:** "Deploy Workforce / Maintain Trust / Scale Autonomy" are abstract. Users can't picture what they actually do.

**Why it matters:** "How It Works" should be crystal clear, not conceptual.

**Exact change:**

- Step 1: "Add Your Agents" (connect your existing AI agents)
- Step 2: "Set Budgets & Rules" (define what they can spend and do)
- Step 3: "Let Them Work" (agents hire other agents automatically)

**Impact:** Medium | **Effort:** Quick

---

#### Issue #12: Pricing Link is Easy to Miss

**What's wrong:** "View pricing" is a small text link below the hero CTAs, easily overlooked.

**Why it matters:** Price-sensitive buyers (especially SMBs) want to know cost upfront.

**Exact change:** Add "Pricing" to main nav OR make "View pricing" a styled button (secondary style).

**Impact:** Medium | **Effort:** Quick

---

### 🟢 LOW IMPACT Issues

#### Issue #13: Transaction Storyboard is Noisy

**What's wrong:** Raw log output with negotiation IDs and technical status codes.

**Why it matters:** Non-technical buyers see noise. It looks impressive but doesn't communicate value.

**Exact change:** Simplify to: "Agent A hired Agent B for $20. Task delivered. Funds released." with friendly formatting.

**Impact:** Low | **Effort:** Moderate

---

#### Issue #14: Footer Has Orphaned Provider Link

**What's wrong:** "List your agent" appears in footer with no context or explanation.

**Why it matters:** Providers won't click a random footer link. It needs positioning.

**Exact change:** Keep footer link but make it consistent with the new Provider Section headline/CTA (see Section C).

**Impact:** Low | **Effort:** Quick

---

#### Issue #15: Cookie Banner Covers CTAs

**What's wrong:** The cookie consent banner obscures the bottom of the viewport on all screenshots.

**Why it matters:** It's distracting and covers content during critical first impressions.

**Exact change:** Make cookie banner less obtrusive (top bar or smaller bottom bar) or auto-dismiss after 5 seconds of scroll.

**Impact:** Low | **Effort:** Quick

---

#### Issue #16: Prime Directive Quote is Insider Language

**What's wrong:** "The SwarmSync Prime Directive" assumes familiarity with brand vocabulary.

**Why it matters:** New visitors don't know what "Prime Directive" means. It sounds like Star Trek.

**Exact change:** Replace with: "Our Security Promise" or just present the principles without the branding.

**Impact:** Low | **Effort:** Quick

---

## C. Provider Section Spec (Final)

### Placement Analysis

**Option A: After "How It Works" / Before "Why SwarmSync"**

- ✅ Natural break point after explaining the buyer journey
- ✅ Provider section would benefit from buyer context established above
- ❌ Might confuse buyers who haven't finished evaluating

**Option B: After "Feature Comparison Table" / Before Final CTA** ⭐ WINNER

- ✅ Buyers have seen full value prop—ready to be segmented
- ✅ Providers get the escrow/verification/trust context established earlier
- ✅ Creates natural "fork in the road" before final CTA
- ✅ Doesn't interrupt buyer flow—providers self-select

**RECOMMENDATION:** Place provider section AFTER the feature comparison table and integration logos, BEFORE the "Ready to onboard autonomy?" final CTA.

This creates a dual-track funnel:

- Buyers: Continue to "Start Free Trial"
- Providers: Branch to "List Your Agent"

---

### Provider Section Specification

#### Section Goal

Convert agent builders/owners into listed providers on the marketplace. Primary metric: Provider signup form submissions.

---

#### Headlines (3 Options)

**Option 1 (Direct):**

> **Built an AI Agent? List It and Earn.**
> Join the marketplace where other agents find you, hire you, and pay you—automatically.

**Option 2 (Discovery-focused):**

> **Get Your Agent Discovered by Thousands of Buyers**
> Stop marketing your agent manually. Let the marketplace bring clients to you.

**Option 3 (Money-forward):** ⭐ RECOMMENDED

> **Your Agent. Your Revenue. Zero Invoicing.**
> List your agent, set your rates, and get paid automatically through escrow.

---

#### Value Proposition Bullets

1. **Get discovered automatically** — Buyers search by capability. If your agent matches, you get hired without lifting a finger.

2. **Set your own pricing** — Choose subscription, per-task, or custom pricing. Keep 80-88% of every transaction (based on tier).

3. **Funds protected by escrow** — You don't work for free. Funds are locked before you start and released when verified.

4. **Build your reputation** — Every successful job increases your score. High-rated agents get priority placement.

5. **Payouts you can count on** — Earnings settle within 48 hours of verification. Withdraw to your connected account anytime.

---

#### Primary CTA

**Button Text:** "List Your Agent"
**Destination:** `/get-started?role=provider` (or modal inline form)

#### Secondary CTA

**Text Link:** "How payouts work" → anchors to an expandable FAQ or opens modal
**Alternative:** "See provider requirements" → links to `/docs/providers`

---

#### Inline Quick Signup Form (Optional—could be modal instead)

**Minimal Fields (6 max):**

| Field                    | Type                | Required | Placeholder/Helper                                       |
| ------------------------ | ------------------- | -------- | -------------------------------------------------------- |
| Agent Name               | Text                | Yes      | "e.g., DataCleanerBot"                                   |
| Category                 | Dropdown            | Yes      | Research / Content / Code / Finance / Marketing / Other  |
| What does it do?         | Textarea (150 char) | Yes      | "Describe your agent's main capability in one sentence"  |
| Pricing Model            | Radio               | Yes      | Subscription / Per-task / Custom                         |
| API Endpoint or Docs URL | URL                 | No       | "https://..."                                            |
| Your Email               | Email               | Yes      | —                                                        |
| ☑️ Checkbox              | Checkbox            | Yes      | "I agree to the Provider Terms and verification process" |

**Submit Button:** "Submit for Review"

---

#### Trust & Safety Microcopy

Add small text below form or CTA:

> **How it works:**
>
> 1. Submit your agent → We review it within 48 hours
> 2. Pass verification → Your listing goes live
> 3. Get hired → Funds are escrowed before work starts
> 4. Deliver results → Buyer verifies, escrow releases
> 5. Get paid → Funds in your account within 48 hours
>
> **Protected by escrow:** If a buyer disputes, we mediate. You're never stiffed for completed work.

---

#### "How Providers Make Money" Mini-Diagram (Text-Only)

```
┌────────────────────────────────────────────────────────────────────┐
│                        PROVIDER EARNINGS FLOW                       │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Your Agent Listed]                                                │
│         │                                                           │
│         ▼                                                           │
│  [Buyer's Agent Finds You] ←── Discovery via capability matching   │
│         │                                                           │
│         ▼                                                           │
│  [Terms Negotiated]  ←── Price, scope, deadline (A2A protocol)     │
│         │                                                           │
│         ▼                                                           │
│  [Escrow Funded] ←── Buyer's funds locked BEFORE you start         │
│         │                                                           │
│         ▼                                                           │
│  [You Deliver Work]                                                 │
│         │                                                           │
│         ▼                                                           │
│  [Verification Passes] ←── Automated or buyer-approved             │
│         │                                                           │
│         ▼                                                           │
│  [Payment Released] ←── 80-88% to you, balance is platform fee     │
│         │                                                           │
│         ▼                                                           │
│  [Withdraw Anytime] ←── Bank, Stripe, or crypto (coming soon)      │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

#### Supporting Visuals (Description)

1. **"Verified Provider" Badge Mock** — Show a green checkmark badge like the ones on the /agents page, so providers see what they'll earn.

2. **Sample Agent Card** — Display a representative agent listing card (like the ones on marketplace) with "Your Agent Here" placeholder.

3. **Revenue Icon Set:**
   - 💰 Money bag for "Set Your Rates"
   - 🔒 Lock for "Escrow Protection"
   - ⭐ Star for "Build Reputation"
   - 📈 Chart for "Track Earnings"

4. **Trust Badges (Reuse from Buyer Section):**
   - SOC 2 Certified
   - Escrow-Protected Payments
   - 48-Hour Payout Guarantee

---

## D. Provider Funnel & Information Architecture

### End-to-End Provider Journey

```
STAGE 1: AWARENESS (Homepage)
─────────────────────────────
1.1 → Visitor lands on homepage
1.2 → Scrolls through buyer-focused content
1.3 → Encounters Provider Section (after feature comparison)
1.4 → Clicks "List Your Agent"

STAGE 2: APPLICATION (Provider Onboarding)
──────────────────────────────────────────
2.1 → /get-started?role=provider loads
2.2 → Quick signup form (6 fields) OR account creation if not logged in
2.3 → Email verification sent
2.4 → Provider dashboard unlocks

STAGE 3: LISTING SETUP (Provider Dashboard)
───────────────────────────────────────────
3.1 → Complete agent profile:
      - Full description
      - Capabilities (tags)
      - Pricing tiers
      - API/webhook configuration
      - Sample outputs (optional)
3.2 → Connect payout method (Stripe Connect)
3.3 → Accept Provider Agreement
3.4 → Submit for review

STAGE 4: VERIFICATION (SwarmSync Review)
────────────────────────────────────────
4.1 → SwarmSync team reviews listing (48h SLA)
4.2 → Automated capability tests run (if applicable)
4.3 → Compliance check (data handling, safety)
4.4 → APPROVED → Agent goes live
      REJECTED → Feedback sent, provider can revise

STAGE 5: LIVE IN MARKETPLACE
────────────────────────────
5.1 → Agent appears in /agents search
5.2 → "Verified" badge displays (if passed verification)
5.3 → Agent is discoverable by buyer agents

STAGE 6: GETTING HIRED
──────────────────────
6.1 → Buyer agent discovers provider agent
6.2 → A2A negotiation begins (terms, price, deadline)
6.3 → Provider agent accepts/counters/rejects
6.4 → Agreement reached

STAGE 7: ESCROW & EXECUTION
───────────────────────────
7.1 → Buyer funds escrow (funds locked)
7.2 → Provider agent receives work request
7.3 → Provider agent executes task
7.4 → Output delivered to buyer agent

STAGE 8: VERIFICATION & PAYOUT
──────────────────────────────
8.1 → Automated verification runs (if configured)
      OR buyer approves manually
8.2 → Verification passes → Escrow releases
8.3 → Platform fee deducted (12-20%)
8.4 → Provider earnings credited
8.5 → Withdraw available (48h settlement)
```

---

### Key Screens/Pages Needed

| Screen                   | URL                               | Purpose                               |
| ------------------------ | --------------------------------- | ------------------------------------- |
| Provider Landing Section | Homepage (inline)                 | Awareness + quick form                |
| Provider Signup          | `/get-started?role=provider`      | Account creation with provider intent |
| Provider Dashboard       | `/dashboard/provider`             | Manage listings, view earnings        |
| Create Listing           | `/dashboard/provider/agents/new`  | Full agent profile form               |
| Connect Payouts          | `/dashboard/provider/payouts`     | Stripe Connect onboarding             |
| Listing Detail           | `/dashboard/provider/agents/[id]` | Edit/view specific listing            |
| Earnings History         | `/dashboard/provider/earnings`    | Transaction history + withdrawals     |
| Provider Docs            | `/docs/providers`                 | Requirements, API specs, FAQ          |

---

### Provider Entry Point Recommendation

**Recommended URL:** `/get-started?role=provider`

**Why this wins over alternatives:**

| Option                          | Pros                                                                   | Cons                                            |
| ------------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------- |
| `/get-started?role=provider` ⭐ | Single onboarding flow, role selection built-in, reduces IA complexity | Requires role param logic                       |
| `/marketplace/apply`            | Clear intent                                                           | Suggests you need "approval" (friction)         |
| `/providers`                    | Dedicated landing page                                                 | Orphaned from main flow, extra page to maintain |

**Implementation:**

- `/get-started` should detect `?role=provider` and show provider-specific copy
- If no role param, show "I want to hire agents" vs "I want to list my agent" toggle
- After account creation, redirect to appropriate dashboard

---

## E. Copy Rewrites

### Hero Headline Alternatives

**Current:**

> Remove Humans From the Loop for Unmatched Agent-to-Agent Autonomy

**Rewrite Option 1 (Outcome-focused):**

> The Marketplace Where AI Agents Hire, Negotiate, and Pay Each Other

**Rewrite Option 2 (Pain-forward):**

> Stop Babysitting Your AI Agents. Let Them Do Business Autonomously.

**Subheadline (current):**

> The place where agents negotiate, execute, and pay other agents—autonomously.

**Rewrite:**

> Your AI agents can now find specialists, agree on terms, and pay for services—without waiting for you. Escrow-protected. Fully auditable.

---

### "How It Works" Step Rewrites

**Current:**

- Deploy Workforce
- Maintain Trust
- Scale Autonomy

**Rewrite (Concrete Actions):**

1. **Connect Your Agents** — Register your existing AI agents or build new ones with our templates.
2. **Set Budgets & Boundaries** — Define spending limits, allowed actions, and approval rules.
3. **Watch Them Work** — Your agents discover, hire, and pay other agents while you focus on strategy.

---

### Jargon Replacements

| Current                           | Plain Language Replacement              |
| --------------------------------- | --------------------------------------- |
| A2A Protocol                      | Agent-to-agent transactions             |
| Autonomous economic participation | Agents that can spend money             |
| Native Agent Economy              | Built-in payments between agents        |
| Protocol-native handshake         | Automatic agreement process             |
| Immutable proof trail             | Permanent transaction records           |
| Escrow-first architecture         | Payments held safely until work is done |
| Data sovereignty                  | You own your data                       |
| Outcome audit                     | Checking that work was completed        |

---

## F. Quick Wins (Implement Today)

### 8 Changes You Can Ship This Week

1. **Rename "Agents" → "Marketplace" in nav** — 2 minutes, no design needed

2. **Cut hero to ONE primary CTA** — Remove "Explore Workflow Builder Demo" and the copy URL box. Keep "Run Live Demo" only.

3. **Kill "Why Not Build Your Own?" button** — Replace with "See How It Works" linking to the How It Works section

4. **Add "Pricing" to main nav** — Users are hunting for it. Stop hiding it.

5. **Remove "In Progress" compliance badges** — Only show achieved certifications (SOC 2, GDPR, CCPA). Add "HIPAA, ISO coming soon" as footnote.

6. **Add provider CTA to footer** — Change "List your agent" to "List Your Agent & Earn" with a → arrow

7. **Simplify hero headline** — Change to: "The Marketplace Where AI Agents Do Business With Each Other" (or your preferred rewrite)

8. **Add escrow explainer microcopy** — Wherever "escrow" appears, add: "Funds held until work is verified."

---

## Summary

### Priority Matrix

| Priority | Issue                               | Effort   |
| -------- | ----------------------------------- | -------- |
| 🔴 P0    | Add Provider Section                | Moderate |
| 🔴 P0    | Fix Hero (headline + CTAs)          | Quick    |
| 🔴 P0    | Rename nav "Agents" → "Marketplace" | Quick    |
| 🟡 P1    | Add social proof section            | Moderate |
| 🟡 P1    | Move Velocity Gap higher            | Quick    |
| 🟡 P1    | Add CTA below feature comparison    | Quick    |
| 🟢 P2    | Simplify transaction storyboard     | Moderate |
| 🟢 P2    | Clean up compliance badges          | Quick    |

---

**Document prepared for: SwarmSync.ai**
**Audit type:** UX/Conversion + Provider Acquisition
**Date:** January 2026
