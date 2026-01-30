'use client';

import { CreditCard } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

import { PayoutSettings } from './payout-settings';

interface BillingDashboardProps {
  userId: string;
  agentId?: string;
}

export function BillingDashboard({ agentId }: BillingDashboardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'invoices' | 'payouts'>('overview');

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="space-y-2">
        <h1 className="text-4xl font-display text-white">Billing & Payments</h1>
        <p className="text-sm text-[var(--text-muted)]">Manage subscriptions, invoices, and payout settings</p>
      </header>

      {/* Tab Navigation */}
      <div className="flex gap-3 border-b border-[var(--border-base)]">
        {(['overview', 'invoices', 'payouts'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-3 text-sm font-semibold uppercase tracking-wide transition ${
              activeTab === tab
                ? 'border-b-2 border-[var(--border-base)] text-white'
                : 'text-[var(--text-muted)] hover:text-white'
            }`}
          >
            {tab === 'overview' && 'Subscription & Credits'}
            {tab === 'invoices' && 'Invoices'}
            {tab === 'payouts' && 'Payouts'}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'overview' && <BillingOverview />}
      {activeTab === 'invoices' && <InvoicesTable />}
      {activeTab === 'payouts' && agentId && <PayoutSettings agentId={agentId} />}

      {!agentId && activeTab === 'payouts' && (
        <Card className="border-[var(--border-base)] bg-[var(--surface-raised)]">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-[var(--text-muted)]">No agent associated with this account.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function BillingOverview() {
  return (
    <div className="space-y-6">
      {/* Current Plan */}
      <Card className="border-white/70 bg-[var(--surface-raised)]">
        <CardHeader>
          <CardTitle className="font-display">Current Plan</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-6 md:grid-cols-2">
          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Plan Tier</p>
              <p className="mt-1 text-2xl font-display text-white">Growth</p>
              <p className="text-sm text-[var(--text-muted)]">$79/month</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Renews</p>
              <p className="mt-1 text-lg font-semibold text-white">Dec 16, 2025</p>
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Monthly Credits</p>
              <p className="mt-1 text-2xl font-display text-white">7,500</p>
              <p className="text-sm text-[var(--text-muted)]">$750 credit value</p>
            </div>
            <Button variant="secondary" className="w-full rounded-full">
              Manage Subscription
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Credit Usage */}
      <Card className="border-white/70 bg-[var(--surface-raised)]">
        <CardHeader>
          <CardTitle className="font-display">Credit Usage (This Month)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-white">Used: 2,430 / 7,500</span>
              <span className="text-xs text-[var(--text-muted)]">32% used</span>
            </div>
            <div className="h-3 w-full rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-brass to-accentTone"
                style={{ width: '32%' }}
              />
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-[var(--surface-raised)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Lead Generation</p>
              <p className="mt-2 text-lg font-semibold text-white">1,500 credits</p>
            </div>
            <div className="rounded-lg bg-[var(--surface-raised)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Quality Checks</p>
              <p className="mt-2 text-lg font-semibold text-white">1,240 credits</p>
            </div>
            <div className="rounded-lg bg-[var(--surface-raised)] p-4">
              <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Other</p>
              <p className="mt-2 text-lg font-semibold text-white">500 credits</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Payment Method */}
      <Card className="border-white/70 bg-[var(--surface-raised)]">
        <CardHeader>
          <CardTitle className="font-display">Payment Method</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4">
            <CreditCard className="h-8 w-8 text-[var(--text-muted)]" />
            <div className="flex-1">
              <p className="font-semibold text-white">Visa •••• 4242</p>
              <p className="text-xs text-[var(--text-muted)]">Expires 12/2026</p>
            </div>
            <Button variant="ghost" size="sm">
              Update
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function InvoicesTable() {
  const invoices = [
    {
      id: 'INV-2025-001',
      date: '2025-11-16',
      amount: 79.0,
      status: 'Paid' as const,
    },
    {
      id: 'INV-2025-002',
      date: '2025-10-16',
      amount: 79.0,
      status: 'Paid' as const,
    },
    {
      id: 'INV-2025-003',
      date: '2025-09-16',
      amount: 79.0,
      status: 'Paid' as const,
    },
  ];

  return (
    <Card className="border-white/70 bg-[var(--surface-raised)]">
      <CardHeader>
        <CardTitle className="font-display">Invoice History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {invoices.map((invoice) => (
            <div
              key={invoice.id}
              className="flex items-center justify-between rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4"
            >
              <div className="flex-1">
                <p className="font-semibold text-white">{invoice.id}</p>
                <p className="text-xs text-[var(--text-muted)]">{new Date(invoice.date).toLocaleDateString()}</p>
              </div>
              <p className="font-semibold text-white">${invoice.amount.toFixed(2)}</p>
              <span className="ml-4 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                {invoice.status}
              </span>
              <Button variant="ghost" size="sm" className="ml-2">
                Download
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
