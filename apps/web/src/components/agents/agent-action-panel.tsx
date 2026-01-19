'use client';

import { Scale, Heart } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useMarketplaceStore } from '@/stores/marketplace-store';

interface AgentActionPanelProps {
  agentSlug: string;
}

export function AgentActionPanel({ agentSlug }: AgentActionPanelProps) {
  const favorites = useMarketplaceStore((state) => state.favorites);
  const compare = useMarketplaceStore((state) => state.compare);
  const toggleFavorite = useMarketplaceStore((state) => state.toggleFavorite);
  const toggleCompare = useMarketplaceStore((state) => state.toggleCompare);

  const isFavorite = favorites.includes(agentSlug);
  const inCompare = compare.includes(agentSlug);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button
        variant="outline"
        className="rounded-full"
        onClick={() => toggleFavorite(agentSlug)}
      >
        <Heart className="mr-2 h-4 w-4" />
        {isFavorite ? 'Favorited' : 'Favorite'}
      </Button>
      <Button
        variant="outline"
        className="rounded-full"
        onClick={() => toggleCompare(agentSlug)}
      >
        <Scale className="mr-2 h-4 w-4" />
        {inCompare ? 'In compare' : 'Compare'}
      </Button>
    </div>
  );
}
