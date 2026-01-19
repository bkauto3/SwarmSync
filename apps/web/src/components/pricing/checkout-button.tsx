'use client';

import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import { billingApi } from '@/lib/api';

interface CheckoutButtonProps {
  planSlug: string;
  stripeLink: string | null;
  ctaLink: string;
  cta: string;
  popular?: boolean;
}

export function CheckoutButton({
  planSlug,
  stripeLink,
  ctaLink,
  cta,
  popular = false,
}: CheckoutButtonProps) {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const checkoutMutation = useMutation({
    mutationFn: async () => {
      const successUrl = `${window.location.origin}/register?status=success&plan=${planSlug}`;
      const cancelUrl = `${window.location.origin}/pricing?status=cancel`;

      // For free plans, just redirect to register
      if (planSlug === 'starter') {
        router.push(ctaLink);
        return { checkoutUrl: null };
      }

      // Use public checkout endpoint (works for both authenticated and unauthenticated users)
      if (isAuthenticated) {
        // If user is logged in, use authenticated checkout
        return billingApi.createCheckoutSession(planSlug, successUrl, cancelUrl);
      } else {
        // If user is not logged in, use public checkout
        return billingApi.createPublicCheckoutSession(planSlug, successUrl, cancelUrl);
      }
    },
    onSuccess: (result) => {
      if (result.checkoutUrl) {
        window.location.href = result.checkoutUrl;
      }
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'Unable to start checkout. Please try again.';
      setError(message);
      console.error('Checkout error:', error);
    },
  });

  const handleCheckout = () => {
    setError(null);
    checkoutMutation.mutate();
  };

  // If no Stripe link, just show the regular CTA
  if (!stripeLink) {
    return (
      <Button
        asChild
        className="w-full"
        variant={popular ? 'default' : 'outline'}
      >
        <a href={ctaLink}>{cta}</a>
      </Button>
    );
  }

  return (
    <div className="space-y-2">
      <Button
        variant="ghost"
        className="w-full chrome-cta justify-center"
        onClick={handleCheckout}
        disabled={checkoutMutation.isPending}
      >
        {checkoutMutation.isPending ? 'Processing...' : 'Checkout with Stripe'}
      </Button>
      {error && (
        <p className="text-xs text-center text-red-400">{error}</p>
      )}
      <p className="text-center text-xs text-[var(--text-muted)]">
        Secure payment via Stripe
      </p>
    </div>
  );
}

