# SwarmSync Tasks: Content & Polish

**Priority:** P1/P2 — This Sprint + Backlog  
**Estimated Effort:** 3-5 hours  
**Files Affected:** Various section components, `app/page.tsx`

---

## P1: Trust & Credibility

### Social Proof Section

- [x] **Add social proof to homepage**
  - Placement: After hero OR after "How It Works"
  - Choose ONE of these approaches:

  **Option A: Customer Logos**

  ```
  Trusted by teams at
  [Logo] [Logo] [Logo] [Logo] [Logo]
  ```

  **Option B: Single Testimonial**

  ```
  "SwarmSync cut our agent coordination time from days to minutes.
   The escrow system means we actually trust autonomous payments now."
   — [Name], [Title] at [Company]
  ```

  **Option C: Aggregate Stats**

  ```
  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │   $2.4M     │  │    847      │  │   12,000+   │
  │ Transactions│  │   Agents    │  │    Tasks    │
  │  Processed  │  │   Listed    │  │  Completed  │
  └─────────────┘  └─────────────┘  └─────────────┘
  ```

### Escrow Explainer

- [x] **Add escrow microcopy throughout site**
  - Wherever "escrow" is mentioned, add inline or tooltip explanation:
  - "Funds held securely until work is verified. If there's a dispute, we mediate."

- [ ] **Consider adding escrow diagram**
  - Simple flow: Buyer funds → Escrow holds → Work done → Verified → Released

### Compliance Badges Cleanup

- [x] **Update compliance badge display**
  - KEEP as-is: SOC 2 Type II Certified, GDPR Compliant, CCPA Compliant
  - CHANGE: "HIPAA Ready" → Remove from badges
  - CHANGE: "ISO 27001 In Progress" → Remove from badges
  - ADD footnote: "HIPAA and ISO 27001 certifications in progress"

---

## P1: Content Reorganization

## -### Move Velocity Gap Section

- [x] **Relocate "The Velocity Gap" section**
  - Current position: After transaction storyboard (too far down)
  - New position: Immediately after hero section
  - Rationale: Agitate the problem before showing solution

### Add CTA After Feature Comparison

- [x] **Add conversion CTA below comparison table**
  - After: SwarmSync vs LangChain/CrewAI/AutoGPT table
  - Before: Integrations logo section
  - CTA: "Start Free Trial" button (primary style)
  - Subtext: "No credit card required • 14-day free trial"

---

## P2: Copy Improvements

-### How It Works Rewrites

- [x] **Update step 1 title and description**
  - Current title: "Deploy Workforce"
  - New title: "Connect Your Agents"
  - New description: "Register your existing AI agents or build new ones with our templates."

- [x] **Update step 2 title and description**
  - Current title: "Maintain Trust"
  - New title: "Set Budgets & Boundaries"
  - New description: "Define spending limits, allowed actions, and approval rules."

- [x] **Update step 3 title and description**
  - Current title: "Scale Autonomy"
  - New title: "Watch Them Work"
  - New description: "Your agents discover, hire, and pay other agents while you focus on strategy."

### Prime Directive Label

- [x] **Simplify "Prime Directive" branding**
  - Current: "The SwarmSync Prime Directive"
  - Option A: "Our Security Promise"
  - Option B: Remove label entirely, just show the principles

### Transaction Storyboard Simplification

- [x] **Make transaction feed more readable**
  - Current: Raw log format with negotiation IDs and status codes
  - New: Human-friendly format

  ```
  Current:
  004 | Negotiation ID: d9f2ee6a-6f3f-4b75-b8a2-374be4d51181
  005 | Escrow locked: $20 (status: PENDING)

  New:
  ✓ Agent A hired Agent B for $20
  ✓ Funds secured in escrow
  ✓ Task completed and verified
  ✓ Payment released to Agent B
  ```

---

## P2: UX Polish

### Cookie Banner

- [x] **Reduce cookie banner obtrusiveness**
  - Option A: Move to top bar (less intrusive)
  - Option B: Auto-dismiss after 5 seconds of scroll
  - Option C: Reduce size, use more subtle styling
  - Option D: Remember preference and don't show again

-### Verified Badge Preview (Provider Section)

- [x] **Add badge preview to provider section**
  - Show the green "✓ Verified" badge
  - Caption: "Earn this badge after verification"
  - Motivates providers to complete the process

-### Sample Agent Card (Provider Section)

- [x] **Add agent card mockup to provider section**
  - Display a representative listing card (like on /agents page)
  - Use placeholder: "Your Agent Name Here"
  - Shows providers what their listing will look like

---

## Jargon Replacement Reference

Use this table when updating copy throughout the site:

| Current Term                      | Plain Language                          |
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

## Section Order (Final Recommended)

After all changes, homepage sections should flow:

1. Hero (simplified)
2. **Velocity Gap (moved up)**
3. Transaction Storyboard / Live Demo
4. Traditional vs SwarmSync Comparison
5. Enterprise-Grade Governance
6. Compliance Badges (cleaned up)
7. Technical Architecture
8. How It Works (rewritten)
9. Why SwarmSync
10. Feature Comparison Table
11. **CTA after comparison (new)**
12. Integrations Logos
13. **Provider Section (new)**
14. Final CTA
15. Footer

---

## QA Checklist

- [ ] Social proof section displays correctly
- [ ] Escrow explainers appear where escrow is mentioned
- [ ] Only achieved compliance badges are shown
- [ ] Velocity Gap section appears after hero
- [ ] CTA appears below feature comparison table
- [ ] How It Works steps have new titles and descriptions
- [ ] Transaction storyboard is human-readable
- [ ] Cookie banner is less intrusive
- [ ] All jargon has been reviewed and simplified where needed

---

_Part 4 of 4 — Content & Polish_
