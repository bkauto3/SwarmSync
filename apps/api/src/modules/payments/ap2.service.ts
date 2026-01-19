import { Injectable, NotFoundException } from '@nestjs/common';
import { EscrowStatus, Prisma, Transaction, TransactionStatus } from '@prisma/client';

import { PrismaService } from '../database/prisma.service.js';
import { CompleteAp2PaymentDto } from './dto/complete-ap2.dto.js';
import { InitiateAp2PaymentDto } from './dto/initiate-ap2.dto.js';
import { WalletsService } from './wallets.service.js';

@Injectable()
export class Ap2Service {
  constructor(
    private readonly prisma: PrismaService,
    private readonly walletsService: WalletsService,
  ) {}

  async initiate(dto: InitiateAp2PaymentDto) {
    const amount = new Prisma.Decimal(dto.amount);

    const holdResult = await this.walletsService.holdFunds(dto.sourceWalletId, amount, dto.memo);

    const escrow = await this.prisma.escrow.create({
      data: {
        sourceWalletId: dto.sourceWalletId,
        destinationWalletId: dto.destinationWalletId,
        transactionId: holdResult.transaction.id,
        amount,
        releaseCondition: dto.memo,
      },
      include: {
        sourceWallet: true,
        destinationWallet: true,
      },
    });

    return {
      escrow,
      holdTransaction: holdResult.transaction,
    };
  }

  async complete(dto: CompleteAp2PaymentDto) {
    const escrow = await this.prisma.escrow.findUnique({
      where: { id: dto.escrowId },
      include: {
        transaction: true,
      },
    });

    if (!escrow) {
      throw new NotFoundException('Escrow not found');
    }

    const amount = escrow.amount;

    if (dto.status === 'FAILED') {
      await this.walletsService.cancelHold(escrow.sourceWalletId, amount, dto.failureReason);

      await this.prisma.transaction.update({
        where: { id: escrow.transactionId },
        data: {
          status: TransactionStatus.FAILED,
        },
      });

      return this.prisma.escrow.update({
        where: { id: escrow.id },
        data: {
          status: EscrowStatus.REFUNDED,
          refundedAt: new Date(),
        },
      });
    }

    if (dto.status === 'AUTHORIZED') {
      await this.prisma.transaction.update({
        where: { id: escrow.transactionId },
        data: {
          status: TransactionStatus.PENDING,
        },
      });

      return escrow;
    }

    return this.walletsService.settleEscrow(escrow.id);
  }

  async release(escrowId: string, memo?: string) {
    const escrow = await this.prisma.escrow.findUnique({
      where: { id: escrowId },
    });

    if (!escrow) {
      throw new NotFoundException('Escrow not found');
    }

    await this.prisma.transaction.update({
      where: { id: escrow.transactionId },
      data: {
        reference: memo ?? undefined,
      },
    });

    return this.walletsService.settleEscrow(escrowId);
  }

  async directTransfer(
    sourceWalletId: string,
    destinationWalletId: string,
    amount: number,
    reference?: string,
  ): Promise<Transaction> {
    const decimalAmount = new Prisma.Decimal(amount);

    await this.walletsService.debitWallet(sourceWalletId, decimalAmount, reference);
    const credit = await this.walletsService.fundWallet(destinationWalletId, {
      amount,
      reference,
    });

    return credit.transaction;
  }
}
