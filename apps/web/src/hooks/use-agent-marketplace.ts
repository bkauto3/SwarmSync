import { useMemo, useState } from 'react';
import { useAgents } from '@/hooks/use-agents';
import { useAuth } from '@/hooks/use-auth';

export function useAgentMarketplace() {
    const { user } = useAuth();
    const [search, setSearch] = useState('');
    const [category, setCategory] = useState('');
    const [capability, setCapability] = useState('');
    const [verifiedOnly, setVerifiedOnly] = useState(false);
    const [showMyAgents, setShowMyAgents] = useState(false);
    const [sortBy, setSortBy] = useState('relevance');
    const [minRating, setMinRating] = useState(0);
    const [priceRange, setPriceRange] = useState<[number, number]>([0, 1000]);

    // When showing "My Agents", also pass showAll to bypass default PUBLIC/APPROVED filter
    const filters = useMemo(
        () => ({
            search: search.trim() || undefined,
            category: category || undefined,
            tag: capability || undefined,
            verifiedOnly,
            creatorId: showMyAgents && user?.id ? user.id : undefined,
            showAll: showMyAgents && user?.id ? 'true' : undefined,
        }),
        [search, category, capability, verifiedOnly, showMyAgents, user?.id],
    );

    // Sort and filter agents client-side (since backend doesn't support all filters yet)
    const effectiveFilters = useMemo(() => {
        if (!showMyAgents) return filters;
        if (user?.id) return filters;
        return null;
    }, [showMyAgents, user?.id, filters]);

    const { data: agents, isLoading: queryLoading, isError, error, refetch } = useAgents(
        effectiveFilters ?? undefined
    );

    const sortedAndFilteredAgents = useMemo(() => {
        if (!agents) return [];
        let filtered = [...agents];

        // Filter by rating
        if (minRating > 0) {
            filtered = filtered.filter((agent) => (agent.trustScore ?? 0) >= minRating);
        }

        // Filter by price range
        filtered = filtered.filter((agent) => {
            const price = agent.basePriceCents ? agent.basePriceCents / 100 : 0;
            return price >= priceRange[0] && price <= priceRange[1];
        });

        // Sort
        switch (sortBy) {
            case 'rating':
                filtered.sort((a, b) => (b.trustScore ?? 0) - (a.trustScore ?? 0));
                break;
            case 'price_low':
                filtered.sort((a, b) => (a.basePriceCents ?? 0) - (b.basePriceCents ?? 0));
                break;
            case 'price_high':
                filtered.sort((a, b) => (b.basePriceCents ?? 0) - (a.basePriceCents ?? 0));
                break;
            case 'newest':
                filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
                break;
            case 'popular':
                filtered.sort((a, b) => {
                    const aPopularity = (a.trustScore ?? 0) + (a.successCount ?? 0);
                    const bPopularity = (b.trustScore ?? 0) + (b.successCount ?? 0);
                    return bPopularity - aPopularity;
                });
                break;
            case 'relevance':
            default:
                break;
        }

        return filtered;
    }, [agents, minRating, priceRange, sortBy]);

    const isLoading = queryLoading || (showMyAgents && !user?.id);

    return {
        state: {
            search,
            category,
            capability,
            verifiedOnly,
            showMyAgents,
            sortBy,
            minRating,
            priceRange,
            isLoading,
            isError,
            error,
            user,
        },
        actions: {
            setSearch,
            setCategory,
            setCapability,
            setVerifiedOnly,
            setShowMyAgents,
            setSortBy,
            setMinRating,
            setPriceRange,
            refetch,
        },
        data: {
            agents: sortedAndFilteredAgents,
        },
    };
}
