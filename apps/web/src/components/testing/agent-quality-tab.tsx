'use client';

import { Play, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { testingApi, type TestRun, type Agent, type TestSuite } from '@/lib/api';

import { TestWizardModal } from './test-wizard-modal';

interface AgentQualityTabProps {
  agentId: string;
  agentName: string;
  trustScore: number;
  badges: string[];
}

export function AgentQualityTab({ agentId, agentName, trustScore, badges }: AgentQualityTabProps) {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [suites, setSuites] = useState<TestSuite[]>([]);

  const fetchRuns = async () => {
    try {
      const data = await testingApi.listRuns({ agentId });
      setRuns(data.runs || []);
      setIsLoading(false);
      return data.runs || [];
    } catch (error) {
      console.error('Failed to fetch test runs:', error);
      setIsLoading(false);
      return [];
    }
  };

  const pollingIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    fetchRuns();
    // Poll for updates every 2 seconds
    pollingIntervalRef.current = window.setInterval(async () => {
      const currentRuns = await fetchRuns();
      const hasActiveRuns = currentRuns.some(
        (run) => run.status === 'QUEUED' || run.status === 'RUNNING',
      );
      // Stop polling if no active runs
      if (!hasActiveRuns && pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }, 2000);

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [agentId]);

  useEffect(() => {
    if (isWizardOpen) {
      Promise.all([testingApi.listSuites()]).then(([suitesData]) => {
        setSuites(suitesData);
        // Create a minimal Agent object for the wizard
        const now = new Date().toISOString();
        setAgents([
          {
            id: agentId,
            slug: agentId,
            name: agentName,
            description: '',
            status: 'APPROVED',
            visibility: 'PUBLIC',
            categories: [],
            tags: [],
            pricingModel: '',
            creatorId: '',
            createdAt: now,
            updatedAt: now,
            verificationStatus: 'VERIFIED',
            trustScore,
            successCount: 0,
            failureCount: 0,
          } as Agent,
        ]);
      });
    }
  }, [isWizardOpen, agentId, agentName, trustScore]);

  const getStatusIcon = (status: TestRun['status']) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle className="h-5 w-5 text-emerald-400" />;
      case 'FAILED':
        return <XCircle className="h-5 w-5 text-red-400" />;
      case 'RUNNING':
        return <Clock className="h-5 w-5 text-blue-400 animate-spin" />;
      case 'QUEUED':
        return <Clock className="h-5 w-5 text-amber-400" />;
      default:
        return <AlertCircle className="h-5 w-5 text-[var(--text-muted)]" />;
    }
  };

  const getStatusColor = (status: TestRun['status']) => {
    switch (status) {
      case 'COMPLETED':
        return 'text-emerald-400';
      case 'FAILED':
        return 'text-red-400';
      case 'RUNNING':
        return 'text-blue-400';
      case 'QUEUED':
        return 'text-amber-400';
      default:
        return 'text-[var(--text-muted)]';
    }
  };

  return (
    <div className="space-y-6">
      {/* Trust Score Hero */}
      <Card className="border-[var(--border-base)] bg-gradient-to-br from-white/10 to-white/5">
        <CardHeader>
          <CardTitle className="text-2xl">Trust Score</CardTitle>
          <CardDescription>Overall quality rating for {agentName}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6">
            <div className="flex h-24 w-24 items-center justify-center rounded-full border-4 border-[var(--border-base)] bg-[var(--surface-raised)] text-3xl font-bold text-slate-300">
              {trustScore}
            </div>
            <div className="flex-1">
              <div className="mb-2 h-3 w-full overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc] transition-all"
                  style={{ width: `${trustScore}%` }}
                />
              </div>
              {badges.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {badges.map((badge) => (
                    <span
                      key={badge}
                      className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-slate-300 capitalize"
                    >
                      {badge.replace(/-/g, ' ')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Run Test Card */}
      <Card>
        <CardHeader>
          <CardTitle>Run Test Suite</CardTitle>
          <CardDescription>Execute quality tests on this agent</CardDescription>
        </CardHeader>
        <CardContent>
          <Button className="w-full" size="lg" onClick={() => setIsWizardOpen(true)}>
            <Play className="mr-2 h-4 w-4" />
            Start Test Run
          </Button>
        </CardContent>
      </Card>

      <TestWizardModal
        isOpen={isWizardOpen}
        onClose={() => setIsWizardOpen(false)}
        agents={agents}
        suites={suites}
        onStartRun={async (agentIds, suiteIds) => {
          const response = await testingApi.startRun({
            agentId: agentIds,
            suiteId: suiteIds,
          });
          // Refresh runs immediately
          await fetchRuns();
          // Restart polling if not already running
          if (!pollingIntervalRef.current) {
            pollingIntervalRef.current = window.setInterval(async () => {
              const currentRuns = await fetchRuns();
              const hasActiveRuns = currentRuns.some(
                (run) => run.status === 'QUEUED' || run.status === 'RUNNING',
              );
              if (!hasActiveRuns && pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
              }
            }, 2000);
          }
          return response;
        }}
      />

      {/* Active Test Runs with Progress */}
      {runs.filter((run) => run.status === 'QUEUED' || run.status === 'RUNNING').length > 0 && (
        <Card className="border-[var(--border-base)] bg-gradient-to-br from-white/10 to-white/5">
          <CardHeader>
            <CardTitle>Active Test Runs</CardTitle>
            <CardDescription>Tests currently in progress</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {runs
                .filter((run) => run.status === 'QUEUED' || run.status === 'RUNNING')
                .map((run) => {
                  const progress =
                    run.status === 'QUEUED' ? 10 : run.status === 'RUNNING' ? 50 : 100;
                  return (
                    <div
                      key={run.id}
                      className="rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4"
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <h4 className="font-semibold text-white font-ui">{run.suite.name}</h4>
                        <span className={`text-xs font-medium ${getStatusColor(run.status)}`}>
                          {run.status}
                        </span>
                      </div>
                      <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-white/10">
                        <div
                          className="h-full bg-gradient-to-r from-brass to-[#bf8616] transition-all duration-500"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                      <p className="text-xs text-[var(--text-muted)] font-ui">
                        {run.status === 'QUEUED'
                          ? 'Waiting to start...'
                          : run.status === 'RUNNING'
                            ? 'Running tests...'
                            : 'Completed'}
                      </p>
                    </div>
                  );
                })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Test History */}
      <Card>
        <CardHeader>
          <CardTitle>Test Results</CardTitle>
          <CardDescription>Completed test runs and scores</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-8 text-center text-sm text-[var(--text-muted)] font-ui">
              Loading test runs...
            </div>
          ) : runs.filter((run) => run.status === 'COMPLETED' || run.status === 'FAILED').length ===
            0 ? (
            <div className="py-8 text-center text-sm text-[var(--text-muted)] font-ui">
              No completed test runs yet. Start a test run to see results here.
            </div>
          ) : (
            <div className="space-y-3">
              {runs
                .filter((run) => run.status === 'COMPLETED' || run.status === 'FAILED')
                .map((run) => (
                  <div
                    key={run.id}
                    className="flex items-center justify-between rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4"
                  >
                    <div className="flex items-center gap-4">
                      {getStatusIcon(run.status)}
                      <div>
                        <h4 className="font-semibold text-white font-ui">{run.suite.name}</h4>
                        <p className="text-xs text-[var(--text-muted)] capitalize font-ui">
                          {run.suite.category}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {run.score !== null && (
                        <div className="text-right">
                          <p className="text-lg font-bold text-white font-ui">Score: {run.score}</p>
                          <p className="text-xs text-[var(--text-muted)] font-ui">
                            {new Date(run.createdAt).toLocaleString()}
                          </p>
                        </div>
                      )}
                      <span className={`text-sm font-medium ${getStatusColor(run.status)}`}>
                        {run.status}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

