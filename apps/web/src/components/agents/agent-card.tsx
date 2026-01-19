'use client';

import { ArrowUpRight, ShieldCheck, Star, Heart, Scale } from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { useMarketplaceStore } from '@/stores/marketplace-store';

import type { Agent } from '@agent-market/sdk';

interface AgentCardProps {
  agent: Agent;
}

const calculateRating = (trustScore: number, successCount: number, failureCount: number) => {
  // Calculate rating from success rate and trust score
  const totalRuns = successCount + failureCount;
  if (totalRuns === 0) {
    // No signal yet – default to perfect rating until data arrives
    return 5.0;
  }
  
  const successRate = successCount / totalRuns;
  const safeTrust = Number.isFinite(trustScore) ? trustScore : 0;
  // Combine success rate (0-1) with trust score (0-100)
  // Success rate contributes 70%, trust score contributes 30%
  const combinedScore = (successRate * 0.7 + (safeTrust / 100) * 0.3) * 5;
  return Math.max(1.0, Math.min(5.0, +combinedScore.toFixed(1)));
};

const priceFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

export function AgentCard({ agent }: AgentCardProps) {
  const favorites = useMarketplaceStore((state) => state.favorites);
  const compareList = useMarketplaceStore((state) => state.compare);
  const toggleFavorite = useMarketplaceStore((state) => state.toggleFavorite);
  const toggleCompare = useMarketplaceStore((state) => state.toggleCompare);

  const rating = calculateRating(agent.trustScore, agent.successCount, agent.failureCount);
  const categories = agent.categories.length ? agent.categories : ['Generalist'];
  const priceLabel =
    typeof agent.basePriceCents === 'number'
      ? `${priceFormatter.format(agent.basePriceCents / 100)}+`
      : 'Custom pricing';

  return (
    <Card className="h-full rounded-[2.5rem] border-[var(--border-base)] bg-[var(--surface-raised)] shadow-brand-panel transition hover:-translate-y-1 hover:shadow-2xl">
      <CardContent className="flex h-full flex-col gap-4 p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.4em] text-[var(--text-muted)]">
              {categories[0]}
            </p>
            <h3 className="mt-1 text-2xl font-semibold text-white">{agent.name}</h3>
          </div>
          <div className="flex flex-col items-end gap-2 text-xs">
            <Badge variant="accent" className="uppercase tracking-wide">
              {agent.pricingModel}
            </Badge>
            {agent.verificationStatus === 'VERIFIED' && (
              <Badge variant="outline" className="inline-flex items-center gap-1 text-emerald-600">
                <ShieldCheck className="h-3 w-3" />
                Verified
              </Badge>
            )}
            {agent.badges && agent.badges.length > 0 && (
              <div className="flex flex-wrap gap-1 justify-end">
                {agent.badges.map((badge) => {
                  let variant: 'default' | 'outline' | 'accent' = 'default';
                  if (badge.includes('Security Passed') || badge.includes('Latency A') || badge.includes('Reasoning A')) {
                    variant = 'default';
                  } else if (badge.includes('Failed') || badge.includes('Latency C') || badge.includes('Reasoning C')) {
                    variant = 'outline';
                  } else {
                    variant = 'accent';
                  }
                  
                  return (
                    <Badge key={badge} variant={variant} className="text-[0.65rem]">
                      {badge}
                    </Badge>
                  );
                })}
              </div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => toggleFavorite(agent.slug)}
                className={cn(
                  'rounded-full border border-transparent p-2 text-[var(--text-muted)] transition hover:text-red-400',
                  favorites.includes(agent.slug) && 'text-red-400',
                )}
                aria-label="Toggle favorite"
              >
                <Heart className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => toggleCompare(agent.slug)}
                className={cn(
                  'rounded-full border border-transparent p-2 text-[var(--text-muted)] transition hover:text-white',
                  compareList.includes(agent.slug) && 'text-white',
                )}
                aria-label="Toggle compare"
              >
                <Scale className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        <p className="text-sm text-[var(--text-muted)] line-clamp-3">{agent.description}</p>

        <div className="flex flex-wrap gap-2">
          {agent.tags.slice(0, 4).map((tag) => (
            <Badge key={tag} variant="outline" className="text-[0.7rem] border-[var(--border-base)] text-slate-300">
              {formatTag(tag)}
            </Badge>
          ))}
        </div>

        <div className="mt-auto space-y-4 text-sm text-[var(--text-muted)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1 font-semibold text-white">
              <Star className="h-4 w-4 fill-slate-400 text-[var(--text-muted)]" />
              {rating}
              <span className="text-xs text-[var(--text-muted)]">
                ({agent.successCount.toLocaleString()} runs)
              </span>
            </div>
            <div className="text-xs uppercase tracking-wide text-white">{priceLabel}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/agents/${agent.slug}`}
              className={cn(
                'inline-flex flex-1 items-center justify-center gap-2 rounded-full border border-[var(--border-base)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-white/10 hover:text-white',
              )}
            >
              View profile
              <ArrowUpRight className="h-4 w-4" />
            </Link>
            <Button
              asChild
              variant="secondary"
              className="flex-1 rounded-full text-xs font-semibold uppercase tracking-wide"
            >
              <Link href={`/agents/${agent.slug}#request-service-panel`}>
                Request service
              </Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function formatTag(tag: string) {
  return tag
    .split(/[-_]/)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');
}
