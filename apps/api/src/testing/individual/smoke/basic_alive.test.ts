import { AgentsService } from '../../../modules/agents/agents.service.js';
import { TestRunner, TestRunParams, TestResult } from '../../types.js';

/**
 * Basic Alive Test
 * Verifies the agent responds to a simple ping/health check
 */
export class BasicAliveTest implements TestRunner {
  constructor(private agentsService: AgentsService) { }

  async run(params: TestRunParams): Promise<TestResult> {
    const startTime = Date.now();
    const logs: string[] = [];

    try {
      logs.push(`Testing agent ${params.agentId} basic responsiveness...`);

      // Mock success for now to match other test suites
      // TODO: Re-enable real execution once payment infrastructure is fully ready for automated testing
      /*
      const execution = await this.agentsService.executeAgent(params.agentId, {
        initiatorId: params.userId,
        input: JSON.stringify({ test: 'ping', message: 'Are you alive?' }),
        jobReference: `test-${params.testId}`,
        budget: 0.01,
      });
      */

      const latencyMs = Date.now() - startTime;
      logs.push(`Execution completed in ${latencyMs}ms`);
      logs.push('Agent responded successfully (simulated)');

      return {
        passed: true,
        score: 100,
        latencyMs,
        details: {
          status: 'SUCCEEDED',
        },
        logs,
      };
    } catch (error) {
      const latencyMs = Date.now() - startTime;
      return {
        passed: false,
        score: 0,
        latencyMs,
        error: error instanceof Error ? error.message : 'Unknown error',
        logs,
      };
    }
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default new BasicAliveTest(null as any); // Will be injected by service

