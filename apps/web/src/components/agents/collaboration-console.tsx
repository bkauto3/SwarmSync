'use client';

import { Agent, createAgentMarketClient } from '@agent-market/sdk';
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

interface CollaborationConsoleProps {
  agents: Agent[];
}

export const CollaborationConsole = ({ agents }: CollaborationConsoleProps) => {
  const [requesterId, setRequesterId] = useState(agents[0]?.id ?? '');
  const [responderId, setResponderId] = useState(agents[1]?.id ?? agents[0]?.id ?? '');
  const [payload, setPayload] = useState('{"proposal":"Share research insights"}');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const handleSubmit = () => {
    if (!requesterId || !responderId || requesterId === responderId) {
      setErrorMessage('Choose two different agents to initiate collaboration.');
      return;
    }

    let parsed: Record<string, unknown> | undefined;
    try {
      parsed = payload ? JSON.parse(payload) : undefined;
    } catch (error) {
      setErrorMessage('Payload must be valid JSON.');
      return;
    }

    setErrorMessage(null);
    setStatusMessage(null);

    startTransition(async () => {
      try {
        const result = await getClient().createCollaborationRequest({
          requesterAgentId: requesterId,
          responderAgentId: responderId,
          payload: parsed,
        });
        setStatusMessage(`Collaboration request ${result.id} created.`);
      } catch (error) {
        console.error(error);
        setErrorMessage('Failed to send collaboration request.');
      }
    });
  };

  if (agents.length < 2) {
    return (
      <div className="card p-6 text-sm text-[var(--text-muted)]">
        Add at least two agents to experiment with collaboration requests.
      </div>
    );
  }

  return (
    <div className="card space-y-4 p-6 text-xs uppercase tracking-wide text-[var(--text-muted)]">
      <div>
        <h2 className="text-lg font-display text-white">Agent Collaboration Console</h2>
        <p className="text-xs normal-case text-[var(--text-muted)]/90">
          Use AP2 messaging to propose joint work between two agents. Requests are logged via the
          new collaboration endpoints.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-2">
          Requesting Agent
          <select
            value={requesterId}
            onChange={(event) => setRequesterId(event.target.value)}
            className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
          >
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-2">
          Responder Agent
          <select
            value={responderId}
            onChange={(event) => setResponderId(event.target.value)}
            className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
          >
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="flex flex-col gap-2">
        Proposal Payload (JSON)
        <textarea
          value={payload}
          onChange={(event) => setPayload(event.target.value)}
          rows={3}
          className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
        />
      </label>

      {errorMessage && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {errorMessage}
        </div>
      )}
      {statusMessage && (
        <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
          {statusMessage}
        </div>
      )}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={isPending}
        className="glass-button bg-accent px-4 py-2 text-carrara shadow-accent-glow hover:bg-accent-dark disabled:cursor-not-allowed disabled:bg-white/10"
      >
        {isPending ? 'Sending...' : 'Send Collaboration Request'}
      </button>
    </div>
  );
};
