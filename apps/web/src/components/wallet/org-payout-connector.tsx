'use client';

import { useState } from 'react';

import { useAuth } from '@/hooks/use-auth';
import { AUTH_TOKEN_KEY } from '@/lib/constants';

const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') as string | undefined) ??
  'https://swarmsync-api.up.railway.app';
const DEFAULT_ORG_SLUG = process.env.NEXT_PUBLIC_DEFAULT_ORG_SLUG ?? 'swarmsync';

export function OrgPayoutConnector() {
  const { user } = useAuth();
  const [status, setStatus] = useState<string | null>(null);
  const [link, setLink] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const token =
    typeof window !== 'undefined' ? window.localStorage.getItem(AUTH_TOKEN_KEY) : null;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const fetchStatus = async () => {
    setIsLoading(true);
    setStatus(null);
    setLink(null);
    try {
      const res = await fetch(`${API_BASE}/payouts/org/account-status/${DEFAULT_ORG_SLUG}`, {
        method: 'GET',
        headers,
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data?.message ?? 'Unable to fetch status');
      } else {
        setStatus(
          data.isReady
            ? 'Bank account connected and ready for payouts.'
            : data.isConnected
              ? 'Connected, finish onboarding to enable payouts.'
              : data.message ?? 'No bank account connected yet.',
        );
      }
    } catch (error) {
      setStatus('Unable to fetch status right now.');
    } finally {
      setIsLoading(false);
    }
  };

  const startOnboarding = async () => {
    if (!user?.email) {
      setStatus('Sign in first so we can use your email for Stripe onboarding.');
      return;
    }
    setIsLoading(true);
    setStatus(null);
    setLink(null);
    try {
      const res = await fetch(`${API_BASE}/payouts/org/setup`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ organizationSlug: DEFAULT_ORG_SLUG, email: user.email }),
      });
      const data = await res.json();
      if (!res.ok) {
        setStatus(data?.message ?? 'Unable to start onboarding');
      } else {
        setLink(data.onboardingUrl);
        setStatus('Onboarding link created. Complete the Stripe form to connect your bank.');
      }
    } catch (error) {
      setStatus('Unable to start onboarding right now.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="card space-y-3 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-white">Bank payouts</h3>
          <p className="text-xs text-[var(--text-muted)]">
            Connect the org wallet to a bank via Stripe to move funds out.
          </p>
        </div>
        <button
          className="rounded-lg bg-black px-3 py-2 text-xs font-semibold text-white hover:bg-black/90 disabled:opacity-50"
          onClick={startOnboarding}
          disabled={isLoading}
        >
          Connect bank
        </button>
      </div>
      <div className="flex items-center gap-3">
        <button
          className="text-xs font-semibold text-white underline decoration-ink/40 underline-offset-4 disabled:opacity-50"
          onClick={fetchStatus}
          disabled={isLoading}
        >
          Check status
        </button>
        {link && (
          <a
            href={link}
            className="text-xs font-semibold text-emerald-700 underline underline-offset-4"
            target="_blank"
            rel="noreferrer"
          >
            Open onboarding
          </a>
        )}
      </div>
      {status && <p className="text-xs text-white">{status}</p>}
      {!token && (
        <p className="text-[11px] text-amber-700">
          You need to be signed in for this to work (uses your session token for the API call).
        </p>
      )}
    </div>
  );
}
