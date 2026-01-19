'use client';

import Link from 'next/link';

export default function OutcomesComingSoonPage() {
  return (
    <div className="space-y-6">
      <header className="glass-card p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Quality</p>
        <h1 className="mt-2 text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Outcomes Console</h1>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          Gathering data on autonomous outcome delivery. We&apos;re still building this experience.
        </p>
      </header>
      <div className="glass-card rounded-3xl border border-white/10 bg-surface p-10 text-center">
        <h2 className="text-2xl font-display font-semibold text-[var(--text-primary)]">Coming soon</h2>
        <p className="mt-3 text-sm text-[var(--text-muted)]">
          We&apos;re collecting quality signals for your agents and will share actionable outcome reporting shortly.
        </p>
        <p className="mt-6 text-sm text-[var(--text-muted)]">
          In the meantime, explore the{' '}
          <Link href="/console/quality/test-library" className="text-accent font-semibold">
            Test Library
          </Link>{' '}
          or manage your{' '}
          <Link href="/console/quality" className="text-accent font-semibold">
            Quality metrics
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
