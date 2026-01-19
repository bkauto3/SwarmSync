'use client';

import { Agent } from '@agent-market/sdk';
import { useEffect, useMemo, useState } from 'react';

import { A2ARoiSummary } from '@/components/dashboard/a2a-roi-summary';
import { A2ATransactionMonitor } from '@/components/dashboard/a2a-transaction-monitor';
import { AgentNetworkGraph } from '@/components/dashboard/agent-network-graph';
import { Ap2Negotiations } from '@/components/dashboard/ap2-negotiations';
import { BudgetControlsCard } from '@/components/dashboard/budget-controls-card';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface A2AOperationsPanelProps {
  agents: Agent[];
}

export function A2AOperationsPanel({ agents }: A2AOperationsPanelProps) {
  const initialAgentId = agents[0]?.id ?? '';
  const [selectedAgentId, setSelectedAgentId] = useState(initialAgentId);

  useEffect(() => {
    if (!agents.length) {
      return;
    }
    if (!agents.find((agent) => agent.id === selectedAgentId)) {
      setSelectedAgentId(agents[0].id);
    }
  }, [agents, selectedAgentId]);

  const focusAgent = useMemo(() => {
    if (!agents.length) {
      return null;
    }
    return agents.find((agent) => agent.id === selectedAgentId) ?? agents[0];
  }, [agents, selectedAgentId]);

  if (!focusAgent) {
    return null;
  }

  return (
    <section className="space-y-6">
      <Card className="card p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)] font-ui">Agent mesh</p>
            <h2 className="mt-1 text-2xl font-semibold text-[var(--text-primary)] font-display">Autonomous purchasing layer</h2>
            <p className="text-sm text-[var(--text-secondary)] font-ui">
              Track real-time deals, network topology, and enforced budgets for the selected agent.
            </p>
          </div>
          <div className="w-full max-w-xs">
            <Select value={focusAgent.id} onValueChange={setSelectedAgentId}>
              <SelectTrigger className="border-[var(--border-base)] bg-[var(--surface-raised)] text-left text-sm text-[var(--text-primary)] focus:border-[var(--border-hover)] focus:ring-2 focus:ring-[var(--shadow-focus)]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {agents.map((agent) => (
                  <SelectItem key={agent.id} value={agent.id}>
                    {agent.name} · {agent.status.toLowerCase()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[3fr,2fr]">
        <A2ATransactionMonitor agentId={focusAgent.id} />
        <BudgetControlsCard agentId={focusAgent.id} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[3fr,2fr]">
        <AgentNetworkGraph agentId={focusAgent.id} />
        <A2ARoiSummary agentId={focusAgent.id} />
      </div>

      <Ap2Negotiations agentId={focusAgent.id} />
    </section>
  );
}
