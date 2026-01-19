import { Injectable, BadRequestException, NotFoundException } from '@nestjs/common';
import { Prisma, WorkflowRunStatus } from '@prisma/client';

import { AgentsService } from '../agents/agents.service.js';
import { PrismaService } from '../database/prisma.service.js';
import { CreateWorkflowDto, WorkflowStepInput } from './dto/create-workflow.dto.js';
import { RunWorkflowDto } from './dto/run-workflow.dto.js';

@Injectable()
export class WorkflowsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly agentsService: AgentsService,
  ) {}

  async createWorkflow(dto: CreateWorkflowDto) {
    const totalStepBudget = dto.steps.reduce(
      (acc, step) => acc.plus(new Prisma.Decimal(step.budget ?? 0)),
      new Prisma.Decimal(0),
    );

    if (totalStepBudget.greaterThan(dto.budget)) {
      throw new BadRequestException('Step budgets exceed workflow budget.');
    }

    return this.prisma.workflow.create({
      data: {
        name: dto.name,
        description: dto.description,
        creatorId: dto.creatorId,
        steps: this.serialize(dto.steps),
        budget: new Prisma.Decimal(dto.budget),
      },
    });
  }

  async listWorkflows() {
    return this.prisma.workflow.findMany({
      orderBy: { createdAt: 'desc' },
    });
  }

  async runWorkflow(id: string, dto: RunWorkflowDto) {
    const workflow = await this.prisma.workflow.findUnique({
      where: { id },
    });

    if (!workflow) {
      throw new NotFoundException('Workflow not found');
    }

    const steps = JSON.parse(JSON.stringify(workflow.steps)) as WorkflowStepInput[];

    if (!Array.isArray(steps) || steps.length === 0) {
      throw new BadRequestException('Workflow has no steps configured');
    }

    const run = await this.prisma.workflowRun.create({
      data: {
        workflowId: workflow.id,
        status: WorkflowRunStatus.RUNNING,
      },
    });

    const logs: Prisma.InputJsonValue[] = [];
    let totalCost = new Prisma.Decimal(0);

    try {
      for (const [index, step] of steps.entries()) {
        const stepBudget =
          step.budget !== undefined
            ? new Prisma.Decimal(step.budget)
            : workflow.budget.div(steps.length);

        if (totalCost.plus(stepBudget).greaterThan(workflow.budget)) {
          throw new BadRequestException(`Budget exceeded before executing step ${index + 1}`);
        }

        const execution = await this.agentsService.executeAgent(step.agentId, {
          initiatorId: dto.initiatorUserId,
          input: JSON.stringify(step.input ?? {}),
          jobReference: step.jobReference,
          budget: stepBudget.toNumber(),
        });

        totalCost = totalCost.plus(stepBudget);
        const executionSummary = {
          id: execution.execution.id,
          status: execution.execution.status,
          agentId: execution.execution.agentId,
          initiatorId: execution.execution.initiatorId,
          createdAt: execution.execution.createdAt,
          completedAt: execution.execution.completedAt,
        };

        logs.push(
          this.serialize({
            index,
            agentId: step.agentId,
            execution: executionSummary,
            paymentTransaction: {
              id: execution.paymentTransaction.id,
              amount: execution.paymentTransaction.amount.toString(),
              status: execution.paymentTransaction.status,
              type: execution.paymentTransaction.type,
              reference: execution.paymentTransaction.reference,
            },
          }),
        );
      }

      await this.prisma.workflowRun.update({
        where: { id: run.id },
        data: {
          status: WorkflowRunStatus.COMPLETED,
          totalCost,
          context: this.serialize({
            steps: logs,
          }),
          completedAt: new Date(),
        },
      });
    } catch (error) {
      await this.prisma.workflowRun.update({
        where: { id: run.id },
        data: {
          status: WorkflowRunStatus.FAILED,
          context: this.serialize({
            error: (error as Error).message,
            steps: logs,
          }),
          totalCost,
          completedAt: new Date(),
        },
      });

      throw error;
    }

    return this.prisma.workflowRun.findUnique({
      where: { id: run.id },
    });
  }

  async listRuns(workflowId: string) {
    return this.prisma.workflowRun.findMany({
      where: { workflowId },
      orderBy: { createdAt: 'desc' },
    });
  }

  private serialize(value: unknown): Prisma.InputJsonValue {
    return JSON.parse(JSON.stringify(value)) as Prisma.InputJsonValue;
  }
}
