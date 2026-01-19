'use client';

import { AgentQualityAnalytics } from '@agent-market/sdk';
import { useQuery } from '@tanstack/react-query';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

interface A2ARoiSummaryProps {
  agentId: string;
}

export function A2ARoiSummary({ agentId }: A2ARoiSummaryProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['agent-analytics', agentId],
    queryFn: async () =>
      api.get(`quality/analytics/agents/${agentId}`).json<AgentQualityAnalytics>(),
    enabled: Boolean(agentId),
    refetchInterval: 30_000,
  });

  const a2aSpend = data ? Number(data.a2a.totalSpend) : null;
  const engagements = data?.a2a.engagements ?? 0;
  const roi = data?.roi ?? null;

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-base font-semibold text-[var(--text-primary)] font-display">A2A ROI snapshot</CardTitle>
        <p className="text-sm text-[var(--text-secondary)] font-ui">
          Rolling analytics from the quality service-verified outcomes, spend, and trust.
        </p>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-14 w-full rounded-2xl" />
            <Skeleton className="h-14 w-full rounded-2xl" />
            <Skeleton className="h-14 w-full rounded-2xl" />
          </div>
        ) : data ? (
          <dl className="space-y-4">
            <div className="rounded-2xl border border-[var(--border-base)]/50 bg-[var(--surface-raised)]/40 px-4 py-3">
              <dt className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)] font-ui">Total spend</dt>
              <dd className="text-2xl font-semibold text-[var(--text-primary)] font-display text-meta-numeric">
                {a2aSpend !== null ? currencyFormatter.format(a2aSpend) : '—'}
              </dd>
              <p className="text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
                Across {engagements} engagements · Avg cost per engagement{' '}
                {roi?.averageCostPerEngagement
                  ? currencyFormatter.format(Number(roi.averageCostPerEngagement))
                  : '—'}
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--border-base)]/50 bg-[var(--surface-raised)]/40 px-4 py-3">
              <dt className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)] font-ui">Verified outcomes</dt>
              <dd className="text-2xl font-semibold text-[var(--text-primary)] font-display text-meta-numeric">
                {roi?.verifiedOutcomeRate ? `${roi.verifiedOutcomeRate}%` : '—'}
              </dd>
              <p className="text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
                Avg cost per outcome{' '}
                {roi?.averageCostPerOutcome
                  ? currencyFormatter.format(Number(roi.averageCostPerOutcome))
                  : '—'}
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--border-base)]/50 bg-[var(--surface-raised)]/40 px-4 py-3">
              <dt className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)] font-ui">Agreements</dt>
              <dd className="text-lg font-semibold text-[var(--text-primary)] font-display text-meta-numeric">
                {data.agreements.active} active · {data.agreements.completed} completed
              </dd>
              <p className="text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
                {data.verifications.verified} verified / {data.verifications.pending} pending
              </p>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-[var(--text-muted)] font-ui">
            No analytics available yet. Run an evaluation or complete an escrow to populate ROI
            metrics.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

