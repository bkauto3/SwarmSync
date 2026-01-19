'use client';

import { useQuery } from '@tanstack/react-query';

import { agentsApi, type AgentListFilters } from '@/lib/api';

export const useAgents = (filters?: AgentListFilters) => {
  return useQuery({
    queryKey: ['agents', filters],
    queryFn: () => agentsApi.list(filters),
    // Don't run query if filters is explicitly undefined (waiting for user data)
    enabled: filters !== undefined,
    retry: 2,
    retryDelay: 1000,
    staleTime: 30 * 1000, // 30 seconds
  });
};
