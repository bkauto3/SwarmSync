'use client';

import { AgentNetworkGraph as AgentNetworkGraphResponse } from '@agent-market/sdk';
import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import ReactFlowRenderer, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

interface AgentNetworkGraphProps {
  agentId: string;
}

export function AgentNetworkGraph({ agentId }: AgentNetworkGraphProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['agent-network', agentId],
    queryFn: async () => api.get(`agents/${agentId}/network`).json<AgentNetworkGraphResponse>(),
    enabled: Boolean(agentId),
    staleTime: 30_000,
    refetchInterval: 20_000,
  });

  const nodes = useMemo(() => {
    if (!data?.nodes?.length) {
      return [];
    }

    const radius = 150;
    const center = 200;

    return data.nodes.map((node, index) => {
      const angle = (index / data.nodes.length) * 2 * Math.PI;
      return {
        id: node.id,
        data: {
          label: node.name,
        },
        position: {
          x: center + Math.cos(angle) * radius,
          y: center + Math.sin(angle) * radius,
        },
        draggable: false,
        selectable: false,
        className: cn(
          'rounded-full border border-[var(--border-base)] bg-[var(--surface-raised)]/80 px-4 py-2 text-xs text-[var(--text-primary)] shadow-sm font-ui',
          node.isPrimary && 'border-[var(--accent-primary)] text-[var(--accent-primary)]',
        ),
      };
    });
  }, [data]);

  const edges = useMemo(() => {
    if (!data?.edges?.length) {
      return [];
    }

    return data.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: `${edge.transactionCount} · $${Math.round(edge.totalValue).toLocaleString()}`,
      animated: edge.latestStatus === 'PENDING',
      labelBgPadding: [6, 2] as [number, number],
      labelBgBorderRadius: 12,
      labelBgStyle: { fill: '#16181d', color: '#fff' },
      style: {
        strokeWidth: 1.5,
        stroke: edge.latestStatus === 'DECLINED' ? '#f87171' : '#7dd3fc',
      },
    }));
  }, [data]);

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="text-base font-semibold text-[var(--text-primary)] font-display">
          Agent collaboration network
        </CardTitle>
        <p className="text-sm text-[var(--text-secondary)] font-ui">
          Visual map of who this agent is hiring, how often, and the GMV flowing through each
          relationship.
        </p>
      </CardHeader>
      <CardContent>
        <div className="h-[320px] overflow-hidden rounded-3xl border border-[var(--border-base)] bg-[var(--surface-raised)]/40">
          {isLoading ? (
            <Skeleton className="h-full w-full rounded-3xl" />
          ) : data && nodes.length > 0 ? (
            <ReactFlowRenderer
              nodes={nodes}
              edges={edges}
              fitView
              panOnDrag={false}
              nodesDraggable={false}
              zoomOnScroll={false}
            >
              <Background />
              <Controls showInteractive={false} />
            </ReactFlowRenderer>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-[var(--text-muted)] font-ui">
              No collaboration data yet. Once this agent starts trading, the live mesh will render
              here.
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
