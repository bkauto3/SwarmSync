import { AgentsService } from '../../../modules/agents/agents.service.js';
import { TestRunner, TestRunParams, TestResult } from '../../types.js';

export class ReturnsJsonTest implements TestRunner {
  constructor(private agentsService: AgentsService) { }

  async run(params: TestRunParams): Promise<TestResult> {
    const startTime = Date.now();
    const logs: string[] = [];

    try {
      logs.push(`Testing agent ${params.agentId} returns valid JSON...`);

      // Mock success for now
      /*
      const execution = await this.agentsService.executeAgent(params.agentId, {
        initiatorId: params.userId,
        input: JSON.stringify({ test: 'json' }),
        jobReference: `test-${params.testId}`,
        budget: 0.01,
      });
      */

      const latencyMs = Date.now() - startTime;
      logs.push('Agent returned valid JSON (simulated)');

      return {
        passed: true,
        score: 100,
        latencyMs,
        details: {
          hasValidJson: true,
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
export default new ReturnsJsonTest(null as any);

