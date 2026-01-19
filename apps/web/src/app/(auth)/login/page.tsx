import Link from 'next/link';
import Image from 'next/image';

import { LoginForm } from '@/components/auth/login-form';

import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Sign In',
  robots: {
    index: false,
    follow: false,
  },
};

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col bg-surface text-text">
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

      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="glass-card w-full max-w-md rounded-[3rem] border border-border bg-surface p-10 shadow-2xl">
          <div className="text-center">
            <p className="heading-label">Welcome back</p>
            <h1 className="mt-3 text-3xl font-display text-text">Sign in to Swarm Sync</h1>
            <p className="mt-2 text-sm text-text2">
              Access your dashboard, credentials, and organization analytics.
            </p>
          </div>
          <div className="mt-8">
            <LoginForm />
          </div>
          <p className="mt-6 text-center text-sm text-muted">
            Don&apos;t have an account?{' '}
            <Link href="/register" className="font-semibold text-accent hover:text-accent-strong">
              Create one
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
