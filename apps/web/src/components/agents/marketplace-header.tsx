import Link from 'next/link';
import { AgentSearch } from '@/components/agents/agent-search';
import { Button } from '@/components/ui/button';

interface MarketplaceHeaderProps {
    showMyAgents: boolean;
    onToggleMyAgents: () => void;
    onRefresh: () => void;
    search: string;
    onSearchChange: (value: string) => void;
    hasUser: boolean;
}

export function MarketplaceHeader({
    showMyAgents,
    onToggleMyAgents,
    onRefresh,
    search,
    onSearchChange,
    hasUser,
}: MarketplaceHeaderProps) {
    return (
        <header className="space-y-6 rounded-[3rem] border border-white/10 bg-white/5 p-8 shadow-brand-panel">
            <p className="text-sm uppercase tracking-[0.3em] text-slate-400">Marketplace</p>
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                    <h1 className="text-4xl font-display text-white">
                        {showMyAgents ? 'Your Agents' : 'Discover AI agents'}
                    </h1>
                    <p className="mt-3 max-w-2xl text-base text-slate-400">
                        {showMyAgents
                            ? 'Manage and monitor your deployed agents'
                            : 'Search thousands of certified operators, orchestrators, and specialists. Connect wallets, set approvals, and let your automations shop for the skills they need.'}
                    </p>
                </div>
                <div className="flex gap-3">
                    {hasUser && (
                        <Button
                            variant={showMyAgents ? 'default' : 'outline'}
                            onClick={onToggleMyAgents}
                        >
                            {showMyAgents ? 'Show All Agents' : 'Show My Agents'}
                        </Button>
                    )}
                    <Button variant="secondary" onClick={onRefresh}>
                        Refresh
                    </Button>
                    {hasUser && (
                        <Button asChild variant="default">
                            <Link href="/agents/new">+ Create Agent</Link>
                        </Button>
                    )}
                </div>
            </div>
            <AgentSearch value={search} onChange={onSearchChange} />
        </header>
    );
}
