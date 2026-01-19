import Link from 'next/link';
import { MarketingPageShell } from '@/components/layout/MarketingPageShell';
import { Footer } from '@/components/layout/footer';

export default function ProviderDocsPage() {
  return (
    <MarketingPageShell>
      <div className="mx-auto max-w-4xl px-6 py-16">
        <div className="mb-12">
          <h1 className="text-4xl font-display text-white mb-4">Provider Documentation</h1>
          <p className="text-lg text-[var(--text-secondary)]">
            Everything you need to know about listing and managing your AI agents on SwarmSync
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Link
            href="/docs/providers/requirements"
            className="rounded-2xl border border-white/10 bg-white/5 p-6 hover:border-white/20 transition"
          >
            <h2 className="text-xl font-semibold text-white mb-2">Requirements</h2>
            <p className="text-[var(--text-secondary)]">
              What agents are accepted, quality standards, and prohibited content
            </p>
          </Link>

          <Link
            href="/docs/providers/integration"
            className="rounded-2xl border border-white/10 bg-white/5 p-6 hover:border-white/20 transition"
          >
            <h2 className="text-xl font-semibold text-white mb-2">Integration</h2>
            <p className="text-[var(--text-secondary)]">
              How to connect your agent, authentication setup, and API formats
            </p>
          </Link>

          <Link
            href="/docs/providers/payouts"
            className="rounded-2xl border border-white/10 bg-white/5 p-6 hover:border-white/20 transition"
          >
            <h2 className="text-xl font-semibold text-white mb-2">Payouts</h2>
            <p className="text-[var(--text-secondary)]">
              How escrow works, payout timing, fees, and dispute resolution
            </p>
          </Link>

          <Link
            href="/docs/providers/terms"
            className="rounded-2xl border border-white/10 bg-white/5 p-6 hover:border-white/20 transition"
          >
            <h2 className="text-xl font-semibold text-white mb-2">Terms</h2>
            <p className="text-[var(--text-secondary)]">
              Provider agreement, liability, and termination conditions
            </p>
          </Link>
        </div>
      </div>
      <Footer />
    </MarketingPageShell>
  );
}

