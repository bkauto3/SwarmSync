'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

import { CreditSummaryCard } from '@/components/dashboard/credit-summary-card';
import { OrgOverviewCard } from '@/components/dashboard/org-overview-card';
import { OrgRoiTimeseriesChart } from '@/components/dashboard/org-roi-timeseries-chart';
import { RecentActivityList } from '@/components/dashboard/recent-activity-list';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { agentsApi } from '@/lib/api';
import { useAuthStore } from '@/stores/auth-store';

import type { OrganizationRoiTimeseriesPoint } from '@agent-market/sdk';

const statusPills = [
    {
        label: 'API',
        state: 'Operational',
        tone: 'bg-emerald-500/15 text-emerald-300',
    },
    {
        label: 'Payments',
        state: 'Sandbox',
        tone: 'bg-amber-500/20 text-amber-200',
    },
];

const defaultNextSteps = [
    {
        title: 'Configure billing',
        detail: 'Connect Stripe, add payment info, and unlock credits.',
        href: '/console/billing',
    },
    {
        title: 'Add agents',
        detail: 'Register your first agents so workflows have collaborators.',
        href: '/console/agents/new',
    },
    {
        title: 'Launch a workflow',
        detail: 'Run agent orchestration workflows to observe spend and outcomes.',
        href: '/console/workflows',
    },
];

export default function OverviewPage() {
    const user = useAuthStore((state) => state.user);


    const orgSlug = process.env.NEXT_PUBLIC_DEFAULT_ORG_SLUG ?? 'genesis';

    // TODO: Fetch organization data once organizationsApi is implemented
    // const { data: orgSummary } = useQuery({
    //     queryKey: ['org-roi', orgSlug],
    //     queryFn: () => organizationsApi.getOrganizationRoi(orgSlug),
    //     retry: false,
    // });

    // const { data: orgTimeseries = [] } = useQuery({
    //     queryKey: ['org-roi-timeseries', orgSlug],
    //     queryFn: () => organizationsApi.getOrganizationRoiTimeseries(orgSlug, 14),
    //     retry: false,
    // });

    // TODO: Implement getSubscription in billingApi
    // const { data: subscription } = useQuery({
    //     queryKey: ['billing-subscription'],
    //     queryFn: () => billingApi.getSubscription(),
    //     retry: false,
    // });
    const subscription = null;
    const orgSummary = null;
    const orgTimeseries: OrganizationRoiTimeseriesPoint[] = [];

    const { data: agents = [] } = useQuery({
        queryKey: ['agents', 'my-agents'],
        queryFn: () => agentsApi.list({ showAll: 'true', creatorId: user?.id }),
        enabled: !!user?.id,
    });

    // Get greeting based on time of day
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    const firstName = user?.displayName?.split(' ')[0] || 'there';

    // Determine alerts/next steps
    const alerts = [];
    if (!subscription) {
        alerts.push({ type: 'warning', message: 'No billing plan configured', action: '/billing', tone: 'violet' });
    }
    if (agents.length === 0) {
        alerts.push({ type: 'info', message: 'Create your first agent to get started', action: '/agents/new' });
    }

    return (
        <div className="dashboard space-y-6">
            {/* Slim Header */}
            <header className="space-y-4">
                <div>
                    <p className="text-xs uppercase tracking-[0.35em] text-[var(--text-muted)] font-ui">Overview</p>
                    <h1 className="mt-1 text-3xl font-semibold text-[var(--text-primary)] font-display" style={{ fontSize: '32px', lineHeight: '1.2' }}>
                        {greeting}, {firstName}
                    </h1>
                    <p className="mt-1 text-sm text-[var(--text-muted)] font-ui">
                        {orgSlug} • {statusPills.map(p => `${p.label}: ${p.state}`).join(' • ')}
                    </p>
                </div>

                <div className="flex flex-wrap gap-3">
                    <Link
                        href="/console/agents/new"
                        className="tactical-button secondary"
                        font-ui
                    >
                        + Create Agent
                    </Link>
                    <Link
                        href="/workflows"
                        className="tactical-button primary"
                        font-ui
                    >
                        Launch Workflow
                    </Link>
                </div>
            </header>

            {/* KPI Row - Max 4 cards */}
            <section className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <CreditSummaryCard subscription={subscription} />
                {orgSummary && <OrgOverviewCard summary={orgSummary} />}
            </section>

            {/* Two-column: Alerts + Activity */}
            <section className="grid gap-6 lg:grid-cols-2">
                {/* Next Steps / Alerts */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg" font-display>Next Steps</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {alerts.length > 0 ? (
                            <div className="space-y-3">
                                {alerts.map((alert, i) => (
                                    <div
                                        key={i}
                                        className={`rounded-lg border p-3 text-sm ${alert.tone === 'violet' || alert.type === 'info'
                                            ? 'border-[var(--accent-primary)]/30 bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]'
                                            : alert.type === 'warning'
                                                ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                                                : 'border-[var(--border-base)] bg-[var(--surface-raised)] text-[var(--text-secondary)]'
                                            }`}
                                    >
                                        <p>{alert.message}</p>
                                        <Link
                                            href={alert.action}
                                            className="mt-1 inline-block text-xs font-medium underline text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                                            font-ui
                                        >
                                            Take action →
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-[var(--text-muted)]" font-ui>All systems operational. No action needed.</p>
                        )}
                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                            {defaultNextSteps.filter(s => !(s.title === 'Add agents' && agents.length > 0)).map((step) => (
                                <Link
                                    key={step.title}
                                    href={step.href}
                                    className="card-inner rounded-xl border border-[var(--border-base)] px-4 py-3 text-sm transition hover:border-[var(--border-hover)]"
                                >
                                    <p className="text-[0.7rem] uppercase tracking-[0.3em] text-[var(--text-muted)]" font-ui>Next</p>
                                    <p className="text-base font-semibold text-[var(--text-primary)]" font-display>{step.title}</p>
                                    <p className="text-xs text-[var(--text-secondary)]" font-ui>{step.detail}</p>
                                </Link>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* My Agents Row - If Exists */}
                {agents.length > 0 && (
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle className="text-lg" font-display>My Agents</CardTitle>
                            <Link href="/console/agents" className="text-xs text-[var(--accent-primary)] hover:underline">View All</Link>
                        </CardHeader>
                        <CardContent>
                            <div className="flex flex-col gap-2">
                                {agents.slice(0, 4).map((agent: any) => (
                                    <Link key={agent.id} href={`/agents/${agent.slug || agent.id}`} className="flex items-center justify-between rounded-md border border-[var(--border-base)] p-2 hover:bg-[var(--surface-raised)]">
                                        <span className="font-semibold text-sm">{agent.name}</span>
                                        <span className="text-xs text-[var(--text-muted)]">{agent.visibility}</span>
                                    </Link>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Recent Activity */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg" font-display>Recent Activity</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <RecentActivityList />
                    </CardContent>
                </Card>
            </section>

            {/* Single Chart Card with Toggle */}
            <section>
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-lg" font-display>Performance</CardTitle>

                        </div>
                    </CardHeader>
                    <CardContent>
                        <OrgRoiTimeseriesChart points={orgTimeseries} />
                    </CardContent>
                </Card>
            </section>
        </div>
    );
}
