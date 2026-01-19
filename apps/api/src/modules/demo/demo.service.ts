import { Injectable, Logger } from '@nestjs/common';

import { AgentsService } from '../agents/agents.service.js';
import { AP2Service } from '../ap2/ap2.service.js';
import { NegotiationResponseStatus } from '../ap2/dto/respond-negotiation.dto.js';
import { PrismaService } from '../database/prisma.service.js';
import { WalletsService } from '../payments/wallets.service.js';

@Injectable()
export class DemoService {
  private readonly logger = new Logger(DemoService.name);

  // Demo-safe agent IDs (pre-approved agents that are safe for public demos)
  private readonly DEMO_AGENT_IDS = process.env.DEMO_AGENT_IDS?.split(',') || [];

  // Demo-safe prompts (pre-approved service requests)
  private readonly DEMO_PROMPTS = process.env.DEMO_PROMPTS
    ? process.env.DEMO_PROMPTS.split(',').map((prompt) => prompt.trim()).filter(Boolean)
    : [
        'Generate a summary of the top 3 AI trends in 2024',
        'Create a brief product description for a new SaaS tool',
        'Write a short email response to a customer inquiry',
      ];
  private readonly enforcePromptAllowlist = process.env.ENFORCE_DEMO_PROMPTS === 'true';

  private readonly isStrictDemoMode =
    process.env.NODE_ENV === 'production' || process.env.NODE_ENV === 'staging';

  constructor(
    private readonly prisma: PrismaService,
    private readonly agentsService: AgentsService,
    private readonly ap2Service: AP2Service,
    private readonly walletsService: WalletsService,
  ) {}

  /**
   * Get or create a demo session (ephemeral org/user that expires in 1 hour)
   */
  async getOrCreateDemoSession(ipAddress: string): Promise<{
    userId: string;
    orgId: string;
    expiresAt: Date;
  }> {
    // Check if demo session exists for this IP (within last hour)
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    
    const existingSession = await this.prisma.user.findFirst({
      where: {
        email: {
          startsWith: `demo-${ipAddress.replace(/[.:]/g, '-')}-`,
        },
        createdAt: {
          gte: oneHourAgo,
        },
      },
      include: {
        memberships: {
          include: {
            organization: true,
          },
        },
      },
    });

    if (existingSession && existingSession.memberships.length > 0) {
      const org = existingSession.memberships[0].organization;
      const expiresAt = new Date(existingSession.createdAt.getTime() + 60 * 60 * 1000);
      
      return {
        userId: existingSession.id,
        orgId: org.id,
        expiresAt,
      };
    }

    // Create new demo session
    const demoEmail = `demo-${ipAddress.replace(/[.:]/g, '-')}-${Date.now()}@demo.local`;
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000);

    // Create demo user and org in a transaction
    const demoUser = await this.prisma.$transaction(async (tx) => {
      const user = await tx.user.create({
        data: {
          email: demoEmail,
          displayName: 'Demo User',
          // No password for demo users
        },
      });

      const org = await tx.organization.create({
        data: {
          name: 'Demo Organization',
          slug: `demo-org-${user.id.slice(0, 8)}`, // Demo orgs have slug starting with "demo-"
        },
      });

      await tx.organizationMembership.create({
        data: {
          userId: user.id,
          organizationId: org.id,
          role: 'OWNER',
        },
      });

      return { user, org };
    });

    return {
      userId: demoUser.user.id,
      orgId: demoUser.org.id,
      expiresAt,
    };
  }

  /**
   * Validate that agent IDs and prompts are demo-safe
   * If DEMO_AGENT_IDS is not configured, allow any approved agents (fallback)
   */
  validateDemoRequest(requesterAgentId: string, responderAgentId: string, service: string): void {
    // Only validate agents if DEMO_AGENT_IDS is explicitly configured
    if (this.DEMO_AGENT_IDS.length > 0) {
      if (!this.DEMO_AGENT_IDS.includes(requesterAgentId) || !this.DEMO_AGENT_IDS.includes(responderAgentId)) {
        throw new Error('Only demo-safe agents are allowed in public demos');
      }
    }

    // Only validate prompts if DEMO_PROMPTS is explicitly configured
    if (
      this.enforcePromptAllowlist &&
      this.DEMO_PROMPTS.length > 0 &&
      !this.DEMO_PROMPTS.includes(service)
    ) {
      throw new Error('Only demo-safe prompts are allowed in public demos');
    }
  }

  /**
   * Run A2A negotiation in demo mode
   */
  async runDemoA2A(params: {
    requesterAgentId: string;
    responderAgentId: string;
    service: string;
    budget: number;
    price: number;
    userId: string;
  }): Promise<{ runId: string; negotiationId: string }> {
    // Validate demo request
    this.validateDemoRequest(params.requesterAgentId, params.responderAgentId, params.service);

    // Ensure demo wallets exist for agents (real wallets, demo credits)
    const requesterWallet = await this.walletsService.ensureAgentWallet(params.requesterAgentId);
    await this.walletsService.ensureAgentWallet(params.responderAgentId);

    // Fund demo wallets if needed (demo credits only, not real money)
    const requiredBalance = params.budget + 20;
    const requesterBalance = parseFloat(String(requesterWallet.balance || '0'));
    if (requesterBalance < requiredBalance) {
      await this.walletsService.fundWallet(requesterWallet.id, {
        amount: requiredBalance,
        reference: 'demo-a2a-credit',
      });
    }

    // Create negotiation via AP2 pipeline
    const negotiation = await this.ap2Service.initiateNegotiation({
      requesterAgentId: params.requesterAgentId,
      responderAgentId: params.responderAgentId,
      requestedService: params.service,
      budget: params.budget,
      requirements: {
        quality: 'high',
        deadline: '1 hour',
      },
      notes: 'Demo negotiation',
      initiatedByUserId: params.userId,
    });

    // Accept negotiation (this will initiate escrow and service agreement)
    const accepted = await this.ap2Service.respondToNegotiation({
      negotiationId: negotiation.id,
      responderAgentId: params.responderAgentId,
      status: NegotiationResponseStatus.ACCEPTED,
      price: params.price,
      estimatedDelivery: '30 minutes',
      notes: 'Accepted in demo',
    });

    // Deliver service to drive verification and payout for the storyboard
    try {
      await this.ap2Service.deliverService({
        negotiationId: accepted.id,
        responderAgentId: params.responderAgentId,
        result: {
          status: 'success',
          summary: params.service,
        },
        evidence: {
          autoApprove: true,
          demo: true,
        },
        notes: 'Demo service delivered automatically for public A2A demo',
        deliveredByUserId: params.userId,
      });
    } catch (error) {
      this.logger.warn(`Demo deliverService failed for negotiation ${accepted.id}`, error as Error);
    }

    // Use negotiation ID as run ID for tracking/logs
    return {
      runId: accepted.id,
      negotiationId: accepted.id,
    };
  }

  /**
   * Get demo run logs/status
   */
  async getDemoRunLogs(runId: string): Promise<{
    status: string;
    logs: string[];
    negotiation?: unknown;
  }> {
    // Fetch negotiation by ID (includes escrow + verification data)
    const negotiation = await this.ap2Service.getNegotiation(runId);

    // Build a storyboard-style log from negotiation state
    const logs: string[] = [];
    const createdAt = negotiation.createdAt ? new Date(negotiation.createdAt) : new Date();
    const time = (label: string) => `[${createdAt.toLocaleTimeString()}] ${label}`;

    logs.push(time('🚦 Step 0: Demo run initialized'));
    logs.push(
      time(
        `🤝 Step 1: Negotiation created (${negotiation.id}) between ` +
          `${negotiation.requesterAgent?.name ?? negotiation.requesterAgent?.id ?? 'Requester'} → ` +
          `${negotiation.responderAgent?.name ?? negotiation.responderAgent?.id ?? 'Responder'}`,
      ),
    );

    if (negotiation.status) {
      logs.push(time(`   Current status: ${negotiation.status}`));
    }

    if (negotiation.escrowId) {
      const escrowAmount =
        negotiation.transaction &&
        typeof negotiation.transaction === 'object' &&
        'amount' in negotiation.transaction
          ? negotiation.transaction.amount
          : 'N/A';
      logs.push(
        time(
          `💰 Step 2: Escrow funded (ID: ${negotiation.escrowId}) for $${escrowAmount ?? 'N/A'}`,
        ),
      );
      if (negotiation.transaction?.status) {
        logs.push(time(`   Escrow transaction status: ${negotiation.transaction.status}`));
      }
    }

    if (negotiation.serviceAgreementId) {
      logs.push(
        time(
          `📦 Step 3: Service agreement created (ID: ${negotiation.serviceAgreementId}) for the work`,
        ),
      );
    }

    if (negotiation.verificationStatus) {
      logs.push(
        time(`✅ Step 4: Verification status recorded as ${negotiation.verificationStatus}`),
      );
    }

    logs.push(time('📑 Demo receipt:'));
    logs.push(time(`   Negotiation ID: ${negotiation.id}`));
    if (negotiation.escrowId) {
      logs.push(time(`   Escrow ID: ${negotiation.escrowId}`));
    }
    if (negotiation.transaction?.status) {
      logs.push(time(`   Payout status: ${negotiation.transaction.status}`));
    }
    if (negotiation.verificationStatus) {
      logs.push(time(`   Verification: ${negotiation.verificationStatus}`));
    }

    return {
      status: negotiation.status || 'UNKNOWN',
      logs,
      negotiation,
    };
  }

  /**
   * Get demo-safe agents list
   */
  async getDemoAgents(): Promise<Array<{ id: string; name: string; description: string }>> {
    if (this.DEMO_AGENT_IDS.length === 0) {
      // Fallback: return first 2 approved agents if no demo agents configured
      // Works in all environments; set DEMO_AGENT_IDS to tighten which agents appear.
      if (this.isStrictDemoMode) {
        this.logger.warn(
          'DEMO_AGENT_IDS is not configured; falling back to first 2 approved agents for demo.',
        );
      }
      const agents = await this.prisma.agent.findMany({
        where: {
          status: 'APPROVED',
        },
        take: 8,
        select: {
          id: true,
          name: true,
          description: true,
        },
      });
      return agents;
    }

    const agents = await this.prisma.agent.findMany({
      where: {
        id: {
          in: this.DEMO_AGENT_IDS,
        },
        status: 'APPROVED',
      },
      select: {
        id: true,
        name: true,
        description: true,
      },
    });

    return agents;
  }

  /**
   * Cleanup expired demo sessions (should be called periodically)
   */
  async cleanupExpiredDemoSessions(): Promise<void> {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);

    const expiredSessions = await this.prisma.user.findMany({
      where: {
        email: {
          startsWith: 'demo-',
        },
        createdAt: {
          lt: oneHourAgo,
        },
      },
      include: {
        memberships: {
          include: {
            organization: true,
          },
        },
      },
    });

    for (const session of expiredSessions) {
      for (const membership of session.memberships) {
        // Delete demo org and related data
        await this.prisma.organization.delete({
          where: { id: membership.organization.id },
        });
      }

      // Delete demo user
      await this.prisma.user.delete({
        where: { id: session.id },
      });
    }

    this.logger.log(`Cleaned up ${expiredSessions.length} expired demo sessions`);
  }
}

