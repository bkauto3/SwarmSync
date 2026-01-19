'use client';

import {
  AgentBudgetSettings,
  UpdateAgentBudgetPayload,
} from '@agent-market/sdk';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
});

interface BudgetControlsCardProps {
  agentId: string;
}

export function BudgetControlsCard({ agentId }: BudgetControlsCardProps) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['agent-budget', agentId],
    queryFn: async () => api.get(`agents/${agentId}/budget`).json<AgentBudgetSettings>(),
    enabled: Boolean(agentId),
  });

  const mutation = useMutation({
    mutationFn: (payload: UpdateAgentBudgetPayload) =>
      api.patch(`agents/${agentId}/budget`, { json: payload }).json<AgentBudgetSettings>(),
    onSuccess: (updated) => {
      queryClient.setQueryData(['agent-budget', agentId], updated);
    },
  });

  const resetCopy = useMemo(() => {
    if (!data?.resetsOn) {
      return 'Resets monthly';
    }
    const date = new Date(data.resetsOn);
    return `Resets ${date.toLocaleDateString()}`;
  }, [data?.resetsOn]);

  const handleBlur = (field: keyof UpdateAgentBudgetPayload, rawValue: string) => {
    if (!data) {
      return;
    }

    if (rawValue.trim() === '') {
      if (field === 'perTransactionLimit' || field === 'approvalThreshold') {
        mutation.mutate({ [field]: null });
      }
      return;
    }

    const numericValue = Number(rawValue);
    if (Number.isNaN(numericValue)) {
      return;
    }

    mutation.mutate({ [field]: numericValue });
  };

  const toggleAutoReload = () => {
    if (!data) {
      return;
    }
    mutation.mutate({ autoReload: !data.autoReload });
  };

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-base font-semibold text-[var(--text-primary)] font-display">Budget controls</CardTitle>
        <p className="text-sm text-[var(--text-secondary)] font-ui">
          Guard rails for this agent&apos;s wallet-auto top ups, per-deal caps, and approval thresholds.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading || !data ? (
          <div className="space-y-3">
            <Skeleton className="h-10 w-full rounded-lg" />
            <Skeleton className="h-10 w-full rounded-lg" />
            <Skeleton className="h-10 w-full rounded-lg" />
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <Label htmlFor="monthly-limit">Monthly budget limit</Label>
              <Input
                id="monthly-limit"
                key={`monthly-${data.updatedAt}`}
                type="number"
                min={0}
                step="100"
                defaultValue={data.monthlyLimit}
                onBlur={(event) => handleBlur('monthlyLimit', event.target.value)}
              />
              <p className="text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
                {currencyFormatter.format(data.spentThisPeriod)} spent · {resetCopy}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="per-transaction">Per-transaction cap</Label>
              <Input
                id="per-transaction"
                key={`per-tx-${data.updatedAt}-${data.perTransactionLimit ?? 'none'}`}
                type="number"
                min={0}
                step="50"
                placeholder="No cap"
                defaultValue={data.perTransactionLimit ?? ''}
                onBlur={(event) => handleBlur('perTransactionLimit', event.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="approval-threshold">Approval threshold</Label>
              <Input
                id="approval-threshold"
                key={`threshold-${data.updatedAt}-${data.approvalThreshold ?? 'none'}`}
                type="number"
                min={0}
                step="50"
                placeholder="Auto-approve all"
                defaultValue={data.approvalThreshold ?? ''}
                onBlur={(event) => handleBlur('approvalThreshold', event.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Approval mode</Label>
              <Select
                value={data.approvalMode}
                onValueChange={(value) => mutation.mutate({ approvalMode: value as 'AUTO' | 'MANUAL' | 'ESCROW' })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="AUTO">Auto approve (wallet guardrails)</SelectItem>
                  <SelectItem value="ESCROW">Escrow-gated</SelectItem>
                  <SelectItem value="MANUAL">Manual approvals required</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-[var(--border-base)]/50 bg-[var(--surface-raised)]/40 px-4 py-3">
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)] font-ui">Auto reload credits</p>
                <p className="text-xs text-[var(--text-muted)] font-ui">
                  Keeps the monthly budget replenished when it drops under 20%.
                </p>
              </div>
              <Button
                type="button"
                variant={data.autoReload ? 'secondary' : 'outline'}
                onClick={toggleAutoReload}
                disabled={mutation.isPending}
              >
                {data.autoReload ? 'On' : 'Off'}
              </Button>
            </div>

            {mutation.isPending ? (
              <p className="text-xs text-[var(--text-muted)]">Saving updates…</p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

