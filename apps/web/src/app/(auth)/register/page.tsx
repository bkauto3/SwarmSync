import Link from 'next/link';
import Image from 'next/image';

import { RegisterForm } from '@/components/auth/register-form';

import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Create Account',
  robots: {
    index: false,
    follow: false,
  },
};

const planNames: Record<string, string> = {
  'starter': 'Free',
  'plus': 'Starter',
  'growth': 'Pro',
  'scale': 'Business',
};

export default function RegisterPage({
  searchParams,
}: {
  searchParams: { plan?: string };
}) {
  const selectedPlan = searchParams.plan ? planNames[searchParams.plan.toLowerCase()] : null;

  return (
    <div className="flex min-h-screen flex-col bg-black text-slate-50">
      {/* Isolated Header for Auth Pages to prevent bundle bleed */}
      <header className="sticky top-0 z-40 border-b border-[var(--border-base)] bg-[var(--surface-base)]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <Link href="/" className="flex items-center gap-4 group flex-shrink-0" aria-label="Swarm Sync homepage">
            <Image
              src="/logos/swarm-sync-purple.png"
              alt="Swarm Sync logo"
              width={180}
              height={60}
              priority
              className="h-10 w-auto md:h-11 transition-transform duration-300 group-hover:scale-105"
            />
          </Link>
        </div>
      </header>

      <div className="flex flex-1 items-center justify-center px-4 py-16">
        <div className="w-full max-w-md rounded-[3rem] border border-white/10 bg-white/5 p-10 shadow-brand-panel">
          <div className="text-center">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Get started</p>
            <h1 className="mt-3 text-3xl font-display text-white">Create your org</h1>
            {selectedPlan && (
              <div className="mt-4 rounded-xl bg-white/10 border border-white/20 px-4 py-2">
                <p className="text-sm font-medium text-slate-300">
                  Selected Plan: <span className="font-semibold text-white">{selectedPlan}</span>
                </p>
              </div>
            )}
            <p className="mt-2 text-sm text-slate-400">
              Provision wallets, invite operators, and onboard agents in minutes.
            </p>
          </div>
          <div className="mt-8">
            <RegisterForm selectedPlan={searchParams.plan} />
          </div>
          <p className="mt-6 text-center text-sm text-slate-400">
            Already have an account?{' '}
            <Link href="/login" className="font-semibold text-slate-300 hover:text-white">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
