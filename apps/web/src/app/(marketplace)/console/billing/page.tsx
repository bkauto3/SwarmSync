import { BillingPlan, BillingSubscription } from '@agent-market/sdk';
import { cookies } from 'next/headers';

import { PlanCard } from '@/components/billing/plan-card';
import { TopUpCard } from '@/components/billing/top-up-card';
import { getAgentMarketClient } from '@/lib/server-client';

import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Billing',
  robots: {
    index: false,
    follow: false,
  },
};

export const dynamic = 'force-dynamic';

export default async function BillingPage() {
  const token = cookies().get('auth_token')?.value;
  const client = getAgentMarketClient(token);
  let plans: BillingPlan[] = [];
  let subscription: BillingSubscription | null = null;

  try {
    const [plansResult, subscriptionResult] = await Promise.allSettled([
      client.listBillingPlans(),
      client.getBillingSubscription(),
    ]);

    if (plansResult.status === 'fulfilled') {
      plans = plansResult.value ?? [];
    }

    if (subscriptionResult.status === 'fulfilled') {
      subscription = subscriptionResult.value || null;
    }
  } catch (error) {
    console.warn('Billing data unavailable during build', error);
  }

  if (!plans.length) {
    return (
      <div className="space-y-8">
        <header className="glass-card p-8">
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Billing</p>
          <h1 className="mt-2 text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Plans & Usage</h1>
        </header>
        <div className="glass-card border border-amber-500/30 bg-amber-500/10 p-8">
          <h2 className="text-lg font-semibold text-amber-300">No Billing Plans Available</h2>
          <p className="mt-2 text-sm text-amber-300">
            We&apos;re currently unable to load billing information. This may be temporary.
          </p>
          <p className="mt-4 text-sm text-[var(--text-muted)]">
            If this issue persists, please contact support or try again later.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="glass-card p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Billing</p>
        <h1 className="mt-2 text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Plans & Usage</h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--text-muted)]">
          Choose the plan that fits your agent marketplace. Upgrades unlock higher credit pools,
          lower platform fees, and additional support options.
        </p>
        {subscription && (
          <div className="mt-4 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-sm text-[var(--text-primary)]">
            Active plan: <span className="font-semibold text-slate-300">{subscription.plan.name}</span>{' '}
            — {subscription.creditUsed}/{subscription.creditAllowance} credits this period
          </div>
        )}
      </header>

      <section className="grid gap-6 lg:grid-cols-3">
        {plans.map((plan) => (
          <PlanCard
            key={plan.slug}
            plan={plan as BillingPlan}
            subscription={subscription as BillingSubscription | null}
          />
        ))}
      </section>

      <TopUpCard />
    </div>
  );
}
