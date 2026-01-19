'use client';

import { AgentFilters } from '@/components/agents/agent-filters';
import { AgentGrid } from '@/components/agents/agent-grid';
import { MarketplaceHeader } from '@/components/agents/marketplace-header';
import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { useAgentMarketplace } from '@/hooks/use-agent-marketplace';

export default function MarketplaceAgentsPage() {
  const { state, actions, data } = useAgentMarketplace();

  if (state.isError && state.error) {
    console.error('Failed to load agents:', state.error);
  }

  return (
    <div className="flex min-h-screen flex-col bg-black text-slate-50">
      <Navbar />
      <div className="flex-1 px-4 py-12">
        <div className="mx-auto max-w-6xl space-y-10">
          <MarketplaceHeader
            showMyAgents={state.showMyAgents}
            onToggleMyAgents={() => actions.setShowMyAgents(!state.showMyAgents)}
            onRefresh={() => actions.refetch()}
            search={state.search}
            onSearchChange={actions.setSearch}
            hasUser={!!state.user}
          />

          <AgentFilters
            category={state.category}
            capability={state.capability}
            verifiedOnly={state.verifiedOnly}
            onCategoryChange={actions.setCategory}
            onCapabilityChange={actions.setCapability}
            onVerifiedToggle={actions.setVerifiedOnly}
            sortBy={state.sortBy}
            onSortChange={actions.setSortBy}
            minRating={state.minRating}
            onMinRatingChange={actions.setMinRating}
            priceRange={state.priceRange}
            onPriceRangeChange={actions.setPriceRange}
          />

          <AgentGrid
            agents={data.agents}
            isLoading={state.isLoading}
            isError={state.isError}
          />
        </div>
      </div>
      <Footer />
    </div>
  );
}
