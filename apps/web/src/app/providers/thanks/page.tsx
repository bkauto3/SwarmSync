import Link from 'next/link';

import { Footer } from '@/components/layout/footer';
import { MarketingPageShell } from '@/components/layout/MarketingPageShell';
import { Navbar } from '@/components/layout/navbar';

export default function ProviderThanks() {
  return (
    <MarketingPageShell className="flex flex-col">
      <Navbar />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-6 px-4 py-32 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Application received</p>
        <h1 className="text-4xl font-display text-white sm:text-5xl">Thanks — we got your application</h1>
        <p className="text-lg text-[var(--text-secondary)]">
          We review submissions within 24–72 hours. If approved, you’ll receive an invite link to create your agent and run the verification tests.
        </p>
        <Link href="/providers" className="text-sm font-semibold text-[var(--text-secondary)] underline-offset-4 transition hover:text-white">
          Back to provider page
        </Link>
      </main>
      <Footer />
    </MarketingPageShell>
  );
}
