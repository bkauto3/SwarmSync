import Link from 'next/link';
import { Suspense } from 'react';

import { WorkflowBuilder } from '@/components/workflows/workflow-builder';
import { WorkflowRunner } from '@/components/workflows/workflow-runner';
import { getAgentMarketClient } from '@/lib/server-client';

import type { Workflow } from '@agent-market/sdk';
import type { Metadata } from 'next';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Workflows',
  robots: {
    index: false,
    follow: false,
  },
};

export default async function WorkflowsPage() {
  const client = getAgentMarketClient();
  let workflows: Workflow[] = [];
  let error: string | null = null;

  try {
    workflows = await client.listWorkflows();
  } catch (err) {
    console.error('Failed to load workflows:', err);
    error = 'Unable to load workflows at this time. Please try again later.';
  }

  return (
    <div className="space-y-10">
      <header className="glass-card p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Workflows</p>
        <h1 className="mt-2 text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Orchestration Studio</h1>
        <p className="mt-2 max-w-4xl text-sm text-[var(--text-muted)]">
          Design lightweight multi-agent workflows with budget guardrails. Executions are logged for
          auditability and leverage the collaboration APIs introduced earlier.
        </p>
      </header>

      {error ? (
        <div className="glass-card border border-amber-500/40 bg-amber-500/10 p-6">
          <h2 className="text-lg font-semibold text-amber-300">Workflows Temporarily Unavailable</h2>
          <p className="mt-2 text-sm text-amber-300">
            {error} The workflow orchestration feature is currently experiencing issues. Our team has been notified.
          </p>
          <p className="mt-4 text-sm text-[var(--text-muted)]">
            In the meantime, you can:
          </p>
          <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-[var(--text-muted)]">
            <li>Browse available agents in the <Link href="/agents" className="text-slate-300 hover:underline">Agent Library</Link></li>
            <li>Check your <Link href="/dashboard" className="text-slate-300 hover:underline">Dashboard</Link> for existing activity</li>
            <li>Review your <Link href="/billing" className="text-slate-300 hover:underline">Billing</Link> information</li>
          </ul>
        </div>
      ) : (
        <>
          <WorkflowBuilder />

          <section className="space-y-6">
            <h2 className="text-lg font-display text-[var(--text-primary)]">Existing Workflows</h2>
            {workflows.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">
                No workflows yet. Create one using the builder above.
              </p>
            ) : (
              <div className="space-y-6">
                {workflows.map((workflow) => (
                  <Suspense
                    key={workflow.id}
                    fallback={
                      <div className="glass-card p-6 text-sm text-[var(--text-muted)]">
                        Loading workflow details…
                      </div>
                    }
                  >
                    <WorkflowRunner workflow={workflow} />
                  </Suspense>
                ))}
              </div>
            )}
          </section>

          <div className="glass-card border border-white/10 bg-white/5 p-6 text-sm text-slate-300">
            Need advanced scheduling? Extend this MVP with queue-based execution, conditional branching,
            and webhook notifications.
          </div>
        </>
      )}

      <Link
        href="/agents"
        className="glass-button inline-flex w-fit items-center border border-white/10 bg-transparent px-4 py-2 text-sm text-[var(--text-primary)]"
      >
        ← Back to Agent Library
      </Link>
    </div>
  );
}
