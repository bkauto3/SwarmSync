# SwarmSync UI Refactor - Implementation Plan

## Current State Analysis

### Router: Next.js App Router

- Location: `apps/web/src/app/`
- Console routes: `apps/web/src/app/(marketplace)/(console)/`

### Current Dashboard Components

Located in `apps/web/src/components/dashboard/`:

1. `credit-summary-card.tsx` - Billing/credits KPI
2. `quick-actions.tsx` - Action buttons
3. `org-overview-card.tsx` - Org-level KPIs
4. `org-roi-timeseries-chart.tsx` - ROI chart
5. `featured-agents.tsx` - Agent discovery/marketplace
6. `a2a-operations-panel.tsx` - Agent mesh operations
7. `a2a-roi-summary.tsx` - A2A ROI metrics
8. `a2a-transaction-monitor.tsx` - A2A transactions
9. `agent-network-graph.tsx` - Network visualization
10. `ap2-negotiations.tsx` - Negotiations list
11. `budget-controls-card.tsx` - Budget management form
12. `recent-activity-list.tsx` - Activity feed

### Current Sidebar Navigation

Located in `apps/web/src/components/layout/Sidebar.tsx`

## Component Migration Map

### Overview Page (`/overview`)

**Keep:**

- `credit-summary-card.tsx` → KPI card (Spend 30d)
- `org-overview-card.tsx` → KPI cards (GMV, Verified outcomes, Active agents)
- `org-roi-timeseries-chart.tsx` → Single toggleable chart
- `recent-activity-list.tsx` → Activity feed
- Status pills (API, Payments, Agent Mesh)

**Remove from overview:**

- `quick-actions.tsx` (redundant with header CTAs)
- `featured-agents.tsx` (move to /agents)
- `a2a-operations-panel.tsx` (move to agent detail)
- All A2A components (move to agent detail tabs)

### Agents List Page (`/agents`)

**New components needed:**

- Agent list/grid view
- Search and filters
- **Move here:** `featured-agents.tsx` (as collapsed "Marketplace" section)

### Agent Detail Page (`/agents/[agentId]`)

**Tab 1: Overview**

- Agent health summary
- Recent events
- Capability summary

**Tab 2: Mesh**

- `budget-controls-card.tsx` → Convert to summary + Edit drawer
- `agent-network-graph.tsx` → Collaboration network
- `a2a-operations-panel.tsx` → Operations view

**Tab 3: Spend & ROI**

- `a2a-roi-summary.tsx` → KPI tiles
- `a2a-transaction-monitor.tsx` → Transactions table

**Tab 4: Negotiations**

- `ap2-negotiations.tsx` → Negotiations list

**Tab 5: Settings**

- Agent config forms (reuse existing)

## Implementation Steps

### Step 1: Create Overview Page

- [ ] Create `/overview/page.tsx`
- [ ] Move relevant components
- [ ] Simplify header (remove giant hero)
- [ ] Add KPI row (4 cards max)
- [ ] Add alerts/next steps section
- [ ] Add activity feed
- [ ] Add single toggleable chart

### Step 2: Create Agents List Page

- [ ] Create `/agents/page.tsx` (or adapt existing)
- [ ] Add search and filters
- [ ] Create agent list component
- [ ] Move `featured-agents.tsx` as collapsed section

### Step 3: Create Agent Detail Page

- [ ] Create `/agents/[agentId]/page.tsx`
- [ ] Create tab navigation component
- [ ] Implement 5 tabs (Overview, Mesh, Spend & ROI, Negotiations, Settings)
- [ ] Convert budget controls to summary + drawer

### Step 4: Update Sidebar

- [ ] Rename "Dashboard" → "Overview"
- [ ] Update route links
- [ ] Reorganize sections per new IA

### Step 5: Add Redirect

- [ ] Create `/dashboard/page.tsx` with redirect to `/overview`

### Step 6: Testing & Documentation

- [ ] Create `COMPONENT_MAP.md`
- [ ] Test all routes
- [ ] Verify empty states
- [ ] Check responsive behavior

## Files to Create/Modify

### New Files

- `apps/web/src/app/(marketplace)/(console)/overview/page.tsx`
- `apps/web/src/app/(marketplace)/(console)/agents/page.tsx`
- `apps/web/src/app/(marketplace)/(console)/agents/[agentId]/page.tsx`
- `apps/web/src/components/agents/agent-list.tsx`
- `apps/web/src/components/agents/agent-detail-tabs.tsx`
- `apps/web/src/components/agents/budget-summary-drawer.tsx`
- `apps/web/COMPONENT_MAP.md`

### Modified Files

- `apps/web/src/components/layout/Sidebar.tsx`
- `apps/web/src/app/(marketplace)/(console)/dashboard/page.tsx` (redirect)
- `apps/web/src/app/(marketplace)/(console)/layout.tsx` (update requireAuth)

## Data Requirements

### Existing Endpoints (from SDK)

- `getOrganizationRoi(orgSlug)` ✅
- `getOrganizationRoiTimeseries(orgSlug, days)` ✅
- `getBillingSubscription()` ✅
- `listAgents(filters)` ✅

### Potentially Missing Endpoints

- Agent detail by ID (may need to check)
- Agent network/mesh data
- Agent transactions
- Agent negotiations
- Recent activity feed (org-level)

## Progressive Disclosure Rules

1. **Empty States:**
   - No transactions → Small message, no table
   - No negotiations → Small message, no list
   - No network data → Collapsed stub

2. **Collapsed Sections:**
   - Marketplace in /agents → Collapsed by default
   - Advanced settings → Behind tabs

3. **Conditional Rendering:**
   - Only show "Approvals" nav item if approvals exist
   - Only show mesh tab if agent has A2A enabled

## Next Steps

Execute implementation in order (Steps 1-6)
