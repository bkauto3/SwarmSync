# A/B Testing Guide

## Overview

SwarmSync's A/B testing infrastructure is a lightweight, production-ready system that:

- ✅ Persists user assignments across sessions (localStorage)
- ✅ Integrates with Google Analytics 4 for tracking
- ✅ Supports weighted variant distribution
- ✅ SSR-safe (returns default variant during server render)
- ✅ Simple API for components

---

## Quick Start

### 1. Define Your Test

Edit `apps/web/src/lib/ab-testing.ts` and add your test to `AB_TESTS`:

```typescript
export const AB_TESTS: Record<string, ABTest> = {
  'my-new-test': {
    id: 'my-new-test',
    name: 'My New Test',
    variants: {
      A: {
        name: 'Control',
        weight: 50, // 50% of users
      },
      B: {
        name: 'Treatment',
        weight: 50, // 50% of users
      },
    },
    enabled: true, // Set to true to activate
  },
};
```

### 2. Use in Components

```tsx
'use client';

import { useABTest } from '@/lib/ab-testing';

export function MyComponent() {
  const variant = useABTest('my-new-test');

  return (
    <div>{variant === 'A' ? <button>Control CTA</button> : <button>Treatment CTA</button>}</div>
  );
}
```

### 3. Track Conversions

When the user completes your goal action (signup, purchase, etc.):

```typescript
import { trackABConversion } from '@/lib/ab-testing';

function onSignupSuccess() {
  trackABConversion('my-new-test');
  // ... rest of signup logic
}
```

---

## Pre-Configured Tests

### 1. Homepage CTA Copy

**Test ID:** `homepage-cta`
**Goal:** Improve trial signup rate from homepage

**Variants:**

- A (Control): "Start Free Trial"
- B (Treatment): "See Agents in Action"

**Where to use:**

```tsx
// apps/web/src/app/page.tsx
const variant = useABTest('homepage-cta');
const ctaText = variant === 'A' ? 'Start Free Trial' : 'See Agents in Action';
```

**Track conversion:**

```tsx
// When user completes signup
trackABConversion('homepage-cta');
```

---

### 2. Pricing Display Format

**Test ID:** `pricing-display`
**Goal:** Increase annual plan selection

**Variants:**

- A (Control): Monthly pricing shown by default
- B (Treatment): Annual pricing shown by default

**Where to use:**

```tsx
// apps/web/src/app/pricing/page.tsx
const variant = useABTest('pricing-display');
const defaultPeriod = variant === 'A' ? 'monthly' : 'annual';
```

**Track conversion:**

```tsx
// When user selects a plan
trackABConversion('pricing-display');
```

---

### 3. Trial Length

**Test ID:** `trial-length`
**Goal:** Optimize trial conversion rate

**Variants:**

- A (Control): 14-day trial
- B (Treatment): 30-day trial

**Where to use:**

```tsx
// apps/web/src/app/register/page.tsx
const variant = useABTest('trial-length');
const trialDays = variant === 'A' ? 14 : 30;
```

**Track conversion:**

```tsx
// When trial converts to paid
trackABConversion('trial-length');
```

---

## API Reference

### `useABTest(testId: string): VariantId`

React hook that returns the assigned variant ('A' or 'B') for a test.

```tsx
const variant = useABTest('homepage-cta');
```

- **SSR-safe**: Returns 'A' during server render
- **Persistent**: Same user gets same variant across sessions
- **Auto-tracked**: Variant assignment tracked in GA4

---

### `getVariant(testId: string): VariantId`

Non-hook version for use outside React components.

```typescript
const variant = getVariant('homepage-cta');
```

---

### `trackABConversion(testId: string, value?: number)`

Track when a user completes the goal action for a test.

```typescript
// Simple conversion
trackABConversion('homepage-cta');

// Conversion with value (e.g., purchase amount)
trackABConversion('pricing-display', 99.0);
```

---

### `getActiveTests(): Array<{...}>`

Get all currently active tests and their assignments.

```typescript
const activeTests = getActiveTests();
// [{ id: 'homepage-cta', name: 'Homepage CTA Copy', variant: 'B', variantName: 'See Agents in Action' }]
```

---

### `resetABTests()`

Clear all A/B test assignments (useful for testing).

```typescript
resetABTests();
```

---

## Example Implementation: Homepage CTA

### Step 1: Update Homepage

```tsx
// apps/web/src/app/page.tsx
'use client';

import { useABTest } from '@/lib/ab-testing';

export default function HomePage() {
  const ctaVariant = useABTest('homepage-cta');

  const ctaConfig = {
    A: {
      text: 'Start Free Trial',
      subtext: 'No credit card required',
    },
    B: {
      text: 'See Agents in Action',
      subtext: 'Watch live demo',
    },
  };

  const config = ctaConfig[ctaVariant];

  return (
    <div>
      <h1>Welcome to SwarmSync</h1>
      <button>{config.text}</button>
      <p>{config.subtext}</p>
    </div>
  );
}
```

### Step 2: Track Conversions

```tsx
// apps/web/src/components/auth/email-register-form.tsx
import { trackABConversion } from '@/lib/ab-testing';

const onSubmit = async (data) => {
  // ... registration logic ...

  // Track conversion for all active tests
  trackABConversion('homepage-cta');
  trackABConversion('pricing-display');
  trackABConversion('trial-length');
};
```

### Step 3: Enable Test

```typescript
// apps/web/src/lib/ab-testing.ts
export const AB_TESTS: Record<string, ABTest> = {
  'homepage-cta': {
    // ...
    enabled: true, // Activate test
  },
};
```

---

## Analyzing Results

### Google Analytics 4

1. Go to **Reports** → **Events**
2. Find events:
   - `ab_test_assigned` - Variant assignments
   - `ab_test_conversion` - Conversions

3. Create custom report:
   - **Dimension:** `test_id`, `variant`
   - **Metrics:** `event_count` (for assignments), `ab_test_conversion` count

### Sample Queries

**Assignment Distribution:**

```
Event: ab_test_assigned
Group by: test_id, variant
Metric: event_count
```

**Conversion Rate:**

```
Conversions / Assignments = Conversion Rate

Variant A: 150 conversions / 1000 assignments = 15%
Variant B: 180 conversions / 1000 assignments = 18%
Winner: Variant B (+20% relative lift)
```

---

## Best Practices

### 1. One Variable at a Time

Test only ONE change per experiment. Don't test both CTA copy AND button color simultaneously.

### 2. Statistical Significance

Run tests until you reach:

- Minimum 100 conversions per variant
- 95% statistical confidence
- Use [this calculator](https://www.optimizely.com/sample-size-calculator/)

### 3. Test Duration

- Run for at least 1 full week (captures weekend vs. weekday behavior)
- Include at least 1000 users per variant
- Don't stop early even if you see a "winner"

### 4. Avoid Testing Fatigue

- Don't run too many tests simultaneously
- Limit to 2-3 active tests at once
- Give users consistent experience within a session

### 5. Document Everything

- Hypothesis: "Changing CTA to action-oriented will increase clicks by 15%"
- Expected outcome: +15% CTR
- Actual outcome: +12% CTR (close enough to validate)

---

## Troubleshooting

### Variant assignments not persisting

**Issue:** Users getting different variants on each visit
**Fix:** Check browser localStorage support, ensure GA4 is loaded

### SSR hydration mismatch

**Issue:** React hydration error with A/B tests
**Fix:** Use `'use client'` directive and `useEffect` for client-only logic

### No data in Google Analytics

**Issue:** Events not showing up in GA4
**Fix:**

1. Verify `NEXT_PUBLIC_GA_MEASUREMENT_ID` is set
2. Check browser console for errors
3. Use GA4 DebugView for real-time testing

---

## Roadmap

### Phase 1 (Current)

- ✅ Variant assignment
- ✅ Conversion tracking
- ✅ GA4 integration
- ✅ Pre-configured tests

### Phase 2 (Future)

- ⏳ Multi-variate testing (A/B/C/D)
- ⏳ Audience targeting (by device, location, etc.)
- ⏳ Auto-winner selection
- ⏳ Visual editor for non-technical users

---

## Support

For questions or issues:

- Check [GA4 Documentation](https://support.google.com/analytics/answer/9267735)
- Review code in `apps/web/src/lib/ab-testing.ts`
- Test in browser console: `localStorage.getItem('ab_test_homepage-cta')`

---

**Status:** Infrastructure complete. Tests configured and ready to activate.
