'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface PayoutSettingsProps {
  agentId: string;
}

interface PayoutAccount {
  isOnboarded: boolean;
  isChargesEnabled?: boolean;
  isPayoutsEnabled?: boolean;
  country?: string;
  email?: string;
}

interface PayoutHistory {
  id: string;
  amount: number;
  currency: string;
  status: 'INITIATED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  createdAt: string;
  completedAt?: string;
  description?: string;
}

export function PayoutSettings({ agentId }: PayoutSettingsProps) {
  const [showSetup, setShowSetup] = useState(false);
  const [email, setEmail] = useState('');

  // Fetch account status
  const { data: account, isLoading: accountLoading } = useQuery<PayoutAccount>({
    queryKey: ['payouts', 'account-status', agentId],
    queryFn: async () => {
      const response = await fetch(`/api/payouts/account-status/${agentId}`);
      if (!response.ok) throw new Error('Failed to fetch account status');
      return response.json();
    },
  });

  // Fetch payout history
  const { data: history = [] } = useQuery<PayoutHistory[]>({
    queryKey: ['payouts', 'history', agentId],
    queryFn: async () => {
      const response = await fetch(`/api/payouts/history/${agentId}`);
      if (!response.ok) throw new Error('Failed to fetch history');
      return response.json();
    },
    enabled: account?.isOnboarded,
  });

  // Setup mutation
  const setupMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/payouts/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId,
          email,
          country: 'US',
          businessType: 'individual',
        }),
      });
      if (!response.ok) throw new Error('Setup failed');
      return response.json();
    },
    onSuccess: (data) => {
      // Redirect to Stripe onboarding
      window.location.href = data.onboardingUrl;
    },
  });

  if (accountLoading) {
    return (
      <Card className="border-white/70 bg-[var(--surface-raised)]">
        <CardContent className="p-6">
          <div className="h-12 w-full animate-pulse rounded-lg bg-white/10" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status Card */}
      {account?.isOnboarded ? (
        <Card className="border-emerald-200 bg-emerald-50">
          <CardContent className="flex items-center gap-4 p-6">
            <CheckCircle2 className="h-8 w-8 text-emerald-600" />
            <div>
              <p className="font-semibold text-emerald-900">Payout Account Connected</p>
              <p className="text-sm text-emerald-700">
                {account.email} • {account.country}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="flex items-center gap-4 p-6">
            <AlertCircle className="h-8 w-8 text-amber-600" />
            <div>
              <p className="font-semibold text-amber-900">No Payout Account</p>
              <p className="text-sm text-amber-700">
                Set up Stripe Connect to receive payouts for your services.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Setup Form */}
      {!account?.isOnboarded && !showSetup && (
        <Button onClick={() => setShowSetup(true)} className="w-full rounded-full">
          Connect Payout Account
        </Button>
      )}

      {!account?.isOnboarded && showSetup && (
        <Card className="border-white/70 bg-[var(--surface-raised)]">
          <CardHeader>
            <CardTitle className="font-display">Set Up Stripe Connect</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)]/50"
              />
            </div>
            <p className="text-xs text-[var(--text-muted)]">
              You&apos;ll be redirected to Stripe to complete your account setup. We accept business accounts
              from over 50 countries.
            </p>
            <div className="flex gap-3">
              <Button
                onClick={() => setupMutation.mutate()}
                disabled={!email || setupMutation.isPending}
                className="flex-1 rounded-full"
              >
                {setupMutation.isPending ? 'Redirecting...' : 'Continue to Stripe'}
              </Button>
              <Button
                variant="secondary"
                onClick={() => setShowSetup(false)}
                className="rounded-full"
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Payout History */}
      {account?.isOnboarded && (
        <Card className="border-white/70 bg-[var(--surface-raised)]">
          <CardHeader>
            <CardTitle className="font-display">Payout History</CardTitle>
          </CardHeader>
          <CardContent>
            {history.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)] italic">No payouts yet.</p>
            ) : (
              <div className="space-y-3">
                {history.map((payout) => (
                  <div key={payout.id} className="flex items-center justify-between rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        {payout.status === 'COMPLETED' && (
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                        )}
                        {payout.status === 'PROCESSING' && (
                          <Clock className="h-4 w-4 text-amber-600" />
                        )}
                        <p className="font-semibold text-white">
                          ${(payout.amount / 100).toFixed(2)} {payout.currency}
                        </p>
                      </div>
                      <p className="text-xs text-[var(--text-muted)] mt-1">
                        {new Date(payout.createdAt).toLocaleDateString()} • {payout.status}
                      </p>
                      {payout.description && (
                        <p className="text-xs text-[var(--text-muted)]">{payout.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
