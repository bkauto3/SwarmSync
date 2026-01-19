import { BillingSubscription } from '@agent-market/sdk';

interface CreditSummaryCardProps {
  subscription: BillingSubscription | null;
}

export function CreditSummaryCard({ subscription }: CreditSummaryCardProps) {
  if (!subscription) {
    return (
      <div className="card p-6 text-sm text-[var(--text-muted)] font-ui">
        No plan assigned yet. Visit the <span className="text-[var(--text-primary)]">Billing</span> tab to activate a
        plan.
      </div>
    );
  }

  const remaining = Math.max(subscription.creditAllowance - subscription.creditUsed, 0);
  const remainingPercent = Math.min(
    Math.round((remaining / subscription.creditAllowance) * 100),
    100,
  );

  return (
    <div className="card space-y-4 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] font-ui">Plan</p>
          <h3 className="text-xl font-semibold text-[var(--text-primary)] font-display">{subscription.plan.name}</h3>
        </div>
        <div className="text-right text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
          Period ends {new Date(subscription.currentPeriodEnd).toLocaleDateString()}
        </div>
      </div>

      <div>
        <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] font-ui">Credits remaining</p>
        <div className="mt-2 text-3xl font-semibold text-[var(--text-primary)] font-display text-meta-numeric">
          {remaining.toLocaleString()}{' '}
          <span className="text-base text-[var(--text-muted)] font-ui text-meta-numeric">
            / {subscription.creditAllowance.toLocaleString()}
          </span>
        </div>
      </div>

      <div className="rounded-full bg-[var(--surface-raised)]">
        <div
          className="rounded-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc] px-2 py-1 text-xs font-semibold text-black"
          style={{ width: `${remainingPercent}%` }}
        >
          {remainingPercent}% left
        </div>
      </div>

      <p className="text-xs text-[var(--text-muted)] font-ui">
        Need more runway?{' '}
        <a href="/billing" className="text-[var(--text-secondary)] underline hover:text-[var(--text-primary)]">
          Upgrade your plan
        </a>
        .
      </p>
    </div>
  );
}
