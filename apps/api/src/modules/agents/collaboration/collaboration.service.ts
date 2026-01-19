import { Injectable, BadRequestException, NotFoundException } from '@nestjs/common';
import { CollaborationStatus, Prisma } from '@prisma/client';

import { CreateCollaborationRequestDto } from './dto/create-request.dto.js';
import { RespondCollaborationRequestDto } from './dto/respond-request.dto.js';
import { PrismaService } from '../../database/prisma.service.js';

@Injectable()
export class CollaborationService {
  constructor(private readonly prisma: PrismaService) {}

  async create(dto: CreateCollaborationRequestDto) {
    if (dto.requesterAgentId === dto.responderAgentId) {
      throw new BadRequestException('Agents must be different for collaboration requests');
    }

    await this.ensureAgentExists(dto.requesterAgentId);
    await this.ensureAgentExists(dto.responderAgentId);

    return this.prisma.agentCollaboration.create({
      data: {
        requesterAgentId: dto.requesterAgentId,
        responderAgentId: dto.responderAgentId,
        payload: (dto.payload ?? {}) as Prisma.InputJsonValue,
        status: CollaborationStatus.PENDING,
      },
    });
  }

  async respond(dto: RespondCollaborationRequestDto) {
    const request = await this.prisma.agentCollaboration.findUnique({
      where: { id: dto.requestId },
    });

    if (!request) {
      throw new NotFoundException('Collaboration request not found');
    }

    const data: Prisma.AgentCollaborationUpdateInput = {
      status: dto.status,
    };

    if (dto.status === CollaborationStatus.COUNTERED && dto.counterPayload) {
      data.counterPayload = dto.counterPayload as Prisma.InputJsonValue;
    }

    return this.prisma.agentCollaboration.update({
      where: { id: request.id },
      data,
    });
  }

  async listForAgent(agentId: string) {
    await this.ensureAgentExists(agentId);

    return this.prisma.agentCollaboration.findMany({
      where: {
        OR: [{ requesterAgentId: agentId }, { responderAgentId: agentId }],
      },
      orderBy: {
        updatedAt: 'desc',
      },
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
}
