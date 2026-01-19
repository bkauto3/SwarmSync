'use client';

import { Agent } from '@agent-market/sdk';
import { useMemo } from 'react';

interface AgentListProps {
  agents: Agent[];
}

const statusStyles: Record<string, string> = {
  DRAFT: 'bg-[var(--surface-raised)]/80 text-[var(--text-muted)]',
  PENDING: 'bg-amber-500/20 text-amber-200',
  APPROVED: 'bg-emerald-500/20 text-emerald-200',
  REJECTED: 'bg-red-500/25 text-red-200',
  DISABLED: 'bg-[var(--surface-raised)] text-[var(--text-muted)]',
};

export const AgentList = ({ agents }: AgentListProps) => {
  const sortedAgents = useMemo(
    () =>
      [...agents].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()),
    [agents],
  );

  if (sortedAgents.length === 0) {
    return (
      <div className="card p-6 text-center text-[var(--text-muted)]">
        No agents yet. Draft your first agent to seed the marketplace.
      </div>
    );
  }

  return (
    <div className="surface-card overflow-hidden">
      <table className="min-w-full divide-y divide-outline/60">
        <thead>
          <tr className="bg-[var(--surface-raised)] text-left text-xs uppercase tracking-wider text-[var(--text-muted)]">
            <th className="px-4 py-3">Agent</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Trust</th>
            <th className="px-4 py-3">Pricing</th>
            <th className="px-4 py-3">Categories</th>
            <th className="px-4 py-3">Updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline/40 text-sm text-[var(--text-muted)]">
          {sortedAgents.map((agent) => (
            <tr key={agent.id} className="transition hover:bg-[var(--surface-raised)]/50">
              <td className="px-4 py-4">
                <div className="space-y-1">
                  <div className="font-semibold text-white">{agent.name}</div>
                  <p className="line-clamp-2 text-xs text-[var(--text-muted)]">{agent.description}</p>
                </div>
              </td>
              <td className="px-4 py-4">
                <span
                  className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusStyles[agent.status] ?? 'bg-[var(--surface-raised)]/80 text-[var(--text-muted)]'}`}
                >
                  {agent.status}
                </span>
              </td>
              <td className="px-4 py-4">
                <div className="flex flex-col gap-1 text-xs">
                  <span className="font-semibold text-emerald-500">Score {agent.trustScore}</span>
                  <span className="text-[var(--text-muted)]/80">{agent.verificationStatus.toLowerCase()}</span>
                </div>
              </td>
              <td className="px-4 py-4 text-white">{agent.pricingModel}</td>
              <td className="px-4 py-4">
                <div className="flex flex-wrap gap-2">
                  {agent.categories.map((category) => (
                    <span
                      key={category}
                      className="rounded-full bg-[var(--surface-raised)]/80 px-3 py-1 text-xs text-[var(--text-muted)]"
                    >
                      {category}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-4 py-4 text-xs text-[var(--text-muted)]/80">
                {new Date(agent.updatedAt).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
