import { Workflow } from '@agent-market/sdk';

import { getAgentMarketClient } from '@/lib/server-client';

import { RunWorkflowButton } from './workflow-runner.client';

interface WorkflowRunnerProps {
  workflow: Workflow;
}

export async function WorkflowRunner({ workflow }: WorkflowRunnerProps) {
  const client = getAgentMarketClient();
  const runs = await client.listWorkflowRuns(workflow.id);

  return (
    <div className="card space-y-4 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-display text-white">{workflow.name}</h3>
          <p className="text-sm text-[var(--text-muted)]">{workflow.description ?? 'No description'}</p>
        </div>
        <span className="rounded-full border border-[var(--border-base)] px-3 py-1 text-xs text-white">
          Budget {workflow.budget}
        </span>
      </div>

      <div className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4">
        <p className="text-xs uppercase tracking-wider text-[var(--text-muted)]">Steps</p>
        <pre className="mt-2 overflow-auto whitespace-pre-wrap font-mono text-xs text-[var(--text-muted)]">
          {JSON.stringify(workflow.steps, null, 2)}
        </pre>
      </div>

      <RunWorkflowButton workflowId={workflow.id} />

      <div>
        <h4 className="text-sm font-display text-white">Recent Runs</h4>
        {runs.length === 0 ? (
          <p className="text-xs text-[var(--text-muted)]">No runs yet.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {runs.slice(0, 5).map((run) => (
              <li
                key={run.id}
                className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-3 text-xs text-[var(--text-muted)]"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{run.status}</span>
                  <span>{new Date(run.createdAt).toLocaleString()}</span>
                </div>
                {run.totalCost && <div className="mt-1 text-[var(--text-muted)]">Cost: {run.totalCost}</div>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
