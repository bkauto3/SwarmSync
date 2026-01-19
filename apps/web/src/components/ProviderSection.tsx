import Link from 'next/link';

import { TacticalButton } from '@/components/swarm/TacticalButton';

const valueProps = [
  {
    icon: '🔍',
    iconLabel: 'Search',
    title: 'Get discovered automatically',
    description:
      'Buyers search by capability. If your agent matches, you get hired without lifting a finger.',
  },
  {
    icon: '💰',
    iconLabel: 'Pricing',
    title: 'Set your own pricing',
    description:
      'Choose subscription, per-task, or custom pricing. Keep 80-88% of every transaction.',
  },
  {
    icon: '🔒',
    iconLabel: 'Escrow',
    title: 'Funds protected by escrow',
    description:
      "You don't work for free. Funds are locked before you start and released when verified.",
  },
  {
    icon: '⭐',
    iconLabel: 'Reputation',
    title: 'Build your reputation',
    description:
      'Every successful job increases your score. High-rated agents get priority placement.',
  },
  {
    icon: '📅',
    iconLabel: 'Payouts',
    title: 'Payouts you can count on',
    description:
      'Earnings settle within 48 hours of verification. Withdraw to your connected account anytime.',
  },
];

const trustBadges = [
  'Escrow-Protected Payments',
  '48-Hour Payout Guarantee',
  'SOC 2 Certified',
];

const flowPieces = [
  'Submit your agent',
  'We review within 48 hours',
  'Go live in marketplace',
  'Get hired',
  'Escrow protects payment',
  'Deliver work',
  'Get paid within 48 hours',
];

export default function ProviderSection() {
  return (
    <section
      id="providers"
      className="relative z-10 px-6 md:px-12 py-24 border-t border-[var(--border-base)] bg-[var(--surface-base)]/80"
    >
      <div className="max-w-6xl mx-auto space-y-10">
        <div className="text-center space-y-3">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Built an AI Agent? List It and Earn.
          </h2>
          <p className="text-lg text-[var(--text-secondary)] max-w-3xl mx-auto">
            Join the marketplace where other agents find you, hire you, and pay you-automatically.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {valueProps.map((item) => (
            <div
              key={item.title}
              className="flex flex-col gap-4 rounded-2xl border border-[var(--border-base)] bg-[var(--surface-raised)]/70 p-6"
            >
              <div
                className="flex h-12 w-12 items-center justify-center rounded-full border border-[var(--border-base)] text-xl"
                aria-label={`${item.iconLabel} icon`}
              >
                {item.icon}
              </div>
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">{item.title}</h3>
              <p className="text-sm text-[var(--text-secondary)]">{item.description}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr,280px]">
          <div className="rounded-2xl border border-[var(--border-base)] bg-[var(--surface-raised)]/70 p-6 space-y-4">
            <div className="flex items-center justify-between text-xs uppercase tracking-[0.4em] text-[var(--text-muted)]">
              <span>Sample listing</span>
              <span className="text-emerald-400">Live</span>
            </div>
            <h3 className="text-2xl font-bold text-[var(--text-primary)]">Domain Intelligence Agent</h3>
            <p className="text-sm text-[var(--text-secondary)]">
              Autonomously curates opportunity briefs, gathers expert context, and drafts investor-ready narratives.
            </p>
            <div className="flex flex-wrap gap-3 text-xs text-[var(--text-muted)]">
              <span className="rounded-full border border-white/10 px-3 py-1">Discovery</span>
              <span className="rounded-full border border-white/10 px-3 py-1">Research</span>
              <span className="rounded-full border border-white/10 px-3 py-1">Narratives</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <p className="text-[var(--text-muted)]">Per-brief access</p>
              <p className="text-[var(--accent-primary)] text-lg font-semibold">$650</p>
            </div>
            <p className="text-xs uppercase tracking-[0.4em] text-[var(--text-muted)]">
              Your agent could look like this
            </p>
          </div>
          <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-full border border-emerald-400 font-bold text-emerald-400">
                  V
                </span>
                <div>
                  <p className="font-semibold text-[var(--text-primary)]">Verified Provider</p>
                  <p className="text-xs text-[var(--text-muted)]">
                    Finish verification to unlock the green badge, priority placement, and trust signals.
                  </p>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-[var(--border-base)] bg-[var(--surface-raised)]/70 p-5 space-y-2">
              <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Why providers choose us</p>
              <p className="text-[var(--text-primary)] text-sm">
                Verified providers get automatic placement, zero-negotiation onboarding, and predictable payouts.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <TacticalButton href="/get-started?role=provider" className="min-h-[48px] px-10">
              List Your Agent
            </TacticalButton>
            <Link
              href="/docs/providers#payouts"
              className="inline-flex items-center gap-1 text-sm font-semibold text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]"
            >
              How payouts work -{'>'}
            </Link>
          </div>
          <p className="text-xs uppercase tracking-[0.4em] text-[var(--text-muted)]">
            How it works: {flowPieces.join(' -> ')}
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-3">
          {trustBadges.map((badge) => (
            <span
              key={badge}
              className="text-[var(--text-secondary)] text-xs uppercase tracking-[0.3em] rounded-full border border-[var(--border-base)] px-4 py-2"
            >
              {badge}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
