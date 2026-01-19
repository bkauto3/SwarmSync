import { TopUpCard } from '@/components/billing/top-up-card';
import { OrgPayoutConnector } from '@/components/wallet/org-payout-connector';
import { WalletBalanceCard } from '@/components/wallet/wallet-balance-card';
import { WalletTransactionsList } from '@/components/wallet/wallet-transactions-list';

export const dynamic = "force-dynamic";

interface Transaction {
  id: string;
  type: string;
  amount: string;
  currency: string;
  status: string;
  createdAt: string;
  reference?: string;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://swarmsync-api.up.railway.app';
const DEFAULT_ORG_SLUG = process.env.NEXT_PUBLIC_DEFAULT_ORG_SLUG ?? 'swarmsync';

async function fetchOrgWallet() {
  try {
    const res = await fetch(`${API_BASE}/wallets/org/${DEFAULT_ORG_SLUG}`, {
      cache: 'no-store',
    });
    if (!res.ok) {
      return null;
    }
    return res.json();
  } catch (error) {
    console.error('Failed to fetch org wallet', error);
    return null;
  }
}

export default async function WalletPage() {
  // Note: In a real implementation, you'd get the user ID from the auth session
  // and fetch wallet data. For now, this shows the UI structure.
  // The wallet will be created automatically when funds are added via TopUpCard.
  const wallet = null;
  const orgWallet = await fetchOrgWallet();
  const transactions: Transaction[] = [];

  return (
    <div className="space-y-8">
      <header className="glass-card p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Wallet</p>
        <h1 className="mt-2 text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Funds & Transactions</h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--text-muted)]">
          Manage your wallet balance, add funds via Stripe, and view transaction history.
          Your organization wallet is shown below so you can see the balance the platform collects.
        </p>
      </header>

      <section className="space-y-8">
        <div className="grid gap-8 lg:grid-cols-2">
          <WalletBalanceCard wallet={wallet} />
          <TopUpCard />
        </div>
        {orgWallet && (
          <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-white/[0.03] to-white/[0.01] p-6">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Organization Wallet</p>
                <p className="mt-1 text-2xl font-display text-white">{orgWallet.orgSlug || DEFAULT_ORG_SLUG}</p>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Total Collected</p>
                <p className="mt-2 text-xl font-display text-white">
                  ${Number(orgWallet.balance || 0).toFixed(2)}
                </p>
              </div>
              <div className="rounded-xl bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Payout Available</p>
                <p className="mt-2 text-xl font-display text-white">
                  ${Number(orgWallet.availableForPayout || 0).toFixed(2)}
                </p>
              </div>
            </div>
            <div className="mt-6">
              <OrgPayoutConnector />
            </div>
          </div>
        )}
      </section>

      <section className="glass-card p-8">
        <h2 className="mb-6 text-xl font-display text-[var(--text-primary)]">Recent Transactions</h2>
        <WalletTransactionsList transactions={transactions} />
      </section>
    </div>
  );
}
