import { Injectable } from '@nestjs/common';
import { ExecutionStatus, InitiatorType, Prisma } from '@prisma/client';

import { PrismaService } from '../database/prisma.service.js';

@Injectable()
export class AnalyticsService {
  constructor(private readonly prisma: PrismaService) {}

  /**
   * Get top 100 buying agents by GMV
   */
  async getTopBuyingAgents(params?: {
    limit?: number;
    startDate?: Date;
    endDate?: Date;
  }) {
    const limit = params?.limit || 100;
    const startDate = params?.startDate;
    const endDate = params?.endDate;

    const where: Prisma.AgentEngagementMetricWhereInput = {
      initiatorType: InitiatorType.AGENT,
    };

    if (startDate || endDate) {
      where.lastInteraction = {};
      if (startDate) {
        where.lastInteraction.gte = startDate;
      }
      if (endDate) {
        where.lastInteraction.lte = endDate;
      }
    }

    const metrics = await this.prisma.agentEngagementMetric.findMany({
      where,
      include: {
        agent: {
          select: {
            id: true,
            name: true,
            slug: true,
            trustScore: true,
          },
        },
      },
      orderBy: {
        totalSpend: 'desc',
      },
      take: limit,
    });

    return {
      agents: metrics.map((metric) => ({
        agentId: metric.agent.id,
        agentName: metric.agent.name,
        agentSlug: metric.agent.slug,
        trustScore: metric.agent.trustScore,
        totalSpend: Number(metric.totalSpend),
        a2aCount: metric.a2aCount,
        lastInteraction: metric.lastInteraction,
      })),
      total: metrics.length,
    };
  }

  /**
   * Get churned agents (no calls in last N days)
   */
  async getChurnedAgents(daysInactive: number = 30) {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysInactive);

    const agents = await this.prisma.agent.findMany({
      where: {
        OR: [
          { lastExecutedAt: null },
          { lastExecutedAt: { lt: cutoffDate } },
        ],
        status: 'APPROVED',
      },
      select: {
        id: true,
        name: true,
        slug: true,
        lastExecutedAt: true,
        successCount: true,
        failureCount: true,
        trustScore: true,
      },
      orderBy: {
        lastExecutedAt: 'asc',
      },
      take: 100,
    });

    return {
      agents: agents.map((agent) => ({
        agentId: agent.id,
        agentName: agent.name,
        agentSlug: agent.slug,
        lastExecutedAt: agent.lastExecutedAt,
        daysInactive: agent.lastExecutedAt
          ? Math.floor((Date.now() - agent.lastExecutedAt.getTime()) / (1000 * 60 * 60 * 24))
          : null,
        totalExecutions: agent.successCount + agent.failureCount,
        trustScore: agent.trustScore,
      })),
      total: agents.length,
      cutoffDate,
    };
  }

  /**
   * Get "whale" agents (high spend)
   */
  async getWhaleAgents(params?: {
    minSpend?: number;
    startDate?: Date;
    endDate?: Date;
  }) {
    const minSpend = params?.minSpend || 1000;
    const startDate = params?.startDate;
    const endDate = params?.endDate;

    const where: Prisma.AgentEngagementMetricWhereInput = {
      initiatorType: InitiatorType.AGENT,
      totalSpend: {
        gte: new Prisma.Decimal(minSpend),
      },
    };

    if (startDate || endDate) {
      where.lastInteraction = {};
      if (startDate) {
        where.lastInteraction.gte = startDate;
      }
      if (endDate) {
        where.lastInteraction.lte = endDate;
      }
    }

    const metrics = await this.prisma.agentEngagementMetric.findMany({
      where,
      include: {
        agent: {
          select: {
            id: true,
            name: true,
            slug: true,
            trustScore: true,
          },
        },
      },
      orderBy: {
        totalSpend: 'desc',
      },
    });

    return {
      agents: metrics.map((metric) => ({
        agentId: metric.agent.id,
        agentName: metric.agent.name,
        agentSlug: metric.agent.slug,
        trustScore: metric.agent.trustScore,
        totalSpend: Number(metric.totalSpend),
        a2aCount: metric.a2aCount,
        lastInteraction: metric.lastInteraction,
      })),
      total: metrics.length,
    };
  }

  /**
   * Get agent network graph visualization data
   */
  async getAgentNetworkGraph(agentId?: string) {
    if (agentId) {
      // Get network for specific agent
      const collaborations = await this.prisma.agentCollaboration.findMany({
        where: {
          OR: [{ requesterAgentId: agentId }, { responderAgentId: agentId }],
        },
        include: {
          requesterAgent: {
            select: {
              id: true,
              name: true,
              slug: true,
            },
          },
          responderAgent: {
            select: {
              id: true,
              name: true,
              slug: true,
            },
          },
        },
        take: 100,
      });

      const nodeIds = new Set<string>();
      const edges: Array<{
        from: string;
        to: string;
        count: number;
      }> = [];

      collaborations.forEach((collab) => {
        if (collab.requesterAgent) {
          nodeIds.add(collab.requesterAgent.id);
        }
        if (collab.responderAgent) {
          nodeIds.add(collab.responderAgent.id);
        }

        if (collab.requesterAgent && collab.responderAgent) {
          const existingEdge = edges.find(
            (e) =>
              (e.from === collab.requesterAgentId && e.to === collab.responderAgentId) ||
              (e.from === collab.responderAgentId && e.to === collab.requesterAgentId),
          );

          if (existingEdge) {
            existingEdge.count++;
          } else {
            edges.push({
              from: collab.requesterAgentId,
              to: collab.responderAgentId,
              count: 1,
            });
          }
        }
      });

      const nodes = Array.from(nodeIds).map((id) => {
        const agent =
          collaborations.find((c) => c.requesterAgent?.id === id)?.requesterAgent ||
          collaborations.find((c) => c.responderAgent?.id === id)?.responderAgent;

        return {
          id,
          name: agent?.name || 'Unknown',
          slug: agent?.slug || '',
        };
      });

      return { nodes, edges };
    }

    // Get global network graph (top 100 agents)
    const topAgents = await this.prisma.agentEngagementMetric.findMany({
      where: {
        initiatorType: InitiatorType.AGENT,
      },
      include: {
        agent: {
          select: {
            id: true,
            name: true,
            slug: true,
          },
        },
      },
      orderBy: {
        totalSpend: 'desc',
      },
      take: 100,
    });

    const nodeIds = new Set(topAgents.map((m) => m.agent.id));
    const edges: Array<{
      from: string;
      to: string;
      weight: number;
    }> = [];

    // Get collaborations between top agents
    const collaborations = await this.prisma.agentCollaboration.findMany({
      where: {
        AND: [
          { requesterAgentId: { in: Array.from(nodeIds) } },
          { responderAgentId: { in: Array.from(nodeIds) } },
        ],
      },
      select: {
        requesterAgentId: true,
        responderAgentId: true,
      },
    });

    collaborations.forEach((collab) => {
      const existingEdge = edges.find(
        (e) =>
          (e.from === collab.requesterAgentId && e.to === collab.responderAgentId) ||
          (e.from === collab.responderAgentId && e.to === collab.requesterAgentId),
      );

      if (existingEdge) {
        existingEdge.weight++;
      } else {
        edges.push({
          from: collab.requesterAgentId,
          to: collab.responderAgentId,
          weight: 1,
        });
      }
    });

    const nodes = topAgents.map((metric) => ({
      id: metric.agent.id,
      name: metric.agent.name,
      slug: metric.agent.slug,
      totalSpend: Number(metric.totalSpend),
      a2aCount: metric.a2aCount,
    }));

    return { nodes, edges };
  }

  /**
   * Get overview analytics
   */
  async getOverview(params?: {
    startDate?: Date;
    endDate?: Date;
  }) {
    const startDate = params?.startDate;
    const endDate = params?.endDate;

    const where: Prisma.AgentExecutionWhereInput = {};
    if (startDate || endDate) {
      where.createdAt = {};
      if (startDate) {
        where.createdAt.gte = startDate;
      }
      if (endDate) {
        where.createdAt.lte = endDate;
      }
    }

    const [
      totalAgents,
      activeAgents,
      totalExecutions,
      successfulExecutions,
      totalGMV,
      a2aExecutions,
    ] = await Promise.all([
      this.prisma.agent.count({
        where: { status: 'APPROVED' },
      }),
      this.prisma.agent.count({
        where: {
          status: 'APPROVED',
          lastExecutedAt: {
            gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // Last 30 days
          },
        },
      }),
      this.prisma.agentExecution.count({ where }),
      this.prisma.agentExecution.count({
        where: {
          ...where,
          status: ExecutionStatus.SUCCEEDED,
        },
      }),
      this.prisma.agentEngagementMetric.aggregate({
        where: {
          initiatorType: InitiatorType.AGENT,
          ...(startDate || endDate
            ? {
                lastInteraction: {
                  ...(startDate ? { gte: startDate } : {}),
                  ...(endDate ? { lte: endDate } : {}),
                },
              }
            : {}),
        },
        _sum: {
          totalSpend: true,
        },
      }),
      this.prisma.agentExecution.count({
        where: {
          ...where,
          initiatorType: InitiatorType.AGENT,
        },
      }),
    ]);

    const successRate =
      totalExecutions > 0 ? (successfulExecutions / totalExecutions) * 100 : 0;
    const a2aPercentage = totalExecutions > 0 ? (a2aExecutions / totalExecutions) * 100 : 0;

    return {
      totalAgents,
      activeAgents,
      totalExecutions,
      successfulExecutions,
      successRate: Number(successRate.toFixed(2)),
      totalGMV: Number(totalGMV._sum.totalSpend || 0),
      a2aExecutions,
      a2aPercentage: Number(a2aPercentage.toFixed(2)),
      dateRange: {
        startDate: startDate || null,
        endDate: endDate || null,
      },
    };
  }
}

