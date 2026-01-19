'use client';

import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/use-auth';
import { billingApi } from '@/lib/api';

export function TopUpCard() {
  const [amount, setAmount] = useState('250');
  const [errorMessage, setErrorMessage] = useState('');
  const { isAuthenticated } = useAuth();

  const mutation = useMutation({
    mutationFn: async () => {
      const amountCents = Math.floor(Number(amount) * 100);
      if (!amountCents || amountCents < 1000) {
        throw new Error('Minimum top-up is $10');
      }
      const origin = window.location.origin;
      return billingApi.createTopUpSession(amountCents, `${origin}/billing?status=topup-success`, `${origin}/billing?status=topup-cancel`);
    },
    onSuccess: (result) => {
      if (result.checkoutUrl) {
        window.location.href = result.checkoutUrl;
      }
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'Unable to start top-up. Please retry.';
      setErrorMessage(message);
    },
  });

  const handleTopUp = () => {
    if (!isAuthenticated) {
      window.location.href = '/login';
      return;
    }
    setErrorMessage('');
    mutation.mutate();
  };

  return (
    <div className="card space-y-4 p-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Credit top-up</p>
        <h3 className="text-2xl font-semibold text-white">Boost your wallet</h3>
        <p className="text-sm text-[var(--text-muted)]">
          Create a one-time checkout to add funds to your organization wallet.
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="topup-amount">Amount (USD)</Label>
        <Input
          id="topup-amount"
          type="number"
          min="10"
          step="25"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
      </div>
      {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}
      <Button
        className="w-full rounded-full"
        disabled={mutation.isPending}
        onClick={handleTopUp}
      >
        {mutation.isPending ? 'Redirecting…' : 'Add credits'}
      </Button>
    </div>
  );
}
