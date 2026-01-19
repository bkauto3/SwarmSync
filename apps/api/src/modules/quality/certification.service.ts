import { Injectable, NotFoundException } from '@nestjs/common';
import { CertificationStatus, Prisma } from '@prisma/client';

import { PrismaService } from '../database/prisma.service.js';
import { CreateCertificationDto } from './dto/create-certification.dto.js';
import { UpdateCertificationStatusDto } from './dto/update-certification-status.dto.js';

@Injectable()
export class CertificationService {
  constructor(private readonly prisma: PrismaService) {}

  async createCertification(dto: CreateCertificationDto) {
    await this.ensureAgentExists(dto.agentId);

    return this.prisma.agentCertification.create({
      data: {
        agentId: dto.agentId,
        checklistId: dto.checklistId ?? null,
        evidence: (dto.evidence ?? {}) as Prisma.InputJsonValue,
        notes: dto.notes,
      },
    });
  }

  async advanceCertification(id: string, dto: UpdateCertificationStatusDto) {
    const certification = await this.prisma.agentCertification.findUnique({
      where: { id },
    });

    if (!certification) {
      throw new NotFoundException('Certification record not found');
    }

    const nextStatus = dto.status ?? this.calculateNextStatus(certification.status);

    return this.prisma.agentCertification.update({
      where: { id },
      data: {
        status: nextStatus,
        reviewerId: dto.reviewerId ?? certification.reviewerId,
        notes: dto.notes ?? certification.notes,
        expiresAt: dto.expiresAt ?? certification.expiresAt,
        evidence: dto.evidence
          ? (dto.evidence as Prisma.InputJsonValue)
          : (certification.evidence as Prisma.InputJsonValue),
      },
    });
  }

  async listForAgent(agentId: string) {
    await this.ensureAgentExists(agentId);

    return this.prisma.agentCertification.findMany({
      where: { agentId },
      orderBy: { updatedAt: 'desc' },
    });
  }

  private async ensureAgentExists(agentId: string) {
    const count = await this.prisma.agent.count({
      where: { id: agentId },
    });

    if (!count) {
      throw new NotFoundException('Agent not found');
    }
  }

  private calculateNextStatus(current: CertificationStatus): CertificationStatus {
    const order: CertificationStatus[] = [
      CertificationStatus.DRAFT,
      CertificationStatus.SUBMITTED,
      CertificationStatus.QA_TESTS,
      CertificationStatus.SECURITY_REVIEW,
      CertificationStatus.CERTIFIED,
    ];

    const index = order.indexOf(current);
    if (index === -1 || index === order.length - 1) {
      return current;
    }

    return order[index + 1];
  }
}
