'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { A2ARunner, type A2AAgent } from '@/components/demo/a2a-runner';
import { API_BASE_URL } from '@/lib/api';

interface DemoRunParams {
  agents: A2AAgent[];
  requesterId: string;
  responderId: string;
  service: string;
  budget: number;
  price: number;
  addLog: (message: string) => void;
  setStatus: (status: string) => void;
  setRunId?: (runId: string | null) => void;
  setLogs: (logs: string[]) => void;
}

interface DemoResumeHelpers {
  setLogs: (logs: string[]) => void;
  setStatus: (status: string) => void;
  addLog: (message: string) => void;
}

interface DemoNegotiationAgent {
  id?: string | null;
  name?: string | null;
}

interface DemoNegotiationTransaction {
  id?: string;
  status?: string | null;
  amount?: number | null;
  settledAt?: string | null;
}

interface DemoNegotiation {
  id: string;
  status?: string | null;
  requesterAgent?: DemoNegotiationAgent | null;
  responderAgent?: DemoNegotiationAgent | null;
  requestedService?: string | null;
  proposedBudget?: number | null;
  counter?: {
    price?: number | null;
    estimatedDelivery?: string | null;
  } | null;
  serviceAgreementId?: string | null;
  escrowId?: string | null;
  transaction?: DemoNegotiationTransaction | null;
  verificationStatus?: string | null;
  verificationUpdatedAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

type DetailView = 'user' | 'developer';

const SAMPLE_NEGOTIATION: DemoNegotiation = {
  id: 'demo-sample-negotiation',
  status: 'ACCEPTED',
  requesterAgent: { id: 'demo-support-agent', name: 'Support Agent' },
  responderAgent: { id: 'demo-darwin-agent', name: 'Darwin Agent' },
  requestedService: 'Generate a summary of the top 3 AI trends in 2024',
  proposedBudget: 25,
  counter: {
    price: 20,
    estimatedDelivery: '30 minutes',
  },
  serviceAgreementId: 'demo-service-agreement',
  escrowId: 'demo-escrow',
  transaction: {
    id: 'demo-transaction',
    status: 'SETTLED',
    amount: 20,
    settledAt: new Date().toISOString(),
  },
  verificationStatus: 'VERIFIED',
  verificationUpdatedAt: new Date().toISOString(),
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const SAMPLE_LOGS: string[] = [
  '[4:37:01 PM] ?? Step 0: Checking and funding agent wallets...',
  '[4:37:01 PM] ?? Requester wallet funded to $40',
  '[4:37:01 PM] ?? Responder wallet funded to $10',
  '[4:37:01 PM] ?? Step 1: Initiating negotiation...',
  '[4:37:01 PM] ?? Negotiation created and accepted',
  '[4:37:01 PM] ?? Step 2: Escrow funded and locked',
  '[4:37:01 PM] ?? Step 3: Delivering service...',
  '[4:37:01 PM] ? Service delivered!',
  '[4:37:01 PM] ?? Step 4: Checking final status...',
  '[4:37:01 PM] ?? Final Status: ACCEPTED (escrow released)',
];

interface TransactionStoryboardProps {
  negotiation: DemoNegotiation | null;
  detailView: DetailView;
  onDetailViewChange: (view: DetailView) => void;
}

interface TimelineStep {
  key: string;
  title: string;
  description: string;
  timestamp?: string;
  state: 'done' | 'upcoming' | 'pending';
}

function buildTimelineSteps(negotiation: DemoNegotiation | null): TimelineStep[] {
  if (!negotiation) {
    return [
      {
        key: 'created',
        title: 'Negotiation created',
        description: 'Run a live demo to see funds move through negotiation, escrow, and payout.',
        state: 'pending',
      },
    ];
  }

  const requesterName =
    negotiation.requesterAgent?.name ?? negotiation.requesterAgent?.id ?? 'Requester agent';
  const responderName =
    negotiation.responderAgent?.name ?? negotiation.responderAgent?.id ?? 'Responder agent';
  const baseTime =
    (negotiation.createdAt && new Date(negotiation.createdAt)) || new Date(negotiation.updatedAt ?? Date.now());
  const offsetsSeconds = [0, 4, 8, 12, 16, 20];
  const stepTime = (index: number) =>
    new Date(baseTime.getTime() + offsetsSeconds[index] * 1000).toLocaleTimeString();

  const accepted =
    negotiation.status === 'ACCEPTED' ||
    negotiation.status === 'COMPLETED' ||
    negotiation.status === 'DELIVERED';
  const escrowFunded = Boolean(negotiation.escrowId);
  const workDelivered = Boolean(negotiation.verificationStatus);
  const verificationPassed = negotiation.verificationStatus === 'VERIFIED';
  const paymentReleased =
    verificationPassed || negotiation.transaction?.status === 'SETTLED';

  const steps: TimelineStep[] = [
    {
      key: 'created',
      title: 'Negotiation created',
      description: `${requesterName} opened a negotiation with ${responderName} for this service request.`,
      timestamp: stepTime(0),
      state: 'done',
    },
    {
      key: 'accepted',
      title: 'Responder accepted',
      description: accepted
        ? `${responderName} accepted the work at the agreed price.`
        : `${responderName} is reviewing the request and price.`,
      timestamp: stepTime(1),
      state: accepted ? 'done' : 'upcoming',
    },
    {
      key: 'escrow',
      title: 'Escrow funded',
      description: escrowFunded
        ? 'Funds were locked in escrow so both sides are protected.'
        : 'Once accepted, funds will move into escrow before work begins.',
      timestamp: stepTime(2),
      state: escrowFunded ? 'done' : accepted ? 'upcoming' : 'pending',
    },
    {
      key: 'delivered',
      title: 'Work delivered',
      description: workDelivered
        ? `${responderName} delivered the agreed result back into the system.`
        : `${responderName} will deliver the result back into the system when work is complete.`,
      timestamp: stepTime(3),
      state: workDelivered ? 'done' : escrowFunded ? 'upcoming' : 'pending',
    },
    {
      key: 'verified',
      title: 'Verification passed',
      description: verificationPassed
        ? 'The outcome passed verification checks and is marked as successful.'
        : workDelivered
          ? 'The result is under verification to confirm quality before payout.'
          : 'Verification runs after the work has been delivered.',
      timestamp: stepTime(4),
      state: verificationPassed ? 'done' : workDelivered ? 'upcoming' : 'pending',
    },
    {
      key: 'paid',
      title: 'Payment released',
      description: paymentReleased
        ? 'Escrow was released and the responder received payment.'
        : 'Once verification passes, escrow releases and the responder is paid.',
      timestamp: stepTime(5),
      state: paymentReleased ? 'done' : verificationPassed ? 'upcoming' : 'pending',
    },
  ];

  return steps;
}

function TransactionStoryboard({
  negotiation,
  detailView,
  onDetailViewChange,
}: TransactionStoryboardProps) {
  const steps = buildTimelineSteps(negotiation);

  const requesterName =
    negotiation?.requesterAgent?.name ?? negotiation?.requesterAgent?.id ?? 'Requester agent';
  const responderName =
    negotiation?.responderAgent?.name ?? negotiation?.responderAgent?.id ?? 'Responder agent';
  const service = negotiation?.requestedService ?? 'this service request';
  const price =
    negotiation?.counter?.price ??
    negotiation?.transaction?.amount ??
    negotiation?.proposedBudget ??
    null;
  const escrowAmount = negotiation?.transaction?.amount ?? negotiation?.proposedBudget ?? null;
  const status = negotiation?.status ?? 'PENDING';
  const payoutStatus = negotiation?.transaction?.status ?? 'INITIATED';
  const verificationStatus = negotiation?.verificationStatus ?? 'PENDING';

  const summarySentence =
    negotiation == null
      ? 'Run the live demo to see a complete, line-item view of how funds move between agents.'
      : `${requesterName} hired ${responderName} to ${service.toLowerCase()} for ${
          price != null ? `$${price}` : 'an agreed budget'
        }.`;

  return (
    <div className="space-y-4">
          <div className="flex items-baseline justify-between">
            <div>
              <h2 className="text-lg font-semibold text-[var(--text-primary)]" font-display>Transaction Storyboard</h2>
              <p className="text-xs text-white" font-ui>
                Outcomes-first view of a full A2A negotiation, escrow, and payout.
              </p>
            </div>
      </div>

      <div className="demo-feed space-y-8">
        {steps.map((step) => (
          <div
            key={step.key}
            className={`step-card flex gap-3 rounded-xl border border-[var(--border-base)] bg-[var(--surface-raised)] p-4 shadow-[var(--shadow-panel)] ${step.state === 'done' ? 'active border-[var(--accent-primary)]' : ''}`}
          >
            <div className="mt-1 flex flex-col items-center">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  step.state === 'done'
                    ? 'bg-emerald-500'
                    : step.state === 'upcoming'
                      ? 'bg-amber-400'
                      : 'bg-slate-600'
                }`}
              />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-[var(--text-primary)]" style={{ fontFamily: 'Space Grotesk, sans-serif', fontSize: '20px' }}>{step.title}</span>
                {step.timestamp && (
                  <span className="text-xs text-white whitespace-nowrap" style={{ fontFamily: 'Inter, sans-serif', fontVariantNumeric: 'tabular-nums' }}>{step.timestamp}</span>
                )}
              </div>
              <p className="mt-1 text-xs text-white" style={{ fontFamily: 'Inter, sans-serif', fontSize: '14px' }}>{step.description}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/5 shadow-sm">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
          <span className="text-sm font-semibold text-white">Run details</span>
          <div className="inline-flex rounded-full bg-white/10 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => onDetailViewChange('user')}
              className={`rounded-full px-3 py-1 ${
                detailView === 'user'
                  ? 'bg-white/20 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              User view
            </button>
            <button
              type="button"
              onClick={() => onDetailViewChange('developer')}
              className={`rounded-full px-3 py-1 ${
                detailView === 'developer'
                  ? 'bg-white/20 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Developer view
            </button>
          </div>
        </div>

        {detailView === 'user' ? (
          <div className="space-y-3 px-4 py-3 text-sm text-slate-200">
            <p>{summarySentence}</p>
            {negotiation && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300">
                <p className="mb-1 font-semibold">Outcome preview</p>
                <p>
                  This run shows a fully funded, escrow-backed transaction from negotiation to
                  payout. The storyboard on the left mirrors how user funds move between agents in
                  production.
                </p>
              </div>
            )}
            {negotiation && (
              <ul className="grid gap-2 text-xs text-slate-300 sm:grid-cols-2">
                <li>
                  <span className="font-semibold">Negotiation status:</span> {status}
                </li>
                <li>
                  <span className="font-semibold">Agreed price:</span>{' '}
                  {price != null ? `$${price}` : 'N/A'}
                </li>
                <li>
                  <span className="font-semibold">Verification:</span> {verificationStatus}
                </li>
                <li>
                  <span className="font-semibold">Payout status:</span> {payoutStatus}
                </li>
              </ul>
            )}
          </div>
        ) : (
          <div className="space-y-3 px-4 py-3 text-xs text-slate-200">
            {negotiation ? (
              <>
                <div className="grid gap-2 sm:grid-cols-2">
                  <div>
                    <div className="font-semibold text-white">IDs & ledger</div>
                    <dl className="mt-1 space-y-1 font-mono">
                      <div>
                        <span className="text-slate-400">negotiationId:</span>{' '}
                        <span className="text-white">{negotiation.id}</span>
                      </div>
                      {negotiation.escrowId && (
                        <div>
                          <span className="text-slate-400">escrowId:</span>{' '}
                          <span className="text-white">{negotiation.escrowId}</span>
                        </div>
                      )}
                      {negotiation.transaction?.id && (
                        <div>
                          <span className="text-slate-400">transactionId:</span>{' '}
                          <span className="text-white">{negotiation.transaction.id}</span>
                        </div>
                      )}
                    </dl>
                  </div>
                  <div>
                    <div className="font-semibold text-white">Status</div>
                    <dl className="mt-1 space-y-1 font-mono">
                      <div>
                        <span className="text-slate-400">negotiationStatus:</span>{' '}
                        <span className="text-white">{status}</span>
                      </div>
                      {negotiation.transaction && (
                        <div>
                          <span className="text-slate-400">payoutStatus:</span>{' '}
                          <span className="text-white">{negotiation.transaction.status}</span>
                        </div>
                      )}
                      {negotiation.verificationStatus && (
                        <div>
                          <span className="text-slate-400">verificationStatus:</span>{' '}
                          <span className="text-white">{negotiation.verificationStatus}</span>
                        </div>
                      )}
                    </dl>
                  </div>
                </div>

                <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    Raw negotiation payload
                  </div>
                  <pre className="max-h-64 overflow-y-auto text-[11px] leading-tight text-slate-300">
                    {JSON.stringify(negotiation, null, 2)}
                  </pre>
                </div>
              </>
            ) : (
              <p className="text-xs text-slate-400">
                Once you run the demo, you&apos;ll see the raw negotiation object, escrow and payout
                fields, and verification status here.
              </p>
            )}
          </div>
        )}
      </div>

      {negotiation && (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs text-emerald-300">
          <div className="mb-2 font-semibold">Receipt</div>
          <dl className="space-y-1 font-mono">
            <div className="flex justify-between gap-2">
              <span className="text-emerald-400">negotiationId</span>
              <span className="text-right text-white">{negotiation.id}</span>
            </div>
            {negotiation.escrowId && (
              <div className="flex justify-between gap-2">
                <span className="text-emerald-400">escrowId</span>
                <span className="text-right text-white">{negotiation.escrowId}</span>
              </div>
            )}
            {escrowAmount != null && (
              <div className="flex justify-between gap-2">
                <span className="text-emerald-400">escrowAmount</span>
                <span className="text-right text-white">${escrowAmount}</span>
              </div>
            )}
            {price != null && (
              <div className="flex justify-between gap-2">
                <span className="text-emerald-400">acceptedPrice</span>
                <span className="text-right text-white">${price}</span>
              </div>
            )}
            {negotiation.transaction?.status && (
              <div className="flex justify-between gap-2">
                <span className="text-emerald-400">payoutResult</span>
                <span className="text-right text-white">{negotiation.transaction.status}</span>
              </div>
            )}
            {negotiation.verificationStatus && (
              <div className="flex justify-between gap-2">
                <span className="text-emerald-400">verificationSummary</span>
                <span className="text-right text-white">{negotiation.verificationStatus}</span>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

export default function DemoA2APage() {
  const searchParams = useSearchParams();
  const runId = searchParams.get('runId');

  const [negotiation, setNegotiation] = useState<DemoNegotiation | null>(null);
  const [detailView, setDetailView] = useState<DetailView>('user');
  const [usingFallbackAgents, setUsingFallbackAgents] = useState(false);

    const fetchDemoAgents = async (): Promise<A2AAgent[]> => {
      try {
        // Primary: demo-specific allowlisted endpoint
        const res = await fetch(`${API_BASE_URL}/demo/a2a/agents`);
        if (res.ok) {
          setUsingFallbackAgents(false);
          return (await res.json()) as A2AAgent[];
        }

        // Fallback: public agents endpoint, limited and filtered
        // This keeps the demo usable even if the demo module is misconfigured.
        // Backend will still enforce DEMO_AGENT_IDS on run, if configured.
        // eslint-disable-next-line no-console
        console.warn(
          'Falling back to /agents for demo A2A because /demo/a2a/agents returned',
          res.status,
        );

        const fallback = await fetch(
          `${API_BASE_URL}/agents?status=APPROVED&visibility=PUBLIC&limit=8`,
        );
        if (fallback.ok) {
          const data = (await fallback.json()) as A2AAgent[];
          setUsingFallbackAgents(true);
          return data;
        }

        // eslint-disable-next-line no-console
        console.warn(
          'Fallback /agents request for demo A2A also failed with status',
          fallback.status,
        );
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Unexpected error while loading demo agents:', error);
      }

      // In the worst case, return an empty list. The UI will still
      // show the storyboard and can replay the last successful run.
      setUsingFallbackAgents(true);
      return [];
    };

    const resumeDemoRun = async (id: string, helpers: DemoResumeHelpers) => {
      try {
        const response = await fetch(`${API_BASE_URL}/demo/a2a/run/${id}/logs`);
        const data = await response.json();

        helpers.setLogs(data.logs || []);

        const rawStatus: string | undefined = data.status;
        if (!rawStatus || rawStatus === 'UNKNOWN') {
          helpers.setStatus('');
        } else {
          const friendly =
            rawStatus === 'ACCEPTED' || rawStatus === 'COMPLETED' || rawStatus === 'VERIFIED'
              ? 'Demo completed successfully!'
              : `Demo status: ${rawStatus}`;
          helpers.setStatus(friendly);
        }

        if (data.negotiation) {
          setNegotiation(data.negotiation as DemoNegotiation);
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Failed to load run logs:', error);
        helpers.addLog('?? Failed to load run logs');
      }
    };

    const runDemo = async (params: DemoRunParams) => {
      const {
        agents,
        requesterId,
        responderId,
        service,
        budget,
        price,
        addLog,
        setStatus,
        setRunId,
        setLogs,
      } = params;

      setNegotiation(null);
      setLogs([]);

      try {
        // Step 1: Initialize demo run
        addLog('?? Step 1: Initializing demo run...');
        addLog(`   Requester: ${agents.find((a) => a.id === requesterId)?.name || requesterId}`);
        addLog(`   Responder: ${agents.find((a) => a.id === responderId)?.name || responderId}`);
        addLog(`   Service: ${service}`);
        addLog(`   Budget: $${budget}`);

        // Step 2: Create demo negotiation (session + synthetic A2A)
        addLog('\n?? Step 2: Creating demo negotiation...');
        const response = await fetch(`${API_BASE_URL}/demo/a2a/run`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            requesterAgentId: requesterId,
            responderAgentId: responderId,
            service,
            budget,
            price,
          }),
        });

        if (!response.ok) {
          const errorBody = await response.json().catch(() => ({}));
          const message =
            (errorBody && typeof (errorBody as { message?: string }).message === 'string' &&
              (errorBody as { message?: string }).message) ||
            'Failed to run demo';
          throw new Error(message);
        }

        const result = await response.json();
        const nextRunId = String(result.runId);

        if (setRunId) {
          setRunId(nextRunId);
        }

        addLog(`   ? Demo negotiation created: ${nextRunId}`);
        if (result.expiresAt) {
          addLog(`   Session expires at: ${new Date(result.expiresAt).toLocaleString()}`);
        }

        // Update URL with runId for sharing
        const url = new URL(window.location.href);
        url.searchParams.set('runId', nextRunId);
        window.history.pushState({}, '', url.toString());

        // Step 3: Fetch final status and logs from API
        addLog('\n?? Step 3: Checking demo status...');
        const logsResponse = await fetch(`${API_BASE_URL}/demo/a2a/run/${nextRunId}/logs`);
        if (logsResponse.ok) {
          const data = await logsResponse.json();
          const rawStatus: string | undefined = data.status;

          if (Array.isArray(data.logs) && data.logs.length > 0) {
            addLog('\n?? Demo engine logs:');
            for (const line of data.logs as string[]) {
              addLog(`   ${line}`);
            }
          }

          if (data.negotiation) {
            setNegotiation(data.negotiation as DemoNegotiation);
          }

          if (!rawStatus || rawStatus === 'UNKNOWN') {
            setStatus('');
          } else {
            addLog('\n?? Final status:');
            addLog(`   ${rawStatus}`);

            setStatus(
              rawStatus === 'ACCEPTED' || rawStatus === 'COMPLETED' || rawStatus === 'VERIFIED'
                ? '? Demo completed successfully!'
                : `?? Demo completed with status: ${rawStatus}`,
            );
          }
        } else {
          addLog('?? Unable to fetch demo status from API.');
          setStatus('? Demo completed (status fetch unavailable)');
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown error';
        // eslint-disable-next-line no-console
        console.error('Live demo run failed, using sample fallback:', error);

        addLog(`?? Live demo failed: ${message}`);
        addLog('?? Showing a previously successful sample demo run instead.');

        setLogs(SAMPLE_LOGS);
        setNegotiation(SAMPLE_NEGOTIATION);
        setStatus('? Showing sample successful run');
      }
    };

  const buildShareLink = (id: string) => `${window.location.origin}/demo/a2a?runId=${id}`;

  return (
    <div className="min-h-screen bg-black text-slate-50">
      <div className="mx-auto max-w-6xl space-y-8 px-4 py-12">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-white">
            Live Agent-to-Agent Demo
          </h1>
          <p className="text-lg text-slate-400">
            Watch two agents negotiate, fund escrow, and release payment in real time - no signup
            required.
          </p>
        </div>

        {usingFallbackAgents && (
          <div className="mx-auto max-w-3xl rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-300">
            Using demo agents from the public catalog.{' '}
            <span className="font-semibold">Sign up</span> to access the full agent directory.
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-lg backdrop-blur-sm">
            <A2ARunner
              mode="demo"
              initialRunId={runId}
              fetchAgents={fetchDemoAgents}
              onRun={runDemo}
              onResumeRun={resumeDemoRun}
              enableShareLink
              buildShareLink={buildShareLink}
            />
          </div>

          <TransactionStoryboard
            negotiation={negotiation}
            detailView={detailView}
            onDetailViewChange={setDetailView}
          />
        </div>

        <div className="text-center space-y-2">
          <Link href="/" className="text-sm text-slate-400 hover:text-white underline">
            Back to Home
          </Link>
          <p className="text-xs text-slate-500">
            Demo sessions expire after 1 hour. No signup required.
          </p>
        </div>
      </div>
    </div>
  );
}
