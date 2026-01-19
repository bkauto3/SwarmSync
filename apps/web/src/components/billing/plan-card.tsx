'use client';

import { BillingPlan, BillingSubscription } from '@agent-market/sdk';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { useAuth } from '@/hooks/use-auth';
import { billingApi } from '@/lib/api';

interface PlanCardProps {
  plan: BillingPlan;
  subscription: BillingSubscription | null;
}

const formatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
});

export function PlanCard({ plan, subscription }: PlanCardProps) {
  const isActive = subscription?.plan?.slug === plan.slug;
  const { isAuthenticated } = useAuth();
  const [errorMessage, setErrorMessage] = useState('');
  const priceLabel =
    plan.priceCents === 0
      ? plan.slug === 'enterprise'
        ? 'Custom'
        : 'Free'
      : `${formatter.format(plan.priceCents / 100)}/mo`;

  const mutation = useMutation({
    mutationFn: async () => {
      const successUrl = `${window.location.origin}/billing?status=success`;
      const cancelUrl = `${window.location.origin}/billing?status=cancel`;

      if (plan.priceCents === 0) {
        await billingApi.changePlan(plan.slug);
        return { checkoutUrl: null };
      }

      return billingApi.createCheckoutSession(plan.slug, successUrl, cancelUrl);
    },
    onSuccess: (result) => {
      if (!result.checkoutUrl) {
        window.location.reload();
      } else {
        window.location.href = result.checkoutUrl;
      }
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'Unable to change plan. Please try again.';
      setErrorMessage(message);
    },
  });

  const handleSelectPlan = () => {
    if (isActive || mutation.isPending) {
      return;
    }

    if (!isAuthenticated) {
      window.location.href = '/login';
      return;
    }

    setErrorMessage('');
    mutation.mutate();
  };

  return (
    <div
      className={`card flex flex-col gap-4 p-6 ${
        isActive ? 'border border-accent' : 'border border-[var(--border-base)]'
      }`}
    >
      <div>
        <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">{plan.slug}</p>
        <h3 className="text-2xl font-semibold text-white">{plan.name}</h3>
      </div>

      <div className="text-3xl font-display text-white">{priceLabel}</div>

      <ul className="space-y-2 text-sm text-[var(--text-muted)]">
        <li>Seats: {plan.seats === 0 ? 'Unlimited' : plan.seats}</li>
        <li>Agents: {plan.agentLimit === 0 ? 'Unlimited' : plan.agentLimit}</li>
        <li>Workflows: {plan.workflowLimit === 0 ? 'Unlimited' : plan.workflowLimit}</li>
        <li>
          Credits / month:{' '}
          {plan.monthlyCredits === 0 ? 'Custom' : plan.monthlyCredits.toLocaleString()}
        </li>
        <li>Platform fee: {(plan.takeRateBasisPoints / 100).toFixed(1)}%</li>
      </ul>

      <div className="space-y-2 text-sm text-[var(--text-muted)]">
        {(plan.features || []).map((feature) => (
          <div key={feature} className="flex items-center gap-2">
            <span className="text-accent">✺</span>
            <span>{feature}</span>
          </div>
        ))}
      </div>

      {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

      <button
        type="button"
        disabled={isActive || mutation.isPending}
        onClick={handleSelectPlan}
        className={`glass-button mt-auto w-full px-4 py-2 text-sm font-semibold ${
          isActive ? 'bg-white/10/60 text-white cursor-not-allowed' : 'bg-accent text-carrara'
        }`}
      >
        {isActive
          ? 'Current plan'
          : mutation.isPending
            ? 'Processing…'
            : plan.slug === 'enterprise'
              ? 'Contact us'
              : 'Choose plan'}
      </button>
    </div>
  );
}
