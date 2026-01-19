import { useQuery } from '@tanstack/react-query';

interface AgentAnalyticsSummary {
  agentId: string;
  agentName: string;
  trustScore: number;
  certificationStatus: string;
  successCount: number;
  failureCount: number;
  averageResponseTime: number;
  totalSpent: number;
  totalEarned: number;
  a2aEngagements: number;
  roiPercentage: number;
  uptime: number;
}

interface AnalyticsPoint {
  timestamp: string;
  cumulativeRoi: number;
  dailyRoi: number;
  engagementCount: number;
  successRate: number;
}

export function useAgentAnalytics(agentId: string) {
  return useQuery({
    queryKey: ['analytics', 'agent', agentId],
    queryFn: async () => {
      const response = await fetch(
        `/api/quality/analytics/agents/${agentId}`,
        {
          headers: {
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_API_KEY || ''}`,
          },
        }
      );
      if (!response.ok) throw new Error('Failed to fetch analytics');
      return response.json() as Promise<AgentAnalyticsSummary>;
    },
  });
}

export function useAgentAnalyticsTimeseries(agentId: string, days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'timeseries', agentId, days],
    queryFn: async () => {
      const response = await fetch(
        `/api/quality/analytics/agents/${agentId}/timeseries?days=${days}`,
        {
          headers: {
            Authorization: `Bearer ${process.env.NEXT_PUBLIC_API_KEY || ''}`,
          },
        }
      );
      if (!response.ok) throw new Error('Failed to fetch timeseries data');
      return response.json() as Promise<AnalyticsPoint[]>;
    },
  });
}
