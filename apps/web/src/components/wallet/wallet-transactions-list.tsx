'use client';

interface Transaction {
  id: string;
  type: string;
  amount: string;
  currency: string;
  status: string;
  createdAt: string;
  reference?: string;
}

interface WalletTransactionsListProps {
  transactions: Transaction[];
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://swarmsync-api.up.railway.app';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
});

export function WalletTransactionsList({ transactions }: WalletTransactionsListProps) {
  if (transactions.length === 0) {
    return (
      <div className="card p-8 text-center text-sm text-[var(--text-muted)]">
        No transactions yet. Add funds to get started.
      </div>
    );
  }

  return (
    <div className="card">
      <div className="border-b border-[var(--border-base)] px-6 py-5">
        <h2 className="text-sm font-display uppercase tracking-wide text-[var(--text-muted)]">
          Transaction History
        </h2>
      </div>
      <ul className="divide-y divide-outline/60">
        {transactions.map((transaction) => {
          const amount = Number.parseFloat(transaction.amount);
          const isCredit = transaction.type === 'CREDIT';
          return (
            <li key={transaction.id} className="px-6 py-5 transition hover:bg-[var(--surface-raised)]">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">
                    {isCredit ? 'Fund Added' : 'Payment'}
                  </div>
                  <div className="text-xs text-[var(--text-muted)]">
                    {new Date(transaction.createdAt).toLocaleDateString()}
                    {transaction.reference && ` • ${transaction.reference}`}
                  </div>
                </div>
                <div className="text-right">
                  <a
                    href={`${API_BASE}/ap2/transactions/${transaction.id}`}
                    target="_blank"
                    rel="noreferrer"
                    className={`block text-sm font-semibold underline decoration-ink/40 underline-offset-4 ${
                      isCredit ? 'text-emerald-600' : 'text-white'
                    }`}
                    title="View transaction details"
                  >
                    {isCredit ? '+' : '-'}
                    {currencyFormatter.format(Math.abs(amount))}
                  </a>
                  <div className="text-xs text-[var(--text-muted)]">{transaction.status}</div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

