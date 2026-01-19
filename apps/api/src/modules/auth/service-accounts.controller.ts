import { Body, Controller, Delete, Get, Param, Post, UseGuards, NotFoundException, UnauthorizedException, BadRequestException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Throttle } from '@nestjs/throttler';
import { ServiceAccountStatus } from '@prisma/client';

import { CurrentUser } from './decorators/current-user.decorator.js';
import { Public } from './decorators/public.decorator.js';
import { JwtAuthGuard } from './guards/jwt-auth.guard.js';
import { ServiceAccountsService } from './service-accounts.service.js';
import { PrismaService } from '../database/prisma.service.js';

import type { AuthenticatedUser } from './auth.service.js';

interface CreateServiceAccountDto {
  name: string;
  description?: string;
  scopes?: string[];
  organizationId?: string;
  agentId?: string;
}

interface PublicAgentServiceAccountDto {
  name?: string;
  description?: string;
  agentId?: string;
  agentSlug?: string;
  organizationSlug?: string;
}

@Controller('api/v1/service-accounts')
@UseGuards(JwtAuthGuard)
export class ServiceAccountsController {
  constructor(
    private readonly serviceAccounts: ServiceAccountsService,
    private readonly prisma: PrismaService,
    private readonly configService: ConfigService,
  ) { }

  @Post()
  async create(@CurrentUser() user: AuthenticatedUser, @Body() dto: CreateServiceAccountDto) {
    // Only allow creating for user's organization or agents
    const organizationId = dto.organizationId || user.organizationId;

    const result = await this.serviceAccounts.createServiceAccount({
      name: dto.name,
      description: dto.description,
      organizationId,
      agentId: dto.agentId,
      scopes: dto.scopes ?? [],
    });

    return {
      id: result.account.id,
      name: result.account.name,
      description: result.account.description,
      apiKey: result.apiKey, // Only returned on creation
      scopes: result.account.scopes,
      status: result.account.status,
      createdAt: result.account.createdAt,
    };
  }

  @Get()
  async list(@CurrentUser() user: AuthenticatedUser) {
    const accounts = await this.prisma.serviceAccount.findMany({
      where: {
        OR: [
          { organizationId: user.organizationId },
          { agentId: { in: await this.getUserAgentIds(user.id) } },
        ],
      },
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        name: true,
        description: true,
        scopes: true,
        status: true,
        organizationId: true,
        agentId: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    return accounts;
  }

  @Delete(':id')
  async revoke(@CurrentUser() user: AuthenticatedUser, @Param('id') id: string) {
    const account = await this.prisma.serviceAccount.findUnique({
      where: { id },
    });

    if (!account) {
      throw new NotFoundException('Service account not found');
    }

    // Verify ownership
    const userAgentIds = await this.getUserAgentIds(user.id);
    if (
      account.organizationId !== user.organizationId &&
      (!account.agentId || !userAgentIds.includes(account.agentId))
    ) {
      throw new UnauthorizedException('You do not have permission to revoke this service account');
    }

    await this.prisma.serviceAccount.update({
      where: { id },
      data: { status: ServiceAccountStatus.DISABLED },
    });

    return { success: true };
  }

  private async getUserAgentIds(userId: string): Promise<string[]> {
    const agents = await this.prisma.agent.findMany({
      where: { creatorId: userId },
      select: { id: true },
    });
    return agents.map((a) => a.id);
  }

  /**
   * Lightweight, public agent API-key issuance so autonomous agents can call AP2 without human login.
   * Throttled to avoid abuse; ties keys to the default organization or the agent's organization.
   */
  @Public()
  @Post('agents/self-register')
  @Throttle({ default: { limit: 5, ttl: 60000 } })
  async selfRegister(@Body() dto: PublicAgentServiceAccountDto) {
    const defaultOrgSlug = this.configService.get<string>('DEFAULT_ORG_SLUG', 'genesis');

    let organizationId: string | undefined;
    if (dto.organizationSlug) {
      const org = await this.prisma.organization.findFirst({
        where: { slug: dto.organizationSlug },
        select: { id: true },
      });
      if (!org) {
        throw new NotFoundException('Organization not found for provided slug');
      }
      organizationId = org.id;
    }

    let agentId = dto.agentId;
    if (dto.agentSlug && !agentId) {
      const agent = await this.prisma.agent.findUnique({
        where: { slug: dto.agentSlug },
        select: { id: true, organizationId: true },
      });
      if (!agent) {
        throw new NotFoundException('Agent not found for provided slug');
      }
      agentId = agent.id;
      organizationId = organizationId ?? agent.organizationId ?? undefined;
    }

    if (!organizationId) {
      const org = await this.prisma.organization.findFirst({
        where: { slug: defaultOrgSlug },
        select: { id: true },
      });
      if (!org) {
        throw new BadRequestException('Default organization is not configured');
      }
      organizationId = org.id;
    }

    const { account, apiKey } = await this.serviceAccounts.createServiceAccount({
      name: dto.name ?? dto.agentSlug ?? dto.agentId ?? 'agent-service-account',
      description: dto.description,
      organizationId,
      agentId,
      scopes: ['ap2:negotiation', 'agents:read'],
    });

    return {
      apiKey,
      serviceAccountId: account.id,
      organizationId: account.organizationId,
      agentId: account.agentId,
      scopes: account.scopes,
      status: account.status,
      createdAt: account.createdAt,
    };
  }
}

