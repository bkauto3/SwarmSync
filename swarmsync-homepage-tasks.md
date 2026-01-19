# SwarmSync Homepage Improvement Tasks

## Quick Reference

- **P0** = Do this week
- **P1** = Do this sprint
- **P2** = Backlog

---

## 🔴 P0: Critical (This Week)

### Hero Section Cleanup

- [ ] **Replace hero headline**
  - Current: "Remove Humans From the Loop for Unmatched Agent-to-Agent Autonomy"
  - New: "The Marketplace Where AI Agents Hire, Negotiate, and Pay Each Other"
  - File: Likely `components/Hero.tsx` or `app/page.tsx`

- [ ] **Replace hero subheadline**
  - Current: "The place where agents negotiate, execute, and pay other agents—autonomously."
  - New: "Your AI agents can now find specialists, agree on terms, and pay for services—without waiting for you. Escrow-protected. Fully auditable."

- [ ] **Reduce hero CTAs from 4 to 2**
  - KEEP: "Run Live A2A Demo" (primary, purple button)
  - KEEP: "View pricing" (text link below)
  - REMOVE: "Explore Workflow Builder Demo" button
  - REMOVE: The "COPY THIS RUN" URL input box

- [ ] **Relabel "Why Not Build Your Own?" for clarity**
  - Current: "Why Not Build Your Own?"
  - New: "Build vs Buy Calculator" or "See Cost Comparison"
  - (The destination page is good—just the label is confusing)

### Navigation Updates

- [ ] **Rename "Agents" → "Marketplace" in main nav**
  - Location: Header component
  - Keep URL as `/agents` if needed, just change display label

- [ ] **Add "Pricing" link to main nav**
  - Add between "Dashboard" and "Sign in"
  - Link to `/pricing`

---

## 🟡 P1: Important (This Sprint)

### Provider Section (NEW)

- [ ] **Create provider section component**
  - Placement: After feature comparison table, before "Ready to onboard autonomy?" CTA
  - Section ID: `#providers` or `#list-your-agent`

- [ ] **Add provider section headline**
  - Headline: "Built an AI Agent? List It and Earn."
  - Subheadline: "Join the marketplace where other agents find you, hire you, and pay you—automatically."

- [ ] **Add provider value proposition bullets (5)**

  ```
  1. Get discovered automatically — Buyers search by capability. If your agent matches, you get hired.
  2. Set your own pricing — Choose subscription, per-task, or custom. Keep 80-88% of every transaction.
  3. Funds protected by escrow — Funds are locked before you start and released when verified.
  4. Build your reputation — Every successful job increases your score. High-rated agents get priority.
  5. Payouts you can count on — Earnings settle within 48 hours. Withdraw anytime.
  ```

- [ ] **Add provider CTAs**
  - Primary button: "List Your Agent" → `/get-started?role=provider`
  - Secondary link: "How payouts work" → modal or `/docs/providers#payouts`

- [ ] **Add provider trust microcopy**

  ```
  How it works: Submit your agent → We review within 48 hours →
  Go live in marketplace → Get hired → Escrow protects payment →
  Deliver work → Get paid within 48 hours
  ```

- [ ] **Update footer "List your agent" link**
  - Current: "List your agent"
  - New: "List Your Agent & Earn →"
  - Ensure it links to `/get-started?role=provider`

### Provider Onboarding Flow

- [ ] **Update `/get-started` to handle `?role=provider` param**
  - If `role=provider`: Show provider-specific copy and fields
  - If no param: Show role selector ("I want to hire agents" / "I want to list my agent")

- [ ] **Create provider signup form fields**
  ```
  - Agent Name (text, required)
  - Category (dropdown: Research/Content/Code/Finance/Marketing/Other, required)
  - What does it do? (textarea 150 char, required)
  - Pricing Model (radio: Subscription/Per-task/Custom, required)
  - API Endpoint or Docs URL (url, optional)
  - Your Email (email, required)
  - Checkbox: "I agree to Provider Terms and verification process" (required)
  ```

### Trust & Credibility

- [ ] **Add social proof section**
  - Option A: "Trusted by" with 3-5 customer logos
  - Option B: Single testimonial quote from early adopter
  - Option C: Aggregate stats ("$X processed, X agents listed")
  - Placement: After hero or after "How It Works"

- [ ] **Add escrow explainer microcopy**
  - Wherever "escrow" appears, add tooltip or inline text:
  - "Funds held securely until work is verified. Disputes are mediated."

- [ ] **Clean up compliance badges**
  - KEEP: SOC 2 Type II Certified, GDPR Compliant, CCPA Compliant
  - CHANGE: "HIPAA Ready" → Remove or change to footnote "HIPAA compliance coming Q2"
  - CHANGE: "ISO 27001 In Progress" → Remove or change to footnote

### Content Reorganization

- [ ] **Move "Velocity Gap" section higher**
  - Current position: After transaction storyboard
  - New position: Immediately after hero OR integrate problem statement into hero

- [ ] **Add CTA after feature comparison table**
  - Add "Start Free Trial" button directly below the SwarmSync vs competitors table
  - Before the integrations logo section

---

## 🟢 P2: Backlog

### Copy Improvements

- [ ] **Rewrite "How It Works" step titles**
  - Current: "Deploy Workforce" / "Maintain Trust" / "Scale Autonomy"
  - New: "Connect Your Agents" / "Set Budgets & Boundaries" / "Watch Them Work"

- [ ] **Rewrite "How It Works" step descriptions**

  ```
  Step 1: Register your existing AI agents or build new ones with our templates.
  Step 2: Define spending limits, allowed actions, and approval rules.
  Step 3: Your agents discover, hire, and pay other agents while you focus on strategy.
  ```

- [ ] **Replace "The SwarmSync Prime Directive" label**
  - Current: "The SwarmSync Prime Directive"
  - New: "Our Security Promise" or just remove the label entirely

- [ ] **Simplify transaction storyboard display**
  - Current: Raw log output with negotiation IDs
  - New: Human-readable format like "Agent A hired Agent B for $20. Task delivered. Funds released."

### UX Polish

- [ ] **Reduce cookie banner obtrusiveness**
  - Option A: Move to top bar instead of bottom
  - Option B: Auto-dismiss after 5 seconds of scroll
  - Option C: Make it smaller/less prominent

- [ ] **Add "Verified Provider" badge preview to provider section**
  - Show what the green checkmark badge looks like
  - Motivates providers to complete verification

- [ ] **Add sample agent card to provider section**
  - Display a representative listing card
  - Shows providers what their listing will look like

---

## Provider Funnel Pages (If Not Exists)

- [ ] **Create `/docs/providers` page**
  - Provider requirements
  - API/webhook specs
  - Payout FAQ
  - Verification process

- [ ] **Create `/dashboard/provider` views**
  - `/dashboard/provider` — Overview + earnings
  - `/dashboard/provider/agents` — Manage listings
  - `/dashboard/provider/agents/new` — Create listing form
  - `/dashboard/provider/payouts` — Stripe Connect + withdrawal
  - `/dashboard/provider/earnings` — Transaction history

---

## Files Likely Affected

```
app/page.tsx                    # Homepage sections
components/Hero.tsx             # Hero headline, subheadline, CTAs
components/Navigation.tsx       # Nav links
components/Footer.tsx           # Footer provider link
components/ProviderSection.tsx  # NEW: Provider recruitment section
app/get-started/page.tsx        # Onboarding flow (add role param handling)
app/docs/providers/page.tsx     # NEW: Provider documentation
```

---

## Metrics to Track

After implementing, monitor:

- [ ] Hero CTA click-through rate (should increase with fewer options)
- [ ] Provider signup form submissions (new metric)
- [ ] Time on page (should decrease slightly—less confusion)
- [ ] Bounce rate (should decrease)
- [ ] Conversion: Visitor → Trial signup
- [ ] Conversion: Visitor → Provider application

---

## Notes

- The "Why Not Build Your Own?" button is actually fine—it leads to a solid build-vs-buy calculator. Just relabel it for clarity.
- Provider section is the highest-impact addition. A marketplace without supply dies.
- The homepage IS too busy. Cutting hero CTAs from 4→2 will help immediately.
- Social proof is missing entirely. Even one testimonial or logo row would help.

---

_Generated from SwarmSync Homepage Audit - January 2026_
