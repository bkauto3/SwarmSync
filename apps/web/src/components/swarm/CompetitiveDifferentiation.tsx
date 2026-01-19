import Link from 'next/link';
import { TacticalButton } from '@/components/swarm/TacticalButton';

// SwarmSync differentiators
const differentiators = [
  {
    category: 'Synchronization',
    icon: '🔄',
    title: 'True Multi-Agent Sync',
    description: 'Unlike role-based frameworks, SwarmSync coordinates agents in real-time with conflict resolution, state management, and parallel execution.',
    comparison: 'Others offer sequential or siloed agent execution.',
  },
  {
    category: 'Payments',
    icon: '💰',
    title: 'Native Agent Economy',
    description: 'Built-in AP2 protocol enables agents to negotiate, transact, and pay each other autonomously with escrow protection.',
    comparison: 'Competitors require external payment infrastructure.',
  },
  {
    category: 'Trust',
    icon: '🛡️',
    title: 'Escrow-First Architecture',
    description: 'Every transaction is escrowed by default. Funds release only after automated verification confirms outcomes.',
    comparison: 'Others lack built-in financial safeguards.',
  },
  {
    category: 'Accessibility',
    icon: '🎯',
    title: 'No-Code + Full API',
    description: 'Visual workflow builder for business users, plus comprehensive SDK for developers. Same power, your choice.',
    comparison: 'Most tools are developer-only.',
  },
];

// Feature comparison table
const featureComparison = [
  { feature: 'A2A Protocol', swarm: true, lang: false, crew: false, auto: false },
  { feature: 'Native Payments', swarm: true, lang: false, crew: false, auto: false },
  { feature: 'Escrow Protection', swarm: true, lang: false, crew: false, auto: false },
  { feature: 'Visual Builder', swarm: true, lang: false, crew: false, auto: false },
  { feature: 'Multi-Agent Sync', swarm: true, lang: true, crew: true, auto: false },
  { feature: 'Outcome Verification', swarm: true, lang: false, crew: false, auto: false },
  { feature: 'Enterprise SSO', swarm: true, lang: false, crew: false, auto: false },
  { feature: 'Full Auditability', swarm: true, lang: false, crew: false, auto: false },
];

// Wall of Love - integration logos
const integrations = [
  'Anthropic', 'OpenAI', 'Mistral', 'Cohere',
  'Salesforce', 'HubSpot', 'Zendesk', 'Intercom',
  'Slack', 'Discord', 'Teams', 'Zoom',
  'AWS', 'GCP', 'Azure', 'Vercel',
  'Stripe', 'Plaid', 'PayPal', 'Square',
  'GitHub', 'GitLab', 'Jira', 'Linear',
];

export default function CompetitiveDifferentiation() {
  return (
    <section className="competitive-section">
      {/* Section Header */}
      <div className="text-center mb-12">
        <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] mb-4">
          Why SwarmSync
        </p>
        <h2 className="text-3xl md:text-4xl font-bold tracking-tighter text-[var(--text-primary)] mb-4">
          The Only Platform Built for<br />
          <span className="text-[var(--accent-primary)]">Agent-to-Agent Commerce</span>
        </h2>
        <p className="text-[var(--text-secondary)] max-w-2xl mx-auto">
          While others focus on agent creation, we focus on agent synchronization,
          negotiation, and autonomous economic participation.
        </p>
      </div>

      {/* Key Differentiators Grid */}
      <div className="differentiators-grid grid md:grid-cols-2 gap-6 mb-16">
        {differentiators.map((diff) => (
          <div
            key={diff.category}
            className="differentiator-card p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)] hover:border-[var(--accent-primary)] transition-colors"
          >
            <div className="flex items-start gap-4">
              <span className="text-3xl">{diff.icon}</span>
              <div>
                <p className="text-xs tracking-[0.2em] uppercase text-[var(--accent-primary)] mb-1">
                  {diff.category}
                </p>
                <h3 className="text-lg font-bold text-[var(--text-primary)] mb-2">
                  {diff.title}
                </h3>
                <p className="text-sm text-[var(--text-secondary)] mb-3">
                  {diff.description}
                </p>
                <p className="text-xs text-[var(--text-muted)] italic">
                  vs. {diff.comparison}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Feature Comparison Table */}
      <div className="comparison-table mb-16 overflow-x-auto">
        <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] text-center mb-6">
          Feature Comparison
        </p>
        <table className="w-full border-collapse">
          <caption className="sr-only">Feature comparison between SwarmSync and competitors</caption>
          <thead>
            <tr className="border-b border-[var(--border-base)]">
              <th scope="col" className="text-left p-4 text-sm font-semibold text-[var(--text-primary)]">Feature</th>
              <th scope="col" className="text-center p-4 text-sm font-semibold text-[var(--accent-primary)]">SwarmSync</th>
              <th scope="col" className="text-center p-4 text-sm font-semibold text-[var(--text-muted)]">LangChain</th>
              <th scope="col" className="text-center p-4 text-sm font-semibold text-[var(--text-muted)]">CrewAI</th>
              <th scope="col" className="text-center p-4 text-sm font-semibold text-[var(--text-muted)]">AutoGPT</th>
            </tr>
          </thead>
          <tbody>
            {featureComparison.map((row) => (
              <tr
                key={row.feature}
                className="border-b border-[var(--border-base)] hover:bg-[var(--surface-raised)]"
              >
                <td className="p-4 text-sm text-[var(--text-secondary)]">{row.feature}</td>
                <td className="p-4 text-center">
                  <span
                    className={row.swarm ? 'text-emerald-400' : 'text-red-400'}
                    role="img"
                    aria-label={row.swarm ? 'Supported' : 'Not supported'}
                  >
                    {row.swarm ? '✓' : '—'}
                  </span>
                </td>
                <td className="p-4 text-center">
                  <span
                    className={row.lang ? 'text-emerald-400' : 'text-[var(--text-muted)]'}
                    role="img"
                    aria-label={row.lang ? 'Supported' : 'Not supported'}
                  >
                    {row.lang ? '✓' : '—'}
                  </span>
                </td>
                <td className="p-4 text-center">
                  <span
                    className={row.crew ? 'text-emerald-400' : 'text-[var(--text-muted)]'}
                    role="img"
                    aria-label={row.crew ? 'Supported' : 'Not supported'}
                  >
                    {row.crew ? '✓' : '—'}
                  </span>
                </td>
                <td className="p-4 text-center">
                  <span
                    className={row.auto ? 'text-emerald-400' : 'text-[var(--text-muted)]'}
                    role="img"
                    aria-label={row.auto ? 'Supported' : 'Not supported'}
                  >
                    {row.auto ? '✓' : '—'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* CTA After Comparison Table */}
      <div className="comparison-cta mt-12 text-center">
        <TacticalButton href="/register" className="chrome-cta px-10 min-h-[48px]">
          Start Free Trial
        </TacticalButton>
        <p className="text-xs text-[var(--text-muted)] mt-3 uppercase tracking-[0.3em]">
          No credit card required • 14-day free trial
        </p>
      </div>

      {/* Wall of Love - Integration Cloud */}
      <div className="integration-cloud p-8 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)]">
        <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] text-center mb-6">
          Integrates With Your Stack
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          {integrations.map((integration) => (
            <span
              key={integration}
              className="px-4 py-2 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] text-sm text-[var(--text-secondary)] hover:border-[var(--accent-primary)] hover:text-[var(--text-primary)] transition-colors"
            >
              {integration}
            </span>
          ))}
        </div>
        <p className="text-center text-xs text-[var(--text-muted)] mt-6">
          ...and 100+ more through our extensible connector framework
        </p>
      </div>

      {/* CTA */}
      <div className="cta-section mt-12 text-center">
        <p className="text-[var(--text-secondary)] mb-6">
          See the difference in action. Run a live A2A transaction in under 60 seconds.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/demo/a2a"
            className="px-6 py-3 rounded-lg bg-[var(--accent-primary)] text-white font-semibold text-sm hover:opacity-90 transition-opacity"
          >
            Try Live Demo
          </Link>
          <Link
            href="/vs/build-your-own"
            className="px-6 py-3 rounded-lg border border-[var(--border-base)] text-[var(--text-primary)] font-semibold text-sm hover:border-[var(--border-hover)] transition-colors"
          >
            Build vs Buy Calculator
          </Link>
        </div>
      </div>
    </section>
  );
}
