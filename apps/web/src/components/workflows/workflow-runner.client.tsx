'use client';

import { createAgentMarketClient } from '@agent-market/sdk';
import { useState, useTransition } from 'react';

const clientCache: { instance?: ReturnType<typeof createAgentMarketClient> } = {};

const getClient = () => {
  if (!clientCache.instance) {
    clientCache.instance = createAgentMarketClient({
      baseUrl: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4000',
    });
  }
  return clientCache.instance;
};

interface RunWorkflowButtonProps {
  workflowId: string;
}

export const RunWorkflowButton = ({ workflowId }: RunWorkflowButtonProps) => {
  const [initiatorId, setInitiatorId] = useState('00000000-0000-0000-0000-000000000000');
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const handleRun = () => {
    setError(null);
    setMessage(null);

    startTransition(async () => {
      try {
        const run = await getClient().runWorkflow(workflowId, initiatorId);
        setMessage(`Workflow run ${run.id} started with status ${run.status}.`);
      } catch (err) {
        console.error(err);
        setError('Failed to run workflow. Ensure the initiator has sufficient budget.');
      }
    });
  };

  return (
    <div className="space-y-3 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4">
      <label className="flex flex-col gap-2 text-xs uppercase tracking-wider text-[var(--text-muted)]">
        Initiator User ID
        <input
          value={initiatorId}
          onChange={(event) => setInitiatorId(event.target.value)}
          className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-xs font-mono text-white focus:border-white/40 focus:outline-none"
        />
      </label>

      {error && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
          {message}
        </div>
      )}

      <button
        type="button"
        onClick={handleRun}
        disabled={isPending}
        className="glass-button bg-accent px-4 py-2 text-xs font-semibold text-carrara shadow-accent-glow hover:bg-accent-dark disabled:cursor-not-allowed disabled:bg-white/10"
      >
        {isPending ? 'Running...' : 'Run Workflow'}
      </button>
    </div>
  );
};
