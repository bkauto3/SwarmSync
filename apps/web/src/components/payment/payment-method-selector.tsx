'use client';

import { CreditCard, Coins } from 'lucide-react';

import { Card } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { cn } from '@/lib/utils';

export interface PaymentMethod {
  type: 'platform' | 'x402';
  currency: string;
  amount: number | null;
  description: string;
  recipient?: string;
  network?: string;
}

interface PaymentMethodSelectorProps {
  methods: PaymentMethod[];
  selected?: string;
  onSelect: (type: string) => void;
}

export function PaymentMethodSelector({ methods, selected, onSelect }: PaymentMethodSelectorProps) {
  if (!methods.length) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Select Payment Method</h3>
      <RadioGroup value={selected} onValueChange={onSelect} className="gap-4">
        {methods.map((method) => (
          <Card
            key={method.type}
            className={cn(
              'p-4 transition-all cursor-pointer',
              selected === method.type ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10' : 'hover:border-[var(--border-hover)] bg-[var(--surface-raised)]',
            )}
            onClick={() => onSelect(method.type)}
          >
            <div className="flex items-start gap-4">
              <RadioGroupItem value={method.type} id={method.type} className="mt-1" />
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-2">
                  {method.type === 'platform' ? <CreditCard className="h-5 w-5" /> : <Coins className="h-5 w-5" />}
                  <span className="font-semibold">
                    {method.type === 'platform' ? 'AgentMarket Balance' : 'Crypto Wallet (USDC)'}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{method.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-lg font-bold">
                    {method.amount !== null ? formatAmount(method.amount, method.currency) : 'Custom Pricing'}
                  </span>
                  {method.type === 'x402' && (
                    <span className="text-xs font-medium text-emerald-600">⚡ Instant Settlement</span>
                  )}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </RadioGroup>
    </div>
  );
}

function formatAmount(amount: number, currency: string) {
  if (currency === 'USD') {
    return `$${amount.toFixed(2)} ${currency}`;
  }
  return `${amount} ${currency}`;
}

