import { AgentCard } from '@/components/agents/agent-card';
import { Skeleton } from '@/components/ui/skeleton';

import type { Agent } from '@agent-market/sdk';

interface AgentGridProps {
  agents?: Agent[];
  isLoading: boolean;
  isError?: boolean;
}

export function AgentGrid({ agents = [], isLoading, isError }: AgentGridProps) {
  if (isLoading) {
    return (
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-64 rounded-[2.5rem]" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-[2.5rem] border border-destructive/20 bg-destructive/5 p-12 text-center">
        <p className="font-semibold text-destructive">Failed to load agents</p>
        <p className="mt-2 text-sm text-destructive/80">
          Please check your connection and try again.
        </p>
        <p className="mt-4 text-xs text-destructive/60">
          If the problem persists, check the browser console for details or contact support.
        </p>
      </div>
    );
  }

  if (!agents.length) {
    return (
      <div className="rounded-[2.5rem] border border-dashed border-border bg-[var(--surface-raised)] p-12 text-center">
        <p className="text-muted-foreground">No agents matched your filters.</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Try broadening your search or{' '}
          <a href="/agents/new" className="text-primary underline hover:no-underline">
            create a new agent
          </a>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}
