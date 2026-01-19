'use client';

import { Ap2NegotiationRecord } from '@agent-market/sdk';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { RefreshCw } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Ap2NegotiationsProps {
  agentId: string;
}

const statusStyles: Record<string, string> = {
  PENDING: 'bg-amber-500/15 text-amber-200',
  COUNTERED: 'bg-sky-500/15 text-sky-200',
  ACCEPTED: 'bg-emerald-500/15 text-emerald-200',
  DECLINED: 'bg-rose-500/15 text-rose-200',
};

const verificationStyles: Record<string, string> = {
  VERIFIED: 'text-emerald-300',
  PENDING: 'text-amber-200',
  REJECTED: 'text-rose-200',
  DISPUTED: 'text-rose-200',
};

export function Ap2Negotiations({ agentId }: Ap2NegotiationsProps) {
  const query = useQuery({
    queryKey: ['ap2-negotiations', agentId],
    queryFn: () =>
      api
        .get('ap2/negotiations/my', {
          searchParams: { agentId },
        })
        .json<Ap2NegotiationRecord[]>(),
    enabled: Boolean(agentId),
    refetchInterval: 5000,
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <div>
          <CardTitle className="text-base font-semibold text-[var(--text-primary)] font-display">AP2 negotiations</CardTitle>
          <p className="text-sm text-[var(--text-secondary)] font-ui">Live status of autonomous procurements.</p>
        </div>
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="h-9 w-9 text-[var(--text-muted)]"
          onClick={() => query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw className={cn('h-4 w-4', query.isFetching && 'animate-spin')} />
          <span className="sr-only">Refresh negotiations</span>
        </Button>
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full rounded-2xl" />
            <Skeleton className="h-16 w-full rounded-2xl" />
            <Skeleton className="h-16 w-full rounded-2xl" />
          </div>
        ) : query.data && query.data.length > 0 ? (
          <div className="space-y-3">
            {query.data.slice(0, 6).map((negotiation) => (
              <article
                key={negotiation.id}
                className="rounded-2xl border border-[var(--border-base)]/50 bg-[var(--surface-raised)]/40 px-4 py-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text-primary)] font-ui">
                      {negotiation.requesterAgent?.name ?? 'Unknown'}{' '}
                      <span className="text-[var(--text-muted)]">&rarr;</span>{' '}
                      {negotiation.responderAgent?.name ?? 'Unknown'}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
                      {negotiation.requestedService ?? 'Custom engagement'} &middot;{' '}
                      {formatDistanceToNow(new Date(negotiation.updatedAt), { addSuffix: true })}
                    </p>
                  </div>
                  <Badge
                    className={cn(
                      'border-transparent bg-white/10 text-[var(--text-primary)]',
                      statusStyles[negotiation.status],
                    )}
                  >
                    {negotiation.status.toLowerCase()}
                  </Badge>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
                  {negotiation.proposedBudget ? (
                    <span>
                      Budget: <strong className="font-mono text-meta-numeric">${negotiation.proposedBudget.toFixed(2)}</strong>
                    </span>
                  ) : null}
                  {negotiation.counter?.price ? (
                    <span>
                      Counter: <strong className="font-mono text-meta-numeric">${Number(negotiation.counter.price).toFixed(2)}</strong>
                    </span>
                  ) : null}
                  {negotiation.transaction?.status ? (
                    <span>
                      Escrow: {negotiation.transaction.status.toLowerCase()}
                    </span>
                  ) : null}
                </div>
                {negotiation.verificationStatus ? (
                  <div className="mt-2 text-xs text-[var(--text-muted)]">
                    Outcome:{' '}
                    <span
                      className={cn(
                        'font-semibold uppercase',
                        verificationStyles[negotiation.verificationStatus] ?? 'text-[var(--text-muted)]',
                      )}
                    >
                      {negotiation.verificationStatus.toLowerCase()}
                    </span>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)] font-ui">
            No negotiations yet. Launch a service request to populate this feed.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

