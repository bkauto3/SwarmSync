'use client';

import { useQuery } from '@tanstack/react-query';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/hooks/use-auth';
import { agentsApi } from '@/lib/api';

export default function LimitsPage() {
  const { user } = useAuth();
  const { data: agents = [] } = useQuery({
    queryKey: ['agents', { creatorId: user?.id }],
    queryFn: () => agentsApi.list({ creatorId: user?.id }),
    enabled: !!user,
  });

  // Calculate limits from agents and budgets
  const totalAgents = agents.length;
  const activeAgents = agents.filter((a) => a.status === 'ACTIVE').length;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Account Limits</h1>
        <p className="text-sm text-[var(--text-muted)]">
          View and manage your account limits, budgets, and spending controls
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Agent Limits</CardTitle>
            <CardDescription>Your current agent usage</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--text-muted)]">Total Agents</span>
              <span className="text-2xl font-semibold text-[var(--text-primary)]">{totalAgents}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--text-muted)]">Active Agents</span>
              <span className="text-2xl font-semibold text-emerald-600">{activeAgents}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-[var(--text-muted)]">Draft Agents</span>
              <span className="text-2xl font-semibold text-[var(--text-primary)]">
                {agents.filter((a) => a.status === 'DRAFT').length}
              </span>
            </div>
            <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-[var(--text-muted)]">
              <p>No hard limit on agents. Create as many as you need.</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Budget Limits</CardTitle>
            <CardDescription>Spending controls and thresholds</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">Wallet Spend Ceiling</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">Not configured</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">Auto-approve Threshold</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">Not configured</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">Monthly Budget Limits</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">
                  {/* Budgets are managed per-agent, not returned in list API */}
                  Configure per agent
                </span>
              </div>
            </div>
            <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-[var(--text-muted)]">
              <p>
                Configure budget limits per agent in the{' '}
                <a href="/console/agents" className="text-primary underline hover:no-underline">
                  Agents
                </a>{' '}
                section.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Organization Limits</CardTitle>
            <CardDescription>Subscription and plan limits</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">Plan</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">Free Tier</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">Monthly Credits</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">Unlimited</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">API Rate Limit</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">1000 req/min</span>
              </div>
            </div>
            <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-[var(--text-muted)]">
              <p>
                Upgrade your plan in{' '}
                <a href="/billing" className="text-primary underline hover:no-underline">
                  Billing
                </a>{' '}
                to increase limits.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Usage Statistics</CardTitle>
            <CardDescription>Current period usage</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">API Calls (this month)</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">-</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">Credits Used</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">-</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-muted)]">Workflows Executed</span>
                <span className="text-sm font-semibold text-[var(--text-primary)]">-</span>
              </div>
            </div>
            <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-3 text-xs text-[var(--text-muted)]">
              <p>Detailed usage analytics coming soon.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
