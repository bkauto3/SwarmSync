'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { useAccount } from 'wagmi';

import { PaymentMethod, PaymentMethodSelector } from '@/components/payment/payment-method-selector';
import { X402Payment } from '@/components/payment/x402-payment';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ConnectWallet } from '@/components/wallet/connect-wallet';
import { API_BASE_URL } from '@/lib/api';

interface AgentWithPayments {
  id: string;
  name: string;
  description: string;
  paymentMethods?: PaymentMethod[];
  x402Price?: number | null;
  priceAmount?: number | null;
  basePriceCents?: number | null;
}

export default function AgentPurchasePage() {
  const params = useParams();
  const router = useRouter();
  const { address, isConnected } = useAccount();

  const slugParam = params?.slug;
  const slug = Array.isArray(slugParam) ? slugParam[0] : slugParam;

  const [agent, setAgent] = useState<AgentWithPayments | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [selectedMethod, setSelectedMethod] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function fetchAgent() {
      if (!slug) {
        return;
      }
      setLoading(true);
      try {
        const response = await fetch(`${API_BASE_URL}/agents/slug/${slug}`);
        if (!response.ok) {
          throw new Error('Failed to load agent');
        }
        const data = (await response.json()) as AgentWithPayments;
        if (!isMounted) return;
        setAgent(data);
        const methods = (data.paymentMethods ?? []) as PaymentMethod[];
        setPaymentMethods(methods);
        if (methods.length) {
          setSelectedMethod((current) => current || methods[0].type);
        }
      } catch (error) {
        console.error(error);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    fetchAgent();
    return () => {
      isMounted = false;
    };
  }, [slug]);

  useEffect(() => {
    if (!paymentMethods.length) {
      return;
    }
    if (!selectedMethod || !paymentMethods.some((method) => method.type === selectedMethod)) {
      setSelectedMethod(paymentMethods[0].type);
    }
  }, [paymentMethods, selectedMethod]);

  const x402Method = useMemo(
    () => paymentMethods.find((method) => method.type === 'x402'),
    [paymentMethods],
  );

  const handlePlatformPayment = () => {
    if (!slug) return;
    router.push(`/agents/${slug}/checkout`);
  };

  const handleX402Success = async (txHash: string) => {
    if (!agent || !address) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/x402/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId: agent.id,
          txHash,
          buyerAddress: address,
          amount:
            x402Method?.amount ?? agent.x402Price ?? agent.priceAmount ?? agent.basePriceCents ?? 0,
        }),
      });

      if (!response.ok) {
        throw new Error('Payment verification failed');
      }

      router.push(`/agents/${slug}/success?tx=${txHash}`);
    } catch (error) {
      console.error('Payment verification error:', error);
    }
  };

  const handleX402Error = (error: Error) => {
    console.error('x402 payment error:', error);
  };

  if (loading) {
    return <div className="p-8 text-center text-muted-foreground">Loading...</div>;
  }

  if (!agent) {
    return <div className="p-8 text-center text-muted-foreground">Agent not found.</div>;
  }

  const needsWalletConnection = selectedMethod === 'x402' && !isConnected;

  return (
    <div className="container mx-auto max-w-4xl py-12">
      <Card className="p-8">
        <div className="mb-8 space-y-2">
          <h1 className="text-3xl font-bold">{agent.name}</h1>
          <p className="text-muted-foreground">{agent.description}</p>
        </div>

        <PaymentMethodSelector
          methods={paymentMethods}
          selected={selectedMethod}
          onSelect={setSelectedMethod}
        />

        <div className="mt-8 space-y-6">
          {selectedMethod === 'platform' && (
            <Button onClick={handlePlatformPayment} className="w-full" size="lg">
              Continue to Checkout
            </Button>
          )}

          {selectedMethod === 'x402' && (
            <div className="space-y-4">
              {needsWalletConnection ? (
                <div className="text-center space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Connect your wallet to pay with crypto
                  </p>
                  <ConnectWallet />
                </div>
              ) : x402Method && x402Method.recipient ? (
                <X402Payment
                  recipient={x402Method.recipient}
                  amount={x402Method.amount ?? 0}
                  onSuccess={handleX402Success}
                  onError={handleX402Error}
                />
              ) : (
                <p className="text-sm text-muted-foreground">
                  This agent has not provided a crypto wallet address yet.
                </p>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
