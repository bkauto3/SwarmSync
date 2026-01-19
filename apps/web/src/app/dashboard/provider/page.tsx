"use client";

import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useEffect, useState, Suspense } from 'react';

import { Button } from '@/components/ui/button';

// Mock data - in production, this would come from an API
const mockAgents = [
  {
    id: '1',
    name: 'DataCleanerBot',
    status: 'Under Review',
    submittedAt: '2 hours ago',
  },
];

function ProviderDashboardContent() {
  const searchParams = useSearchParams();
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    if (searchParams.get('success') === 'true') {
      setShowSuccess(true);
      // Clear the success param from URL
      window.history.replaceState({}, '', '/dashboard/provider');
      // Hide success message after 5 seconds
      setTimeout(() => setShowSuccess(false), 5000);
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-black text-slate-50">
      <div className="mx-auto max-w-7xl px-6 py-12">
        {showSuccess && (
          <div className="mb-6 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-emerald-300">
            Your agent has been submitted for review! We'll get back to you within 48 hours.
          </div>
        )}

        <div className="mb-8">
          <h1 className="text-3xl font-display text-white mb-2">Provider Dashboard</h1>
          <p className="text-[var(--text-secondary)]">
            Manage your agents, track earnings, and configure payouts
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3 mb-8">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <p className="text-sm text-[var(--text-muted)] mb-2">Total Earnings</p>
            <p className="text-3xl font-bold text-white">$0.00</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">No transactions yet</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <p className="text-sm text-[var(--text-muted)] mb-2">Active Agents</p>
            <p className="text-3xl font-bold text-white">{mockAgents.length}</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">In review</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <p className="text-sm text-[var(--text-muted)] mb-2">Available Balance</p>
            <p className="text-3xl font-bold text-white">$0.00</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">Ready to withdraw</p>
          </div>
        </div>

        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-display text-white">Your Agents</h2>
            <Link href="/dashboard/provider/agents/new">
              <Button>Add Agent</Button>
            </Link>
          </div>

          <div className="space-y-4">
            {mockAgents.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center">
                <p className="text-[var(--text-secondary)] mb-4">You haven't submitted any agents yet.</p>
                <Link href="/dashboard/provider/agents/new">
                  <Button>Create Your First Agent</Button>
                </Link>
              </div>
            ) : (
              mockAgents.map((agent) => (
                <div
                  key={agent.id}
                  className="rounded-2xl border border-white/10 bg-white/5 p-6 flex items-center justify-between"
                >
                  <div>
                    <h3 className="text-xl font-semibold text-white mb-1">{agent.name}</h3>
                    <div className="flex items-center gap-4">
                      <span className="inline-flex items-center rounded-full border border-yellow-500/40 bg-yellow-500/10 px-3 py-1 text-xs font-semibold text-yellow-300">
                        {agent.status}
                      </span>
                      <span className="text-sm text-[var(--text-muted)]">Submitted {agent.submittedAt}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Link href={`/dashboard/provider/agents/${agent.id}`}>
                      <Button variant="outline" size="sm">View</Button>
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Link href="/dashboard/provider/earnings" className="rounded-2xl border border-white/10 bg-white/5 p-6 hover:border-white/20 transition">
            <h3 className="text-lg font-semibold text-white mb-2">View Earnings</h3>
            <p className="text-sm text-[var(--text-secondary)]">See your transaction history and earnings breakdown</p>
          </Link>
          <Link href="/dashboard/provider/payouts" className="rounded-2xl border border-white/10 bg-white/5 p-6 hover:border-white/20 transition">
            <h3 className="text-lg font-semibold text-white mb-2">Payout Settings</h3>
            <p className="text-sm text-[var(--text-secondary)]">Configure your payment method and withdrawal preferences</p>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ProviderDashboardPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-black text-slate-50 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    }>
      <ProviderDashboardContent />
    </Suspense>
  );
}

