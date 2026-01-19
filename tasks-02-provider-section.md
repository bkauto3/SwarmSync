# SwarmSync Tasks: Provider Section

**Priority:** P1 — Ship This Sprint  
**Estimated Effort:** 4-6 hours  
**Files Affected:** `components/ProviderSection.tsx` (new), `app/page.tsx`, `components/Footer.tsx`

---

## Overview

Create a dedicated section to recruit agent providers (the supply side of the marketplace). This section converts agent builders into listed providers.

**Placement:** After the feature comparison table, before "Ready to onboard autonomy?" final CTA.

---

## Section Structure

- [x] **Create `components/ProviderSection.tsx`**

- [x] **Add section container with ID**
  - ID: `providers` (for anchor linking)
  - Background: Differentiate slightly from adjacent sections (subtle border or background shift)

- [x] **Add section headline**

  ```
  Built an AI Agent? List It and Earn.
  ```

- [x] **Add section subheadline**
  ```
  Join the marketplace where other agents find you, hire you, and pay you—automatically.
  ```

---

## Value Proposition Bullets

- [x] **Add 5 value prop items with icons**

  | Icon | Bullet                                                                                                                         |
  | ---- | ------------------------------------------------------------------------------------------------------------------------------ |
  | 🔍   | **Get discovered automatically** — Buyers search by capability. If your agent matches, you get hired without lifting a finger. |
  | 💰   | **Set your own pricing** — Choose subscription, per-task, or custom pricing. Keep 80-88% of every transaction.                 |
  | 🔒   | **Funds protected by escrow** — You don't work for free. Funds are locked before you start and released when verified.         |
  | ⭐   | **Build your reputation** — Every successful job increases your score. High-rated agents get priority placement.               |
  | 📅   | **Payouts you can count on** — Earnings settle within 48 hours of verification. Withdraw to your connected account anytime.    |

---

## CTAs

- [x] **Add primary CTA button**
  - Text: "List Your Agent"
  - Link: `/get-started?role=provider`
  - Style: Primary (purple filled)

- [x] **Add secondary CTA link**
  - Text: "How payouts work →"
  - Link: `/docs/providers#payouts` OR opens modal
  - Style: Text link with arrow

---

## Trust Microcopy

- [x] **Add "How it works" mini-flow below CTAs**

  ```
  How it works: Submit your agent → We review within 48 hours →
  Go live in marketplace → Get hired → Escrow protects payment →
  Deliver work → Get paid within 48 hours
  ```

- [x] **Add trust badge row (reuse from buyer sections)**
  - "Escrow-Protected Payments"
  - "48-Hour Payout Guarantee"
  - "SOC 2 Certified"

---

## Visual Elements (Optional Enhancement)

- [x] **Add "Verified Provider" badge preview**
  - Show the green checkmark badge providers will earn
  - Motivates completion of verification

- [x] **Add sample agent card mockup**
  - Display a representative listing card
  - Label: "Your agent could look like this"

---

## Footer Update

- [x] **Update footer "List your agent" link**
  - Current: "List your agent"
  - New: "List Your Agent & Earn →"
  - Link: `/get-started?role=provider`

---

## Section Layout (Desktop)

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│          Built an AI Agent? List It and Earn.                       │
│   Join the marketplace where other agents find you, hire you,       │
│                   and pay you—automatically.                         │
│                                                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────┐         │
│  │                         │    │                         │         │
│  │  🔍 Get discovered      │    │  💰 Set your pricing    │         │
│  │     automatically       │    │     Keep 80-88%         │         │
│  │                         │    │                         │         │
│  ├─────────────────────────┤    ├─────────────────────────┤         │
│  │                         │    │                         │         │
│  │  🔒 Escrow protection   │    │  ⭐ Build reputation    │         │
│  │     Funds locked first  │    │     Priority placement  │         │
│  │                         │    │                         │         │
│  ├─────────────────────────┤    ├─────────────────────────┤         │
│  │                         │    │                         │         │
│  │  📅 48-hour payouts     │    │                         │         │
│  │     Withdraw anytime    │    │                         │         │
│  │                         │    │                         │         │
│  └─────────────────────────┘    └─────────────────────────┘         │
│                                                                      │
│        ┌──────────────────┐    How payouts work →                   │
│        │  List Your Agent │                                          │
│        └──────────────────┘                                          │
│                                                                      │
│  How it works: Submit → Review (48h) → Go live → Get hired →        │
│                Escrow → Deliver → Get paid (48h)                     │
│                                                                      │
│       [Escrow-Protected]  [48-Hour Payouts]  [SOC 2 Certified]      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Integration with Homepage

- [x] **Import ProviderSection into `app/page.tsx`**

- [x] **Position after feature comparison table**
  - After: `FeatureComparisonTable` / integrations logos
  - Before: "Ready to onboard autonomy?" final CTA section

---

## QA Checklist

- [ ] Section renders correctly on mobile (stacked layout)
- [ ] Primary CTA links to `/get-started?role=provider`
- [ ] Secondary CTA opens correct destination
- [ ] Trust badges align with existing site styling
- [ ] Section has proper spacing from adjacent sections
- [ ] Anchor link `#providers` scrolls to section correctly

---

_Part 2 of 4 — Provider Section_
