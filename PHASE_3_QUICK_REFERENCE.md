# Phase 3 Quick Reference Guide

A developer-focused summary of all new features and where to find them.

## Feature Map

### 🎨 UI Components

| Component                   | Location                                               | Purpose                          |
| --------------------------- | ------------------------------------------------------ | -------------------------------- |
| `MarketplaceHero`           | `components/marketplace/hero.tsx`                      | Landing page hero section        |
| `OnboardingChecklist`       | `components/onboarding/checklist.tsx`                  | 3-step getting started guide     |
| `AgentCard` (enhanced)      | `components/agents/enhanced-agent-card.tsx`            | Beautiful agent listing card     |
| `CreatorAnalyticsDashboard` | `components/analytics/creator-analytics-dashboard.tsx` | Full metrics dashboard           |
| `SimpleLineChart`           | `components/charts/simple-line-chart.tsx`              | SVG line chart for trends        |
| `BillingDashboard`          | `components/billing/billing-dashboard.tsx`             | Subscription & payout management |
| `PayoutSettings`            | `components/billing/payout-settings.tsx`               | Stripe Connect setup UI          |

### 📊 Analytics

| Hook                          | Location                 | Returns                                         |
| ----------------------------- | ------------------------ | ----------------------------------------------- |
| `useAgentAnalytics`           | `hooks/use-analytics.ts` | AgentAnalyticsSummary (ROI, success rate, etc.) |
| `useAgentAnalyticsTimeseries` | `hooks/use-analytics.ts` | Array of 30-day daily metrics                   |

**Endpoint**: `/api/quality/analytics/agents/:agentId`

### 💳 Stripe Integration

| Service                   | Location                                        | Key Methods                                                 |
| ------------------------- | ----------------------------------------------- | ----------------------------------------------------------- |
| `StripeConnectService`    | `modules/payments/stripe-connect.service.ts`    | createConnectedAccount, initiatePayout, handlePayoutWebhook |
| `PayoutsController`       | `modules/payments/payouts.controller.ts`        | REST API (4 endpoints)                                      |
| `StripeWebhookController` | `modules/payments/stripe-webhook.controller.ts` | Webhook handlers                                            |

**Endpoints**:

```
POST   /payouts/setup
GET    /payouts/account-status/:agentId
POST   /payouts/request
GET    /payouts/history/:agentId
```

### 🔄 Workflow Builder

**File**: `components/workflows/workflow-builder.tsx`  
**Features**:

- Form-based step builder (add/remove steps)
- JSON editor fallback
- Per-step budget allocation

---

## Styling Quick Reference

### Colors

- **Primary Accent**: `brass` (gold-brown)
- **Success**: `emerald-600`
- **Warning**: `amber-600`
- **Text**: `ink`, `ink-muted`
- **Backgrounds**: `white/80`, `outline/5`

### Spacing Pattern

- Large cards: `p-8` + `rounded-[3rem]`
- Content sections: `rounded-2xl` + `p-6`
- Padding: Standard Tailwind scale

### Typography

- **Headlines**: `font-headline` (Bodoni MT Black)
- **Body**: `font-body` (Bodoni MT Black via globals.css)
- **Display**: `font-display` (for large text)

### Components

```tsx
// Metric display (example from analytics)
<Card className="border-white/70 bg-white/80">
  <CardHeader>
    <CardTitle className="text-lg font-headline">Title</CardTitle>
  </CardHeader>
  <CardContent>{/* content */}</CardContent>
</Card>
```

---

## Common Tasks

### Add a new metric to analytics dashboard

1. Add field to `AgentAnalyticsSummary` interface in `use-analytics.ts`
2. Create `MetricCard` in `creator-analytics-dashboard.tsx`
3. Hook up to new API field

### Create a new billing tab

1. Add `BillingTabName` to enum in `billing-dashboard.tsx`
2. Create tab content component
3. Add to tab list in TabsContent

### Add payout status check

```tsx
const { data: status, isLoading } = useQuery({
  queryKey: ['payout-status', agentId],
  queryFn: async () => {
    const res = await fetch(`/api/payouts/account-status/${agentId}`);
    return res.json();
  },
});
```

### Handle Stripe webhook

1. Ensure env vars set: `STRIPE_WEBHOOK_SECRET_*`
2. Webhook automatically routed to `stripe-webhook.controller.ts`
3. Calls `stripeConnectService.handlePayoutWebhook()`
4. Updates DB payout records

---

## File Tree Summary

```
apps/
  web/src/
    components/
      analytics/
        ✨ creator-analytics-dashboard.tsx (new)
      agents/
        ✨ enhanced-agent-card.tsx (new)
      billing/
        ✨ billing-dashboard.tsx (new)
        ✨ payout-settings.tsx (new)
      charts/
        ✨ simple-line-chart.tsx (new)
      marketplace/
        ✨ hero.tsx (new)
      onboarding/
        ✨ checklist.tsx (new)
    hooks/
      ✨ use-analytics.ts (new)
    app/(marketplace)/
      agents/page.tsx (updated)
      (console)/agents/[agentId]/
        ✨ analytics/page.tsx (new)
  api/src/
    modules/
      payments/
        ✨ stripe-connect.service.ts (new)
        ✨ payouts.controller.ts (new)
        ✨ stripe-webhook.controller.ts (new)
        payments.module.ts (updated)

public/logos/
  ✨ logo.png (new)
  ✨ swarm-sync-wordmark.png (new)
  ✨ swarm-sync-logo.png (new)
  ✨ logo_artboard_1000x1000.png (new)
```

---

## Quick Start for New Features

### To use analytics dashboard:

```tsx
import { CreatorAnalyticsDashboard } from '@/components/analytics/creator-analytics-dashboard';

<CreatorAnalyticsDashboard agentId="agent_123" agentName="Lead Gen Pro" />;
```

### To add payout UI:

```tsx
import { BillingDashboard } from '@/components/billing/billing-dashboard';

<BillingDashboard agentId="agent_123" />;
```

### To initiate payout (backend):

```typescript
const payout = await this.stripeConnectService.initiatePayout(
  'agent_123',
  5000, // cents ($50)
);
```

### To render hero page:

```tsx
import { MarketplaceHero } from '@/components/marketplace/hero';

<MarketplaceHero />;
```

---

## Testing Checklist

- [ ] Analytics metrics display correctly
- [ ] Chart renders with data points
- [ ] Stripe Connect redirects work
- [ ] Webhook events update status
- [ ] Workflow steps add/remove
- [ ] Billing dashboard shows all tabs
- [ ] Onboarding checklist tracks progress
- [ ] Hero page loads all sections
- [ ] Agent cards hover effects work
- [ ] Mobile responsive layout

---

## Environment Variables

```env
# .env.local (frontend)
NEXT_PUBLIC_API_URL=http://localhost:3001

# .env (backend)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET_PAYOUTS=whsec_...
STRIPE_WEBHOOK_SECRET_ACCOUNT=whsec_...
STRIPE_CONNECT_PLATFORM_ACCOUNT_ID=acct_...
```

---

## Troubleshooting

**Analytics not loading?**

- Verify backend endpoint: `GET /api/quality/analytics/agents/:agentId`
- Check React Query cache with `@tanstack/react-query-devtools`

**Stripe webhook failing?**

- Confirm webhook secret matches in dashboard
- Check logs: `mcp_copilot_conta_logs_for_container`

**Chart not rendering?**

- Verify `SimpleLineChart` receives non-empty data array
- Check browser console for SVG errors

**Styling looks wrong?**

- Clear Tailwind cache: `rm -rf .next/`
- Verify font files loaded: Check `src/app/globals.css`

---

**Last Updated**: November 16, 2025  
**Prepared for**: Development team, QA, and product onboarding
