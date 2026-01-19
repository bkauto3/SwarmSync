import { createHash, randomBytes } from 'node:crypto';

import { Injectable } from '@nestjs/common';
import { ServiceAccountStatus } from '@prisma/client';

import { AuthenticatedUser } from './auth.service.js';
import { PrismaService } from '../database/prisma.service.js';

interface CreateServiceAccountOptions {
  name: string;
  description?: string;
  organizationId?: string;
  agentId?: string;
  scopes?: string[];
}

@Injectable()
export class ServiceAccountsService {
  constructor(private readonly prisma: PrismaService) {}

  async validateApiKey(apiKey: string): Promise<AuthenticatedUser | null> {
    const apiKeyHash = this.hashSecret(apiKey);
    const serviceAccount = await this.prisma.serviceAccount.findFirst({
      where: {
        apiKeyHash,
        status: ServiceAccountStatus.ACTIVE,
      },
      include: {
        organization: {
          select: {
            id: true,
            name: true,
            slug: true,
          },
        },
        agent: {
          select: {
            id: true,
            name: true,
            slug: true,
          },
        },
      },
    });

    if (!serviceAccount) {
      return null;
    }

    return {
      id: `service-account:${serviceAccount.id}`,
      email: `${serviceAccount.name}@service-account.agent-market`,
      displayName: serviceAccount.name,
      kind: 'service_account',
      serviceAccountId: serviceAccount.id,
      organizationId: serviceAccount.organizationId ?? undefined,
      agentId: serviceAccount.agentId ?? undefined,
      scopes: serviceAccount.scopes,
    };
  }

  async createServiceAccount(options: CreateServiceAccountOptions) {
    const apiKey = this.generateToken();
    const apiKeyHash = this.hashSecret(apiKey);
    const account = await this.prisma.serviceAccount.create({
      data: {
        name: options.name,
        description: options.description,
        apiKeyHash,
        organizationId: options.organizationId,
        agentId: options.agentId,
        scopes: options.scopes ?? [],
      },
    });

    return {
      account,
      apiKey,
    };
  }

  private hashSecret(secret: string) {
    return createHash('sha256').update(secret).digest('hex');
  }

  private generateToken() {
    return `sa_${randomBytes(24).toString('hex')}`;
  }
}
