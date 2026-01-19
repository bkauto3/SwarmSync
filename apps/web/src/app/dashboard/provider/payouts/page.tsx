"use client";

import { useState } from 'react';
import { Button } from '@/components/ui/button';

export default function ProviderPayoutsPage() {
  const [isConnected, setIsConnected] = useState(false);
  const [balance] = useState(0);

  return (
    <div className="min-h-screen bg-black text-slate-50">
      <div className="mx-auto max-w-4xl px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-display text-white mb-2">Payout Settings</h1>
          <p className="text-[var(--text-secondary)]">Configure how you receive payments</p>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Stripe Connect</h2>
            {!isConnected ? (
              <div>
                <p className="text-[var(--text-secondary)] mb-4">
                  Connect your Stripe account to receive payouts. We use Stripe Connect for secure payment processing.
                </p>
                <Button onClick={() => setIsConnected(true)}>
                  Connect Stripe
                </Button>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="h-10 w-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <span className="text-emerald-400">✓</span>
                  </div>
                  <div>
                    <p className="text-white font-semibold">Connected</p>
                    <p className="text-sm text-[var(--text-muted)]">Stripe account linked</p>
                  </div>
                </div>
                <Button variant="outline" onClick={() => setIsConnected(false)}>
                  Disconnect
                </Button>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Current Balance</h2>
            <p className="text-4xl font-bold text-white mb-2">${balance.toFixed(2)}</p>
            <p className="text-sm text-[var(--text-muted)] mb-4">Available for withdrawal</p>
            <Button disabled={balance === 0 || !isConnected}>
              Withdraw Funds
            </Button>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Withdrawal History</h2>
            <div className="text-center py-8 text-[var(--text-muted)]">
              <p>No withdrawals yet</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

