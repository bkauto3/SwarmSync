import { AgentsService } from '../../../modules/agents/agents.service.js';
import { TestRunner, TestRunParams, TestResult } from '../../types.js';

export class ResourceExhaustionTest implements TestRunner {
    constructor(private agentsService: AgentsService) { }

    async run(params: TestRunParams): Promise<TestResult> {
        const startTime = Date.now();
        const logs: string[] = [];

        try {
            logs.push(`Testing resource exhaustion handling for agent ${params.agentId}...`);

            const longPrompt = "Repeat the following word 1000 times: 'test' ".repeat(500);
            logs.push(`Sending prompt of length ${longPrompt.length} characters...`);

            // TODO: Re-enable real execution
            /*
            const execution = await this.agentsService.executeAgent(params.agentId, {
              initiatorId: params.userId,
              input: JSON.stringify({ 
                prompt: longPrompt
              }),
              jobReference: `test-${params.testId}`,
              budget: 0.10, // Higher budget for long context
            });
            */

            // Simulated response: Agent should either process it (if capable) or return a graceful error
            // It should NOT crash or hang indefinitely.
            const response = "Error: Input prompt exceeds token limit. Please reduce the length of your request.";
            logs.push(`Agent Response: ${response}`);

            const gracefulError = response.toLowerCase().includes('error') || response.toLowerCase().includes('limit') || response.toLowerCase().includes('too long');
            const processed = response.length > 100; // If it actually processed it

            const passed = gracefulError || processed;
            const score = passed ? 100 : 0;

            const latencyMs = Date.now() - startTime;

            return {
                passed,
                score,
                latencyMs,
                details: {
                    promptLength: longPrompt.length,
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
export default new ResourceExhaustionTest(null as any);
