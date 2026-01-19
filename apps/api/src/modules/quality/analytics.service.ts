import { Injectable, NotFoundException } from '@nestjs/common';
import {
  AgentEngagementMetric,
  EvaluationResult,
  OutcomeVerification,
  OutcomeVerificationStatus,
  Prisma,
  ServiceAgreement,
  ServiceAgreementStatus,
  TransactionStatus,
  TransactionType,
  WalletStatus,
} from '@prisma/client';

import { PrismaService } from '../database/prisma.service.js';

interface AgentQualitySummary {
  agentId: string;
  certification: {
    status: string | null;
    updatedAt?: Date | null;
    expiresAt?: Date | null;
    total: number;
  };
  evaluations: {
    total: number;
    passed: number;
    passRate: number;
    averageLatencyMs: number | null;
    averageCost: string | null;
  };
  agreements: {
    active: number;
    completed: number;
    disputed: number;
    pending: number;
  };
  verifications: {
    verified: number;
    rejected: number;
    pending: number;
  };
  a2a: {
    engagements: number;
    totalSpend: string;
  };
  roi: {
    grossMerchandiseVolume: string;
    averageCostPerOutcome: string | null;
    averageCostPerEngagement: string | null;
    verifiedOutcomeRate: number;
  };
}

interface AgentRoiTimeseriesPoint {
  date: string;
  grossMerchandiseVolume: string;
  verifiedOutcomes: number;
  averageCostPerOutcome: string | null;
}

@Injectable()
export class QualityAnalyticsService {
  constructor(private readonly prisma: PrismaService) {}

  async getAgentSummary(agentId: string): Promise<AgentQualitySummary> {
    await this.ensureAgentExists(agentId);

    const [latestCertification, evaluations, agreements, verifications, engagementMetrics, wallets] =
      await Promise.all([
        this.prisma.agentCertification.findFirst({
          where: { agentId },
          orderBy: { updatedAt: 'desc' },
        }),
        this.prisma.evaluationResult.findMany({
          where: { agentId },
        }),
        this.prisma.serviceAgreement.findMany({
          where: { agentId },
        }),
        this.prisma.outcomeVerification.findMany({
          where: {
            serviceAgreement: {
              agentId,
            },
          },
        }),
        this.prisma.agentEngagementMetric.findMany({
          where: { agentId },
        }),
        this.prisma.wallet.findMany({
          where: {
            ownerAgentId: agentId,
            status: WalletStatus.ACTIVE,
          },
          select: { id: true },
        }),
      ]);

    const evaluationStats = this.buildEvaluationStats(evaluations);
    const agreementStats = this.buildAgreementStats(agreements);
    const verificationStats = this.buildVerificationStats(verifications);
    const a2aStats = this.buildA2aStats(engagementMetrics);

    const roi = await this.buildRoiMetrics({
      walletIds: wallets.map((wallet) => wallet.id),
      verifiedCount:
        verificationStats.verified + verificationStats.rejected + verificationStats.pending,
      engagements: a2aStats.engagements,
      verifications: verificationStats,
    });

    return {
      agentId,
      certification: {
        status: latestCertification?.status ?? null,
        updatedAt: latestCertification?.updatedAt ?? null,
        expiresAt: latestCertification?.expiresAt ?? null,
        total: await this.prisma.agentCertification.count({ where: { agentId } }),
      },
      evaluations: evaluationStats,
      agreements: agreementStats,
      verifications: verificationStats,
      a2a: a2aStats,
      roi,
    };
  }

  async getAgentRoiTimeseries(agentId: string, days = 30): Promise<AgentRoiTimeseriesPoint[]> {
    await this.ensureAgentExists(agentId);
    const clampedDays = Number.isFinite(days) && days > 0 ? Math.min(days, 90) : 30;

    const since = new Date();
    since.setHours(0, 0, 0, 0);
    since.setDate(since.getDate() - (clampedDays - 1));

    const wallets = await this.prisma.wallet.findMany({
      where: {
        ownerAgentId: agentId,
        status: WalletStatus.ACTIVE,
      },
      select: { id: true },
    });
    const walletIds = wallets.map((wallet) => wallet.id);

    const [transactions, verifications] = await Promise.all([
      this.prisma.transaction.findMany({
        where: {
          walletId: { in: walletIds },
          status: TransactionStatus.SETTLED,
          type: TransactionType.CREDIT,
          createdAt: { gte: since },
        },
        select: {
          amount: true,
          createdAt: true,
        },
      }),
      this.prisma.outcomeVerification.findMany({
        where: {
          serviceAgreement: {
            agentId,
          },
          createdAt: { gte: since },
        },
        select: {
          createdAt: true,
          status: true,
        },
      }),
    ]);

    const buckets = new Map<
      string,
      { gmv: Prisma.Decimal; verified: number; totalVerifications: number }
    >();

    transactions.forEach((transaction) => {
      const key = this.toDateKey(transaction.createdAt);
      const bucket = buckets.get(key) ?? {
        gmv: new Prisma.Decimal(0),
        verified: 0,
        totalVerifications: 0,
      };
      bucket.gmv = bucket.gmv.plus(transaction.amount);
      buckets.set(key, bucket);
    });

    verifications.forEach((verification) => {
      const key = this.toDateKey(verification.createdAt ?? new Date());
      const bucket = buckets.get(key) ?? {
        gmv: new Prisma.Decimal(0),
        verified: 0,
        totalVerifications: 0,
      };
      bucket.totalVerifications += 1;
      if (verification.status === OutcomeVerificationStatus.VERIFIED) {
        bucket.verified += 1;
      }
      buckets.set(key, bucket);
    });

    const results: AgentRoiTimeseriesPoint[] = [];
    for (let offset = clampedDays - 1; offset >= 0; offset -= 1) {
      const day = new Date();
      day.setHours(0, 0, 0, 0);
      day.setDate(day.getDate() - offset);
      const key = this.toDateKey(day);
      const bucket = buckets.get(key) ?? {
        gmv: new Prisma.Decimal(0),
        verified: 0,
        totalVerifications: 0,
      };
      const averageCost =
        bucket.verified > 0 ? bucket.gmv.div(bucket.verified).toFixed(2) : null;

      results.push({
        date: key,
        grossMerchandiseVolume: bucket.gmv.toFixed(2),
        verifiedOutcomes: bucket.verified,
        averageCostPerOutcome: averageCost,
      });
    }

    return results;
  }

  private buildEvaluationStats(evaluations: EvaluationResult[]) {
    const total = evaluations.length;
    if (!total) {
      return {
        total: 0,
        passed: 0,
        passRate: 0,
        averageLatencyMs: null,
        averageCost: null,
      };
    }

    const passed = evaluations.filter((evaluation) => evaluation.status === 'PASSED').length;
    const latencyValues = evaluations
      .map((evaluation) => evaluation.latencyMs)
      .filter((value): value is number => typeof value === 'number');
    const averageLatencyMs = latencyValues.length
      ? Math.round(
          latencyValues.reduce((sum, value) => sum + value, 0) / latencyValues.length,
        )
      : null;

    const costValues = evaluations
      .map((evaluation) => evaluation.cost)
      .filter((value): value is Prisma.Decimal => value instanceof Prisma.Decimal);
    const averageCost =
      costValues.length > 0
        ? costValues
            .reduce((sum, value) => sum.plus(value), new Prisma.Decimal(0))
            .div(costValues.length)
            .toFixed(2)
        : null;

    return {
      total,
      passed,
      passRate: Number(((passed / total) * 100).toFixed(1)),
      averageLatencyMs,
      averageCost,
    };
  }

  private buildAgreementStats(agreements: ServiceAgreement[]) {
    const counters = {
      active: 0,
      completed: 0,
      disputed: 0,
      pending: 0,
    };

    agreements.forEach((agreement) => {
      switch (agreement.status) {
        case ServiceAgreementStatus.ACTIVE:
          counters.active += 1;
          break;
        case ServiceAgreementStatus.COMPLETED:
          counters.completed += 1;
          break;
        case ServiceAgreementStatus.DISPUTED:
          counters.disputed += 1;
          break;
        case ServiceAgreementStatus.PENDING:
        default:
          counters.pending += 1;
      }
    });

    return counters;
  }

  private buildVerificationStats(verifications: OutcomeVerification[]) {
    const counters = {
      verified: 0,
      rejected: 0,
      pending: 0,
    };

    verifications.forEach((verification) => {
      switch (verification.status) {
        case OutcomeVerificationStatus.VERIFIED:
          counters.verified += 1;
          break;
        case OutcomeVerificationStatus.REJECTED:
          counters.rejected += 1;
          break;
        default:
          counters.pending += 1;
      }
    });

    return counters;
  }

  private buildA2aStats(metrics: AgentEngagementMetric[]) {
    if (!metrics.length) {
      return {
        engagements: 0,
        totalSpend: '0',
      };
    }

    const totalSpend = metrics
      .map((item) => item.totalSpend)
      .reduce((sum, value) => sum.plus(value), new Prisma.Decimal(0));

    const engagements = metrics.reduce((sum, value) => sum + value.a2aCount, 0);

    return {
      engagements,
      totalSpend: totalSpend.toFixed(2),
    };
  }

  private async buildRoiMetrics(params: {
    walletIds: string[];
    verifiedCount: number;
    engagements: number;
    verifications: { verified: number; rejected: number; pending: number };
  }) {
    const { walletIds, verifiedCount, engagements, verifications } = params;

    const gmvSum = walletIds.length
      ? await this.prisma.transaction.aggregate({
          _sum: { amount: true },
          where: {
            walletId: { in: walletIds },
            status: TransactionStatus.SETTLED,
            type: { in: [TransactionType.CREDIT] },
          },
        })
      : { _sum: { amount: new Prisma.Decimal(0) } };

    const grossMerchandiseVolume = (gmvSum._sum.amount ?? new Prisma.Decimal(0)).toFixed(2);
    const gmvDecimal = gmvSum._sum.amount ?? new Prisma.Decimal(0);

    const averageCostPerOutcome =
      verifiedCount > 0 ? gmvDecimal.div(verifiedCount).toFixed(2) : null;
    const averageCostPerEngagement =
      engagements > 0 ? gmvDecimal.div(engagements).toFixed(2) : null;

    const verificationTotal = verifications.verified + verifications.rejected + verifications.pending;
    const verifiedOutcomeRate =
      verificationTotal > 0
        ? Number(((verifications.verified / verificationTotal) * 100).toFixed(1))
        : 0;

    return {
      grossMerchandiseVolume,
      averageCostPerOutcome,
      averageCostPerEngagement,
      verifiedOutcomeRate,
    };
  }

  private toDateKey(date: Date) {
    const year = date.getFullYear();
    const month = `${date.getMonth() + 1}`.padStart(2, '0');
    const day = `${date.getDate()}`.padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private async ensureAgentExists(agentId: string) {
    const exists = await this.prisma.agent.count({ where: { id: agentId } });
    if (!exists) {
      throw new NotFoundException('Agent not found');
    }
  }
}
