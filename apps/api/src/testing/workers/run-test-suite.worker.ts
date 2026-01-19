import { Injectable, Logger } from '@nestjs/common';
import { Prisma, TestRunStatus } from '@prisma/client';
import { Worker, Job } from 'bullmq';
import Redis from 'ioredis';

import { AgentsService } from '../../modules/agents/agents.service.js';
import { PrismaService } from '../../modules/database/prisma.service.js';
import { getSuiteBySlug } from '../suites/index.js';
import { TestRunProgress, TestRunner } from '../types.js';

@Injectable()
export class RunTestSuiteWorker {
  private readonly logger = new Logger(RunTestSuiteWorker.name);
  private worker: Worker | null = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private redis: any;

  constructor(
    private readonly prisma: PrismaService,
    private readonly agentsService: AgentsService,
  ) { }

  /**
   * Initialize the worker (called after module initialization)
   */
  initialize() {
    if (this.worker) {
      return; // Already initialized
    }

    // Railway provides REDIS_URL in format: redis://default:password@host:port or rediss://default:password@host:port (TLS)
    const redisUrl = process.env.REDIS_URL;
    let parsedRedisUrl: URL | null = null;
    if (redisUrl) {
      try {
        parsedRedisUrl = new URL(redisUrl);
        this.logger.log(`Parsed REDIS_URL: host=${parsedRedisUrl.hostname}, port=${parsedRedisUrl.port}, hasPassword=${!!parsedRedisUrl.password}`);
      } catch (error) {
        this.logger.warn(`Invalid REDIS_URL provided: ${error instanceof Error ? error.message : 'Unknown error'}, falling back to REDIS_HOST/PORT`);
      }
    }
    const redisHost = process.env.REDIS_HOST ?? parsedRedisUrl?.hostname;
    const redisPort = parseInt(process.env.REDIS_PORT ?? parsedRedisUrl?.port ?? '6379', 10);
    // Extract password from URL (Railway format: redis://default:password@host:port)
    // URL.password contains the password part after the colon
    const redisPassword = process.env.REDIS_PASSWORD ?? parsedRedisUrl?.password;

    // Log Redis configuration for debugging
    if (redisHost) {
      this.logger.log(`Redis configuration: host=${redisHost}, port=${redisPort}, hasPassword=${!!redisPassword}, fromUrl=${!!parsedRedisUrl}`);
    }

    if (!redisHost) {
      this.logger.warn('Redis not configured - test run worker will not start');
      return;
    }

    try {
      // Initialize Redis for pub/sub
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      this.redis = new (Redis as any)({
        host: redisHost,
        port: redisPort,
        password: redisPassword,
        retryStrategy: () => null, // Don't retry on connection failure
        maxRetriesPerRequest: null,
        lazyConnect: true,
      });

      // Handle connection errors gracefully
      this.redis.on('error', (err: Error) => {
        this.logger.warn(`Redis connection error (worker): ${err.message}`);
      });

      // Initialize BullMQ worker
      this.worker = new Worker(
        'run-test-suite',
        async (job: Job) => {
          await this.processJob(job);
        },
        {
          connection: {
            host: redisHost,
            port: redisPort,
            password: redisPassword,
          },
          concurrency: 1, // Run tests sequentially
        },
      );

      this.worker.on('completed', (job) => {
        this.logger.log(`Test run ${job.id} completed`);
      });

      this.worker.on('failed', (job, err) => {
        const errorMessage = err instanceof Error ? err.message : String(err);
        const jobId = job?.id ?? 'unknown';
        this.logger.error(`Test run ${jobId} failed: ${errorMessage}`);
      });

      this.logger.log('Test run worker initialized');
    } catch (err) {
      this.logger.error(`Failed to initialize test run worker: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }

  }

  /**
   * Gracefully shutdown worker
   */
  async shutdown() {
    if (this.worker) {
      await this.worker.close();
      this.worker = null;
    }
    if (this.redis) {
      await this.redis.quit();
      this.redis = null;
    }
  }

  /**
   * Publish progress update to Redis pub/sub
   */
  private async publishProgress(runId: string, progress: TestRunProgress) {
    if (!this.redis) {
      this.logger.debug(`Redis not available, skipping progress publish for run ${runId}`);
      return;
    }

    try {
      const channel = `test-run:${runId}`;
      await this.redis.publish(channel, JSON.stringify(progress));
    } catch (error) {
      // Don't fail the test run if Redis publish fails
      this.logger.warn(`Failed to publish progress for run ${runId}: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Process a test run job from BullMQ
   */
  private async processJob(job: Job<{ runId: string; agentId: string; suiteId: string; userId: string; testIds?: string[] }, unknown, string>) {
    const { runId, agentId, suiteId, userId, testIds } = job.data;
    await this.runSuite({ runId, agentId, suiteId, userId, testIds });
  }

  /**
   * Run a test suite (shared by worker and inline fallback)
   */
  async runSuite(params: { runId: string; agentId: string; suiteId: string; userId: string; testIds?: string[] }) {
    const { runId, agentId, suiteId, userId, testIds } = params;

    this.logger.log(`Starting test run ${runId} for agent ${agentId} with suite ${suiteId}`);

    try {
      // Update status to RUNNING
      await this.prisma.testRun.update({
        where: { id: runId },
        data: {
          status: TestRunStatus.RUNNING,
          startedAt: new Date(),
        },
      });

      await this.publishProgress(runId, {
        runId,
        status: 'running',
        completedTests: 0,
        totalTests: 0,
      });

      // Get suite definition
      const suite = await this.prisma.testSuite.findUnique({
        where: { id: suiteId },
      });

      if (!suite) {
        throw new Error(`Suite ${suiteId} not found`);
      }

      // Get suite definition from registry
      const suiteDef = getSuiteBySlug(suite.slug);
      if (!suiteDef) {
        throw new Error(`Suite definition for ${suite.slug} not found`);
      }

      const totalTests = suiteDef.tests.length;
      const results: Array<{
        testId: string;
        passed: boolean;
        score: number;
        latencyMs?: number;
        costUsd?: number;
        error?: string;
        details?: Record<string, unknown>;
        logs?: string[];
      }> = [];
      let totalScore = 0;
      let totalCost = 0;
      let totalLatency = 0;
      let passedTests = 0;

      // Run each test sequentially
      for (let i = 0; i < suiteDef.tests.length; i++) {
        const testDef = suiteDef.tests[i];

        // Filter tests if testIds is provided
        if (testIds && testIds.length > 0 && !testIds.includes(testDef.id)) {
          continue;
        }

        await this.publishProgress(runId, {
          runId,
          status: 'running',
          currentTest: testDef.id,
          completedTests: i,
          totalTests,
        });

        try {
          // Dynamically import and run the test
          const testModule = await testDef.runner();
          // Handle both module with default export and direct TestRunner
          const testRunnerOrModule = 'default' in testModule ? testModule.default : testModule;

          // Extract the actual TestRunner instance
          // Always instantiate with agentsService to ensure proper dependency injection
          // Some test runners export pre-instantiated instances with null agentsService
          let testRunner: TestRunner;
          if (typeof testRunnerOrModule === 'function') {
            // It's a class constructor, instantiate it with agentsService
            // Ensure agentsService is available before instantiating
            if (!this.agentsService) {
              throw new Error(`AgentsService is not available for test ${testDef.id}`);
            }
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            testRunner = new (testRunnerOrModule as any)(this.agentsService);
          } else if (typeof testRunnerOrModule === 'object' && testRunnerOrModule !== null && 'run' in testRunnerOrModule) {
            // It's already an instance, but we should check if it needs agentsService
            // If it has a constructor property, try to re-instantiate it
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const constructor = (testRunnerOrModule as any).constructor;
            if (constructor && typeof constructor === 'function' && this.agentsService) {
              // Re-instantiate with proper agentsService
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              testRunner = new (constructor as any)(this.agentsService);
            } else {
              // Use the instance as-is (might have null agentsService, but we'll handle errors)
              testRunner = testRunnerOrModule as TestRunner;
            }
          } else {
            throw new Error(`Invalid test runner for test ${testDef.id}: expected object with 'run' method or constructor function, got ${typeof testRunnerOrModule}`);
          }

          // Validate testRunner has run method before calling
          if (!testRunner) {
            throw new Error(`Test runner for test ${testDef.id} is null or undefined`);
          }
          if (typeof testRunner.run !== 'function') {
            throw new Error(`Test runner for test ${testDef.id} does not have a valid 'run' method. Type: ${typeof testRunner.run}`);
          }

          // Ensure agentsService is available if test runner needs it
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          if (this.agentsService && typeof (testRunner as any).agentsService !== 'undefined') {
            // If test runner has agentsService property, ensure it's set
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (testRunner as any).agentsService = this.agentsService;
          }

          const testResult = await testRunner.run({
            agentId,
            suiteId,
            testId: testDef.id,
            userId,
          });

          results.push({
            testId: testDef.id,
            ...testResult,
          });

          if (testResult.passed) {
            passedTests++;
          }

          totalScore += testResult.score;
          totalCost += testResult.costUsd || 0;
          totalLatency += testResult.latencyMs || 0;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const errorStack = error instanceof Error ? error.stack : undefined;
          this.logger.error(`Test ${testDef.id} failed: ${errorMessage}`, errorStack);
          results.push({
            testId: testDef.id,
            passed: false,
            score: 0,
            error: errorMessage,
            details: {
              errorType: error instanceof Error ? error.constructor.name : typeof error,
              stack: errorStack,
            },
          });
        }
      }

      // Calculate final score (average of all test scores)
      const finalScore = totalTests > 0 ? Math.round(totalScore / totalTests) : 0;

      // Update agent trust score and badges if this is a baseline suite
      if (suiteDef.isRecommended && suiteDef.category === 'smoke') {
        await this.updateAgentTrustScore(agentId, finalScore);
      }

      // Update test run status
      await this.prisma.testRun.update({
        where: { id: runId },
        data: {
          status: TestRunStatus.COMPLETED,
          score: finalScore,
          completedAt: new Date(),
          rawResults: {
            results,
            summary: {
              totalTests,
              passedTests,
              failedTests: totalTests - passedTests,
              averageScore: finalScore,
              totalCost,
              totalLatency,
            },
          } as Prisma.InputJsonValue,
        },
      });

      await this.publishProgress(runId, {
        runId,
        status: 'completed',
        completedTests: totalTests,
        totalTests,
        score: finalScore,
      });

      this.logger.log(`Test run ${runId} completed with score ${finalScore}`);
    } catch (error) {
      this.logger.error(`Test run ${runId} failed: ${error instanceof Error ? error.message : 'Unknown error'}`);

      await this.prisma.testRun.update({
        where: { id: runId },
        data: {
          status: TestRunStatus.FAILED,
          completedAt: new Date(),
          rawResults: {
            error: error instanceof Error ? error.message : 'Unknown error',
          } as Prisma.InputJsonValue,
        },
      });

      await this.publishProgress(runId, {
        runId,
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
        completedTests: 0,
        totalTests: 0,
      });

      throw error;
    }
  }

  /**
   * Update agent trust score and badges based on test results
   */
  private async updateAgentTrustScore(agentId: string, score: number) {
    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
    });

    if (!agent) {
      return;
    }

    const badges: string[] = [...(agent.badges || [])];
    const updates: { trustScore: number; badges: string[] } = {
      trustScore: agent.trustScore,
      badges,
    };

    // Award badges based on score
    if (score >= 90 && !badges.includes('high-quality')) {
      badges.push('high-quality');
    }

    if (score >= 95 && !badges.includes('production-ready')) {
      badges.push('production-ready');
    }

    if (score >= 100 && !badges.includes('perfect-score')) {
      badges.push('perfect-score');
    }

    // Update trust score (weighted average with existing score)
    const newTrustScore = Math.round(agent.trustScore * 0.7 + score * 0.3);

    updates.trustScore = newTrustScore;

    await this.prisma.agent.update({
      where: { id: agentId },
      data: updates,
    });

    this.logger.log(`Updated agent ${agentId} trust score to ${newTrustScore} and badges: ${badges.join(', ')}`);
  }
}

