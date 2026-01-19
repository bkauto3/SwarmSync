import { Body, Controller, Get, Param, Post } from '@nestjs/common';

import { CreateWorkflowDto } from './dto/create-workflow.dto.js';
import { RunWorkflowDto } from './dto/run-workflow.dto.js';
import { WorkflowsService } from './workflows.service.js';

@Controller('workflows')
export class WorkflowsController {
  constructor(private readonly workflowsService: WorkflowsService) {}

  @Post()
  create(@Body() body: CreateWorkflowDto) {
    return this.workflowsService.createWorkflow(body);
  }

  @Get()
  list() {
    return this.workflowsService.listWorkflows();
  }

  @Post(':id/run')
  run(@Param('id') id: string, @Body() body: RunWorkflowDto) {
    return this.workflowsService.runWorkflow(id, body);
  }

  @Get(':id/runs')
  runs(@Param('id') id: string) {
    return this.workflowsService.listRuns(id);
  }
}
