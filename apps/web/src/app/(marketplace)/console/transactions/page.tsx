import { TransactionHistoryList } from '@/components/transactions/transaction-history-list';
import { getAgentMarketClient } from '@/lib/server-client';

interface TransactionsPageProps {
  searchParams?: {
    agentId?: string;
  };
}

export default async function TransactionsPage({ searchParams }: TransactionsPageProps) {
  const client = getAgentMarketClient();

  let agentId = searchParams?.agentId ?? null;
  let agentName = '';

  if (agentId) {
    const agent = await client.getAgent(agentId).catch(() => null);
    if (agent) {
      agentName = agent.name;
    }
  }

  if (!agentId) {
    const agents = await client.listAgents();
    if (agents.length > 0) {
      agentId = agents[0].id;
      agentName = agents[0].name;
    }
  }

  const history = agentId ? await client.getAgentPaymentHistory(agentId) : [];

  const transactions = history.map((entry) => ({
    id: entry.id,
    type: entry.type,
    amount: entry.amount,
    currency: entry.currency,
    status: entry.status,
    createdAt: entry.createdAt,
    rail: entry.rail,
    reference: entry.reference ?? undefined,
    buyerAddress: entry.buyerAddress ?? undefined,
    sellerAddress: entry.sellerAddress ?? undefined,
    network: entry.network ?? undefined,
    txHash: entry.txHash ?? undefined,
  }));

  return (
    <div className="space-y-8">
      <header className="glass-card p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Transactions</p>
        <h1 className="mt-2 text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Payment History</h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--text-muted)]">
          View platform and x402 payments for your agents.{' '}
          {agentName ? `Currently showing ${agentName}.` : ''}
        </p>
      </header>

      <TransactionHistoryList transactions={transactions} />
    </div>
  );
}
