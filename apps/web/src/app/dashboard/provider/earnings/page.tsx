"use client";

import { Button } from '@/components/ui/button';

// Mock data
const transactions: any[] = [];

export default function ProviderEarningsPage() {
  return (
    <div className="min-h-screen bg-black text-slate-50">
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-display text-white mb-2">Earnings History</h1>
          <p className="text-[var(--text-secondary)]">View all your transactions and earnings</p>
        </div>

        <div className="mb-6 flex gap-4">
          <input
            type="date"
            className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-white focus:border-[var(--accent-primary)] focus:outline-none"
            placeholder="Start date"
          />
          <input
            type="date"
            className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-white focus:border-[var(--accent-primary)] focus:outline-none"
            placeholder="End date"
          />
          <Button variant="outline">Filter</Button>
          <Button variant="outline">Export CSV</Button>
        </div>

        {transactions.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-12 text-center">
            <p className="text-lg text-[var(--text-secondary)]">No transactions yet</p>
            <p className="text-sm text-[var(--text-muted)] mt-2">
              Your earnings will appear here once your agents start getting hired
            </p>
          </div>
        ) : (
          <div className="rounded-2xl border border-white/10 bg-white/5 overflow-hidden">
            <table className="w-full">
              <thead className="border-b border-white/10">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-white">Date</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-white">Buyer</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-white">Agent</th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-white">Amount</th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-white">Fee</th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-white">Net</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-white">Status</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-6 py-4 text-[var(--text-secondary)]">{tx.date}</td>
                    <td className="px-6 py-4 text-white">{tx.buyer}</td>
                    <td className="px-6 py-4 text-white">{tx.agent}</td>
                    <td className="px-6 py-4 text-right text-white">${tx.amount}</td>
                    <td className="px-6 py-4 text-right text-[var(--text-muted)]">${tx.fee}</td>
                    <td className="px-6 py-4 text-right text-emerald-400 font-semibold">${tx.net}</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300">
                        {tx.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

