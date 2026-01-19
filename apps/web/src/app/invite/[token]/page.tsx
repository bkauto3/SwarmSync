"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { useAuthStore } from '@/stores/auth-store';
import Link from 'next/link';

export default function InviteAcceptPage({ params }: { params: { token: string } }) {
  const router = useRouter();
  const { data: session, status: sessionStatus, update } = useSession();
  const authStore = useAuthStore();
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'expired' | 'used' | 'manual_login_required'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const acceptInvite = async () => {
      try {
        // Wait for session to load before checking authentication
        if (sessionStatus === 'loading') {
          console.log('[Invite] Session still loading, waiting...');
          return;
        }

        console.log('[Invite] Session status settle:', sessionStatus, 'Session data exists:', !!session);
        console.log('[Invite] Auth Store user:', !!authStore.user);

        // Check if user is authenticated (either OAuth or email/password)
        const isAuthenticated = !!session || !!authStore.user;

        if (!isAuthenticated) {
          console.log('[Invite] Initial check shows not authenticated. Current Status:', sessionStatus);
          await new Promise(resolve => setTimeout(resolve, 2000));

          // Re-check session status
          if (sessionStatus === 'unauthenticated' && !authStore.user) {
            console.log('[Invite] Still not authenticated after wait. STOPPING AUTO-REDIRECT.');
            // DO NOT REDIRECT AUTOMATICALLY. Show check UI instead.
            setStatus('manual_login_required');
            return;
          }
        }

        console.log('[Invite] User authenticated, accepting invite...');

        // Accept the invite
        const response = await fetch('/api/beta-invites/accept', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: params.token }),
        });

        const data = await response.json();

        if (!response.ok) {
          if (data.error === 'Invite expired') {
            setStatus('expired');
            setMessage('This invite link has expired.');
          } else if (data.error === 'Invite already used') {
            setStatus('used');
            setMessage('This invite link has already been used.');
          } else {
            setStatus('error');
            setMessage(data.error || 'Invalid invite link.');
          }
          return;
        }

        // Success! Update the session
        await update();
        setStatus('success');
        setMessage('Beta access granted! Redirecting...');

        // Redirect to agents page after 2 seconds
        setTimeout(() => {
          router.push('/agents/new');
        }, 2000);
      } catch (error) {
        console.error('Invite acceptance error:', error);
        setStatus('error');
        setMessage('Something went wrong. Please try again.');
      }
    };

    acceptInvite();
  }, [session, sessionStatus, authStore.user, params.token, router, update]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black text-slate-50 px-6">
      <div className="max-w-md w-full text-center">
        {status === 'loading' && (
          <>
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-[var(--accent-primary)] mx-auto mb-6"></div>
            <h1 className="text-2xl font-bold mb-2">Processing your invite...</h1>
            <p className="text-[var(--text-secondary)]">Please wait</p>
          </>
        )}

        {status === 'manual_login_required' && (
          <div className="p-8 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-base)]">
            <div className="text-4xl mb-4">🔑</div>
            <h1 className="text-2xl font-bold mb-4">Authentication Required</h1>
            <p className="text-[var(--text-secondary)] mb-6">
              To accept this invite, you need to be signed in.
            </p>
            <p className="text-sm text-yellow-500 mb-6 bg-yellow-500/10 p-2 rounded">
              Debug Status: {sessionStatus} (Session: {session ? 'Yes' : 'No'})
            </p>
            <button
              onClick={() => router.push(`/login?callbackUrl=${encodeURIComponent(window.location.pathname)}`)}
              className="w-full px-6 py-3 rounded-lg bg-[var(--accent-primary)] text-white font-semibold hover:bg-[var(--accent-primary)]/90 transition"
            >
              Sign In to Accept
            </button>
          </div>
        )}

        {status === 'success' && (
          <>
            <div className="text-6xl mb-6">✅</div>
            <h1 className="text-3xl font-bold text-emerald-400 mb-2">Welcome to SwarmSync!</h1>
            <p className="text-[var(--text-secondary)] mb-6">{message}</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="text-6xl mb-6">❌</div>
            <h1 className="text-3xl font-bold text-red-400 mb-2">Invalid Invite</h1>
            <p className="text-[var(--text-secondary)] mb-6">{message}</p>
            <Link
              href="/"
              className="inline-block px-6 py-3 rounded-lg bg-[var(--accent-primary)] text-white font-semibold hover:bg-[var(--accent-primary)]/90 transition"
            >
              Back to Home
            </Link>
          </>
        )}

        {status === 'expired' && (
          <>
            <div className="text-6xl mb-6">⏰</div>
            <h1 className="text-3xl font-bold text-orange-400 mb-2">Invite Expired</h1>
            <p className="text-[var(--text-secondary)] mb-6">{message}</p>
            <Link
              href="/beta-gate"
              className="inline-block px-6 py-3 rounded-lg bg-[var(--accent-primary)] text-white font-semibold hover:bg-[var(--accent-primary)]/90 transition"
            >
              Request New Invite
            </Link>
          </>
        )}

        {status === 'used' && (
          <>
            <div className="text-6xl mb-6">🔒</div>
            <h1 className="text-3xl font-bold text-orange-400 mb-2">Invite Already Used</h1>
            <p className="text-[var(--text-secondary)] mb-6">{message}</p>
            {session ? (
              <Link
                href="/agents/new"
                className="inline-block px-6 py-3 rounded-lg bg-[var(--accent-primary)] text-white font-semibold hover:bg-[var(--accent-primary)]/90 transition"
              >
                Continue to Dashboard
              </Link>
            ) : (
              <button
                onClick={() => router.push('/login')}
                className="inline-block px-6 py-3 rounded-lg bg-[var(--accent-primary)] text-white font-semibold hover:bg-[var(--accent-primary)]/90 transition"
              >
                Sign In
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
