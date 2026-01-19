import { Injectable, NotFoundException } from '@nestjs/common';
import {
  Organization,
  Prisma,
  TransactionStatus,
  TransactionType,
  WalletStatus,
} from '@prisma/client';

import { PrismaService } from '../database/prisma.service.js';

export interface OrganizationRoiSummary {
  organization: Pick<Organization, 'id' | 'name' | 'slug'>;
  grossMerchandiseVolume: string;
  totalAgents: number;
  verifiedOutcomes: number;
  averageCostPerOutcome: string | null;
}

export interface OrganizationRoiTimeseriesPoint {
  date: string;
  grossMerchandiseVolume: string;
  verifiedOutcomes: number;
  averageCostPerOutcome: string | null;
}

@Injectable()
export class OrganizationsService {
  constructor(private readonly prisma: PrismaService) {}

  async getOrganizationRoi(orgSlug: string): Promise<OrganizationRoiSummary> {
    const organization = await this.prisma.organization.findUnique({
      where: { slug: orgSlug },
    });

    if (!organization) {
      throw new NotFoundException('Organization not found');
    }

    const agents = await this.prisma.agent.findMany({
      where: { organizationId: organization.id },
      select: { id: true },
    });

    const wallets = await this.prisma.wallet.findMany({
      where: {
        organizationId: organization.id,
        status: WalletStatus.ACTIVE,
      },
      select: { id: true },
    });

    const [transactions, verifications] = await Promise.all([
      this.prisma.transaction.findMany({
        where: {
          walletId: { in: wallets.map((wallet) => wallet.id) },
          status: TransactionStatus.SETTLED,
          type: TransactionType.CREDIT,
        },
        select: {
          amount: true,
        },
      }),
      this.prisma.outcomeVerification.findMany({
        where: {
          serviceAgreement: {
            agent: {
              organizationId: organization.id,
            },
          },
        },
        select: {
          status: true,
        },
      }),
    ]);

    const gmv = transactions
      .map((transaction) => transaction.amount)
      .reduce((sum, value) => sum.plus(value), new Prisma.Decimal(0));

    const verified = verifications.filter(
      (verification) => verification.status === 'VERIFIED',
    ).length;

    return {
      organization: {
        id: organization.id,
        name: organization.name,
        slug: organization.slug,
      },
      grossMerchandiseVolume: gmv.toFixed(2),
      totalAgents: agents.length,
      verifiedOutcomes: verified,
      averageCostPerOutcome:
        verified > 0 ? gmv.div(verified).toFixed(2) : null,
    };
  }

  async getOrganizationRoiTimeseries(
    orgSlug: string,
    days = 30,
  ): Promise<OrganizationRoiTimeseriesPoint[]> {
    const organization = await this.prisma.organization.findUnique({
      where: { slug: orgSlug },
    });

    if (!organization) {
      throw new NotFoundException('Organization not found');
    }

    const clampedDays = Number.isFinite(days) && days > 0 ? Math.min(days, 90) : 30;

    const since = new Date();
    since.setHours(0, 0, 0, 0);
    since.setDate(since.getDate() - (clampedDays - 1));

    const wallets = await this.prisma.wallet.findMany({
      where: {
        organizationId: organization.id,
        status: WalletStatus.ACTIVE,
      },
      select: { id: true },
    });

    const [transactions, verifications] = await Promise.all([
      this.prisma.transaction.findMany({
        where: {
          walletId: { in: wallets.map((wallet) => wallet.id) },
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
            agent: {
              organizationId: organization.id,
            },
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
      if (verification.status === 'VERIFIED') {
        bucket.verified += 1;
      }
      buckets.set(key, bucket);
    });

    const points: OrganizationRoiTimeseriesPoint[] = [];
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

      points.push({
        date: key,
        grossMerchandiseVolume: bucket.gmv.toFixed(2),
        verifiedOutcomes: bucket.verified,
        averageCostPerOutcome:
          bucket.verified > 0 ? bucket.gmv.div(bucket.verified).toFixed(2) : null,
      });
    }

    return points;
  }

  private toDateKey(date: Date) {
    return date.toISOString().split('T')[0];
  }
}
