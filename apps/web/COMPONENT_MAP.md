# Component Migration Map

This document tracks the migration of dashboard components from the old `/dashboard` page to the new IA structure.

## Overview

The refactor splits the busy dashboard into three focused pages:

- `/overview` - Org-level KPIs and alerts
- `/agents` - Agent list and marketplace discovery
- `/agents/[slug]` - Individual agent detail with tabs

## Component Locations

### Old Dashboard → New Overview (`/overview`)

| Component                      | Old Location     | New Location              | Notes                         |
| ------------------------------ | ---------------- | ------------------------- | ----------------------------- |
| `credit-summary-card.tsx`      | Dashboard main   | Overview KPI row          | Billing/credits summary       |
| `org-overview-card.tsx`        | Dashboard main   | Overview KPI row          | GMV, outcomes, active agents  |
| `org-roi-timeseries-chart.tsx` | Dashboard main   | Overview chart section    | Performance trend chart       |
| `recent-activity-list.tsx`     | Not used         | Overview activity section | Recent transactions/events    |
| Status pills (API, Payments)   | Dashboard header | Overview header           | Inline in subtitle            |
| Primary CTAs                   | Dashboard header | Overview header           | Create Agent, Launch Workflow |

**Removed from Overview:**

- `quick-actions.tsx` - Redundant with header CTAs
- `featured-agents.tsx` - Moved to /agents
- All A2A components - Moved to agent detail tabs

### Old Dashboard → New Agents List (`/agents`)

| Component             | Old Location   | New Location            | Notes                                   |
| --------------------- | -------------- | ----------------------- | --------------------------------------- |
| `featured-agents.tsx` | Dashboard main | Agents page (collapsed) | Marketplace discovery section           |
| Agent list/grid       | NEW            | Agents page main        | Shows user's agents with search/filters |

### Old Dashboard → New Agent Detail (`/agents/[slug]`)

#### Tab 1: Overview

- Agent health summary (NEW)
- Recent events (NEW)
- Capability summary (NEW)

#### Tab 2: Mesh

| Component                  | Old Location   | New Location | Notes                               |
| -------------------------- | -------------- | ------------ | ----------------------------------- |
| `budget-controls-card.tsx` | Dashboard main | Mesh tab     | Converted to summary + Edit drawer  |
| `agent-network-graph.tsx`  | Dashboard main | Mesh tab     | Collaboration network visualization |
| `a2a-operations-panel.tsx` | Dashboard main | Mesh tab     | Agent operations view               |

#### Tab 3: Spend & ROI

| Component                     | Old Location   | New Location    | Notes              |
| ----------------------------- | -------------- | --------------- | ------------------ |
| `a2a-roi-summary.tsx`         | Dashboard main | Spend & ROI tab | KPI tiles          |
| `a2a-transaction-monitor.tsx` | Dashboard main | Spend & ROI tab | Transactions table |

#### Tab 4: Negotiations

| Component              | Old Location   | New Location     | Notes                 |
| ---------------------- | -------------- | ---------------- | --------------------- |
| `ap2-negotiations.tsx` | Dashboard main | Negotiations tab | AP2 negotiations list |

#### Tab 5: Settings

- Agent configuration (NEW)
- API keys, permissions (reused from existing settings)

## Navigation Changes

### Old Sidebar

```
Build
  - Home
  - Dashboard  ← CHANGED
  - Wallet
  - Agents
  - Workflows
  - Billing
  - Quality

Analytics
  - Usage
  - Cost
  - Logs
  - Batches
  - Agent Mesh

Manage
  - API keys
  - Limits
  - Settings
```

### New Sidebar

```
Home
  - Overview  ← NEW (was Dashboard)

Build
  - Agents
  - Workflows

Spend
  - Wallet
  - Billing

Quality
  - Test Library
  - Outcomes

System
  - Logs
  - API Keys
  - Limits
  - Settings
```

## Redirect

- `/dashboard` → `/overview` (Next.js redirect)

## Progressive Disclosure

### Empty States

- No agents → Compact message with CTA
- No transactions → Small message, no table
- No negotiations → Small message, no list
- No network data → Collapsed stub

### Collapsed Sections

- Marketplace in `/agents` → Collapsed by default, expandable
- Advanced settings → Behind tabs in agent detail

## Files Created

### New Pages

- `apps/web/src/app/(marketplace)/(console)/overview/page.tsx`
- `apps/web/src/app/(marketplace)/(console)/agents/page.tsx`
- `apps/web/src/app/(marketplace)/(console)/agents/[slug]/page.tsx`

### Modified Files

- `apps/web/src/components/layout/Sidebar.tsx` - Updated navigation
- `apps/web/src/app/(marketplace)/(console)/dashboard/page.tsx` - Now redirects to /overview
- `apps/web/src/app/(marketplace)/(console)/layout.tsx` - Updated auth redirect

## Component Reuse

All dashboard components in `apps/web/src/components/dashboard/` are reused as-is:

- ✅ No visual changes to existing components
- ✅ Components moved to appropriate pages/tabs
- ✅ Progressive disclosure applied via conditional rendering

## Testing Checklist

- [ ] `/overview` loads with KPIs, alerts, and chart
- [ ] `/dashboard` redirects to `/overview`
- [ ] `/agents` shows agent list with search
- [ ] `/agents/[slug]` shows agent detail with 5 tabs
- [ ] Sidebar navigation reflects new IA
- [ ] Empty states are compact and helpful
- [ ] No duplicate CTAs or redundant sections
- [ ] All existing components render correctly in new locations
