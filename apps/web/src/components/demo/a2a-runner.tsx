'use client';

/**
 * Shared UI component for running A2A flows.
 *
 * - mode="demo": used by /demo/a2a, wired to demo-only API endpoints with no real wallet/escrow writes.
 * - mode="test": used by console test pages, wired to full AP2 + wallets APIs for end-to-end testing.
 *
 * Keep backend wiring (API calls, wallet funding, etc.) in the page-level wrappers
 * and pass them in via props. This component focuses on the form, status, and logs.
 */

import { useEffect, useState, useTransition } from 'react';

import { Button } from '@/components/ui/button';

export interface A2AAgent {
  id: string;
  name: string;
  description?: string;
}

interface A2ARunParams {
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

interface ResumeRunHelpers {
  setLogs: (logs: string[]) => void;
  setStatus: (status: string) => void;
  addLog: (message: string) => void;
}

export interface A2ARunnerProps {
  mode: 'demo' | 'test';
  initialService?: string;
  initialBudget?: number;
  initialPrice?: number;
  initialRunId?: string | null;
  fetchAgents: () => Promise<A2AAgent[]>;
  getInitialSelection?: (
    agents: A2AAgent[],
  ) => { requesterId: string; responderId: string } | null;
  onRun: (params: A2ARunParams) => Promise<void>;
  onResumeRun?: (runId: string, helpers: ResumeRunHelpers) => Promise<void>;
  enableShareLink?: boolean;
  buildShareLink?: (runId: string) => string;
}

const DEMO_DEFAULT_AGENTS: A2AAgent[] = [
  { id: 'demo-support-agent', name: 'Support Agent' },
  { id: 'demo-darwin-agent', name: 'Darwin Agent' },
];

export function A2ARunner(props: A2ARunnerProps) {
  const {
    mode,
    initialService,
    initialBudget = 25,
    initialPrice = 20,
    initialRunId = null,
    fetchAgents,
    getInitialSelection,
    onRun,
    onResumeRun,
    enableShareLink,
    buildShareLink,
  } = props;

  const defaultAgents = props.mode === 'demo' ? DEMO_DEFAULT_AGENTS : [];

  const [agents, setAgents] = useState<A2AAgent[]>(defaultAgents);
  const [requesterId, setRequesterId] = useState(
    defaultAgents[0]?.id ?? '',
  );
  const [responderId, setResponderId] = useState(
    defaultAgents[1]?.id ?? '',
  );
  const [service, setService] = useState(
    initialService ?? 'Generate a summary of the top 3 AI trends in 2024',
  );
  const [budget, setBudget] = useState(initialBudget);
  const [price, setPrice] = useState(initialPrice);
  const [status, setStatus] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(initialRunId ?? null);
  const [lastSuccessfulRunId, setLastSuccessfulRunId] = useState<string | null>(
    initialRunId ?? null,
  );
  const [logsVisible, setLogsVisible] = useState(mode === 'test');
  const [isPending, startTransition] = useTransition();
  const [showLoadingHint, setShowLoadingHint] = useState(mode === 'demo');

  const addLog = (message: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const handleSetRunId = (runId: string | null) => {
    setCurrentRunId(runId);
    if (runId) {
      setLastSuccessfulRunId(runId);
    }
  };

  useEffect(() => {
    if (mode === 'demo') {
      const timer = setTimeout(() => {
        setShowLoadingHint(false);
      }, 300);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [mode]);

  useEffect(() => {
    let cancelled = false;

    const loadAgents = async () => {
      try {
        const data = await fetchAgents();
        if (cancelled) {
          return;
        }

        // If we got a non-empty list, replace any demo defaults.
        if (data.length >= 2) {
          setAgents(data);
          const selection = getInitialSelection?.(data);
          if (selection && selection.requesterId && selection.responderId) {
            setRequesterId(selection.requesterId);
            setResponderId(selection.responderId);
          } else {
            setRequesterId(data[0].id);
            setResponderId(data[1].id);
          }
        } else if (data.length === 1) {
          setAgents(data);
          setRequesterId(data[0].id);
          setResponderId(data[0].id);
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Failed to load agents:', error);
        if (mode === 'test') {
          addLog('?? Note: Some features require login. Using demo mode...');
        } else {
          addLog('?? Failed to load agents');
        }
      }
    };

    loadAgents();

    return () => {
      cancelled = true;
    };
    // We intentionally run this once on mount; fetchAgents/getInitialSelection
    // are expected to be stable for the lifetime of the component.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!initialRunId || !onResumeRun) {
      return;
    }

    onResumeRun(initialRunId, { setLogs, setStatus, addLog }).catch((error) => {
      // eslint-disable-next-line no-console
      console.error('Failed to resume demo run:', error);
    });
  }, [initialRunId, onResumeRun]);

  const handleRun = () => {
    if (!requesterId || !responderId || requesterId === responderId) {
      addLog('?? Please select two different agents');
      return;
    }

    setLogs([]);
    setLogsVisible(mode === 'test');
    setStatus('Running...');
    setCurrentRunId(null);

    startTransition(async () => {
      try {
        await onRun({
          agents,
          requesterId,
          responderId,
          service,
          budget,
          price,
          addLog,
          setStatus,
          setLogs,
          setRunId: handleSetRunId,
        });
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        addLog(`?? ${mode === 'demo' ? 'Demo' : 'Test'} failed: ${errorMessage}`);

        if (mode === 'demo' && lastSuccessfulRunId && onResumeRun) {
          addLog('?? Replaying last successful demo run instead...');
          try {
            await onResumeRun(lastSuccessfulRunId, { setLogs, setStatus, addLog });
            setStatus('? Showing last successful run');
          } catch (replayError) {
            // eslint-disable-next-line no-console
            console.error('Failed to replay last demo run:', replayError);
            setStatus('?? Demo failed');
          }
        } else {
          setStatus(`?? ${mode === 'demo' ? 'Demo' : 'Test'} failed`);
        }
      }
    });
  };

  const handleReplayLastRun = () => {
    if (!lastSuccessfulRunId || !onResumeRun) {
      return;
    }

    startTransition(async () => {
      setStatus('Replaying last successful run...');
      try {
        await onResumeRun(lastSuccessfulRunId, { setLogs, setStatus, addLog });
        setStatus('? Showing last successful run');
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Failed to replay last run:', error);
        setStatus('?? Failed to replay last run');
      }
    });
  };

  const shareLink =
    enableShareLink && currentRunId && buildShareLink ? buildShareLink(currentRunId) : null;

  const canReplayLastRun = mode === 'demo' && !!lastSuccessfulRunId && !!onResumeRun;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-white">Requester Agent</span>
          <select
            value={requesterId}
            onChange={(e) => setRequesterId(e.target.value)}
            disabled={agents.length === 0}
            className="rounded-lg border border-border bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-border focus:outline-none disabled:bg-[rgba(11,14,28,0.6)]"
          >
            {agents.length === 0 ? (
              <option>
                {showLoadingHint ? 'Loading agents...' : 'Using demo agents (limited set)'}
              </option>
            ) : (
              agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))
            )}
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-white">Responder Agent</span>
          <select
            value={responderId}
            onChange={(e) => setResponderId(e.target.value)}
            disabled={agents.length === 0}
            className="rounded-lg border border-border bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-border focus:outline-none disabled:bg-[rgba(11,14,28,0.6)]"
          >
            {agents.length === 0 ? (
              <option>
                {showLoadingHint ? 'Loading agents...' : 'Using demo agents (limited set)'}
              </option>
            ) : (
              agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))
            )}
          </select>
        </label>
      </div>

      <label className="flex flex-col gap-2">
        <span className="text-sm font-semibold text-white">Service Request</span>
        <textarea
          value={service}
          onChange={(e) => setService(e.target.value)}
          rows={3}
          className="rounded-lg border border-border bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-border focus:outline-none"
        />
      </label>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-white">Budget ($)</span>
          <input
            type="number"
            value={budget}
            onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
            className="rounded-lg border border-border bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-border focus:outline-none"
          />
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-semibold text-white">Acceptance Price ($)</span>
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-white/40 focus:outline-none"
          />
        </label>
      </div>

      <Button
        type="button"
        onClick={handleRun}
        disabled={isPending || agents.length < 2}
        className="w-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc] text-white hover:bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc]/90 text-lg py-6"
        size="lg"
      >
        {isPending
          ? mode === 'demo'
            ? 'Running demo...'
            : 'Running test...'
          : mode === 'demo'
          ? 'Run Live Demo'
          : 'Run Full A2A Test'}
      </Button>

      {canReplayLastRun && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleReplayLastRun}
            className="text-xs text-gray-600 underline underline-offset-4 hover:text-gray-900"
          >
            Replay last successful run
          </button>
        </div>
      )}

      {shareLink && (
        <div className="rounded-lg border border-[var(--border-base)]/20 bg-[var(--surface-raised)] p-4">
          <p className="text-sm font-semibold text-gray-900 mb-2">
            {mode === 'demo' ? 'Copy this successful run:' : 'Share this demo:'}
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={shareLink}
              readOnly
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900"
            />
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                if (!shareLink) {
                  return;
                }
                navigator.clipboard.writeText(shareLink);
                // Basic UX feedback; safe for demo
                // eslint-disable-next-line no-alert
                alert('Link copied to clipboard!');
              }}
            >
              Copy
            </Button>
          </div>
        </div>
      )}

      {status && (
        <div
          className={`rounded-lg border p-4 ${
            status.includes('??')
              ? 'border-red-500/40 bg-red-50 text-red-800'
              : 'border-emerald-500/40 bg-emerald-50 text-emerald-800'
          }`}
        >
          {status}
        </div>
      )}

      {logs.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">
              {mode === 'demo' ? 'Demo Logs:' : 'Test Logs:'}
            </h3>
            {mode === 'demo' && (
              <button
                type="button"
                onClick={() => setLogsVisible((visible) => !visible)}
                className="text-xs text-gray-600 underline underline-offset-4 hover:text-gray-900"
              >
                {logsVisible ? 'Hide live log' : 'Show live log'}
              </button>
            )}
          </div>
          {logsVisible && (
            <div className="max-h-96 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-4 font-mono text-xs text-gray-800">
              {logs.map((log, index) => (
                <div key={index} className="mb-1">
                  {log}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
