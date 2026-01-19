'use client';

import { X } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useTestRunProgress } from '@/hooks/use-test-run-progress';
import type { StartTestRunResponse } from '@/lib/api';

interface TestSuite {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  estimatedDurationSec: number;
  approximateCostUsd: number;
  isRecommended: boolean;
}

interface Agent {
  id: string;
  name: string;
  slug: string;
}

interface TestWizardModalProps {
  isOpen: boolean;
  onClose: () => void;
  agents: Agent[];
  suites: TestSuite[];
  individualTests?: { id: string; suiteSlug: string; suiteName: string; category: string }[];
  isLoading?: boolean;
   initialSuiteId?: string | null;
   initialTestId?: string | null;
   defaultMode?: 'suite' | 'individual';
  onStartRun: (agentIds: string[], suiteIds: string[], testIds?: string[]) => Promise<StartTestRunResponse>;
}

export function TestWizardModal({
  isOpen,
  onClose,
  agents,
  suites,
  individualTests,
  isLoading,
   initialSuiteId,
   initialTestId,
   defaultMode,
  onStartRun,
}: TestWizardModalProps) {
  const [step, setStep] = useState(1);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [selectedSuites, setSelectedSuites] = useState<string[]>([]);
  const [selectedIndividualTests, setSelectedIndividualTests] = useState<string[]>([]);
  const [mode, setMode] = useState<'suite' | 'individual'>('suite');
  const [isRunning, setIsRunning] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runStatusLabel, setRunStatusLabel] = useState<string | null>(null);

  const { progress } = useTestRunProgress(activeRunId);

  useEffect(() => {
    if (!isOpen) {
      setStep(1);
      setSelectedAgents([]);
      setSelectedSuites([]);
      setSelectedIndividualTests([]);
      setMode('suite');
      setIsRunning(false);
      setStartError(null);
      setActiveRunId(null);
      return;
    }

    // When opening, apply any initial selection hints from the caller
    if (initialSuiteId) {
      setMode('suite');
      setSelectedSuites([initialSuiteId]);
    }
    if (initialTestId) {
      setMode('individual');
      setSelectedIndividualTests([initialTestId]);
    }
    if (defaultMode) {
      setMode(defaultMode);
    }
  }, [isOpen, initialSuiteId, initialTestId, defaultMode]);

  if (!isOpen) return null;

  const handleStart = async () => {
    if (selectedAgents.length === 0) {
      return;
    }

    if (mode === 'suite' && selectedSuites.length === 0) return;
    if (mode === 'individual' && selectedIndividualTests.length === 0) return;

    setIsRunning(true);
    setStartError(null);
    setRunStatusLabel('Starting…');
    try {
      let response;
      if (mode === 'individual') {
        // Group by suite
        const testsBySuite = new Map<string, string[]>();
        selectedIndividualTests.forEach(testId => {
          const test = individualTests?.find(t => t.id === testId);
          if (test) {
            const existing = testsBySuite.get(test.suiteSlug) || [];
            testsBySuite.set(test.suiteSlug, [...existing, test.id]);
          }
        });

        // We can only run one startRun call per suite/agent combo easily with current API
        // For now, let's just pick the first suite found or handle multiple calls
        // Simplification: Just take the first suite found for now or refactor API later
        // Actually, the API supports array of suites. But testIds is global for the run.
        // If we select tests from DIFFERENT suites, we might have an issue if the API expects testIds to apply to ALL suites.
        // Let's assume for now we just pass all testIds and the backend filters them per suite.

        const uniqueSuites = Array.from(testsBySuite.keys());
        response = await onStartRun(selectedAgents, uniqueSuites, selectedIndividualTests);
      } else {
        response = await onStartRun(selectedAgents, selectedSuites);
      }
      const firstRun = response?.runs?.[0];
      if (firstRun?.id) {
        setActiveRunId(firstRun.id);
        setStep(3);
      } else {
        setStartError('Test run started, but no run ID was returned.');
      }
    } catch (error) {
      console.error('Failed to start test run:', error);
      let message = 'Failed to start test run. Please try again.';
      const httpError = error as { response?: Response };
      if (httpError?.response) {
        const body = await httpError.response.clone().json().catch(() => null);
        message =
          (body as { message?: string })?.message ??
          httpError.response.statusText ??
          message;
      } else if (error instanceof Error) {
        message = error.message;
      }
      setStartError(message);
      setRunStatusLabel(null);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="relative w-full max-w-5xl max-h-[90vh] overflow-hidden rounded-2xl card border border-[var(--border-base)] p-6 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full p-2 text-[var(--text-muted)] transition hover:bg-[var(--surface-raised)]"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="mb-6">
          <h2 className="text-2xl font-display text-white">Test & Evaluate Agents</h2>
          <p className="mt-2 text-sm text-[var(--text-muted)]">Run quality tests on your agents</p>
        </div>

        <div className="mb-6 flex items-center gap-4">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full border-2 ${step >= s
                  ? 'border-[var(--border-base)] bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc] text-carrara'
                  : 'border-[var(--border-base)] text-[var(--text-muted)]'
                  }`}
              >
                {s}
              </div>
              {s < 3 && (
                <div className={`h-1 w-16 ${step > s ? 'bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc]' : 'bg-white/10'}`} />
              )}
            </div>
          ))}
        </div>

        <div className="max-h-[60vh] overflow-y-auto pr-1">
          {startError && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {startError}
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white">Select Agents</h3>
              <p className="text-sm text-[var(--text-muted)]">Choose which agents to test</p>
              {isLoading ? (
                <div className="py-8 text-center text-sm text-[var(--text-muted)]">Loading agents...</div>
              ) : agents.length === 0 ? (
                <div className="py-8 text-center text-sm text-[var(--text-muted)]">
                  No agents available. Create an agent first.
                </div>
              ) : (
                <div className="grid max-h-[40vh] gap-3 overflow-y-auto pr-1 md:grid-cols-2">
                  {agents.map((agent) => (
                    <Card
                      key={agent.id}
                      className={`cursor-pointer transition ${selectedAgents.includes(agent.id)
                        ? 'border-[var(--border-base)] bg-[var(--surface-raised)]'
                        : 'border-[var(--border-base)] hover:border-[var(--border-base)]'
                        }`}
                      onClick={() => {
                        setSelectedAgents((prev) =>
                          prev.includes(agent.id)
                            ? prev.filter((id) => id !== agent.id)
                            : [...prev, agent.id],
                        );
                      }}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-semibold text-white">{agent.name}</h4>
                            <p className="text-xs text-[var(--text-muted)]">{agent.slug}</p>
                          </div>
                          {selectedAgents.includes(agent.id) && (
                            <div className="h-5 w-5 rounded-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc]" />
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-white">Select Tests</h3>
                  <p className="text-sm text-[var(--text-muted)]">Choose entire suites or specific tests</p>
                </div>
                <div className="flex rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-1">
                  <button
                    onClick={() => setMode('suite')}
                    className={`rounded-md px-3 py-1 text-sm font-medium transition ${mode === 'suite'
                      ? 'bg-[var(--surface-raised)] text-white shadow-sm'
                      : 'text-[var(--text-muted)] hover:text-white'
                      }`}
                  >
                    Test Suites
                  </button>
                  <button
                    onClick={() => setMode('individual')}
                    className={`rounded-md px-3 py-1 text-sm font-medium transition ${mode === 'individual'
                      ? 'bg-[var(--surface-raised)] text-white shadow-sm'
                      : 'text-[var(--text-muted)] hover:text-white'
                      }`}
                  >
                    Individual Tests
                  </button>
                </div>
              </div>

              {mode === 'suite' ? (
                isLoading ? (
                  <div className="py-8 text-center text-sm text-[var(--text-muted)]">Loading test suites...</div>
                ) : suites.length === 0 ? (
                  <div className="py-8 text-center text-sm text-[var(--text-muted)]">No test suites available.</div>
                ) : (
                  <div className="grid max-h-[40vh] gap-3 overflow-y-auto pr-1 md:grid-cols-2">
                    {suites.map((suite) => (
                      <Card
                        key={suite.id}
                        className={`cursor-pointer transition ${selectedSuites.includes(suite.id)
                          ? 'border-[var(--border-base)] bg-[var(--surface-raised)]'
                          : 'border-[var(--border-base)] hover:border-[var(--border-base)]'
                          }`}
                        onClick={() => {
                          setSelectedSuites((prev) =>
                            prev.includes(suite.id)
                              ? prev.filter((id) => id !== suite.id)
                              : [...prev, suite.id],
                          );
                        }}
                      >
                        <CardHeader className="p-4 pb-2">
                          <div className="flex items-start justify-between">
                            <div>
                              <CardTitle className="text-base">{suite.name}</CardTitle>
                              {suite.isRecommended && (
                                <span className="mt-1 inline-block rounded-full bg-white/10 px-2 py-0.5 text-xs text-slate-300">
                                  Recommended
                                </span>
                              )}
                            </div>
                            {selectedSuites.includes(suite.id) && (
                              <div className="h-5 w-5 rounded-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc]" />
                            )}
                          </div>
                        </CardHeader>
                        <CardContent className="p-4 pt-2">
                          <CardDescription className="text-xs">{suite.description}</CardDescription>
                          <div className="mt-3 flex items-center gap-4 text-xs text-[var(--text-muted)]">
                            <span>~{Math.round(suite.estimatedDurationSec / 60)} min</span>
                            <span>~${suite.approximateCostUsd.toFixed(2)}</span>
                            <span className="capitalize">{suite.category}</span>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )
              ) : (
                // Individual Tests View
                isLoading ? (
                  <div className="py-8 text-center text-sm text-[var(--text-muted)]">Loading tests...</div>
                ) : !individualTests || individualTests.length === 0 ? (
                  <div className="py-8 text-center text-sm text-[var(--text-muted)]">No individual tests available.</div>
                ) : (
                  <div className="grid max-h-[40vh] gap-3 overflow-y-auto pr-1 md:grid-cols-2">
                    {individualTests.map((test) => (
                      <Card
                        key={test.id}
                        className={`cursor-pointer transition ${selectedIndividualTests.includes(test.id)
                          ? 'border-[var(--border-base)] bg-[var(--surface-raised)]'
                          : 'border-[var(--border-base)] hover:border-[var(--border-base)]'
                          }`}
                        onClick={() => {
                          setSelectedIndividualTests((prev) =>
                            prev.includes(test.id)
                              ? prev.filter((id) => id !== test.id)
                              : [...prev, test.id],
                          );
                        }}
                      >
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <h4 className="font-semibold text-white">{test.id}</h4>
                              <p className="text-xs text-[var(--text-muted)]">{test.suiteName} • {test.category}</p>
                            </div>
                            {selectedIndividualTests.includes(test.id) && (
                              <div className="h-5 w-5 rounded-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc]" />
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white">Review & Confirm</h3>
              {activeRunId ? (
                <div className="space-y-4 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase text-[var(--text-muted)]">Run in progress</p>
                      <p className="text-sm font-semibold text-white">ID: {activeRunId}</p>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-medium ${progress?.status === 'completed'
                        ? 'bg-green-100 text-green-800'
                        : progress?.status === 'failed'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-amber-100 text-amber-800'
                        }`}
                    >
                      {progress?.status ?? runStatusLabel ?? 'queued'}
                    </span>
                  </div>

                  <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full bg-gradient-to-r from-brass to-[#bf8616] transition-all duration-500"
                      style={{
                        width: `${progress?.totalTests
                          ? Math.min(
                            100,
                            Math.round((progress.completedTests / progress.totalTests) * 100),
                          )
                          : progress?.status === 'completed'
                            ? 100
                            : progress?.status === 'running'
                              ? 50
                              : runStatusLabel
                                ? 20
                                : 15
                          }%`,
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
                    <span>
                      {progress?.status === 'completed'
                        ? 'Completed'
                        : progress?.status === 'failed'
                          ? 'Failed'
                          : progress?.status === 'running'
                            ? `Running${progress?.currentTest ? `: ${progress.currentTest}` : ''}`
                            : runStatusLabel ?? 'Queued...'}
                    </span>
                    {progress?.score !== undefined && progress.score !== null && (
                      <span className="font-semibold text-white">Score: {progress.score}</span>
                    )}
                  </div>
                  {progress?.error && (
                    <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                      {progress.error}
                    </div>
                  )}
                </div>
              ) : null}

              <div className="space-y-6">
                <div>
                  <h4 className="mb-2 text-sm font-semibold text-white">Selected Agents</h4>
                  <div className="space-y-2">
                    {selectedAgents.map((agentId) => {
                      const agent = agents.find((a) => a.id === agentId);
                      return agent ? (
                        <div
                          key={agentId}
                          className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-3"
                        >
                          <p className="text-sm font-medium text-white">{agent.name}</p>
                        </div>
                      ) : null;
                    })}
                  </div>
                </div>
                <div>
                  <h4 className="mb-2 text-sm font-semibold text-white">Selected Test Suites</h4>
                  <div className="space-y-2">
                    {mode === 'suite' ? (
                      selectedSuites.map((suiteId) => {
                        const suite = suites.find((s) => s.id === suiteId);
                        return suite ? (
                          <div
                            key={suiteId}
                            className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-3"
                          >
                            <p className="text-sm font-medium text-white">{suite.name}</p>
                            <p className="mt-1 text-xs text-[var(--text-muted)]">
                              ~{Math.round(suite.estimatedDurationSec / 60)} min • ~$
                              {suite.approximateCostUsd.toFixed(2)}
                            </p>
                            <p className="mt-1 text-xs text-[var(--text-muted)]">{suite.description}</p>
                          </div>
                        ) : null;
                      })
                    ) : (
                      selectedIndividualTests.map((testId) => {
                        const test = individualTests?.find((t) => t.id === testId);
                        return test ? (
                          <div
                            key={testId}
                            className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-3"
                          >
                            <p className="text-sm font-medium text-white">{test.id}</p>
                            <p className="mt-1 text-xs text-[var(--text-muted)]">
                              Suite: {test.suiteName}
                            </p>
                          </div>
                        ) : null;
                      })
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-between border-t border-[var(--border-base)] pt-4">
          <Button
            variant="ghost"
            onClick={() => {
              if (step > 1) {
                setStep(step - 1);
              } else {
                onClose();
              }
            }}
          >
            {step === 1 ? 'Cancel' : 'Back'}
          </Button>
          <div className="flex gap-3">
            {step < 3 ? (
              <Button
                onClick={() => {
                  if (step === 1 && selectedAgents.length > 0) {
                    setStep(2);
                  } else if (step === 2) {
                    if (mode === 'suite' && selectedSuites.length > 0) {
                      setStep(3);
                    } else if (mode === 'individual' && selectedIndividualTests.length > 0) {
                      setStep(3);
                    }
                  }
                }}
                disabled={
                  (step === 1 && selectedAgents.length === 0) ||
                  (step === 2 && mode === 'suite' && selectedSuites.length === 0) ||
                  (step === 2 && mode === 'individual' && selectedIndividualTests.length === 0)
                }
              >
                Next
              </Button>
            ) : (
              <Button onClick={handleStart} disabled={isRunning}>
                {isRunning ? 'Starting...' : 'Start Test Run'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
