'use client';

import { Agent, AgentMarketClient, AgentPayload, createAgentMarketClient } from '@agent-market/sdk';
import { useRouter } from 'next/navigation';
import { useMemo, useState, useTransition } from 'react';

const clientCache: { instance?: AgentMarketClient } = {};

const getClient = () => {
  if (clientCache.instance) {
    return clientCache.instance;
  }

  clientCache.instance = createAgentMarketClient({
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4000',
  });
  return clientCache.instance;
};

interface AgentCreateFormProps {
  onCreated?: (agent: Agent) => void;
}

export const AgentCreateForm = ({ onCreated }: AgentCreateFormProps) => {
  const router = useRouter();
  const defaultCreatorId = useMemo(() => crypto.randomUUID(), []);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [categories, setCategories] = useState('research,automation');
  const [pricingModel, setPricingModel] = useState('outcome-based');
  const [creatorId, setCreatorId] = useState(defaultCreatorId);
  const [tags, setTags] = useState('beta, curated');
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setStatus(null);

    const payload: AgentPayload = {
      name,
      description,
      pricingModel,
      creatorId,
      categories: categories
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      tags: tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    };

    startTransition(async () => {
      try {
        const agent = await getClient().createAgent(payload);
        setStatus(`Agent ${agent.name} created and saved as draft.`);
        onCreated?.(agent);
        setName('');
        setDescription('');
        setTags('beta, curated');
        router.refresh();
      } catch (err) {
        console.error(err);
        setError('Failed to create agent. Check API connectivity.');
      }
    });
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-4 p-6 text-sm text-[var(--text-muted)]">
      <h3 className="text-lg font-display text-white">Create a curated agent</h3>
      <p>
        Draft agents start in <span className="font-mono text-slate-300">DRAFT</span> status. Submit them
        for review once you are ready.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-2">
          Agent name
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-white placeholder:text-[var(--text-muted)] focus:border-white/40 focus:outline-none"
            placeholder="Intelligence Research Agent"
            required
          />
        </label>
        <label className="flex flex-col gap-2">
          Pricing model
          <input
            value={pricingModel}
            onChange={(event) => setPricingModel(event.target.value)}
            className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-white placeholder:text-[var(--text-muted)] focus:border-white/40 focus:outline-none"
            placeholder="Outcome-based per insight"
            required
          />
        </label>
      </div>
      <label className="flex flex-col gap-2">
        Description
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-white placeholder:text-[var(--text-muted)] focus:border-white/40 focus:outline-none"
          placeholder="Summarises competitive intelligence and prepares deal briefs."
          rows={3}
          required
        />
      </label>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-2">
          Categories (comma separated)
          <input
            value={categories}
            onChange={(event) => setCategories(event.target.value)}
            className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-white placeholder:text-[var(--text-muted)] focus:border-white/40 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-2">
          Tags (comma separated)
          <input
            value={tags}
            onChange={(event) => setTags(event.target.value)}
            className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-white placeholder:text-[var(--text-muted)] focus:border-white/40 focus:outline-none"
          />
        </label>
      </div>
      <label className="flex flex-col gap-2">
        Creator ID (demo)
        <input
          value={creatorId}
          onChange={(event) => setCreatorId(event.target.value)}
          className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 font-mono text-xs text-white placeholder:text-[var(--text-muted)] focus:border-white/40 focus:outline-none"
          required
        />
        <span className="text-xs text-[var(--text-muted)]">
          For now, we generate a temporary UUID. Replace with a real user ID when auth wiring is
          ready.
        </span>
      </label>
      {error && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}
      {status && (
        <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
          {status}
        </div>
      )}
      <button
        type="submit"
        disabled={isPending}
        className="glass-button bg-accent px-5 py-2 text-carrara shadow-accent-glow hover:bg-accent-dark disabled:cursor-not-allowed disabled:bg-white/10"
      >
        {isPending ? 'Creating...' : 'Create Agent'}
      </button>
    </form>
  );
};
