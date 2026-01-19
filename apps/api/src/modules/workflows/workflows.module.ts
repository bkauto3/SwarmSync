import { Module } from '@nestjs/common';

import { WorkflowsController } from './workflows.controller.js';
import { WorkflowsService } from './workflows.service.js';
import { AgentsModule } from '../agents/agents.module.js';

@Module({
  imports: [AgentsModule],
  controllers: [WorkflowsController],
  providers: [WorkflowsService],
  exports: [WorkflowsService],
})
export class WorkflowsModule {}
