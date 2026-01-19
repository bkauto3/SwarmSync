# SwarmSync Tasks: Hero & Navigation

**Priority:** P0 — Ship This Week  
**Estimated Effort:** 2-4 hours  
**Files Affected:** `components/Hero.tsx`, `components/Navigation.tsx`, `app/page.tsx`

---

## Hero Section

- [x] **Replace hero headline**
  - Current: "Remove Humans From the Loop for Unmatched Agent-to-Agent Autonomy"
  - New: "The Marketplace Where AI Agents Hire, Negotiate, and Pay Each Other"

- [x] **Replace hero subheadline**
  - Current: "The place where agents negotiate, execute, and pay other agents—autonomously."
  - New: "Your AI agents can now find specialists, agree on terms, and pay for services—without waiting for you. Escrow-protected. Fully auditable."

- [x] **Remove "Explore Workflow Builder Demo" button**
  - Keep only "Run Live A2A Demo" as primary CTA

- [x] **Remove "COPY THIS RUN" URL input box**
  - Too technical for first impression, adds clutter

- [x] **Relabel "Why Not Build Your Own?" button**
  - Current: "Why Not Build Your Own?"
  - New: "Build vs Buy Calculator" or "See Cost Comparison"
  - Keep destination URL — the page content is good

- [x] **Keep "View pricing" text link**
  - Position below primary CTA
  - Consider making it slightly more visible (underline on hover)

---

## Navigation

- [x] **Rename "Agents" → "Marketplace" in main nav**
  - Display label change only
  - Keep URL as `/agents` (no routing changes needed)

- [x] **Add "Pricing" link to main nav**
  - Position: Between "Dashboard" and "Sign in"
  - Link to: `/pricing`

---

## Final Hero Structure

```
┌─────────────────────────────────────────────────────────────┐
│  HEADLINE                                                    │
│  The Marketplace Where AI Agents Hire,                      │
│  Negotiate, and Pay Each Other                              │
│                                                              │
│  SUBHEADLINE                                                 │
│  Your AI agents can now find specialists, agree on terms,   │
│  and pay for services—without waiting for you.              │
│  Escrow-protected. Fully auditable.                         │
│                                                              │
│  ┌──────────────────┐   ┌─────────────────────┐             │
│  │ Run Live A2A Demo│   │ Build vs Buy Calculator │          │
│  └──────────────────┘   └─────────────────────┘             │
│           (primary)              (secondary)                 │
│                                                              │
│                    View pricing                              │
│                    (text link)                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Final Nav Structure

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]   Marketplace   Dashboard   Pricing  │  Sign in  [Get Started] │
└─────────────────────────────────────────────────────────────┘
```

---

## QA Checklist

- [ ] Hero headline renders correctly on mobile (line breaks)
- [ ] Subheadline doesn't overflow on small screens
- [ ] Primary CTA is visually dominant (purple filled button)
- [ ] Secondary CTA is visually subordinate (outline or ghost button)
- [ ] "View pricing" link is clickable and goes to `/pricing`
- [ ] Nav "Marketplace" link goes to `/agents`
- [ ] Nav "Pricing" link goes to `/pricing`

---

_Part 1 of 4 — Hero & Navigation_
