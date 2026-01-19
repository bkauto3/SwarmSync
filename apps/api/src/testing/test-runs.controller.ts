import {
  Controller,
  Get,
  Post,
  Body,
  Param,
  Query,
  Delete,
  Request,
  NotFoundException,
  BadRequestException,
} from '@nestjs/common';
import { TestRunStatus } from '@prisma/client';
import { Allow } from 'class-validator';

import { TestRunService } from './test-run.service.js';

class StartTestRunDto {
  @Allow()
  agentId!: string | string[];

  @Allow()
  suiteId!: string | string[];
}

@Controller('api/v1/test-runs')
export class TestRunsController {
  constructor(private readonly testRunService: TestRunService) {}

  @Post()
  async startRun(@Body() body: StartTestRunDto, @Request() req?: { user?: { id: string } }) {
    // Validate that agentId and suiteId are provided and not empty
    const agentIds = Array.isArray(body.agentId) ? body.agentId : [body.agentId];
    const suiteIds = Array.isArray(body.suiteId) ? body.suiteId : [body.suiteId];

    if (!body.agentId || agentIds.length === 0 || agentIds.some((id) => !id || id.trim() === '')) {
      throw new BadRequestException('agentId is required and cannot be empty');
    }
    if (!body.suiteId || suiteIds.length === 0 || suiteIds.some((id) => !id || id.trim() === '')) {
      throw new BadRequestException('suiteId is required and cannot be empty');
    }

    const userId = req?.user?.id ?? 'anonymous';
    return this.testRunService.startRun({
      agentId: body.agentId,
      suiteId: body.suiteId,
      userId,
    });
  }

  @Get()
  async listRuns(
    @Query('agentId') agentId?: string,
    @Query('suiteId') suiteId?: string,
    @Query('status') status?: TestRunStatus,
    @Query('limit') limit?: string,
    @Query('offset') offset?: string,
    @Request() req?: { user?: { id: string } },
  ) {
    return this.testRunService.listRuns({
      agentId,
      suiteId,
      userId: req?.user?.id,
      status,
      limit: limit ? parseInt(limit, 10) : undefined,
      offset: offset ? parseInt(offset, 10) : undefined,
    });
  }

  @Get(':id')
  async getRun(@Param('id') id: string, @Request() req?: { user?: { id: string } }) {
    try {
      return await this.testRunService.getRun(id, req?.user?.id);
    } catch (error) {
      if (error instanceof NotFoundException) {
        throw error;
      }
      throw new NotFoundException(`Test run ${id} not found`);
    }
  }

  @Delete(':id')
  async cancelRun(@Param('id') id: string, @Request() req?: { user?: { id: string } }) {
    return this.testRunService.cancelRun(id, req?.user?.id ?? 'anonymous');
  }
}

