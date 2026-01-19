import { Module, OnModuleInit, OnModuleDestroy } from '@nestjs/common';

import { upsertTestSuites } from './suites/index.js';
import { TestRunService } from './test-run.service.js';
import { TestRunsController } from './test-runs.controller.js';
import { TestRunsGateway } from './test-runs.gateway.js';
import { TestSuitesController } from './test-suites.controller.js';
import { RunTestSuiteWorker } from './workers/run-test-suite.worker.js';
import { AgentsModule } from '../modules/agents/agents.module.js';
import { AuthModule } from '../modules/auth/auth.module.js';
import { DatabaseModule } from '../modules/database/database.module.js';
import { PrismaService } from '../modules/database/prisma.service.js';

@Module({
  imports: [DatabaseModule, AgentsModule, AuthModule],
  controllers: [TestRunsController, TestSuitesController],
  providers: [TestRunService, RunTestSuiteWorker, TestRunsGateway],
  exports: [TestRunService],
})
export class TestingModule implements OnModuleInit, OnModuleDestroy {
  constructor(
    private readonly prisma: PrismaService,
    private readonly worker: RunTestSuiteWorker,
  ) {}

  async onModuleInit() {
    // Upsert all test suites on startup (gracefully handles missing table)
    try {
      await upsertTestSuites(this.prisma);
    } catch (error) {
      // Log but don't fail startup if test suites can't be registered
      console.warn('Failed to register test suites:', error instanceof Error ? error.message : 'Unknown error');
    }
    // Initialize worker (will skip if Redis not configured)
    this.worker.initialize();
  }

  async onModuleDestroy() {
    // Shutdown worker gracefully
    await this.worker.shutdown();
  }
}

