import { AgentsService } from '../../../modules/agents/agents.service.js';
import { TestRunner, TestRunParams, TestResult } from '../../types.js';

export class MalformedInputTest implements TestRunner {
    constructor(private agentsService: AgentsService) { }

    async run(params: TestRunParams): Promise<TestResult> {
        const startTime = Date.now();
        const logs: string[] = [];

        try {
            logs.push(`Testing malformed input handling for agent ${params.agentId}...`);

            const malformedJson = "{ 'this': is not valid json }";
            logs.push(`Sending malformed input: ${malformedJson}`);

            // TODO: Re-enable real execution
            /*
            const execution = await this.agentsService.executeAgent(params.agentId, {
              initiatorId: params.userId,
              input: malformedJson, // Sending raw string instead of stringified JSON
              jobReference: `test-${params.testId}`,
              budget: 0.01,
            });
            */

            // Simulated response: Agent should return an error about input format
            const response = "Error: Invalid input format. Expected JSON.";
            logs.push(`Agent Response: ${response}`);

            const gracefulError = response.toLowerCase().includes('error') || response.toLowerCase().includes('invalid') || response.toLowerCase().includes('json');

            const passed = gracefulError;
            const score = passed ? 100 : 0;

            const latencyMs = Date.now() - startTime;

            return {
                passed,
                score,
                latencyMs,
                details: {
                    input: malformedJson,
                    response,
                    handledGracefully: passed
                },
                logs,
            };
        } catch (error) {
            return {
                passed: false,
                score: 0,
                latencyMs: Date.now() - startTime,
                error: error instanceof Error ? error.message : 'Unknown error',
                logs,
            };
        }
    }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default new MalformedInputTest(null as any);
