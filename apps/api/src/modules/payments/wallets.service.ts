import { Injectable, NotFoundException, BadRequestException } from '@nestjs/common';
import {
  EscrowStatus,
  Prisma,
  TransactionStatus,
  TransactionType,
  WalletOwnerType,
  WalletStatus,
} from '@prisma/client';

import { PrismaService } from '../database/prisma.service.js';
import { CreateWalletDto } from './dto/create-wallet.dto.js';
import { FundWalletDto } from './dto/fund-wallet.dto.js';

const PLATFORM_SLUG = process.env.DEFAULT_ORG_SLUG ?? 'genesis';
const PLATFORM_FEE_BASIS_POINTS =
  Number(process.env.PLATFORM_TAKE_RATE_BPS ?? process.env.TAKE_RATE_BPS ?? '500') || 0;

@Injectable()
export class WalletsService {
  constructor(private readonly prisma: PrismaService) {}

  async createWallet(dto: CreateWalletDto) {
    if (dto.ownerType === WalletOwnerType.USER && !dto.ownerUserId) {
      throw new BadRequestException('ownerUserId must be provided for user wallets');
    }

    if (dto.ownerType === WalletOwnerType.AGENT && !dto.ownerAgentId) {
      throw new BadRequestException('ownerAgentId must be provided for agent wallets');
    }

    if (dto.organizationId && dto.ownerType !== WalletOwnerType.PLATFORM) {
      throw new BadRequestException('organizationId is only valid for platform wallets');
    }

    const wallet = await this.prisma.wallet.create({
      data: {
        ownerType: dto.ownerType,
        ownerUserId: dto.ownerUserId,
        ownerAgentId: dto.ownerAgentId,
        organizationId: dto.organizationId,
        currency: dto.currency ?? 'USD',
        status: WalletStatus.ACTIVE,
      },
    });

    return wallet;
  }

  async ensureAgentWallet(agentId: string, currency = 'USD') {
    const wallet = await this.prisma.wallet.findFirst({
      where: {
        ownerAgentId: agentId,
        status: WalletStatus.ACTIVE,
      },
    });

    if (wallet) {
      return wallet;
    }

    return this.createWallet({
      ownerType: WalletOwnerType.AGENT,
      ownerAgentId: agentId,
      currency,
    });
  }

  async ensureUserWallet(userId: string, currency = 'USD') {
    const wallet = await this.prisma.wallet.findFirst({
      where: {
        ownerUserId: userId,
        status: WalletStatus.ACTIVE,
      },
    });

    if (wallet) {
      return wallet;
    }

    return this.createWallet({
      ownerType: WalletOwnerType.USER,
      ownerUserId: userId,
      currency,
    });
  }

  async ensureOrganizationWallet(organizationId: string, currency = 'USD') {
    const wallet = await this.prisma.wallet.findFirst({
      where: {
        organizationId,
        status: WalletStatus.ACTIVE,
      },
    });

    if (wallet) {
      return wallet;
    }

    return this.createWallet({
      ownerType: WalletOwnerType.PLATFORM,
      organizationId,
      currency,
    });
  }

  async ensureOrganizationWalletBySlug(slug: string, currency = 'USD') {
    const organization = await this.prisma.organization.findUnique({
      where: { slug },
    });

    if (!organization) {
      throw new NotFoundException('Organization not found');
    }

    return this.ensureOrganizationWallet(organization.id, currency);
  }

  async getWallet(id: string) {
    const wallet = await this.prisma.wallet.findUnique({
      where: { id },
      include: {
        transactions: {
          orderBy: { createdAt: 'desc' },
          take: 25,
        },
      },
    });

    if (!wallet) {
      throw new NotFoundException('Wallet not found');
    }

    return wallet;
  }

  async fundWallet(id: string, dto: FundWalletDto) {
    const wallet = await this.ensureWallet(id);

    const amount = new Prisma.Decimal(dto.amount);

    const updated = await this.prisma.$transaction(async (tx) => {
      const transaction = await tx.transaction.create({
        data: {
          walletId: wallet.id,
          type: TransactionType.CREDIT,
          status: TransactionStatus.SETTLED,
          amount,
          reference: dto.reference,
        },
      });

      const updatedWallet = await tx.wallet.update({
        where: { id: wallet.id },
        data: {
          balance: wallet.balance.plus(amount),
        },
      });

      return {
        transaction,
        wallet: updatedWallet,
      };
    });

    return updated;
  }

  async debitWallet(id: string, amount: Prisma.Decimal, reference?: string) {
    const wallet = await this.ensureWallet(id);

    if (wallet.balance.minus(wallet.reserved).lessThan(amount)) {
      throw new BadRequestException('Insufficient available funds');
    }

    return this.prisma.$transaction(async (tx) => {
      const transaction = await tx.transaction.create({
        data: {
          walletId: id,
          type: TransactionType.DEBIT,
          status: TransactionStatus.SETTLED,
          amount,
          reference,
        },
      });

      const updatedWallet = await tx.wallet.update({
        where: { id },
        data: {
          balance: wallet.balance.minus(amount),
        },
      });

      return {
        transaction,
        wallet: updatedWallet,
      };
    });
  }

  async holdFunds(id: string, amount: Prisma.Decimal, reference?: string) {
    const wallet = await this.ensureWallet(id);

    if (wallet.balance.minus(wallet.reserved).lessThan(amount)) {
      throw new BadRequestException('Insufficient balance to hold funds');
    }

    return this.prisma.$transaction(async (tx) => {
      const transaction = await tx.transaction.create({
        data: {
          walletId: id,
          type: TransactionType.HOLD,
          status: TransactionStatus.PENDING,
          amount,
          reference,
        },
      });

      const updatedWallet = await tx.wallet.update({
        where: { id },
        data: {
          reserved: wallet.reserved.plus(amount),
        },
      });

      return {
        transaction,
        wallet: updatedWallet,
      };
    });
  }

  async releaseHold(id: string, amount: Prisma.Decimal, reference?: string) {
    const wallet = await this.ensureWallet(id);

    return this.prisma.$transaction(async (tx) => {
      const transaction = await tx.transaction.create({
        data: {
          walletId: id,
          type: TransactionType.RELEASE,
          status: TransactionStatus.SETTLED,
          amount,
          reference,
        },
      });

      const updatedWallet = await tx.wallet.update({
        where: { id },
        data: {
          reserved: wallet.reserved.minus(amount),
          balance: wallet.balance.minus(amount),
        },
      });

      return {
        transaction,
        wallet: updatedWallet,
      };
    });
  }

  async cancelHold(id: string, amount: Prisma.Decimal, reference?: string) {
    const wallet = await this.ensureWallet(id);

    if (wallet.reserved.lessThan(amount)) {
      throw new BadRequestException('No held funds available to cancel');
    }

    return this.prisma.$transaction(async (tx) => {
      const transaction = await tx.transaction.create({
        data: {
          walletId: id,
          type: TransactionType.RELEASE,
          status: TransactionStatus.CANCELLED,
          amount,
          reference,
        },
      });

      const updatedWallet = await tx.wallet.update({
        where: { id },
        data: {
          reserved: wallet.reserved.minus(amount),
        },
      });

      return {
        transaction,
        wallet: updatedWallet,
      };
    });
  }

  async settleEscrow(escrowId: string) {
    const escrow = await this.prisma.escrow.findUnique({
      where: { id: escrowId },
      include: {
        sourceWallet: {
          include: { ownerAgent: { include: { organization: true } } },
        },
        destinationWallet: {
          include: { ownerAgent: { include: { organization: true } } },
        },
        transaction: true,
      },
    });

    if (!escrow) {
      throw new NotFoundException('Escrow not found');
    }

    if (escrow.status !== EscrowStatus.HELD) {
      return escrow;
    }

    const amount = new Prisma.Decimal(escrow.amount);
    const feeBasisPoints = await this.resolveFeeBasisPoints(
      escrow.sourceWallet.ownerAgent?.organizationId ??
        escrow.destinationWallet.ownerAgent?.organizationId ??
        null,
    );

    await this.prisma.$transaction(async (tx) => {
      await tx.wallet.update({
        where: { id: escrow.sourceWalletId },
        data: {
          reserved: escrow.sourceWallet.reserved.minus(amount),
          balance: escrow.sourceWallet.balance.minus(amount),
        },
      });

      await tx.wallet.update({
        where: { id: escrow.destinationWalletId },
        data: {
          balance: escrow.destinationWallet.balance.plus(amount),
        },
      });

      await tx.transaction.update({
        where: { id: escrow.transactionId },
        data: { status: TransactionStatus.SETTLED },
      });

      // Apply platform fee symmetrically to buyer and seller if configured
      if (feeBasisPoints > 0) {
        const feeDecimal = amount
          .times(feeBasisPoints)
          .dividedBy(10000)
          .toDecimalPlaces(2, Prisma.Decimal.ROUND_HALF_UP);

        const platformOrg =
          escrow.destinationWallet.ownerAgent?.organization ??
          escrow.sourceWallet.ownerAgent?.organization ??
          (await tx.organization.findFirst({
            where: { slug: PLATFORM_SLUG },
            orderBy: { createdAt: 'asc' },
          }));

        let platformWallet = platformOrg
          ? await tx.wallet.findFirst({
              where: { organizationId: platformOrg.id, ownerType: WalletOwnerType.PLATFORM },
            })
          : null;

        if (!platformWallet && platformOrg) {
          platformWallet = await tx.wallet.create({
            data: {
              ownerType: WalletOwnerType.PLATFORM,
              organizationId: platformOrg.id,
              currency: escrow.destinationWallet.currency,
              status: WalletStatus.ACTIVE,
            },
          });
        }

        if (platformWallet) {
          // Buyer fee
          await tx.transaction.create({
            data: {
              walletId: escrow.sourceWalletId,
              type: TransactionType.DEBIT,
              status: TransactionStatus.SETTLED,
              amount: feeDecimal,
              reference: `platform-fee-buyer:${escrow.id}`,
            },
          });
          await tx.wallet.update({
            where: { id: escrow.sourceWalletId },
            data: {
              balance: { decrement: feeDecimal },
            },
          });

          // Seller fee (deduct from credited amount)
          await tx.transaction.create({
            data: {
              walletId: escrow.destinationWalletId,
              type: TransactionType.DEBIT,
              status: TransactionStatus.SETTLED,
              amount: feeDecimal,
              reference: `platform-fee-seller:${escrow.id}`,
            },
          });
          await tx.wallet.update({
            where: { id: escrow.destinationWalletId },
            data: {
              balance: { decrement: feeDecimal },
            },
          });

          // Credit platform wallet with both fees
          await tx.transaction.create({
            data: {
              walletId: platformWallet.id,
              type: TransactionType.CREDIT,
              status: TransactionStatus.SETTLED,
              amount: feeDecimal.times(2),
              reference: `platform-fee:${escrow.id}`,
            },
          });
          await tx.wallet.update({
            where: { id: platformWallet.id },
            data: {
              balance: platformWallet.balance.plus(feeDecimal.times(2)),
            },
          });
        }
      }

      await tx.escrow.update({
        where: { id: escrow.id },
        data: {
          status: EscrowStatus.RELEASED,
          releasedAt: new Date(),
        },
      });
    });

    return this.prisma.escrow.findUnique({ where: { id: escrow.id } });
  }

  private async resolveFeeBasisPoints(organizationId: string | null) {
    if (organizationId) {
      const subscription = await this.prisma.organizationSubscription.findUnique({
        where: { organizationId },
        include: { plan: true },
      });

      if (subscription?.plan?.takeRateBasisPoints) {
        return subscription.plan.takeRateBasisPoints;
      }
    }

    return PLATFORM_FEE_BASIS_POINTS;
  }

  private async ensureWallet(id: string) {
    const wallet = await this.prisma.wallet.findUnique({
      where: { id },
    });

    if (!wallet) {
      throw new NotFoundException('Wallet not found');
    }

    return wallet;
  }
}
