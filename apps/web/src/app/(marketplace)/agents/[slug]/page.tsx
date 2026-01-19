import Link from 'next/link';
import { notFound } from 'next/navigation';

import { AgentActionPanel } from '@/components/agents/agent-action-panel';
import { RequestServiceForm } from '@/components/agents/request-service-form';
import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { getAgentMarketClient } from '@/lib/server-client';

import type { Agent, AgentSchemaDefinition } from '@agent-market/sdk';

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

// Mark this route as dynamic since it fetches data based on slug
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> | { slug: string } }
) {
  const resolvedParams = params instanceof Promise ? await params : params;

  if (!resolvedParams?.slug) {
    return { title: 'Agent Not Found | SwarmSync' };
  }

  try {
    const client = getAgentMarketClient();
    const agent = await client.getAgentBySlug(resolvedParams.slug);

    if (!agent) {
      return { title: 'Agent Not Found | SwarmSync' };
    }

    return {
      title: `${agent.name} | SwarmSync`,
      description: agent.description || `Hire ${agent.name} on SwarmSync Marketplace.`,
      openGraph: {
        title: agent.name,
        description: agent.description,
      },
    };
  } catch (error) {
    return { title: 'Agent Details | SwarmSync' };
  }
}

export default async function AgentDetailPage({
  params
}: {
  params: Promise<{ slug: string }> | { slug: string }
}) {
  // Handle both Promise and direct params (Next.js 13-15 compatibility)
  const resolvedParams = params instanceof Promise ? await params : params;
  const slug = resolvedParams.slug;

  if (!slug || typeof slug !== 'string') {
    console.error('Invalid slug parameter:', slug);
    notFound();
  }

  const client = getAgentMarketClient();
  let agent: Agent | null = null;

  try {
    console.log('[AgentDetailPage] Fetching agent with slug:', slug);
    agent = await client.getAgentBySlug(slug);
    console.log('[AgentDetailPage] Agent fetched successfully:', agent?.id, agent?.name);
  } catch (error) {
    console.error('[AgentDetailPage] Failed to fetch agent by slug:', slug, error);
    // Log more details about the error
    if (error instanceof Error) {
      console.error('[AgentDetailPage] Error message:', error.message);
      console.error('[AgentDetailPage] Error stack:', error.stack);
    }
    agent = null;
  }

  if (!agent) {
    console.error('[AgentDetailPage] Agent not found for slug:', slug);
    notFound();
  }

  const [schema, budget, qualityAnalytics, evaluations, certifications] = await Promise.all([
    client.getAgentSchema(agent.id).catch(() => null),
    client.getAgentBudget(agent.id).catch(() => null),
    client.getQualityAnalytics(agent.id).catch(() => null),
    client.listEvaluationResults(agent.id).catch(() => []),
    client.listCertifications(agent.id).catch(() => []),
  ]);

  const categories = agent.categories.length ? agent.categories : ['Generalist'];
  const price =
    typeof agent.basePriceCents === 'number'
      ? currency.format(agent.basePriceCents / 100)
      : 'Custom';

  return (
    <div className="flex min-h-screen flex-col bg-black text-slate-50">
      <Navbar />
      <div className="flex-1 px-4 py-12">
        <div className="mx-auto flex max-w-5xl flex-col gap-10">
          <header className="rounded-[3rem] border border-white/10 bg-white/5 p-10 shadow-brand-panel">
            <div className="flex flex-wrap items-center gap-4 text-xs uppercase tracking-[0.4em] text-slate-400">
              <span>{categories[0]}</span>
              {agent.verificationStatus === 'VERIFIED' && (
                <Badge variant="accent" className="text-[0.65rem] uppercase tracking-wide">
                  Verified
                </Badge>
              )}
              {agent.badges && agent.badges.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {agent.badges.map((badge) => {
                    let variant: 'default' | 'outline' | 'accent' = 'default';
                    if (badge.includes('Security Passed') || badge.includes('Latency A') || badge.includes('Reasoning A')) {
                      variant = 'default';
                    } else if (badge.includes('Failed') || badge.includes('Latency C') || badge.includes('Reasoning C')) {
                      variant = 'outline';
                    } else {
                      variant = 'accent';
                    }

                    return (
                      <Badge key={badge} variant={variant} className="text-[0.65rem] uppercase tracking-wide">
                        {badge}
                      </Badge>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="mt-6 flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h1 className="text-4xl font-display text-white">{agent.name}</h1>
                <p className="mt-4 text-base text-slate-400">{agent.description}</p>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-400">
                  {agent.tags.map((tag) => (
                    <Badge key={tag} variant="outline">
                      {formatTag(tag)}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-3">
                <div className="rounded-full border border-border px-4 py-2 text-center text-xs uppercase tracking-wide text-slate-400">
                  Pricing model: {agent.pricingModel}
                </div>
                <div className="text-3xl font-headline text-white">{price} / engagement</div>
                <div className="flex flex-wrap gap-3">
                  <Button
                    asChild
                    className="rounded-full px-6 py-2 text-sm font-semibold uppercase tracking-wide bg-gradient-to-r from-[var(--accent-primary)] to-[#FFD87E] text-black"
                  >
                    <Link href="#request-service-panel">Hire This Agent</Link>
                  </Button>
                  <AgentActionPanel agentSlug={agent.slug} />
                </div>
                <p className="text-xs text-slate-400 text-center">
                  Start an A2A transaction with this agent
                </p>
              </div>
            </div>
          </header>

          <section className="grid gap-4 md:grid-cols-3">
            <StatCard
              label="Trust rating"
              value={`${calculateRating(agent.trustScore, agent.successCount, agent.failureCount)} / 5`}
            />
            <StatCard
              label="Successful runs"
              value={agent.successCount.toLocaleString()}
              hint={`${agent.failureCount.toLocaleString()} failures`}
            />
            <StatCard
              label="Budget ceiling"
              value={
                budget
                  ? `${currency.format(budget.perTransactionLimit ?? budget.monthlyLimit)}`
                  : 'Auto'
              }
              hint={budget ? `Approval mode: ${budget.approvalMode}` : 'Wallet-managed'}
            />
          </section>

          {qualityAnalytics && (
            <Card className="border-white/10 bg-white/5">
              <CardContent className="space-y-6 p-6">
                <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
                  Quality & Testing
                </h2>
                <div className="grid gap-4 md:grid-cols-4">
                  <StatCard
                    label="Test Pass Rate"
                    value={`${formatPercent(qualityAnalytics.evaluations.passRate)}%`}
                    hint={`${qualityAnalytics.evaluations.passed}/${qualityAnalytics.evaluations.total} tests passed`}
                  />
                  <StatCard
                    label="Avg Latency"
                    value={
                      qualityAnalytics.evaluations.averageLatencyMs
                        ? `${qualityAnalytics.evaluations.averageLatencyMs.toFixed(0)}ms`
                        : 'N/A'
                    }
                    hint="Response time"
                  />
                  <StatCard
                    label="Certification"
                    value={qualityAnalytics.certification.status || 'None'}
                    hint={
                      qualityAnalytics.certification.expiresAt
                        ? `Expires ${new Date(qualityAnalytics.certification.expiresAt).toLocaleDateString()}`
                        : 'Not certified'
                    }
                  />
                  <StatCard
                    label="Verified Outcomes"
                    value={`${formatPercent(qualityAnalytics.roi.verifiedOutcomeRate)}%`}
                    hint={`${qualityAnalytics.verifications.verified} verified`}
                  />
                </div>
                {evaluations.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Recent Test Results
                    </h3>
                    <div className="space-y-1">
                      {evaluations.slice(0, 5).map((evaluation) => (
                        <div
                          key={evaluation.id}
                          className="flex items-center justify-between rounded-lg border border-border/50 bg-background/50 px-3 py-2 text-sm"
                        >
                          <span className="font-medium">{evaluation.scenario.name}</span>
                          <div className="flex items-center gap-3">
                            {evaluation.latencyMs && (
                              <span className="text-xs text-slate-400">{evaluation.latencyMs}ms</span>
                            )}
                            <span
                              className={`rounded-full px-2 py-0.5 text-xs font-semibold ${evaluation.status === 'PASSED'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-red-100 text-red-700'
                                }`}
                            >
                              {evaluation.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {certifications.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      Certifications
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {certifications.map((cert) => (
                        <Badge key={cert.id} variant="accent">
                          {cert.status}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <section className="grid gap-6 lg:grid-cols-2">
            <Card className="border-white/10 bg-white/5">
              <CardContent className="space-y-3 p-6">
                <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
                  Input schema
                </h2>
                <SchemaBlock data={schema?.schemas?.input} />
              </CardContent>
            </Card>
            <Card className="border-white/10 bg-white/5">
              <CardContent className="space-y-3 p-6">
                <h2 className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-400">
                  Output schema
                </h2>
                <SchemaBlock data={schema?.schemas?.output} />
              </CardContent>
            </Card>
          </section>

          {budget && (
            <Card className="border-white/10 bg-white/5">
              <CardContent className="grid gap-6 p-6 md:grid-cols-3">
                <BudgetMetric
                  label="Monthly allocation"
                  value={currency.format(budget.monthlyLimit)}
                  hint={`${currency.format(budget.remaining)} remaining`}
                />
                <BudgetMetric
                  label="Per-transaction"
                  value={
                    budget.perTransactionLimit
                      ? currency.format(budget.perTransactionLimit)
                      : 'Inherit wallet'
                  }
                  hint="Spending guardrails"
                />
                <BudgetMetric
                  label="Auto-approve threshold"
                  value={
                    budget.approvalThreshold
                      ? currency.format(budget.approvalThreshold)
                      : 'Manual review'
                  }
                  hint={budget.autoReload ? 'Auto reload enabled' : 'Manual approvals'}
                />
              </CardContent>
            </Card>
          )}

          <div id="request-service-panel">
            <RequestServiceForm responderAgentId={agent.id} responderAgentName={agent.name} />
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}

function SchemaBlock({ data }: { data?: AgentSchemaDefinition['schemas']['input'] | null }) {
  if (!data) {
    return <p className="text-sm text-slate-400">Schema not published yet.</p>;
  }
  return (
    <pre className="overflow-auto rounded-2xl border border-border bg-black/50 p-4 text-xs text-slate-400">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="border-white/10 bg-white/5">
      <CardContent className="space-y-1 p-5">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{label}</p>
        <p className="text-2xl font-display text-white">{value}</p>
        {hint && <p className="text-xs text-slate-400">{hint}</p>}
      </CardContent>
    </Card>
  );
}

function BudgetMetric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">{label}</p>
      <p className="mt-2 text-xl font-semibold text-white">{value}</p>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

function calculateRating(trustScore: number, successCount: number, failureCount: number) {
  const totalRuns = successCount + failureCount;
  if (totalRuns === 0) {
    // No production signal yet – start every new agent at a perfect 5.0
    return 5.0;
  }
  const safeTrust = Number.isFinite(trustScore) ? trustScore : 0;
  const successRate = successCount / totalRuns;
  const combinedScore = (successRate * 0.7 + (safeTrust / 100) * 0.3) * 5;
  return Math.max(1.0, Math.min(5.0, +combinedScore.toFixed(1)));
}

function formatPercent(raw: number | undefined | null) {
  if (raw === null || raw === undefined || Number.isNaN(raw)) return 0;
  const normalized = raw > 1 ? raw / 100 : raw;
  return Math.round(Math.min(Math.max(normalized, 0), 1) * 100);
}

function formatTag(tag: string) {
  return tag
    .split(/[-_]/)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}
