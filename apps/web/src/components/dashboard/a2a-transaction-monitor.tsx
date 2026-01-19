'use client';

import { AgentA2aTransactionRecord } from '@agent-market/sdk';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface A2ATransactionMonitorProps {
  agentId: string;
}

const statusVariant: Record<string, string> = {
  ACCEPTED: 'bg-emerald-500/15 text-emerald-300',
  COMPLETED: 'bg-emerald-500/15 text-emerald-300',
  PENDING: 'bg-amber-500/15 text-amber-200',
  COUNTERED: 'bg-sky-500/15 text-sky-200',
  DECLINED: 'bg-rose-500/15 text-rose-200',
};

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

export function A2ATransactionMonitor({ agentId }: A2ATransactionMonitorProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['a2a-transactions', agentId],
    queryFn: async () =>
      api.get(`agents/${agentId}/a2a-transactions`).json<AgentA2aTransactionRecord[]>(),
    enabled: Boolean(agentId),
    refetchInterval: 15_000,
  });

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-base font-semibold text-[var(--text-primary)] font-display">
          Agent-to-agent transactions
        </CardTitle>
        <p className="text-sm text-[var(--text-secondary)] font-ui">
          Autonomous purchases, escrows, and negotiations initiated by this agent.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full rounded-2xl" />
            <Skeleton className="h-16 w-full rounded-2xl" />
            <Skeleton className="h-16 w-full rounded-2xl" />
          </div>
        ) : data && data.length > 0 ? (
          data.slice(0, 5).map((transaction) => (
            <article
              key={transaction.id}
              className="rounded-2xl border border-[var(--border-base)]/50 bg-[var(--surface-raised)]/40 px-4 py-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-[var(--text-primary)] font-ui">
                    {transaction.requesterAgent?.name ?? 'Unknown'}{' '}
                    <span className="text-[var(--text-muted)]">&rarr;</span>{' '}
                    {transaction.responderAgent?.name ?? 'Unknown'}
                  </p>
                  <p className="text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
                    {transaction.requestedService ?? 'Custom engagement'} &middot;{' '}
                    {formatDistanceToNow(new Date(transaction.updatedAt), { addSuffix: true })}
                  </p>
                </div>
                <Badge
                  className={cn(
                    'border-transparent bg-white/10 text-[var(--text-primary)]',
                    statusVariant[transaction.status],
                  )}
                >
                  {transaction.status.toLowerCase()}
                </Badge>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-6 text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
                <span>
                  Bid:{' '}
                  <strong className="text-[var(--text-primary)] font-mono text-meta-numeric">
                    {transaction.amount
                      ? currencyFormatter.format(transaction.amount)
                      : transaction.proposedBudget
                        ? currencyFormatter.format(transaction.proposedBudget)
                        : '—'}
                  </strong>
                </span>
                <span>
                  Escrow:{' '}
                  {transaction.transaction?.status
                    ? transaction.transaction.status.toLowerCase()
                    : 'not funded'}
                </span>
                {transaction.transaction?.settledAt ? (
                  <span>
                    Settled{' '}
                    {formatDistanceToNow(new Date(transaction.transaction.settledAt), {
                      addSuffix: true,
                    })}
                  </span>
                ) : null}
              </div>
            </article>
          ))
        ) : (
          <p className="text-sm text-[var(--text-muted)] font-ui">
            No agent-to-agent activity yet. Once this agent starts transacting, live deals will
            appear here.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
