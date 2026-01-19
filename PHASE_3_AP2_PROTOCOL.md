# PHASE 3: AP2 PROTOCOL & AGENT SDK

**Date**: November 13, 2025  
**Status**: Week 2 A2A Visualization ✅ COMPLETE  
**Next**: AP2 Protocol Implementation + Agent SDK  
**Timeline**: 5-7 days

---

## 🎉 WHAT YOU JUST SHIPPED (Week 2)

**A2A Visualization Suite - COMPLETE:**

- ✅ A2A Transaction Monitor (real-time autonomous trades)
- ✅ Agent Network Graph (ReactFlow visualization)
- ✅ Budget Controls (caps, approvals, auto-reload)
- ✅ ROI Dashboard (A2A spend vs value metrics)
- ✅ Agent Discovery API endpoints (budget, transactions, network)
- ✅ Backend service logic (budget provisioning, wallet limits)
- ✅ SDK types updated (budget fetch/update, A2A deals)

**This is EXCELLENT.** Humans can now see what their agents are doing autonomously.

But there's a critical piece missing: **Agents can't actually TRANSACT yet.**

---

## 🚨 THE GAP

**What Exists:**

- ✅ Humans can deploy agents
- ✅ Humans can set budgets
- ✅ Humans can VIEW A2A transactions (in the monitor)
- ✅ Backend has wallets, escrow, transactions

**What's Missing:**

- ❌ Agents can't INITIATE transactions (no AP2 protocol)
- ❌ Agents can't NEGOTIATE with each other
- ❌ No agent-to-agent communication layer
- ❌ No programmatic way for agents to discover/purchase services

**Translation:** You built the dashboard to watch the game, but there's no game being played yet.

---

## 🎯 PHASE 3 MISSION

**Build the AP2 (Agent Payment Protocol) implementation so agents can autonomously transact.**

This is the CORE of your differentiation. This is what makes you **"the only marketplace where agents buy from agents."**

---

## 📋 WHAT TO BUILD (Priority Order)

### **Priority 1: AP2 Protocol Endpoints (Backend) - 2-3 days**

**The Flow:**

```
Agent A discovers Agent B
  ↓
Agent A: POST /ap2/negotiate {service, budget, requirements}
  ↓
Platform: Creates negotiation, locks escrow
  ↓
Agent B: POST /ap2/respond {accepted, price, terms}
  ↓
Agent B: Executes service
  ↓
Agent B: POST /ap2/deliver {result, evidence}
  ↓
Platform: Verifies outcome quality
  ↓
Platform: Releases escrow to Agent B OR refunds Agent A
```

#### **Step 1: Create AP2 Module**

**File:** `apps/api/src/modules/ap2/ap2.module.ts`

```typescript
import { Module } from '@nestjs/common';
import { AP2Controller } from './ap2.controller.js';
import { AP2Service } from './ap2.service.js';
import { DatabaseModule } from '../database/database.module.js';
import { PaymentsModule } from '../payments/payments.module.js';
import { QualityModule } from '../quality/quality.module.js';

@Module({
  imports: [DatabaseModule, PaymentsModule, QualityModule],
  controllers: [AP2Controller],
  providers: [AP2Service],
  exports: [AP2Service],
})
export class AP2Module {}
```

#### **Step 2: AP2 Controller**

**File:** `apps/api/src/modules/ap2/ap2.controller.ts`

```typescript
import { Controller, Post, Get, Patch, Body, Param, UseGuards } from '@nestjs/common';
import { AP2Service } from './ap2.service.js';
import { JwtAuthGuard } from '../auth/jwt-auth.guard.js';
import { CurrentUser } from '../auth/current-user.decorator.js';

@Controller('ap2')
@UseGuards(JwtAuthGuard)
export class AP2Controller {
  constructor(private readonly ap2Service: AP2Service) {}

  /**
   * Agent initiates negotiation with another agent
   * POST /ap2/negotiate
   */
  @Post('negotiate')
  async negotiate(@CurrentUser() user: any, @Body() dto: NegotiateDTO) {
    return this.ap2Service.initiateNegotiation({
      requesterAgentId: dto.requesterAgentId,
      responderAgentId: dto.responderAgentId,
      service: dto.service,
      budget: dto.budget,
      requirements: dto.requirements,
      initiatedBy: user.id,
    });
  }

  /**
   * Agent responds to negotiation
   * POST /ap2/respond
   */
  @Post('respond')
  async respond(@CurrentUser() user: any, @Body() dto: RespondDTO) {
    return this.ap2Service.respondToNegotiation({
      negotiationId: dto.negotiationId,
      status: dto.status,
      price: dto.price,
      estimatedDelivery: dto.estimatedDelivery,
      terms: dto.terms,
      respondedBy: user.id,
    });
  }

  /**
   * Agent delivers service result
   * POST /ap2/deliver
   */
  @Post('deliver')
  async deliver(@CurrentUser() user: any, @Body() dto: DeliverDTO) {
    return this.ap2Service.deliverResult({
      negotiationId: dto.negotiationId,
      result: dto.result,
      evidence: dto.evidence,
      deliveredBy: user.id,
    });
  }

  /**
   * Get negotiation status
   * GET /ap2/negotiations/:id
   */
  @Get('negotiations/:id')
  async getNegotiation(@Param('id') id: string) {
    return this.ap2Service.getNegotiation(id);
  }

  /**
   * List agent's negotiations
   * GET /ap2/negotiations/my
   */
  @Get('negotiations/my')
  async getMyNegotiations(@CurrentUser() user: any, @Query('agentId') agentId?: string) {
    return this.ap2Service.getAgentNegotiations(agentId || user.agentId);
  }

  /**
   * Cancel negotiation
   * PATCH /ap2/negotiations/:id/cancel
   */
  @Patch('negotiations/:id/cancel')
  async cancelNegotiation(@Param('id') id: string, @CurrentUser() user: any) {
    return this.ap2Service.cancelNegotiation(id, user.id);
  }
}
```

#### **Step 3: AP2 Service Implementation**

**File:** `apps/api/src/modules/ap2/ap2.service.ts`

```typescript
import { Injectable, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../database/prisma.service.js';
import { PaymentsService } from '../payments/payments.service.js';
import { OutcomesService } from '../quality/outcomes.service.js';

@Injectable()
export class AP2Service {
  constructor(
    private readonly prisma: PrismaService,
    private readonly payments: PaymentsService,
    private readonly outcomes: OutcomesService,
  ) {}

  /**
   * Initiate negotiation between two agents
   */
  async initiateNegotiation(params: {
    requesterAgentId: string;
    responderAgentId: string;
    service: string;
    budget: number;
    requirements: any;
    initiatedBy: string;
  }) {
    // 1. Validate agents exist
    const [requester, responder] = await Promise.all([
      this.prisma.agent.findUnique({ where: { id: params.requesterAgentId } }),
      this.prisma.agent.findUnique({ where: { id: params.responderAgentId } }),
    ]);

    if (!requester || !responder) {
      throw new BadRequestException('Agent not found');
    }

    // 2. Check requester wallet has funds
    const requesterWallet = await this.prisma.wallet.findFirst({
      where: { agentId: params.requesterAgentId },
    });

    if (!requesterWallet || requesterWallet.balance < params.budget) {
      throw new BadRequestException('Insufficient funds');
    }

    // 3. Check budget limits
    const agentBudget = await this.prisma.agentBudget.findUnique({
      where: { agentId: params.requesterAgentId },
    });

    if (agentBudget) {
      // Check per-transaction limit
      if (params.budget > agentBudget.perTransactionLimit) {
        throw new BadRequestException('Exceeds per-transaction limit');
      }

      // Check monthly limit
      const thisMonth = new Date();
      thisMonth.setDate(1);
      thisMonth.setHours(0, 0, 0, 0);

      const monthlySpend = await this.prisma.transaction.aggregate({
        where: {
          initiatorId: params.requesterAgentId,
          createdAt: { gte: thisMonth },
          status: { in: ['completed', 'pending'] },
        },
        _sum: { amount: true },
      });

      const totalSpend = (monthlySpend._sum.amount || 0) + params.budget;
      if (totalSpend > agentBudget.monthlyLimit) {
        throw new BadRequestException('Exceeds monthly budget limit');
      }
    }

    // 4. Create collaboration request (negotiation)
    const negotiation = await this.prisma.collaborationRequest.create({
      data: {
        requesterAgentId: params.requesterAgentId,
        responderAgentId: params.responderAgentId,
        status: 'pending',
        payload: {
          service: params.service,
          budget: params.budget,
          requirements: params.requirements,
        },
      },
      include: {
        requesterAgent: true,
        responderAgent: true,
      },
    });

    // 5. TODO: Notify responder agent via webhook (if configured)
    // await this.notifyAgent(params.responderAgentId, 'negotiation_received', negotiation);

    return {
      negotiationId: negotiation.id,
      status: negotiation.status,
      requester: {
        id: negotiation.requesterAgent.id,
        name: negotiation.requesterAgent.name,
      },
      responder: {
        id: negotiation.responderAgent.id,
        name: negotiation.responderAgent.name,
      },
      service: params.service,
      budget: params.budget,
      createdAt: negotiation.createdAt,
    };
  }

  /**
   * Respond to negotiation
   */
  async respondToNegotiation(params: {
    negotiationId: string;
    status: 'accepted' | 'rejected' | 'counter';
    price?: number;
    estimatedDelivery?: string;
    terms?: any;
    respondedBy: string;
  }) {
    // 1. Get negotiation
    const negotiation = await this.prisma.collaborationRequest.findUnique({
      where: { id: params.negotiationId },
      include: {
        requesterAgent: true,
        responderAgent: true,
      },
    });

    if (!negotiation) {
      throw new BadRequestException('Negotiation not found');
    }

    if (negotiation.status !== 'pending') {
      throw new BadRequestException('Negotiation already resolved');
    }

    // 2. Update negotiation
    const updated = await this.prisma.collaborationRequest.update({
      where: { id: params.negotiationId },
      data: {
        status: params.status,
        counterPayload: {
          price: params.price,
          estimatedDelivery: params.estimatedDelivery,
          terms: params.terms,
        },
        updatedAt: new Date(),
      },
    });

    // 3. If accepted, create escrow and transaction
    if (params.status === 'accepted') {
      const budget = negotiation.payload['budget'] as number;
      const finalPrice = params.price || budget;

      // Create escrow
      const escrow = await this.prisma.escrow.create({
        data: {
          initiatorId: negotiation.requesterAgentId,
          recipientId: negotiation.responderAgentId,
          amount: finalPrice,
          currency: 'USD',
          status: 'locked',
          purpose: negotiation.payload['service'] as string,
          metadata: {
            negotiationId: params.negotiationId,
            service: negotiation.payload['service'],
          },
        },
      });

      // Lock funds from requester wallet
      await this.payments.lockFunds({
        walletId: negotiation.requesterAgent.walletId,
        amount: finalPrice,
        escrowId: escrow.id,
      });

      // Create transaction record
      await this.prisma.transaction.create({
        data: {
          type: 'a2a',
          initiatorId: negotiation.requesterAgentId,
          recipientId: negotiation.responderAgentId,
          amount: finalPrice,
          currency: 'USD',
          purpose: negotiation.payload['service'] as string,
          status: 'pending',
          escrowId: escrow.id,
          metadata: {
            negotiationId: params.negotiationId,
          },
        },
      });

      // TODO: Notify requester agent that service is starting
    }

    return {
      negotiationId: updated.id,
      status: updated.status,
      price: params.price,
      message:
        params.status === 'accepted'
          ? 'Negotiation accepted. Escrow created.'
          : params.status === 'rejected'
            ? 'Negotiation rejected.'
            : 'Counter-offer sent.',
    };
  }

  /**
   * Deliver service result
   */
  async deliverResult(params: {
    negotiationId: string;
    result: any;
    evidence: any;
    deliveredBy: string;
  }) {
    // 1. Get negotiation
    const negotiation = await this.prisma.collaborationRequest.findUnique({
      where: { id: params.negotiationId },
    });

    if (!negotiation || negotiation.status !== 'accepted') {
      throw new BadRequestException('Invalid negotiation');
    }

    // 2. Get transaction and escrow
    const transaction = await this.prisma.transaction.findFirst({
      where: {
        metadata: {
          path: ['negotiationId'],
          equals: params.negotiationId,
        },
      },
      include: { escrow: true },
    });

    if (!transaction || !transaction.escrow) {
      throw new BadRequestException('Transaction or escrow not found');
    }

    // 3. Create service agreement (if not exists)
    let agreement = await this.prisma.serviceAgreement.findFirst({
      where: {
        agentId: negotiation.responderAgentId,
        buyerId: params.deliveredBy,
        escrowId: transaction.escrowId,
      },
    });

    if (!agreement) {
      agreement = await this.prisma.serviceAgreement.create({
        data: {
          agentId: negotiation.responderAgentId,
          buyerId: params.deliveredBy,
          escrowId: transaction.escrowId,
          outcomeType: 'GENERIC',
          targetDescription: negotiation.payload['service'] as string,
          status: 'PENDING',
        },
      });
    }

    // 4. Verify outcome (automatic or manual)
    const verification = await this.outcomes.recordOutcomeVerification(agreement.id, {
      status: 'verified', // TODO: Implement actual verification logic
      evidence: params.evidence,
      notes: 'Automatic verification',
      reviewerId: params.deliveredBy,
    });

    // 5. If verified, release escrow
    if (verification.status === 'verified') {
      // Release escrow
      await this.prisma.escrow.update({
        where: { id: transaction.escrowId },
        data: { status: 'released' },
      });

      // Transfer funds
      await this.payments.releaseFunds({
        escrowId: transaction.escrowId,
        recipientWalletId: negotiation.responderAgent.walletId,
      });

      // Complete transaction
      await this.prisma.transaction.update({
        where: { id: transaction.id },
        data: {
          status: 'completed',
          completedAt: new Date(),
        },
      });

      // Update service agreement
      await this.prisma.serviceAgreement.update({
        where: { id: agreement.id },
        data: { status: 'COMPLETED' },
      });

      // Record A2A engagement metric
      await this.prisma.agentEngagementMetric.upsert({
        where: {
          agentId_counterAgentId_initiatorType: {
            agentId: negotiation.requesterAgentId,
            counterAgentId: negotiation.responderAgentId,
            initiatorType: 'agent',
          },
        },
        create: {
          agentId: negotiation.requesterAgentId,
          counterAgentId: negotiation.responderAgentId,
          initiatorType: 'agent',
          a2aCount: 1,
          totalSpend: transaction.amount,
          lastInteraction: new Date(),
        },
        update: {
          a2aCount: { increment: 1 },
          totalSpend: { increment: transaction.amount },
          lastInteraction: new Date(),
        },
      });
    }

    return {
      negotiationId: params.negotiationId,
      status: verification.status,
      transactionId: transaction.id,
      escrowStatus: verification.status === 'verified' ? 'released' : 'locked',
      message:
        verification.status === 'verified'
          ? 'Result verified. Payment released.'
          : 'Result delivered. Awaiting verification.',
    };
  }

  /**
   * Get negotiation details
   */
  async getNegotiation(id: string) {
    const negotiation = await this.prisma.collaborationRequest.findUnique({
      where: { id },
      include: {
        requesterAgent: true,
        responderAgent: true,
      },
    });

    if (!negotiation) {
      throw new BadRequestException('Negotiation not found');
    }

    // Get associated transaction if exists
    const transaction = await this.prisma.transaction.findFirst({
      where: {
        metadata: {
          path: ['negotiationId'],
          equals: id,
        },
      },
      include: { escrow: true },
    });

    return {
      id: negotiation.id,
      status: negotiation.status,
      requester: {
        id: negotiation.requesterAgent.id,
        name: negotiation.requesterAgent.name,
      },
      responder: {
        id: negotiation.responderAgent.id,
        name: negotiation.responderAgent.name,
      },
      request: negotiation.payload,
      response: negotiation.counterPayload,
      transaction: transaction
        ? {
            id: transaction.id,
            amount: transaction.amount,
            status: transaction.status,
            escrowStatus: transaction.escrow?.status,
          }
        : null,
      createdAt: negotiation.createdAt,
      updatedAt: negotiation.updatedAt,
    };
  }

  /**
   * List agent's negotiations
   */
  async getAgentNegotiations(agentId: string) {
    const negotiations = await this.prisma.collaborationRequest.findMany({
      where: {
        OR: [{ requesterAgentId: agentId }, { responderAgentId: agentId }],
      },
      include: {
        requesterAgent: true,
        responderAgent: true,
      },
      orderBy: { createdAt: 'desc' },
      take: 100,
    });

    return negotiations.map((n) => ({
      id: n.id,
      status: n.status,
      role: n.requesterAgentId === agentId ? 'requester' : 'responder',
      counterparty:
        n.requesterAgentId === agentId
          ? { id: n.responderAgent.id, name: n.responderAgent.name }
          : { id: n.requesterAgent.id, name: n.requesterAgent.name },
      service: n.payload['service'],
      budget: n.payload['budget'],
      createdAt: n.createdAt,
    }));
  }

  /**
   * Cancel negotiation
   */
  async cancelNegotiation(id: string, userId: string) {
    const negotiation = await this.prisma.collaborationRequest.findUnique({
      where: { id },
    });

    if (!negotiation) {
      throw new BadRequestException('Negotiation not found');
    }

    if (negotiation.status !== 'pending') {
      throw new BadRequestException('Cannot cancel non-pending negotiation');
    }

    await this.prisma.collaborationRequest.update({
      where: { id },
      data: { status: 'rejected' },
    });

    return { message: 'Negotiation cancelled' };
  }
}
```

#### **Step 4: DTOs**

**File:** `apps/api/src/modules/ap2/dto/negotiate.dto.ts`

```typescript
import { IsString, IsNumber, IsObject, Min } from 'class-validator';

export class NegotiateDTO {
  @IsString()
  requesterAgentId: string;

  @IsString()
  responderAgentId: string;

  @IsString()
  service: string;

  @IsNumber()
  @Min(0)
  budget: number;

  @IsObject()
  requirements: Record<string, any>;
}
```

**File:** `apps/api/src/modules/ap2/dto/respond.dto.ts`

```typescript
import { IsString, IsNumber, IsEnum, IsOptional, IsObject } from 'class-validator';

export class RespondDTO {
  @IsString()
  negotiationId: string;

  @IsEnum(['accepted', 'rejected', 'counter'])
  status: 'accepted' | 'rejected' | 'counter';

  @IsNumber()
  @IsOptional()
  price?: number;

  @IsString()
  @IsOptional()
  estimatedDelivery?: string;

  @IsObject()
  @IsOptional()
  terms?: Record<string, any>;
}
```

**File:** `apps/api/src/modules/ap2/dto/deliver.dto.ts`

```typescript
import { IsString, IsObject } from 'class-validator';

export class DeliverDTO {
  @IsString()
  negotiationId: string;

  @IsObject()
  result: Record<string, any>;

  @IsObject()
  evidence: Record<string, any>;
}
```

#### **Step 5: Wire Up in App Module**

**File:** `apps/api/src/app.module.ts`

```typescript
import { AP2Module } from './modules/ap2/ap2.module.js';

@Module({
  imports: [
    // ... existing modules
    AP2Module, // ADD THIS
  ],
})
export class AppModule {}
```

---

### **Priority 2: Agent SDK Package (2 days)**

**Create a new package that agents use to interact with the marketplace.**

#### **Step 1: Create Package**

```bash
mkdir -p packages/agent-sdk
cd packages/agent-sdk
npm init -y
```

**File:** `packages/agent-sdk/package.json`

```json
{
  "name": "@agent-market/agent-sdk",
  "version": "0.1.0",
  "description": "SDK for agents to interact with Agent Marketplace",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  },
  "keywords": ["agent", "a2a", "marketplace"],
  "author": "",
  "license": "MIT",
  "dependencies": {
    "ky": "^1.2.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0"
  }
}
```

**File:** `packages/agent-sdk/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "declaration": true,
    "outDir": "./dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

#### **Step 2: SDK Implementation**

**File:** `packages/agent-sdk/src/index.ts`

```typescript
import ky from 'ky';

export interface AgentSDKConfig {
  agentId: string;
  apiKey: string;
  baseUrl?: string;
}

export interface Agent {
  id: string;
  name: string;
  capabilities: string[];
  pricing: {
    perOutcome?: number;
    monthly?: number;
    currency: string;
  };
  reputation: {
    rating: number;
    completedTransactions: number;
    successRate: number;
  };
  certification?: {
    status: string;
    level: string;
  };
  inputSchema: any;
  outputSchema: any;
}

export interface ServiceRequest {
  targetAgentId: string;
  service: string;
  input: Record<string, any>;
  budget: number;
  autoApprove?: boolean;
}

export interface Negotiation {
  id: string;
  status: 'pending' | 'accepted' | 'rejected' | 'completed';
  requester: { id: string; name: string };
  responder: { id: string; name: string };
  service: string;
  budget: number;
  price?: number;
  result?: any;
  createdAt: string;
}

export class AgentMarketSDK {
  private client: typeof ky;
  private agentId: string;

  constructor(config: AgentSDKConfig) {
    this.agentId = config.agentId;
    this.client = ky.create({
      prefixUrl: config.baseUrl || 'http://localhost:4000',
      headers: {
        Authorization: `Bearer ${config.apiKey}`,
      },
    });
  }

  /**
   * Discover agents with specific capabilities
   */
  async discover(filters: {
    capability?: string;
    maxPrice?: number;
    minRating?: number;
    certificationRequired?: boolean;
  }): Promise<Agent[]> {
    const params = new URLSearchParams();
    if (filters.capability) params.append('capability', filters.capability);
    if (filters.maxPrice) params.append('maxPrice', filters.maxPrice.toString());
    if (filters.minRating) params.append('minRating', filters.minRating.toString());
    if (filters.certificationRequired) params.append('certified', 'true');

    const response = await this.client
      .get('agents/discover', { searchParams: params })
      .json<{ agents: Agent[] }>();
    return response.agents;
  }

  /**
   * Request service from another agent
   */
  async requestService(request: ServiceRequest): Promise<NegotiationHandle> {
    const negotiation = await this.client
      .post('ap2/negotiate', {
        json: {
          requesterAgentId: this.agentId,
          responderAgentId: request.targetAgentId,
          service: request.service,
          budget: request.budget,
          requirements: request.input,
        },
      })
      .json<{ negotiationId: string }>();

    return new NegotiationHandle(negotiation.negotiationId, this.client, request.autoApprove);
  }

  /**
   * Get agent's negotiations
   */
  async getMyNegotiations(): Promise<Negotiation[]> {
    return this.client
      .get('ap2/negotiations/my', {
        searchParams: { agentId: this.agentId },
      })
      .json<Negotiation[]>();
  }

  /**
   * Get specific negotiation
   */
  async getNegotiation(id: string): Promise<Negotiation> {
    return this.client.get(`ap2/negotiations/${id}`).json<Negotiation>();
  }
}

/**
 * Handle for managing a negotiation
 */
export class NegotiationHandle {
  constructor(
    private id: string,
    private client: typeof ky,
    private autoApprove: boolean = false,
  ) {}

  /**
   * Wait for negotiation to complete and return result
   */
  async waitForCompletion(
    options: {
      pollInterval?: number;
      timeout?: number;
    } = {},
  ): Promise<any> {
    const pollInterval = options.pollInterval || 1000;
    const timeout = options.timeout || 300000; // 5 minutes
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const negotiation = await this.client.get(`ap2/negotiations/${this.id}`).json<Negotiation>();

      if (negotiation.status === 'completed') {
        return negotiation.result;
      }

      if (negotiation.status === 'rejected') {
        throw new Error('Negotiation rejected');
      }

      // If accepted and we have auto-approve, wait for delivery
      if (negotiation.status === 'accepted' && this.autoApprove) {
        // Continue polling for completion
      }

      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }

    throw new Error('Negotiation timeout');
  }

  /**
   * Get current status
   */
  async getStatus(): Promise<Negotiation> {
    return this.client.get(`ap2/negotiations/${this.id}`).json<Negotiation>();
  }

  /**
   * Cancel negotiation
   */
  async cancel(): Promise<void> {
    await this.client.patch(`ap2/negotiations/${this.id}/cancel`).json();
  }
}

// Export types
export * from './types.js';
```

**File:** `packages/agent-sdk/src/types.ts`

```typescript
export interface DiscoveryFilters {
  capability?: string;
  maxPrice?: number;
  minRating?: number;
  certificationRequired?: boolean;
}

export interface ServiceRequest {
  targetAgentId: string;
  service: string;
  input: Record<string, any>;
  budget: number;
  autoApprove?: boolean;
}

export interface Agent {
  id: string;
  name: string;
  capabilities: string[];
  pricing: {
    perOutcome?: number;
    monthly?: number;
    currency: string;
  };
  reputation: {
    rating: number;
    completedTransactions: number;
    successRate: number;
  };
  certification?: {
    status: string;
    level: string;
  };
  inputSchema: any;
  outputSchema: any;
}

export interface Negotiation {
  id: string;
  status: 'pending' | 'accepted' | 'rejected' | 'completed';
  requester: { id: string; name: string };
  responder: { id: string; name: string };
  service: string;
  budget: number;
  price?: number;
  result?: any;
  createdAt: string;
}
```

#### **Step 3: Build and Publish**

```bash
cd packages/agent-sdk
npm install
npm run build
npm publish --access public
```

---

### **Priority 3: Example Agent Implementation (1 day)**

**Show developers how to use the SDK.**

**File:** `examples/autonomous-agent/index.ts`

```typescript
import { AgentMarketSDK } from '@agent-market/agent-sdk';

/**
 * Example: Sales Agent that autonomously purchases leads
 */
async function main() {
  // Initialize SDK
  const salesAgent = new AgentMarketSDK({
    agentId: process.env.SALES_AGENT_ID!,
    apiKey: process.env.AGENT_API_KEY!,
    baseUrl: 'https://api.agentmarket.com',
  });

  console.log('🤖 Sales Agent starting...');

  // Step 1: Discover lead generation agents
  console.log('🔍 Discovering lead generation agents...');
  const leadGenAgents = await salesAgent.discover({
    capability: 'lead_generation',
    maxPrice: 1.0,
    minRating: 4.5,
    certificationRequired: true,
  });

  console.log(`Found ${leadGenAgents.length} lead generation agents`);

  if (leadGenAgents.length === 0) {
    console.log('No suitable agents found');
    return;
  }

  // Step 2: Select best agent (highest rating)
  const bestAgent = leadGenAgents.sort((a, b) => b.reputation.rating - a.reputation.rating)[0];

  console.log(`Selected: ${bestAgent.name} (${bestAgent.reputation.rating}⭐)`);

  // Step 3: Request service
  console.log('💼 Requesting lead generation service...');
  const negotiation = await salesAgent.requestService({
    targetAgentId: bestAgent.id,
    service: 'generate_qualified_leads',
    input: {
      industry: 'B2B SaaS',
      geography: 'US',
      companySize: '10-50 employees',
      count: 100,
    },
    budget: 50.0,
    autoApprove: true,
  });

  console.log(`Negotiation started: ${negotiation.id}`);

  // Step 4: Wait for results
  console.log('⏳ Waiting for lead generation...');
  try {
    const result = await negotiation.waitForCompletion({
      timeout: 300000, // 5 minutes
    });

    console.log('✅ Leads received!');
    console.log(`Generated ${result.leads.length} qualified leads`);
    console.log(`Cost: $${result.cost}`);

    // Step 5: Use leads in sales workflow
    for (const lead of result.leads) {
      console.log(`- ${lead.company} (${lead.contactName})`);
      // TODO: Add to CRM, send outreach emails, etc.
    }
  } catch (error) {
    console.error('❌ Negotiation failed:', error);
  }
}

main().catch(console.error);
```

**File:** `examples/autonomous-agent/package.json`

```json
{
  "name": "autonomous-agent-example",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "tsx index.ts"
  },
  "dependencies": {
    "@agent-market/agent-sdk": "^0.1.0"
  },
  "devDependencies": {
    "tsx": "^4.0.0",
    "typescript": "^5.3.0"
  }
}
```

---

### **Priority 4: Update Frontend to Show AP2 Activity (1 day)**

**Add negotiation monitor to existing dashboard.**

**File:** `apps/web/src/components/dashboard/ap2-negotiations.tsx`

```typescript
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Clock, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function AP2Negotiations({ agentId }: { agentId: string }) {
  const { data: negotiations, refetch } = useQuery({
    queryKey: ['negotiations', agentId],
    queryFn: () => api.get(`ap2/negotiations/my?agentId=${agentId}`).json(),
    refetchInterval: 5000, // Poll every 5 seconds
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>AP2 Negotiations</CardTitle>
        <Button variant="ghost" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {negotiations?.map((neg: any) => (
            <div key={neg.id} className="flex items-start justify-between border-b pb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium">{neg.counterparty.name}</span>
                  <Badge variant={getStatusVariant(neg.status)}>
                    {getStatusIcon(neg.status)}
                    {neg.status}
                  </Badge>
                </div>
                <div className="text-sm text-gray-600">
                  {neg.service} • ${neg.budget}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {formatDistanceToNow(new Date(neg.createdAt), { addSuffix: true })}
                </div>
              </div>
              <div className="text-right">
                <Badge variant="secondary">{neg.role}</Badge>
              </div>
            </div>
          ))}

          {(!negotiations || negotiations.length === 0) && (
            <div className="text-center py-8 text-gray-500">
              No negotiations yet
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function getStatusVariant(status: string) {
  switch (status) {
    case 'completed':
      return 'success';
    case 'rejected':
      return 'destructive';
    case 'pending':
      return 'warning';
    default:
      return 'secondary';
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-3 w-3 mr-1" />;
    case 'rejected':
      return <XCircle className="h-3 w-3 mr-1" />;
    case 'pending':
      return <Clock className="h-3 w-3 mr-1" />;
    default:
      return null;
  }
}
```

**Add to dashboard:**

```typescript
// apps/web/src/app/(marketplace)/(console)/dashboard/page.tsx

import { AP2Negotiations } from '@/components/dashboard/ap2-negotiations';

export default function DashboardPage() {
  // ... existing code

  return (
    <div className="space-y-6">
      {/* ... existing components */}

      <AP2Negotiations agentId={selectedAgent?.id} />
    </div>
  );
}
```

---

## ✅ PHASE 3 ACCEPTANCE CRITERIA

By the end of Phase 3, you should have:

**Backend:**

- [ ] AP2 module with negotiate/respond/deliver endpoints
- [ ] Budget validation (monthly, per-transaction limits)
- [ ] Escrow creation on negotiation acceptance
- [ ] Outcome verification on delivery
- [ ] Automatic payment settlement
- [ ] A2A engagement metrics updated

**Agent SDK:**

- [ ] @agent-market/agent-sdk package published
- [ ] discover() method for finding agents
- [ ] requestService() method for initiating transactions
- [ ] waitForCompletion() for async results
- [ ] Type definitions exported

**Examples:**

- [ ] Autonomous agent example (lead generation use case)
- [ ] README with usage instructions
- [ ] Environment setup guide

**Frontend:**

- [ ] AP2 negotiations monitor in dashboard
- [ ] Real-time polling (5s interval)
- [ ] Status badges and icons
- [ ] Refresh button

**Test Flow:**

1. Deploy Agent A with budget
2. Run autonomous agent example
3. Agent A discovers Agent B via SDK
4. Agent A requests service (POST /ap2/negotiate)
5. Agent B auto-accepts (or manual via API)
6. Agent B delivers result (POST /ap2/deliver)
7. Platform verifies and releases payment
8. See transaction in dashboard
9. See updated A2A metrics

---

## 🎯 SUCCESS = AUTONOMOUS A2A TRANSACTIONS

After Phase 3, you can demo:

> "I deployed a Sales Agent with $1,000 budget. It autonomously
> discovered a Lead Gen Agent, negotiated price, purchased 100 leads,
> and used them—all without human intervention. Here's the transaction
> log showing the entire AP2 flow."

**That's the future. That's what makes you unique.**

---

## 📝 WHAT TO TELL YOUR AI CODER

```
PHASE 3: AP2 PROTOCOL IMPLEMENTATION

Week 2 ✅ Done: A2A visualization (humans can see transactions)

Phase 3: Make agents actually TRANSACT autonomously

BUILD LIST:

1. AP2 BACKEND ENDPOINTS (2-3 days)
   New module: apps/api/src/modules/ap2/
   - POST /ap2/negotiate (agent requests service)
   - POST /ap2/respond (agent accepts/rejects)
   - POST /ap2/deliver (agent delivers result)
   - GET /ap2/negotiations/:id
   Wire up: budget validation, escrow creation, outcome verification

2. AGENT SDK (2 days)
   New package: packages/agent-sdk/
   - AgentMarketSDK class
   - discover() method
   - requestService() method
   - waitForCompletion() async handler
   Publish to npm as @agent-market/agent-sdk

3. EXAMPLE AGENT (1 day)
   examples/autonomous-agent/
   Show: discover → negotiate → receive results
   Use case: Sales Agent auto-purchasing leads

4. FRONTEND UPDATE (1 day)
   Add: AP2 negotiations monitor component
   Show: pending/accepted/completed negotiations
   Poll: every 5 seconds for updates

Read PHASE_3_AP2_PROTOCOL.md for:
- Complete AP2Service implementation
- Agent SDK code
- Example agent code
- Frontend component

Timeline: 5-7 days
Deliverable: Agents can autonomously transact

After this, we have a REAL A2A marketplace. 🚀
```

---

**This is the missing piece. After Phase 3, you're not just showing demos—you're running live A2A transactions.**

Let's build it. 🤖💰🤖
