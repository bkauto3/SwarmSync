import { Prisma, PrismaClient, TransactionStatus, TransactionType } from '@prisma/client';

const prisma = new PrismaClient();

export const getOrganizationRoiSummary = async (slug: string) => {
  const organization = await prisma.organization.findUnique({
    where: { slug },
    include: {
      agents: {
        select: { id: true },
      },
      wallets: {
        select: { id: true, status: true },
      },
    },
  });

  if (!organization) {
    throw new Error(`Organization ${slug} not found`);
  }

  const walletIds = organization.wallets
    .filter((wallet) => wallet.status === 'ACTIVE')
    .map((wallet) => wallet.id);

  const transactions = await prisma.transaction.findMany({
    where: {
      walletId: { in: walletIds },
      status: TransactionStatus.SETTLED,
      type: TransactionType.CREDIT,
    },
    select: { amount: true },
  });

  const verifications = await prisma.outcomeVerification.count({
    where: {
      status: 'VERIFIED',
      serviceAgreement: {
        agent: {
          organizationId: organization.id,
        },
      },
    },
  });

  const gmv = transactions.reduce((sum, tx) => sum.plus(tx.amount), new Prisma.Decimal(0));

  return {
    organization: {
      id: organization.id,
      name: organization.name,
      slug: organization.slug,
    },
    grossMerchandiseVolume: gmv.toFixed(2),
    verifiedOutcomes: verifications,
    totalAgents: organization.agents.length,
  };
};

export const getOrganizationRoiTimeseries = async (slug: string, days = 30) => {
  const organization = await prisma.organization.findUnique({
    where: { slug },
  });

  if (!organization) {
    throw new Error(`Organization ${slug} not found`);
  }

  const since = new Date();
  since.setDate(since.getDate() - (days - 1));
  since.setHours(0, 0, 0, 0);

  const wallets = await prisma.wallet.findMany({
    where: { organizationId: organization.id, status: 'ACTIVE' },
    select: { id: true },
  });

  const [transactions, verifications] = await Promise.all([
    prisma.transaction.findMany({
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
    prisma.outcomeVerification.findMany({
      where: {
        serviceAgreement: {
          agent: { organizationId: organization.id },
        },
        createdAt: { gte: since },
      },
      select: {
        createdAt: true,
        status: true,
      },
    }),
  ]);

  const spendMap = new Map<string, Prisma.Decimal>();
  transactions.forEach((tx) => {
    const key = tx.createdAt.toISOString().split('T')[0];
    const current = spendMap.get(key) ?? new Prisma.Decimal(0);
    spendMap.set(key, current.plus(tx.amount));
  });

  const verificationMap = new Map<string, { verified: number }>();
  verifications.forEach((verification) => {
    const key = (verification.createdAt ?? new Date()).toISOString().split('T')[0];
    const bucket = verificationMap.get(key) ?? { verified: 0 };
    if (verification.status === 'VERIFIED') {
      bucket.verified += 1;
    }
    verificationMap.set(key, bucket);
  });

  return Array.from({ length: days }, (_, idx) => {
    const day = new Date(since);
    day.setDate(since.getDate() + idx);
    const key = day.toISOString().split('T')[0];
    const spend = spendMap.get(key) ?? new Prisma.Decimal(0);
    const stats = verificationMap.get(key) ?? { verified: 0 };

    return {
      date: key,
      grossMerchandiseVolume: spend.toFixed(2),
      verifiedOutcomes: stats.verified,
      averageCostPerOutcome: stats.verified > 0 ? spend.div(stats.verified).toFixed(2) : null,
    };
  });
};
