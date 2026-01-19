import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import {
  AgentStatus,
  AgentVisibility,
  BudgetApprovalMode,
  CertificationStatus,
  ExecutionStatus,
  InitiatorType,
  PaymentEventStatus,
  Prisma,
  ReviewStatus,
  VerificationStatus,
  type Wallet as WalletModel,
} from '@prisma/client';

import { presentAgent, presentExecution, presentReview } from './agents.presenter.js';
import { TriggerService } from './trigger.service.js';
import { PrismaService } from '../database/prisma.service.js';
import { Ap2Service } from '../payments/ap2.service.js';
import { WalletsService } from '../payments/wallets.service.js';
import { AgentDiscoveryQueryDto } from './dto/agent-discovery-query.dto.js';
import { CreateAgentDto } from './dto/create-agent.dto.js';
import { ExecuteAgentDto } from './dto/execute-agent.dto.js';
import { ReviewAgentDto } from './dto/review-agent.dto.js';
import { SubmitForReviewDto } from './dto/submit-for-review.dto.js';
import { UpdateAgentDto } from './dto/update-agent.dto.js';
import { UpdateAgentBudgetDto } from './dto/update-budget.dto.js';

const slugify = (value: string) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

type AgentDiscoveryAgent = Prisma.AgentGetPayload<{
  include: {
    certifications: true;
    metricsPrimary: true;
  };
}>;

@Injectable()
export class AgentsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly walletsService: WalletsService,
    private readonly ap2Service: Ap2Service,
    private readonly triggerService: TriggerService,
  ) { }

  async create(data: CreateAgentDto) {
    const slug = slugify(`${data.name}-${Date.now()}`);

    const agent = await this.prisma.agent.create({
      data: {
        slug,
        name: data.name,
        description: data.description,
        categories: data.categories,
        tags: data.tags ?? [],
        pricingModel: data.pricingModel,
        visibility: data.visibility ?? AgentVisibility.PUBLIC,
        creatorId: data.creatorId,
        basePriceCents: data.basePriceCents ?? null,
        inputSchema: (data.inputSchema ?? Prisma.JsonNull) as Prisma.InputJsonValue,
        outputSchema: (data.outputSchema ?? Prisma.JsonNull) as Prisma.InputJsonValue,
        ap2Endpoint: data.ap2Endpoint ?? null,
      },
    });

    return presentAgent(agent);
  }

  async findAll(params?: {
    status?: AgentStatus;
    visibility?: AgentVisibility;
    category?: string;
    tag?: string;
    search?: string;
    verifiedOnly?: boolean;
    creatorId?: string;
    showAll?: boolean;
    userId?: string;
    organizationId?: string;
  }) {
    const where: Prisma.AgentWhereInput = {};
    try {
      // Status filter
      const hasStatusFilter = params?.status !== undefined;
      if (hasStatusFilter) {
        where.status = params.status;
      }

      // Visibility filter with user context
      const hasVisibilityFilter = params?.visibility !== undefined;
      if (hasVisibilityFilter) {
        where.visibility = params.visibility;
      }

      // Only apply default PUBLIC/APPROVED filter if showAll is not true and no explicit filters are set
      // This allows authenticated users to see all agents by setting showAll=true
      if (!params?.showAll && !hasStatusFilter && !hasVisibilityFilter && !params?.creatorId) {
        // Apply visibility-based filtering
        if (params?.userId) {
          // Authenticated user: show PUBLIC, PRIVATE (own), and ORGANIZATION (if in org)
          const visibilityConditions: Prisma.AgentWhereInput[] = [
            { visibility: AgentVisibility.PUBLIC },
            { visibility: AgentVisibility.PRIVATE, creatorId: params.userId },
          ];

          if (params.organizationId) {
            visibilityConditions.push({
              visibility: AgentVisibility.ORGANIZATION,
              organizationId: params.organizationId,
            });
          }

          where.OR = visibilityConditions;
        } else {
          // Unauthenticated user: only show PUBLIC agents
          where.visibility = AgentVisibility.PUBLIC;
        }
        where.status = AgentStatus.APPROVED;
      }

      // Category filter
      if (params?.category) {
        where.categories = {
          has: params.category,
        };
      }

      // Tag filter
      if (params?.tag) {
        where.tags = {
          has: params.tag,
        };
      }

      // Verified only filter
      if (params?.verifiedOnly) {
        where.verificationStatus = VerificationStatus.VERIFIED;
      }

      // Search filter
      if (params?.search?.trim()) {
        const term = params.search.trim();
        where.OR = [
          { name: { contains: term, mode: 'insensitive' } },
          { description: { contains: term, mode: 'insensitive' } },
        ];
      }

      // Creator filter
      if (params?.creatorId) {
        where.creatorId = params.creatorId;
      }

      const agents = await this.prisma.agent.findMany({
        where,
        orderBy: {
          updatedAt: 'desc',
        },
      });

      return agents.map(presentAgent);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error fetching agents:', error);
      // Fallback: if the badges column is missing in prod DB, attempt to create it once and retry
      const message = error instanceof Error ? error.message : '';
      if (message.includes('Agent.badges')) {
        // eslint-disable-next-line no-console
        console.warn('Missing Agent.badges column detected. Attempting to add column automatically.');
        try {
          await this.prisma.$executeRawUnsafe(
            'ALTER TABLE "Agent" ADD COLUMN IF NOT EXISTS "badges" TEXT[] DEFAULT ARRAY[]::TEXT[];',
          );
          const agents = await this.prisma.agent.findMany({
            where,
            orderBy: {
              updatedAt: 'desc',
            },
          });
          return agents.map(presentAgent);
        } catch (migrateError) {
          // eslint-disable-next-line no-console
          console.error('Failed to auto-add badges column:', migrateError);
        }
      }
      // Re-throw with more context
      if (error instanceof Error) {
        throw new BadRequestException(`Failed to fetch agents: ${error.message}`);
      }
      throw new BadRequestException('Failed to fetch agents. Please try again later.');
    }
  }

  async findOne(id: string) {
    const agent = await this.prisma.agent.findUnique({
      where: { id },
    });

    if (!agent) {
      throw new NotFoundException('Agent not found');
    }

    return presentAgent(agent);
  }

  async findBySlug(slug: string) {
    const agent = await this.prisma.agent.findUnique({
      where: { slug },
    });

    if (!agent) {
      throw new NotFoundException('Agent not found');
    }

    return presentAgent(agent);
  }

  async update(id: string, data: UpdateAgentDto) {
    await this.ensureExists(id);
    const agent = await this.prisma.agent.findUnique({ where: { id } });
    if (!agent) {
      throw new NotFoundException('Agent not found');
    }

    const { categories, tags, ...rest } = data;

    const updatedAgent = await this.prisma.agent.update({
      where: { id },
      data: {
        ...rest,
        categories: categories ?? undefined,
        tags: tags ?? undefined,
        basePriceCents: data.basePriceCents ?? undefined,
        inputSchema:
          data.inputSchema === undefined
            ? undefined
            : ((data.inputSchema ?? Prisma.JsonNull) as Prisma.InputJsonValue),
        outputSchema:
          data.outputSchema === undefined
            ? undefined
            : ((data.outputSchema ?? Prisma.JsonNull) as Prisma.InputJsonValue),
        ap2Endpoint: data.ap2Endpoint ?? undefined,
      },
    });

    return presentAgent(updatedAgent);
  }

  async submitForReview(id: string, data: SubmitForReviewDto) {
    await this.ensureExists(id);

    const agent = await this.prisma.agent.update({
      where: { id },
      data: {
        status: AgentStatus.PENDING,
      },
    });

    if (data.notes) {
      await this.prisma.agentReview.create({
        data: {
          agentId: id,
          reviewerId: data.reviewerId,
          status: ReviewStatus.NEEDS_WORK,
          notes: data.notes,
        },
      });
    }

    // Trigger autonomous verification
    this.triggerService.triggerAgentVerification(
      id,
      agent.ap2Endpoint ?? undefined,
      agent.inputSchema as unknown,
      agent.outputSchema as unknown
    ).catch(error => {
      console.error(`Failed to trigger verification for agent ${id}:`, error);
    });

    return presentAgent(agent);
  }

  async reviewAgent(id: string, data: ReviewAgentDto) {
    await this.ensureExists(id);

    const agent = await this.prisma.agent.update({
      where: { id },
      data: {
        status: data.targetStatus,
      },
    });

    const review = await this.prisma.agentReview.create({
      data: {
        agentId: id,
        reviewerId: data.reviewerId,
        status: data.reviewStatus,
        notes: data.notes,
      },
    });

    return {
      agent: presentAgent(agent),
      review: presentReview(review),
    };
  }

  async executeAgent(id: string, data: ExecuteAgentDto) {
    await this.ensureExists(id);
    const agentRecord = await this.prisma.agent.findUnique({ where: { id } });
    if (!agentRecord) {
      throw new NotFoundException('Agent not found');
    }
    const parsedInput = this.safeParseJson(data.input);
    const initiatorType = data.initiatorType ?? InitiatorType.USER;

    const paymentAmount = data.budget ? new Prisma.Decimal(data.budget) : new Prisma.Decimal(5);

    const fundingWallet = await this.resolveFundingWallet({
      initiatorType,
      initiatorUserId: data.initiatorId,
      initiatorAgentId: data.initiatorAgentId,
      sourceWalletId: data.sourceWalletId,
      amount: paymentAmount,
    });

    const execution = await this.prisma.agentExecution.create({
      data: {
        agentId: id,
        initiatorId: data.initiatorId,
        initiatorType,
        sourceWalletId: fundingWallet.id,
        input: parsedInput,
        status: ExecutionStatus.SUCCEEDED,
        output: {
          message: 'Execution simulated',
          jobReference: data.jobReference ?? null,
        },
        completedAt: new Date(),
      },
    });

    const agentWallet = await this.walletsService.ensureAgentWallet(id);

    const paymentTransaction = await this.ap2Service.directTransfer(
      fundingWallet.id,
      agentWallet.id,
      paymentAmount.toNumber(),
      data.jobReference ?? `execution:${execution.id}`,
    );

    await this.recordPaymentEvent({
      transactionId: paymentTransaction.id,
      sourceWalletId: fundingWallet.id,
      destinationWalletId: agentWallet.id,
      amount: paymentAmount,
      initiatorType,
    });

    const counterAgentId =
      initiatorType === InitiatorType.AGENT ? data.initiatorAgentId ?? null : null;
    await this.recordAgentEngagement(id, counterAgentId, initiatorType, paymentAmount);

    const nextTrustScore = Math.min(100, agentRecord.trustScore + 1);
    await this.prisma.agent.update({
      where: { id },
      data: {
        successCount: { increment: 1 },
        trustScore: nextTrustScore,
        lastExecutedAt: new Date(),
      },
    });

    return {
      execution: presentExecution(execution),
      paymentTransaction,
    };
  }

  async listExecutions(agentId: string) {
    await this.ensureExists(agentId);

    const executions = await this.prisma.agentExecution.findMany({
      where: { agentId },
      orderBy: { createdAt: 'desc' },
      take: 25,
    });

    return executions.map(presentExecution);
  }

  async listReviews(agentId: string) {
    await this.ensureExists(agentId);

    const reviews = await this.prisma.agentReview.findMany({
      where: { agentId },
      orderBy: { createdAt: 'desc' },
      take: 25,
    });

    return reviews.map(presentReview);
  }

  async discover(filters: AgentDiscoveryQueryDto) {
    const normalizedCapability = filters.capability?.trim();
    const normalizedLimit = Math.min(Math.max(filters.limit ?? 20, 1), 100);

    const where: Prisma.AgentWhereInput = {
      status: AgentStatus.APPROVED,
      visibility: AgentVisibility.PUBLIC,
    };

    if (normalizedCapability) {
      where.OR = [
        { categories: { has: normalizedCapability } },
        { tags: { has: normalizedCapability } },
      ];
    }

    if (typeof filters.maxPriceCents === 'number') {
      where.basePriceCents = { lte: filters.maxPriceCents };
    }

    if (filters.certificationRequired) {
      where.certifications = {
        some: { status: CertificationStatus.CERTIFIED },
      };
    }

    if (typeof filters.minRating === 'number') {
      const trustThreshold = Math.min(100, Math.max(0, Math.round(filters.minRating * 20)));
      where.trustScore = { gte: trustThreshold };
    }

    const total = await this.prisma.agent.count({ where });

    const agents = await this.prisma.agent.findMany({
      where,
      orderBy:
        typeof filters.maxPriceCents === 'number'
          ? [{ basePriceCents: 'asc' }, { updatedAt: 'desc' }]
          : [{ updatedAt: 'desc' }],
      cursor: filters.cursor ? { id: filters.cursor } : undefined,
      skip: filters.cursor ? 1 : 0,
      take: normalizedLimit + 1,
      include: {
        certifications: {
          where: { status: CertificationStatus.CERTIFIED },
          orderBy: { updatedAt: 'desc' },
          take: 1,
        },
        metricsPrimary: true,
      },
    });

    const hasNext = agents.length > normalizedLimit;
    const trimmed = hasNext ? agents.slice(0, -1) : agents;
    const nextCursor = hasNext ? agents[agents.length - 1].id : null;

    return {
      total,
      nextCursor,
      agents: trimmed.map((agent) => this.presentDiscoveryAgent(agent)),
    };
  }

  async getAgentSchema(id: string) {
    const agent = await this.prisma.agent.findUnique({
      where: { id },
      select: {
        id: true,
        slug: true,
        name: true,
        description: true,
        categories: true,
        tags: true,
        pricingModel: true,
        basePriceCents: true,
        inputSchema: true,
        outputSchema: true,
        ap2Endpoint: true,
      },
    });

    if (!agent) {
      throw new NotFoundException('Agent not found');
    }

    return {
      id: agent.id,
      slug: agent.slug,
      name: agent.name,
      description: agent.description,
      categories: agent.categories,
      tags: agent.tags,
      pricing: {
        model: agent.pricingModel,
        basePriceCents: agent.basePriceCents ?? null,
        currency: 'USD',
      },
      ap2Endpoint: agent.ap2Endpoint ?? null,
      schemas: {
        input: agent.inputSchema ?? null,
        output: agent.outputSchema ?? null,
      },
    };
  }

  async getAgentBudget(agentId: string) {
    await this.ensureExists(agentId);
    const wallet = await this.walletsService.ensureAgentWallet(agentId);
    const budget = await this.ensureBudgetRecord(agentId, wallet.id);
    return this.presentBudgetSnapshot(budget, wallet);
  }

  async getAgentPaymentHistory(agentId: string) {
    await this.ensureExists(agentId);

    const wallets = await this.prisma.wallet.findMany({
      where: { ownerAgentId: agentId },
      include: {
        transactions: {
          orderBy: { createdAt: 'desc' },
          take: 50,
        },
      },
    });

    const platformTransactions = wallets.flatMap((wallet) =>
      wallet.transactions.map((transaction) => ({
        id: transaction.id,
        rail: 'platform' as const,
        type: transaction.type,
        amount: Number(transaction.amount),
        currency: wallet.currency,
        status: transaction.status,
        reference: transaction.reference,
        metadata: transaction.metadata,
        createdAt: transaction.createdAt,
        walletId: wallet.id,
      })),
    );

    const x402Transactions = await this.prisma.x402Transaction.findMany({
      where: { agentId },
      orderBy: { createdAt: 'desc' },
      take: 50,
    });

    const cryptoTransactions = x402Transactions.map((transaction) => ({
      id: transaction.id,
      rail: 'x402' as const,
      type: 'X402',
      amount: Number(transaction.amount),
      currency: transaction.currency,
      status: transaction.status,
      reference: transaction.txHash,
      txHash: transaction.txHash,
      buyerAddress: transaction.buyerAddress,
      sellerAddress: transaction.sellerAddress,
      network: transaction.network,
      createdAt: transaction.createdAt,
    }));

    return [...platformTransactions, ...cryptoTransactions]
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 50);
  }

  async updateAgentBudget(agentId: string, dto: UpdateAgentBudgetDto) {
    await this.ensureExists(agentId);
    let wallet = await this.walletsService.ensureAgentWallet(agentId);
    let budget = await this.ensureBudgetRecord(agentId, wallet.id);

    const budgetUpdate: Prisma.AgentBudgetUpdateInput = {};
    let budgetTouched = false;

    if (dto.monthlyLimit !== undefined) {
      const nextLimit = new Prisma.Decimal(dto.monthlyLimit);
      const spent = budget.monthlyLimit.minus(budget.remaining);
      let remaining = nextLimit.minus(spent);
      if (remaining.lessThan(0)) {
        remaining = new Prisma.Decimal(0);
      }
      budgetUpdate.monthlyLimit = nextLimit;
      budgetUpdate.remaining = remaining;
      budgetTouched = true;
    }

    if (dto.approvalMode) {
      budgetUpdate.approvalMode = dto.approvalMode;
      budgetTouched = true;
    } else if (typeof dto.autoReload === 'boolean') {
      budgetUpdate.approvalMode = dto.autoReload ? BudgetApprovalMode.AUTO : BudgetApprovalMode.MANUAL;
      budgetTouched = true;
    }

    if (budgetTouched) {
      budget = await this.prisma.agentBudget.update({
        where: { id: budget.id },
        data: budgetUpdate,
      });
    }

    const walletUpdate: Prisma.WalletUpdateInput = {};
    let walletTouched = false;

    if (dto.perTransactionLimit !== undefined) {
      walletUpdate.spendCeiling =
        dto.perTransactionLimit === null ? null : new Prisma.Decimal(dto.perTransactionLimit);
      walletTouched = true;
    }

    if (dto.approvalThreshold !== undefined) {
      walletUpdate.autoApproveThreshold =
        dto.approvalThreshold === null ? null : new Prisma.Decimal(dto.approvalThreshold);
      walletTouched = true;
    }

    if (walletTouched) {
      await this.prisma.wallet.update({
        where: { id: wallet.id },
        data: walletUpdate,
      });
      wallet = await this.prisma.wallet.findUniqueOrThrow({ where: { id: wallet.id } });
    }

    return this.presentBudgetSnapshot(budget, wallet);
  }

  async listAgentA2aTransactions(agentId: string) {
    await this.ensureExists(agentId);

    const collaborations = await this.prisma.agentCollaboration.findMany({
      where: {
        OR: [{ requesterAgentId: agentId }, { responderAgentId: agentId }],
      },
      include: {
        requesterAgent: { select: { id: true, name: true, slug: true } },
        responderAgent: { select: { id: true, name: true, slug: true } },
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
      orderBy: { updatedAt: 'desc' },
      take: 50,
    });

    return collaborations.map((collaboration) => {
      const payload = this.safeParseJson(collaboration.payload as Record<string, unknown> | undefined);
      const counterPayload = this.safeParseJson(
        collaboration.counterPayload as Record<string, unknown> | undefined,
      );
      const escrow = collaboration.serviceAgreement?.escrow ?? null;
      const transaction = escrow?.transaction ?? null;

      return {
        id: collaboration.id,
        status: collaboration.status,
        requesterAgent: collaboration.requesterAgent
          ? {
            id: collaboration.requesterAgent.id,
            name: collaboration.requesterAgent.name,
            slug: collaboration.requesterAgent.slug,
          }
          : null,
        responderAgent: collaboration.responderAgent
          ? {
            id: collaboration.responderAgent.id,
            name: collaboration.responderAgent.name,
            slug: collaboration.responderAgent.slug,
          }
          : null,
        requestedService:
          typeof payload.requestedService === 'string' ? (payload.requestedService as string) : null,
        proposedBudget: typeof payload.budget === 'number' ? (payload.budget as number) : null,
        counterPrice: typeof counterPayload.price === 'number' ? (counterPayload.price as number) : null,
        amount: escrow?.amount ? Number(escrow.amount) : null,
        currency: 'USD',
        transaction: transaction
          ? {
            id: transaction.id,
            status: transaction.status,
            settledAt: transaction.settledAt,
            createdAt: transaction.createdAt,
          }
          : null,
        serviceAgreementId: collaboration.serviceAgreementId,
        escrowId: escrow?.id ?? null,
        createdAt: collaboration.createdAt,
        updatedAt: collaboration.updatedAt,
      };
    });
  }

  async getAgentNetwork(agentId: string) {
    const transactions = await this.listAgentA2aTransactions(agentId);

    const nodes = new Map<
      string,
      {
        id: string;
        name: string;
        slug: string;
        isPrimary: boolean;
        interactions: number;
        dealsAsBuyer: number;
        dealsAsSeller: number;
        lastInteraction: Date | null;
      }
    >();
    const edges = new Map<
      string,
      {
        id: string;
        source: string;
        target: string;
        transactionCount: number;
        totalValue: number;
        latestStatus: string;
        updatedAt: Date;
      }
    >();

    const registerAgent = (
      agent: { id: string; name: string; slug: string } | null,
      role: 'buyer' | 'seller',
      timestamp: Date,
    ) => {
      if (!agent) {
        return;
      }

      const existing =
        nodes.get(agent.id) ??
        {
          id: agent.id,
          name: agent.name,
          slug: agent.slug,
          isPrimary: agent.id === agentId,
          interactions: 0,
          dealsAsBuyer: 0,
          dealsAsSeller: 0,
          lastInteraction: null,
        };

      existing.interactions += 1;
      if (role === 'buyer') {
        existing.dealsAsBuyer += 1;
      } else {
        existing.dealsAsSeller += 1;
      }
      if (!existing.lastInteraction || existing.lastInteraction < timestamp) {
        existing.lastInteraction = timestamp;
      }

      nodes.set(agent.id, existing);
    };

    transactions.forEach((transaction) => {
      const timestamp = new Date(transaction.updatedAt);
      registerAgent(transaction.requesterAgent, 'buyer', timestamp);
      registerAgent(transaction.responderAgent, 'seller', timestamp);

      if (transaction.requesterAgent && transaction.responderAgent) {
        const edgeKey = `${transaction.requesterAgent.id}->${transaction.responderAgent.id}`;
        const existing =
          edges.get(edgeKey) ??
          {
            id: edgeKey,
            source: transaction.requesterAgent.id,
            target: transaction.responderAgent.id,
            transactionCount: 0,
            totalValue: 0,
            latestStatus: transaction.status,
            updatedAt: timestamp,
          };

        existing.transactionCount += 1;
        if (typeof transaction.amount === 'number') {
          existing.totalValue += transaction.amount;
        }
        existing.latestStatus = transaction.status;
        existing.updatedAt = timestamp;
        edges.set(edgeKey, existing);
      }
    });

    return {
      primaryAgentId: agentId,
      nodes: Array.from(nodes.values()),
      edges: Array.from(edges.values()),
      updatedAt: new Date().toISOString(),
    };
  }

  private async ensureBudgetRecord(agentId: string, walletId: string) {
    const existing = await this.prisma.agentBudget.findFirst({
      where: { agentId },
      orderBy: { updatedAt: 'desc' },
    });

    if (existing) {
      return existing;
    }

    const defaultLimit = new Prisma.Decimal(500);

    return this.prisma.agentBudget.create({
      data: {
        agentId,
        walletId,
        monthlyLimit: defaultLimit,
        remaining: defaultLimit,
        approvalMode: BudgetApprovalMode.AUTO,
        resetsOn: this.calculateNextResetDate(),
      },
    });
  }

  private presentBudgetSnapshot(
    budget: {
      agentId: string;
      walletId: string;
      monthlyLimit: Prisma.Decimal;
      remaining: Prisma.Decimal;
      approvalMode: BudgetApprovalMode;
      resetsOn: Date;
      updatedAt: Date;
    },
    wallet: WalletModel,
  ) {
    const monthlyLimit = budget.monthlyLimit;
    const remaining = budget.remaining;
    const spent = monthlyLimit.minus(remaining);

    return {
      agentId: budget.agentId,
      walletId: wallet.id,
      currency: wallet.currency,
      monthlyLimit: Number(monthlyLimit),
      remaining: Number(remaining),
      spentThisPeriod: Number(spent),
      approvalMode: budget.approvalMode,
      perTransactionLimit: wallet.spendCeiling ? Number(wallet.spendCeiling) : null,
      approvalThreshold: wallet.autoApproveThreshold ? Number(wallet.autoApproveThreshold) : null,
      autoReload: budget.approvalMode !== BudgetApprovalMode.MANUAL,
      resetsOn: budget.resetsOn,
      updatedAt: budget.updatedAt,
    };
  }

  private calculateNextResetDate(base?: Date) {
    const reference = base ?? new Date();
    const year = reference.getUTCFullYear();
    const month = reference.getUTCMonth();
    return new Date(Date.UTC(year, month + 1, 1));
  }

  private async ensureExists(id: string) {
    const exists = await this.prisma.agent.count({ where: { id } });
    if (!exists) {
      throw new NotFoundException('Agent not found');
    }
  }

  private safeParseJson(raw: string | Record<string, unknown> | undefined) {
    if (!raw) {
      return {};
    }

    if (typeof raw === 'string') {
      try {
        return JSON.parse(raw);
      } catch {
        return { raw };
      }
    }

    return raw;
  }

  private async resolveFundingWallet(params: {
    initiatorType: InitiatorType;
    initiatorUserId: string;
    initiatorAgentId?: string;
    sourceWalletId?: string;
    amount: Prisma.Decimal;
  }): Promise<WalletModel> {
    if (params.initiatorType === InitiatorType.USER) {
      const wallet = await this.walletsService.ensureUserWallet(params.initiatorUserId);
      this.assertWalletCanSpend(wallet, params.amount);
      return wallet;
    }

    if (params.initiatorType === InitiatorType.AGENT) {
      const agentId = params.initiatorAgentId;
      if (!agentId) {
        throw new BadRequestException('initiatorAgentId is required for agent-initiated executions');
      }
      await this.ensureExists(agentId);
      const wallet = await this.walletsService.ensureAgentWallet(agentId);
      await this.applyAgentBudget(agentId, params.amount);
      this.assertWalletCanSpend(wallet, params.amount);
      return wallet;
    }

    if (!params.sourceWalletId) {
      throw new BadRequestException('sourceWalletId is required for workflow-initiated executions');
    }

    const wallet = await this.prisma.wallet.findUnique({
      where: { id: params.sourceWalletId },
    });

    if (!wallet) {
      throw new NotFoundException('Wallet not found');
    }

    this.assertWalletCanSpend(wallet, params.amount);
    return wallet;
  }

  private assertWalletCanSpend(wallet: WalletModel, amount: Prisma.Decimal) {
    const available = wallet.balance.minus(wallet.reserved);
    if (available.lessThan(amount)) {
      throw new BadRequestException('Insufficient available funds');
    }

    if (wallet.spendCeiling && amount.greaterThan(wallet.spendCeiling)) {
      throw new BadRequestException('Amount exceeds wallet spend ceiling');
    }

    if (wallet.autoApproveThreshold && amount.greaterThan(wallet.autoApproveThreshold)) {
      throw new BadRequestException('Amount exceeds wallet auto-approval threshold');
    }
  }

  private async applyAgentBudget(agentId: string, amount: Prisma.Decimal) {
    const budget = await this.prisma.agentBudget.findFirst({
      where: { agentId },
      orderBy: { updatedAt: 'desc' },
    });

    if (!budget) {
      return;
    }

    if (budget.approvalMode === BudgetApprovalMode.MANUAL) {
      throw new BadRequestException('Manual approval required before initiating spend');
    }

    if (budget.remaining.lessThan(amount)) {
      throw new BadRequestException('Agent budget exhausted');
    }

    await this.prisma.agentBudget.update({
      where: { id: budget.id },
      data: {
        remaining: budget.remaining.minus(amount),
      },
    });
  }

  private async recordPaymentEvent(params: {
    transactionId: string;
    sourceWalletId: string;
    destinationWalletId: string;
    amount: Prisma.Decimal;
    initiatorType: InitiatorType;
  }) {
    await this.prisma.paymentEvent.create({
      data: {
        transactionId: params.transactionId,
        protocol: 'LEDGER',
        status: PaymentEventStatus.SETTLED,
        sourceWalletId: params.sourceWalletId,
        destinationWalletId: params.destinationWalletId,
        amount: params.amount,
        initiatorType: params.initiatorType,
      },
    });
  }

  private async recordAgentEngagement(
    agentId: string,
    counterAgentId: string | null,
    initiatorType: InitiatorType,
    amount: Prisma.Decimal,
  ) {
    const normalizedCounterAgentId = counterAgentId ?? agentId;

    await this.prisma.agentEngagementMetric.upsert({
      where: {
        agentId_counterAgentId_initiatorType: {
          agentId,
          counterAgentId: normalizedCounterAgentId,
          initiatorType,
        },
      },
      update: {
        a2aCount: { increment: 1 },
        totalSpend: { increment: amount },
        lastInteraction: new Date(),
      },
      create: {
        agentId,
        counterAgentId: normalizedCounterAgentId,
        initiatorType,
        a2aCount: 1,
        totalSpend: amount,
        lastInteraction: new Date(),
      },
    });
  }

  private presentDiscoveryAgent(agent: AgentDiscoveryAgent) {
    const totalExecutions = agent.successCount + agent.failureCount;
    const successRate = totalExecutions > 0 ? agent.successCount / totalExecutions : 0;
    const rating = Number(Math.min(5, Math.max(1, (agent.trustScore ?? 0) / 20)).toFixed(1));

    const totalA2a = agent.metricsPrimary.reduce((sum, metric) => sum + metric.a2aCount, 0);
    const totalSpend = agent.metricsPrimary.reduce(
      (sum, metric) => sum.plus(metric.totalSpend),
      new Prisma.Decimal(0),
    );

    const latestCertification = agent.certifications[0] ?? null;

    return {
      id: agent.id,
      slug: agent.slug,
      name: agent.name,
      description: agent.description,
      categories: agent.categories,
      tags: agent.tags,
      pricing: {
        model: agent.pricingModel,
        basePriceCents: agent.basePriceCents ?? null,
        currency: 'USD',
      },
      ap2: {
        endpoint: agent.ap2Endpoint ?? null,
      },
      schemas: {
        input: agent.inputSchema ?? null,
        output: agent.outputSchema ?? null,
      },
      reputation: {
        rating,
        trustScore: agent.trustScore,
        successRate: Number(successRate.toFixed(2)),
        totalExecutions,
        totalA2a,
        totalSpendUsd: totalSpend.toFixed(2),
      },
      certification: {
        certified: Boolean(latestCertification),
        checklistId: latestCertification?.checklistId ?? null,
        lastCertifiedAt: latestCertification?.updatedAt ?? null,
      },
      updatedAt: agent.updatedAt,
    };
  }
}
