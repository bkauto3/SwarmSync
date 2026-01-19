'use client';

import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';

const CATEGORY_OPTIONS = ['orchestration', 'marketing', 'support', 'security', 'analysis'];

const CAPABILITY_OPTIONS = [
  'lead_generation',
  'workflow_orchestration',
  'research',
  'support',
  'qa',
  'security',
];

const SORT_OPTIONS = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'rating', label: 'Rating (Highest)' },
  { value: 'price_low', label: 'Price (Low to High)' },
  { value: 'price_high', label: 'Price (High to Low)' },
  { value: 'newest', label: 'Newest' },
  { value: 'popular', label: 'Most Hired' },
];

interface AgentFiltersProps {
  category: string;
  capability: string;
  verifiedOnly: boolean;
  onCategoryChange: (value: string) => void;
  onCapabilityChange: (value: string) => void;
  onVerifiedToggle: (value: boolean) => void;
  sortBy?: string;
  onSortChange?: (value: string) => void;
  minRating?: number;
  onMinRatingChange?: (value: number) => void;
  priceRange?: [number, number];
  onPriceRangeChange?: (value: [number, number]) => void;
}

export function AgentFilters({
  category,
  capability,
  verifiedOnly,
  onCategoryChange,
  onCapabilityChange,
  onVerifiedToggle,
  sortBy = 'relevance',
  onSortChange,
  minRating = 0,
  onMinRatingChange,
  priceRange = [0, 1000],
  onPriceRangeChange,
}: AgentFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const activeLabel = useMemo(() => {
    if (!category) return 'All categories';
    return category.charAt(0).toUpperCase() + category.slice(1);
  }, [category]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-[var(--border-base)] bg-[var(--surface-raised)] p-4 shadow-brand-panel">
        <Select value={category || 'all'} onValueChange={(value) => onCategoryChange(value === 'all' ? '' : value)}>
          <SelectTrigger className="w-[220px] rounded-full bg-white text-black font-semibold">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            {CATEGORY_OPTIONS.map((option) => (
              <SelectItem key={option} value={option}>
                {option.charAt(0).toUpperCase() + option.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {onSortChange && (
          <Select value={sortBy} onValueChange={onSortChange}>
            <SelectTrigger className="w-[200px] rounded-full bg-white/10 text-white font-semibold border-white/20">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        <div className="flex flex-wrap gap-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-[0.7rem] uppercase tracking-wide">
              Capabilities
            </span>
            <div className="flex flex-wrap gap-2">
              {CAPABILITY_OPTIONS.map((option) => {
                const isActive = capability === option;
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => onCapabilityChange(isActive ? '' : option)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onCapabilityChange(isActive ? '' : option);
                      }
                    }}
                    className={`rounded-full px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-wide transition focus:outline-none focus:ring-2 focus:ring-brass focus:ring-offset-2 ${isActive
                        ? 'bg-foreground text-background'
                        : 'border border-border text-muted-foreground hover:text-foreground'
                      }`}
                    aria-pressed={isActive}
                    aria-label={`Filter by ${option.replace(/_/g, ' ')}`}
                  >
                    {option.replace(/_/g, ' ')}
                  </button>
                );
              })}
            </div>
          </div>
          <button
            type="button"
            onClick={() => onVerifiedToggle(!verifiedOnly)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onVerifiedToggle(!verifiedOnly);
              }
            }}
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-wide transition focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:ring-offset-2 ${verifiedOnly
                ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]'
                : 'border-[var(--border-base)] text-[var(--text-muted)] hover:text-[var(--text-primary)]'
              }`}
            aria-pressed={verifiedOnly}
            aria-label="Show only verified agents"
          >
            <span className="h-2 w-2 rounded-full bg-current" aria-hidden="true" />
            Verified agents only
          </button>
          <Badge variant="outline">{activeLabel}</Badge>
          {capability && <Badge variant="outline">{capability.replace(/_/g, ' ')}</Badge>}
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="ml-auto"
          aria-expanded={isExpanded}
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-4 w-4 mr-1" />
              Less Filters
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4 mr-1" />
              More Filters
            </>
          )}
        </Button>
      </div>

      {isExpanded && (
        <div className="rounded-xl border border-[var(--border-base)] bg-[var(--surface-raised)] p-6 space-y-6">
          {onMinRatingChange && (
            <div className="space-y-2">
              <Label className="text-sm font-medium text-white">
                Minimum Rating: {minRating > 0 ? `${minRating}+` : 'Any'}
              </Label>
              <Slider
                value={[minRating]}
                onValueChange={(value) => onMinRatingChange(value[0] ?? 0)}
                min={0}
                max={5}
                step={0.5}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-[var(--text-secondary)]">
                <span>Any</span>
                <span>5.0</span>
              </div>
            </div>
          )}

          {onPriceRangeChange && (
            <div className="space-y-2">
              <Label className="text-sm font-medium text-white">
                Price Range: ${priceRange[0]} - ${priceRange[1] === 1000 ? '1000+' : `$${priceRange[1]}`}
              </Label>
              <Slider
                value={priceRange}
                onValueChange={(value) => onPriceRangeChange(value as [number, number])}
                min={0}
                max={1000}
                step={10}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-[var(--text-secondary)]">
                <span>$0</span>
                <span>$1000+</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
