'use client';

import { useQuery } from '@tanstack/react-query';

import { agentsApi } from '@/lib/api';
import { useAuthStore } from '@/stores/auth-store';

export function useOwnedAgents() {
  const user = useAuthStore((state) => state.user);
  const userId = user?.id;

  return useQuery({
    queryKey: ['owned-agents', userId],
    queryFn: () =>
      userId ? agentsApi.list({ creatorId: userId, limit: 100 }) : Promise.resolve([]),
    enabled: Boolean(userId),
    staleTime: 60 * 1000,
  });
}
