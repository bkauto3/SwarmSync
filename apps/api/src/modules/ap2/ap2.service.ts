import {
  BadRequestException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import {
  Agent,
  AgentCollaboration,
  BudgetApprovalMode,
  CollaborationStatus,
  InitiatorType,
  OutcomeVerificationStatus,
  Prisma,
  Wallet,
} from '@prisma/client';
import { isUUID } from 'class-validator';

import { PrismaService } from '../database/prisma.service.js';
import { Ap2Service as PaymentsAp2Service } from '../payments/ap2.service.js';
import { WalletsService } from '../payments/wallets.service.js';
import { OutcomesService } from '../quality/outcomes.service.js';
import { NegotiationRequestDto } from './dto/negotiation-request.dto.js';
import {
  NegotiationResponseStatus,
  RespondNegotiationDto,
} from './dto/respond-negotiation.dto.js';
import { ServiceDeliveryDto } from './dto/service-delivery.dto.js';
import { Ap2PaymentPurpose } from '../payments/dto/initiate-ap2.dto.js';

type NegotiationPayload = {
  requestedService: string;
  budget: number;
  requirements: Prisma.JsonValue | null;
  notes: string | null;
  initiatedByUserId: string | null;
};

type NegotiationCounterPayload = {
  status: NegotiationResponseStatus | null;
  price: number | null;
  estimatedDelivery: string | null;
  terms: Prisma.JsonValue | null;
  notes: string | null;
};

type NegotiationWithRelations = AgentCollaboration & {
  requesterAgent?: Pick<Agent, 'id' | 'name' | 'slug'> | null;
  responderAgent?: Pick<Agent, 'id' | 'name' | 'slug'> | null;
  serviceAgreement?: Prisma.ServiceAgreementGetPayload<{
    include: {
      escrow: {
        include: {
          transaction: true;
        };
      };
      verifications: {
        orderBy: { createdAt: 'desc' };
        take: 1;
      };
    };
  }> | null;
};

@Injectable()
export class AP2Service {
  constructor(
    private readonly prisma: PrismaService,
    private readonly walletsService: WalletsService,
    private readonly paymentsAp2Service: PaymentsAp2Service,
    private readonly outcomesService: OutcomesService,
  ) {}

  async initiateNegotiation(payload: NegotiationRequestDto & { initiatedByUserId?: string }) {
    if (payload.requesterAgentId === payload.responderAgentId) {
      throw new BadRequestException('Requester and responder must differ');
    }

    const [requester, responder] = await Promise.all([
      this.ensureAgentExists(payload.requesterAgentId),
      this.ensureAgentExists(payload.responderAgentId),
    ]);

    const amount = new Prisma.Decimal(payload.budget);
    await this.ensureAgentBudget(payload.requesterAgentId, amount);

    const negotiationPayload: NegotiationPayload = {
      requestedService: payload.requestedService,
      budget: payload.budget,
      requirements: this.toJsonValue(payload.requirements),
      notes: payload.notes ?? null,
      initiatedByUserId: payload.initiatedByUserId ?? null,
    };

    const negotiation = await this.prisma.agentCollaboration.create({
      data: {
        requesterAgentId: payload.requesterAgentId,
        responderAgentId: payload.responderAgentId,
        status: CollaborationStatus.PENDING,
        payload: negotiationPayload as Prisma.InputJsonValue,
      },
      include: this.baseNegotiationInclude,
    });

    return this.presentNegotiation(negotiation, requester, responder);
  }

  async respondToNegotiation(payload: RespondNegotiationDto) {
    const negotiation = await this.prisma.agentCollaboration.findUnique({
      where: { id: payload.negotiationId },
      include: this.baseNegotiationInclude,
    });

    if (!negotiation) {
      throw new NotFoundException('Negotiation not found');
    }

    if (negotiation.responderAgentId !== payload.responderAgentId) {
      throw new BadRequestException('Responder agent mismatch');
    }

    if (
      negotiation.status !== CollaborationStatus.PENDING &&
      negotiation.status !== CollaborationStatus.COUNTERED
    ) {
      throw new BadRequestException('Negotiation no longer actionable');
    }

    const basePayload = (negotiation.payload as NegotiationPayload | null) ?? null;
    if (!basePayload) {
      throw new BadRequestException('Negotiation payload missing');
    }

    switch (payload.status) {
      case NegotiationResponseStatus.ACCEPTED:
        return this.acceptNegotiation(negotiation, basePayload, payload);
      case NegotiationResponseStatus.REJECTED: {
        const updated = await this.prisma.agentCollaboration.update({
          where: { id: negotiation.id },
          data: {
            status: CollaborationStatus.DECLINED,
            counterPayload: this.buildCounterPayload({
              status: payload.status,
              notes: payload.notes,
            }),
          },
          include: this.baseNegotiationInclude,
        });

        return this.presentNegotiation(
          updated,
          negotiation.requesterAgent,
          negotiation.responderAgent,
        );
      }
      case NegotiationResponseStatus.COUNTERED: {
        const updated = await this.prisma.agentCollaboration.update({
          where: { id: negotiation.id },
          data: {
            status: CollaborationStatus.COUNTERED,
            counterPayload: this.buildCounterPayload({
              status: payload.status,
              price: payload.price,
              estimatedDelivery: payload.estimatedDelivery,
              terms: payload.terms,
              notes: payload.notes,
            }),
          },
          include: this.baseNegotiationInclude,
        });

        return this.presentNegotiation(
          updated,
          negotiation.requesterAgent,
          negotiation.responderAgent,
        );
      }
      default:
        throw new BadRequestException('Unsupported negotiation response');
    }
  }

  async deliverService(payload: ServiceDeliveryDto & { deliveredByUserId?: string | null }) {
    const negotiation = await this.prisma.agentCollaboration.findUnique({
      where: { id: payload.negotiationId },
      include: {
        requesterAgent: true,
        responderAgent: true,
        serviceAgreement: {
          include: {
            escrow: {
              include: {
                transaction: true,
              },
            },
          },
        },
      },
    });

    if (!negotiation) {
      throw new NotFoundException('Negotiation not found');
    }

    if (negotiation.responderAgentId !== payload.responderAgentId) {
      throw new BadRequestException('Responder agent mismatch');
    }

    if (
      negotiation.status !== CollaborationStatus.ACCEPTED ||
      !negotiation.serviceAgreement ||
      !negotiation.serviceAgreement.escrowId
    ) {
      throw new BadRequestException('Negotiation is not ready for delivery');
    }

    const nextStatus = this.determineVerificationStatus(payload);
    const reviewerId =
      payload.deliveredByUserId && isUUID(payload.deliveredByUserId)
        ? payload.deliveredByUserId
        : undefined;

    const verification = await this.outcomesService.recordVerification(
      negotiation.serviceAgreement.id,
      {
        status: nextStatus,
        escrowId: negotiation.serviceAgreement.escrowId,
        evidence: {
          result: payload.result ?? {},
          evidence: payload.evidence ?? null,
        },
        notes: payload.notes,
        reviewerId,
      },
    );

    if (verification.status === OutcomeVerificationStatus.VERIFIED) {
      const escrowAmount =
        negotiation.serviceAgreement?.escrow?.amount ?? new Prisma.Decimal(0);

      await this.recordEngagementMetric(
        negotiation.requesterAgentId,
        negotiation.responderAgentId,
        escrowAmount,
      );
    }

    return verification;
  }

  async getNegotiation(id: string) {
    const negotiation = await this.prisma.agentCollaboration.findUnique({
      where: { id },
      include: this.baseNegotiationInclude,
    });

    if (!negotiation) {
      throw new NotFoundException('Negotiation not found');
    }

    return this.presentNegotiation(
      negotiation,
      negotiation.requesterAgent,
      negotiation.responderAgent,
    );
  }

  async getAgentNegotiations(agentId?: string) {
    if (!agentId) {
      throw new BadRequestException('agentId is required');
    }

    await this.ensureAgentExists(agentId);

    const negotiations = await this.prisma.agentCollaboration.findMany({
      where: {
        OR: [{ requesterAgentId: agentId }, { responderAgentId: agentId }],
      },
      include: this.baseNegotiationInclude,
      orderBy: { updatedAt: 'desc' },
      take: 100,
    });

    return negotiations.map((negotiation) =>
      this.presentNegotiation(
        negotiation,
        negotiation.requesterAgent,
        negotiation.responderAgent,
      ),
    );
  }

  async cancelNegotiation(id: string) {
    const negotiation = await this.prisma.agentCollaboration.findUnique({
      where: { id },
    });

    if (!negotiation) {
      throw new NotFoundException('Negotiation not found');
    }

    if (negotiation.status !== CollaborationStatus.PENDING) {
      throw new BadRequestException('Only pending negotiations can be cancelled');
    }

    await this.prisma.agentCollaboration.update({
      where: { id },
      data: {
        status: CollaborationStatus.DECLINED,
      },
    });

    return { id, status: CollaborationStatus.DECLINED };
  }

  async getTransactionStatus(transactionId: string) {
    const [transaction, escrow] = await Promise.all([
      this.prisma.transaction.findUnique({
        where: { id: transactionId },
      }),
      this.prisma.escrow.findUnique({
        where: { transactionId },
        include: {
          serviceAgreement: {
            include: {
              ap2Negotiation: {
                include: this.baseNegotiationInclude,
              },
            },
          },
        },
      }),
    ]);

    if (!transaction || !escrow) {
      throw new NotFoundException('Transaction not found');
    }

    return {
      transaction,
      escrow,
      negotiation: escrow.serviceAgreement?.ap2Negotiation
        ? this.presentNegotiation(
            escrow.serviceAgreement.ap2Negotiation,
            escrow.serviceAgreement.ap2Negotiation.requesterAgent,
            escrow.serviceAgreement.ap2Negotiation.responderAgent,
          )
        : null,
    };
  }

  async listTransactionsForAgent(agentId: string) {
    await this.ensureAgentExists(agentId);

    const negotiations = await this.prisma.agentCollaboration.findMany({
      where: {
        OR: [{ requesterAgentId: agentId }, { responderAgentId: agentId }],
      },
      include: this.baseNegotiationInclude,
      orderBy: { updatedAt: 'desc' },
      take: 50,
    });

    return negotiations.map((negotiation) => ({
      ...this.presentNegotiation(
        negotiation,
        negotiation.requesterAgent,
        negotiation.responderAgent,
      ),
      serviceAgreementId: negotiation.serviceAgreementId,
      escrowId: negotiation.serviceAgreement?.escrowId ?? null,
      transaction: negotiation.serviceAgreement?.escrow?.transaction ?? null,
    }));
  }

  private async acceptNegotiation(
    negotiation: NegotiationWithRelations,
    basePayload: NegotiationPayload,
    payload: RespondNegotiationDto,
  ) {
    if (!payload.price) {
      throw new BadRequestException('Price is required when accepting');
    }

    if (payload.price > basePayload.budget) {
      throw new BadRequestException('Price exceeds proposed budget');
    }

    const priceDecimal = new Prisma.Decimal(payload.price);
    const { wallet: requesterWallet } = await this.ensureBudgetCapacity(
      negotiation.requesterAgentId,
      priceDecimal,
    );
    const responderWallet = await this.walletsService.ensureAgentWallet(negotiation.responderAgentId);

    const { escrow } = await this.paymentsAp2Service.initiate({
      sourceWalletId: requesterWallet.id,
      destinationWalletId: responderWallet.id,
      amount: priceDecimal.toNumber(),
      purpose: Ap2PaymentPurpose.AGENT_HIRE,
      memo: `ap2:${negotiation.id}`,
      metadata: {
        negotiationId: negotiation.id,
        requestedService: basePayload.requestedService,
      },
    });

    const agreement = await this.outcomesService.createAgreement({
      agentId: negotiation.responderAgentId,
      buyerId: undefined,
      escrowId: escrow.id,
      outcomeType: 'GENERIC',
      targetDescription: basePayload.requestedService,
    });

    await this.consumeAgentBudget(negotiation.requesterAgentId, priceDecimal);

    const updated = await this.prisma.agentCollaboration.update({
      where: { id: negotiation.id },
      data: {
        status: CollaborationStatus.ACCEPTED,
        counterPayload: this.buildCounterPayload({
          status: payload.status,
          price: payload.price,
          estimatedDelivery: payload.estimatedDelivery,
          terms: payload.terms,
          notes: payload.notes,
        }),
        serviceAgreementId: agreement.id,
      },
      include: this.baseNegotiationInclude,
    });

    return this.presentNegotiation(updated, negotiation.requesterAgent, negotiation.responderAgent);
  }

  private buildCounterPayload(input: {
    status: NegotiationResponseStatus;
    price?: number;
    estimatedDelivery?: string;
    terms?: Record<string, unknown>;
    notes?: string;
  }): NegotiationCounterPayload {
    return {
      status: input.status,
      price: input.price ?? null,
      estimatedDelivery: input.estimatedDelivery ?? null,
      terms: this.toJsonValue(input.terms),
      notes: input.notes ?? null,
    };
  }

  private toJsonValue(value?: Record<string, unknown> | null): Prisma.JsonValue | null {
    if (value == null) {
      return null;
    }
    return value as Prisma.JsonValue;
  }

  private get baseNegotiationInclude() {
    return {
      requesterAgent: {
        select: { id: true, name: true, slug: true },
      },
      responderAgent: {
        select: { id: true, name: true, slug: true },
      },
      serviceAgreement: {
        include: {
          escrow: {
            include: {
              transaction: true,
            },
          },
          verifications: {
            orderBy: { createdAt: 'desc' as Prisma.SortOrder },
            take: 1,
          },
        },
      },
    } satisfies Prisma.AgentCollaborationInclude;
  }

  private presentNegotiation(
    negotiation: NegotiationWithRelations,
    requester?: Pick<Agent, 'id' | 'name' | 'slug'> | null,
    responder?: Pick<Agent, 'id' | 'name' | 'slug'> | null,
  ) {
    const payload = (negotiation.payload as NegotiationPayload | null) ?? null;
    const counterPayload = (negotiation.counterPayload as NegotiationCounterPayload | null) ?? null;
    const escrow = negotiation.serviceAgreement?.escrow ?? null;
    const transaction = escrow?.transaction ?? null;
    const verification = negotiation.serviceAgreement?.verifications?.[0] ?? null;

    return {
      id: negotiation.id,
      status: negotiation.status,
      requesterAgent: requester ?? negotiation.requesterAgent ?? null,
      responderAgent: responder ?? negotiation.responderAgent ?? null,
      requestedService: payload?.requestedService ?? null,
      proposedBudget: payload?.budget ?? null,
      requirements: payload?.requirements ?? null,
      counter: counterPayload,
      serviceAgreementId: negotiation.serviceAgreementId ?? null,
      escrowId: escrow?.id ?? null,
      transaction: transaction
        ? {
            id: transaction.id,
            status: transaction.status,
            amount: transaction.amount,
            settledAt: transaction.settledAt,
          }
        : null,
      verificationStatus: verification?.status ?? null,
      verificationUpdatedAt: verification?.verifiedAt ?? verification?.createdAt ?? null,
      createdAt: negotiation.createdAt,
      updatedAt: negotiation.updatedAt,
    };
  }

  private async ensureAgentExists(agentId: string) {
    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
    });

    if (!agent) {
      throw new NotFoundException('Agent not found');
    }

    return agent;
  }

  private async ensureAgentBudget(agentId: string, amount: Prisma.Decimal) {
    await this.ensureBudgetCapacity(agentId, amount);
  }

  private async ensureBudgetCapacity(agentId: string, amount: Prisma.Decimal) {
    const wallet = await this.walletsService.ensureAgentWallet(agentId);

    this.assertWalletCanSpend(wallet, amount);

    const budget = await this.prisma.agentBudget.findFirst({
      where: { agentId },
      orderBy: { updatedAt: 'desc' },
    });

    if (budget) {
      if (budget.approvalMode === BudgetApprovalMode.MANUAL) {
        throw new BadRequestException('Manual approval required before initiating spend');
      }

      if (budget.remaining.lessThan(amount)) {
        throw new BadRequestException('Agent budget exhausted');
      }
    }

    return { wallet, budget };
  }

  private async consumeAgentBudget(agentId: string, amount: Prisma.Decimal) {
    const budget = await this.prisma.agentBudget.findFirst({
      where: { agentId },
      orderBy: { updatedAt: 'desc' },
    });

    if (!budget) {
      return;
    }

    const nextRemaining = budget.remaining.minus(amount);
    if (nextRemaining.lessThan(0)) {
      throw new BadRequestException('Agent budget exhausted');
    }

    await this.prisma.agentBudget.update({
      where: { id: budget.id },
      data: {
          remaining: nextRemaining,
      },
    });
  }

  private assertWalletCanSpend(wallet: Wallet, amount: Prisma.Decimal) {
    const available = wallet.balance.minus(wallet.reserved);
    if (available.lessThan(amount)) {
      throw new BadRequestException('Insufficient available funds');
    }

    if (wallet.spendCeiling && amount.greaterThan(wallet.spendCeiling)) {
      throw new BadRequestException('Amount exceeds per-transaction limit');
    }
  }

  private async recordEngagementMetric(
    agentId: string,
    counterAgentId: string,
    amount: Prisma.Decimal,
  ) {
    if (amount.lessThanOrEqualTo(0)) {
      return;
    }

    await this.prisma.agentEngagementMetric.upsert({
      where: {
        agentId_counterAgentId_initiatorType: {
          agentId,
          counterAgentId,
          initiatorType: InitiatorType.AGENT,
        },
      },
      update: {
        a2aCount: { increment: 1 },
        totalSpend: { increment: amount },
        lastInteraction: new Date(),
      },
      create: {
        agentId,
        counterAgentId,
        initiatorType: InitiatorType.AGENT,
        a2aCount: 1,
        totalSpend: amount,
        lastInteraction: new Date(),
      },
    });
  }

  private determineVerificationStatus(
    payload: ServiceDeliveryDto,
  ): OutcomeVerificationStatus {
    const resultStatus =
      typeof payload.result?.status === 'string'
        ? payload.result.status.toLowerCase()
        : null;
    if (resultStatus === 'failed') {
      return OutcomeVerificationStatus.REJECTED;
    }

    const autoApprove =
      (payload.evidence as Record<string, unknown> | undefined)?.['autoApprove'] === true ||
      resultStatus === 'success';

    if (autoApprove) {
      return OutcomeVerificationStatus.VERIFIED;
    }

    return OutcomeVerificationStatus.PENDING;
  }
}
