'use client';

import React from 'react';

interface Transaction {
  id: string;
  type: string;
  amount: number;
  currency: string;
  status: string;
  createdAt: string;
  rail?: 'platform' | 'x402';
  reference?: string;
  buyerAddress?: string;
  sellerAddress?: string;
  network?: string;
  metadata?: Record<string, unknown>;
  txHash?: string;
}

interface TransactionHistoryListProps {
  transactions: Transaction[];
}

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
});

const typeLabels: Record<string, string> = {
  A2A: 'Agent-to-Agent',
  H2A: 'Human-to-Agent',
  PAYOUT: 'Payout',
  REFUND: 'Refund',
  TOPUP: 'Top-up',
  CREDIT: 'Credit',
  DEBIT: 'Debit',
  X402: 'x402 Payment',
};

const formatAmount = (amount: number, currency: string) => {
  if (currency === 'USD') {
    return currencyFormatter.format(amount);
  }
  return `${amount.toFixed(2)} ${currency}`;
};

const truncateMiddle = (value: string, chars = 6) => {
  if (!value) {
    return '';
  }
  if (value.length <= chars * 2) {
    return value;
  }
  return `${value.slice(0, chars)}…${value.slice(-chars)}`;
};

export function TransactionHistoryList({ transactions }: TransactionHistoryListProps) {
  if (transactions.length === 0) {
    return (
      <div className="card p-8 text-center text-sm text-[var(--text-muted)]">
        No transactions yet. Execute agents or add funds to see transaction history.
      </div>
    );
  }

  return (
    <div className="card">
      <div className="border-b border-[var(--border-base)] px-6 py-5">
        <h2 className="text-sm font-display uppercase tracking-wide text-[var(--text-muted)]">
          All Transactions
        </h2>
      </div>
      <ul className="divide-y divide-outline/60">
        {transactions.map((transaction) => {
          const isCredit = ['CREDIT', 'TOPUP', 'REFUND'].includes(transaction.type);
          const typeLabel = typeLabels[transaction.type] || transaction.type;

          return (
            <li key={transaction.id} className="px-6 py-5 transition hover:bg-[var(--surface-raised)]">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-sm font-semibold text-white">{typeLabel}</div>
                    {transaction.rail === 'x402' && (
                      <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wide text-emerald-700">
                        x402
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">
                    {new Date(transaction.createdAt).toLocaleString()}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-3 text-xs text-[var(--text-muted)]">
                    {transaction.reference && <span>Ref {truncateMiddle(transaction.reference)}</span>}
                    {transaction.txHash && <span>Hash {truncateMiddle(transaction.txHash)}</span>}
                    {transaction.buyerAddress && <span>From {truncateMiddle(transaction.buyerAddress)}</span>}
                    {transaction.sellerAddress && <span>To {truncateMiddle(transaction.sellerAddress)}</span>}
                    {transaction.network && <span>Network {transaction.network}</span>}
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className={`text-sm font-semibold ${isCredit ? 'text-emerald-600' : 'text-white'}`}
                  >
                    {isCredit ? '+' : '-'}
                    {formatAmount(Math.abs(transaction.amount), transaction.currency)}
                  </div>
                  <div className="text-xs text-[var(--text-muted)] capitalize">{transaction.status.toLowerCase()}</div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

