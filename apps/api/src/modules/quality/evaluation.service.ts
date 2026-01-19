import { Injectable, NotFoundException } from '@nestjs/common';
import { EvaluationStatus, Prisma } from '@prisma/client';

import { PrismaService } from '../database/prisma.service.js';
import { RunEvaluationDto } from './dto/run-evaluation.dto.js';

@Injectable()
export class EvaluationService {
  constructor(private readonly prisma: PrismaService) {}

  async runScenario(dto: RunEvaluationDto) {
    await this.ensureAgentExists(dto.agentId);

    const scenario =
      (dto.scenarioId &&
        (await this.prisma.evaluationScenario.findUnique({ where: { id: dto.scenarioId } }))) ||
      (await this.prisma.evaluationScenario.create({
        data: {
          name: dto.scenarioName ?? `Scenario-${Date.now()}`,
          vertical: dto.vertical,
          input: (dto.input ?? {}) as Prisma.InputJsonValue,
          expected: (dto.expected ?? {}) as Prisma.InputJsonValue,
          tolerances: (dto.tolerances ?? {}) as Prisma.InputJsonValue,
        },
      }));

    const result = await this.prisma.evaluationResult.create({
      data: {
        agentId: dto.agentId,
        scenarioId: scenario.id,
        status: dto.passed ? EvaluationStatus.PASSED : EvaluationStatus.FAILED,
        latencyMs: dto.latencyMs ?? null,
        cost: dto.cost ? new Prisma.Decimal(dto.cost) : null,
        logs: (dto.logs ?? {}) as Prisma.InputJsonValue,
        certificationId: dto.certificationId ?? null,
      },
      include: {
        scenario: true,
      },
    });

    return result;
  }

  async listResults(agentId: string) {
    await this.ensureAgentExists(agentId);

    return this.prisma.evaluationResult.findMany({
      where: { agentId },
      include: { scenario: true },
      orderBy: { createdAt: 'desc' },
      take: 50,
    });
  }

  private async ensureAgentExists(agentId: string) {
    const exists = await this.prisma.agent.count({ where: { id: agentId } });
    if (!exists) {
      throw new NotFoundException('Agent not found');
    }
  }
}
