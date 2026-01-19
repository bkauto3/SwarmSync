'use client';

import { EvaluationResultRecord, createAgentMarketClient } from '@agent-market/sdk';
import { useRouter } from 'next/navigation';
import { useMemo, useState, useTransition } from 'react';

interface EvaluationConsoleProps {
  agentId: string;
  evaluations: EvaluationResultRecord[];
}

export function EvaluationConsole({ agentId, evaluations }: EvaluationConsoleProps) {
  const router = useRouter();
  const [scenarioName, setScenarioName] = useState('Workflow smoke test');
  const [vertical, setVertical] = useState('orchestration');
  const [passed, setPassed] = useState(true);
  const [latencyMs, setLatencyMs] = useState(1200);
  const [cost, setCost] = useState(0);
  const [notes, setNotes] = useState('');
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const latestEvaluations = useMemo(() => evaluations.slice(0, 4), [evaluations]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    startTransition(async () => {
      try {
        setError(null);
        await createAgentMarketClient().runEvaluation({
          agentId,
          scenarioName,
          vertical,
          passed,
          latencyMs,
          cost,
          logs: notes ? { notes } : undefined,
        });
        setNotes('');
        router.refresh();
      } catch (err) {
        console.error(err);
        setError('Failed to record evaluation result.');
      }
    });
  };

  return (
    <div className="surface-card space-y-6 p-6">
      <div>
        <h2 className="text-lg font-display text-white">Evaluation Runner</h2>
        <p className="text-sm text-[var(--text-muted)]">
          Log manual or automated evaluation outcomes. GitHub Actions can push to the same endpoint
          for fully automated pipelines.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3 surface-card border p-4">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
            Scenario name
            <input
                className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              value={scenarioName}
              onChange={(event) => setScenarioName(event.target.value)}
            />
          </label>
          <label className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
            Vertical
            <input
              className="mt-1 w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
              value={vertical}
              onChange={(event) => setVertical(event.target.value)}
            />
          </label>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <label className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
            Outcome
            <select
              className="mt-1 w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
              value={passed ? 'passed' : 'failed'}
              onChange={(event) => setPassed(event.target.value === 'passed')}
            >
              <option value="passed">Passed</option>
              <option value="failed">Failed</option>
                </select>
              </label>
          <label className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
            Latency (ms)
            <input
              type="number"
              min={0}
              className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              value={latencyMs}
              onChange={(event) => setLatencyMs(Number(event.target.value))}
            />
          </label>
          <label className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
            Cost ($)
            <input
              type="number"
              min={0}
              step="0.01"
              className="mt-1 w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
              value={cost}
              onChange={(event) => setCost(Number(event.target.value))}
            />
          </label>
        </div>

        <textarea
          placeholder="Logs / notes"
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text focus:border-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          rows={3}
        />

        <button
          type="submit"
          disabled={isPending}
          className="glass-button bg-accent px-4 py-2 text-xs font-semibold text-carrara disabled:cursor-not-allowed disabled:bg-white/10"
        >
          {isPending ? 'Publishing...' : 'Record evaluation'}
        </button>
      </form>

      <div className="rounded-lg border border-[var(--border-base)] p-4">
        <h3 className="text-sm font-semibold text-white">Recent evaluations</h3>
        <ul className="mt-3 space-y-2 text-sm text-[var(--text-muted)]">
          {latestEvaluations.length === 0 && (
            <li className="text-xs text-[var(--text-muted)]">No evaluations captured yet.</li>
          )}
          {latestEvaluations.map((evaluation) => (
            <li key={evaluation.id} className="rounded-lg bg-[var(--surface-raised)] p-3">
              <div className="flex justify-between text-xs">
                <span
                  className={
                    evaluation.status === 'PASSED' ? 'text-emerald-400 font-semibold' : 'text-red-400'
                  }
                >
                  {evaluation.status}
                </span>
                <span>{new Date(evaluation.createdAt).toLocaleString()}</span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Scenario: {evaluation.scenario.name} ({evaluation.scenario.vertical ?? 'general'})
              </p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
