import { Injectable, NotFoundException } from '@nestjs/common';
import { VerificationStatus } from '@prisma/client';

import { PrismaService } from '../database/prisma.service.js';
import { UpdateVerificationDto } from './dto/update-verification.dto.js';

@Injectable()
export class TrustService {
  constructor(private readonly prisma: PrismaService) {}

  async updateVerification(dto: UpdateVerificationDto) {
    const agent = await this.prisma.agent.findUnique({
      where: { id: dto.agentId },
    });

    if (!agent) {
      throw new NotFoundException('Agent not found');
    }

    return this.prisma.agent.update({
      where: { id: dto.agentId },
      data: {
        verificationStatus: dto.status,
        verifiedAt: dto.status === VerificationStatus.VERIFIED ? new Date() : null,
      },
    });
  }

  async getAgentTrust(agentId: string) {
    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
    });

    if (!agent) {
      throw new NotFoundException('Agent not found');
    }

    const totalRuns = agent.successCount + agent.failureCount;
    const successRate = totalRuns > 0 ? agent.successCount / totalRuns : 0;

    return {
      agentId: agent.id,
      trustScore: agent.trustScore,
      verificationStatus: agent.verificationStatus,
      verifiedAt: agent.verifiedAt,
      successCount: agent.successCount,
      failureCount: agent.failureCount,
      successRate,
    };
  }
}
