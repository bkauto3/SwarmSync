import { Injectable, Logger } from '@nestjs/common';

import { PrismaService } from '../database/prisma.service.js';

@Injectable()
export class AgentsBadgesService {
  private readonly logger = new Logger(AgentsBadgesService.name);

  constructor(private readonly prisma: PrismaService) {}

  /**
   * Update badges for an agent based on their test run results
   */
  async updateAgentBadges(agentId: string): Promise<string[]> {
    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
    });

    if (!agent) {
      throw new Error(`Agent ${agentId} not found`);
    }

    // Get all completed test runs for this agent
    const testRuns = await this.prisma.testRun.findMany({
      where: {
        agentId,
        status: 'COMPLETED',
      },
      include: {
        suite: true,
      },
      orderBy: {
        completedAt: 'desc',
      },
      take: 100, // Get recent test runs
    });

    const badges: string[] = [];

    // Group test runs by category
    const securityTests = testRuns.filter((run) => run.suite?.category === 'security');
    const latencyTests = testRuns.filter((run) => run.suite?.category === 'smoke' || run.suite?.category === 'reliability');
    const reasoningTests = testRuns.filter((run) => run.suite?.category === 'reasoning');

    // Security badge
    if (securityTests.length > 0) {
      const latestSecurity = securityTests[0];
      const rawResults = latestSecurity.rawResults as { passed?: boolean; results?: Array<{ passed: boolean }> } | null;
      const passed = rawResults?.passed ?? (rawResults?.results?.every((r) => r.passed) ?? false);
      
      if (passed) {
        badges.push('Security Passed');
      } else {
        badges.push('Security Failed');
      }
    }

    // Latency badge (A = <500ms, B = 500-1000ms, C = >1000ms)
    if (latencyTests.length > 0) {
      const latencyResults = latencyTests
        .map((run) => {
          const rawResults = run.rawResults as { latencyMs?: number; results?: Array<{ latencyMs?: number }> } | null;
          if (rawResults?.latencyMs) return rawResults.latencyMs;
          if (rawResults?.results) {
            const avgLatency = rawResults.results.reduce((sum, r) => sum + (r.latencyMs || 0), 0) / rawResults.results.length;
            return avgLatency;
          }
          return null;
        })
        .filter((ms): ms is number => ms !== null);

      if (latencyResults.length > 0) {
        const avgLatency = latencyResults.reduce((sum, ms) => sum + ms, 0) / latencyResults.length;
        if (avgLatency < 500) {
          badges.push('Latency A');
        } else if (avgLatency < 1000) {
          badges.push('Latency B');
        } else {
          badges.push('Latency C');
        }
      }
    }

    // Reasoning badge (A = >90%, B = 70-90%, C = <70%)
    if (reasoningTests.length > 0) {
      const reasoningResults = reasoningTests
        .map((run) => {
          const score = run.score ?? null;
          if (score !== null) return score;
          const rawResults = run.rawResults as { accuracy?: number; results?: Array<{ passed: boolean }> } | null;
          if (rawResults?.accuracy !== undefined) return rawResults.accuracy * 100;
          if (rawResults?.results) {
            const passedCount = rawResults.results.filter((r) => r.passed).length;
            return (passedCount / rawResults.results.length) * 100;
          }
          return null;
        })
        .filter((score): score is number => score !== null);

      if (reasoningResults.length > 0) {
        const avgScore = reasoningResults.reduce((sum, score) => sum + score, 0) / reasoningResults.length;
        if (avgScore >= 90) {
          badges.push('Reasoning A');
        } else if (avgScore >= 70) {
          badges.push('Reasoning B');
        } else {
          badges.push('Reasoning C');
        }
      }
    }

    // Update agent badges
    await this.prisma.agent.update({
      where: { id: agentId },
      data: { badges },
    });

    this.logger.log(`Updated badges for agent ${agentId}: ${badges.join(', ')}`);

    return badges;
  }

  /**
   * Update badges for all agents
   */
  async updateAllAgentBadges(): Promise<void> {
    const agents = await this.prisma.agent.findMany({
      where: {
        status: 'APPROVED',
      },
      select: {
        id: true,
        name: true,
      },
    });

    this.logger.log(`Updating badges for ${agents.length} agents...`);

    for (const agent of agents) {
      try {
        await this.updateAgentBadges(agent.id);
      } catch (error) {
        this.logger.error(`Failed to update badges for agent ${agent.id}:`, error);
      }
    }

    this.logger.log(`Completed updating badges for all agents`);
  }
}

