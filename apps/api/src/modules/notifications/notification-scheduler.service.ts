import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';

import { PrismaService } from '../database/prisma.service.js';

@Injectable()
export class NotificationSchedulerService {
  private readonly logger = new Logger(NotificationSchedulerService.name);

  constructor(private readonly prisma: PrismaService) {}

  /**
   * Check for churned agents and send reactivation notifications
   * Runs daily at 9 AM UTC
   */
  @Cron(CronExpression.EVERY_DAY_AT_9AM)
  async checkChurnedAgents() {
    this.logger.log('Checking for churned agents...');

    const daysInactive = 30;
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysInactive);

    const churnedAgents = await this.prisma.agent.findMany({
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
        lastExecutedAt: true,
      },
      take: 100, // Process in batches
    });

    this.logger.log(`Found ${churnedAgents.length} churned agents`);

    // In production, this would call the notification service
    // For now, we'll just log
    for (const agent of churnedAgents) {
      this.logger.log(
        `Agent ${agent.id} (${agent.name}) is churned - last executed: ${agent.lastExecutedAt || 'never'}`,
      );
      // TODO: Call notification service
      // await this.notificationService.checkAndSendReactivation(agent.id, daysInactive);
    }

    return { processed: churnedAgents.length };
  }

  /**
   * Check for agents hitting budget limits and send upsell notifications
   * Runs every 6 hours
   */
  @Cron('0 */6 * * *') // Every 6 hours
  async checkBudgetLimits() {
    this.logger.log('Checking for agents hitting budget limits...');

    const budgets = await this.prisma.agentBudget.findMany({
      where: {
        approvalMode: 'AUTO',
      },
      include: {
        agent: {
          select: {
            id: true,
            name: true,
          },
        },
      },
    });

    let processed = 0;

    for (const budget of budgets) {
      const remaining = Number(budget.remaining);
      const monthlyLimit = Number(budget.monthlyLimit);
      const usagePercent = ((monthlyLimit - remaining) / monthlyLimit) * 100;

      // Send notification if usage is above 80%
      if (usagePercent >= 80) {
        this.logger.log(
          `Agent ${budget.agent.id} (${budget.agent.name}) has used ${usagePercent.toFixed(0)}% of budget`,
        );
        // TODO: Call notification service
        // await this.notificationService.checkAndSendUpsell(budget.agent.id);
        processed++;
      }
    }

    this.logger.log(`Processed ${processed} agents with high budget usage`);
    return { processed };
  }

  /**
   * Send onboarding notifications to newly approved agents
   * Runs every hour
   */
  @Cron(CronExpression.EVERY_HOUR)
  async sendOnboardingNotifications() {
    this.logger.log('Checking for new agents to onboard...');

    const oneHourAgo = new Date();
    oneHourAgo.setHours(oneHourAgo.getHours() - 1);

    const newAgents = await this.prisma.agent.findMany({
      where: {
        status: 'APPROVED',
        createdAt: {
          gte: oneHourAgo,
        },
        // Only agents that haven't been executed yet (truly new)
        lastExecutedAt: null,
      },
      select: {
        id: true,
        name: true,
        createdAt: true,
      },
      take: 50,
    });

    this.logger.log(`Found ${newAgents.length} new agents to onboard`);

    for (const agent of newAgents) {
      this.logger.log(`Sending onboarding notification to agent ${agent.id} (${agent.name})`);
      // TODO: Call notification service
      // await this.notificationService.sendOnboarding(agent.id);
    }

    return { processed: newAgents.length };
  }

  /**
   * Update loyalty tiers for all agents
   * Runs daily at midnight UTC
   */
  @Cron(CronExpression.EVERY_DAY_AT_MIDNIGHT)
  async updateLoyaltyTiers() {
    this.logger.log('Updating loyalty tiers for all agents...');

    // Note: loyaltyTier field doesn't exist in schema yet
    // TODO: Add loyaltyTier to Agent model in Prisma schema
    // Once added, uncomment the code below to update loyalty tiers
    
    // const agents = await this.prisma.agent.findMany({
    //   where: {
    //     status: 'APPROVED',
    //   },
    //   include: {
    //     executions: {
    //       where: { status: 'SUCCEEDED' },
    //     },
    //     metricsPrimary: true,
    //   },
    //   take: 1000, // Process in batches
    // });
    //
    // let updated = 0;
    // for (const agent of agents) {
    //   const executionCount = agent.executions.length;
    //   const totalSpend = agent.metricsPrimary.reduce(
    //     (sum, metric) => sum.plus(metric.totalSpend),
    //     new (await import('@prisma/client')).Prisma.Decimal(0),
    //   );
    //   const gmv = totalSpend.toNumber();
    //
    //   let newTier: 'NEW' | 'TRUSTED' | 'ELITE' = 'NEW';
    //   if (executionCount >= 50 && gmv >= 1000 && (agent.trustScore || 0) >= 80) {
    //     newTier = 'ELITE';
    //   } else if (executionCount >= 10 && gmv >= 200 && (agent.trustScore || 0) >= 70) {
    //     newTier = 'TRUSTED';
    //   }
    //
    //   if (agent.loyaltyTier !== newTier && newTier !== 'NEW') {
    //     await this.prisma.agent.update({
    //       where: { id: agent.id },
    //       data: { loyaltyTier: newTier },
    //     });
    //     this.logger.log(`Updated agent ${agent.id} to ${newTier} tier`);
    //     updated++;
    //   }
    // }

    this.logger.log('Loyalty tier updates skipped - field not in schema');
    return { updated: 0 };
  }
}

