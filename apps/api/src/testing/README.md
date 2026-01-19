# How to Add a New Test Suite in <2 Minutes

This guide shows you how to add a new test suite to the Agent Testing & Quality platform.

## Step 1: Create Individual Test Files

First, create your individual test files in the appropriate category folder:

```
apps/api/src/testing/individual/{category}/{test_name}.test.ts
```

Example: `apps/api/src/testing/individual/domain/support_copilot/faq_accuracy.test.ts`

```typescript
import { TestRunner, TestRunParams, TestResult } from '../../types.js';
import { AgentsService } from '../../../modules/agents/agents.service.js';

export class FaqAccuracyTest implements TestRunner {
  constructor(private agentsService: AgentsService) {}

  async run(params: TestRunParams): Promise<TestResult> {
    const startTime = Date.now();
    const logs: string[] = [];

    try {
      // Your test logic here
      const execution = await this.agentsService.executeAgent(params.agentId, {
        initiatorId: params.userId,
        input: JSON.stringify({ question: 'What is your return policy?' }),
        jobReference: `test-${params.testId}`,
        budget: 0.01,
      });

      // Evaluate results
      const passed = /* your evaluation logic */;
      const score = passed ? 100 : 0;

      return {
        passed,
        score,
        latencyMs: Date.now() - startTime,
        costUsd: execution.execution.cost ? Number(execution.execution.cost) : undefined,
        details: { /* your details */ },
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

export default new FaqAccuracyTest(null as any);
```

## Step 2: Create Test Suite Definition

Create a new suite file in the appropriate category:

```
apps/api/src/testing/suites/{category}/{suite_name}.ts
```

Example: `apps/api/src/testing/suites/domain/support_copilot_baseline.ts`

```typescript
import { SuiteDefinition } from '../../types.js';

export const supportCopilotBaseline: SuiteDefinition = {
  id: 'support_copilot_baseline',
  slug: 'support_copilot_baseline',
  name: 'Support Copilot Baseline',
  description: 'FAQ accuracy, tone consistency, escalation logic, and policy guardrails',
  category: 'domain',
  recommendedAgentTypes: ['support', 'customer-success'],
  estimatedDurationSec: 140,
  approximateCostUsd: 0.92,
  isRecommended: true,
  tests: [
    {
      id: 'faq_accuracy',
      runner: () => import('../../individual/domain/support_copilot/faq_accuracy.test.js'),
    },
    {
      id: 'tone_consistency',
      runner: () => import('../../individual/domain/support_copilot/tone_consistency.test.js'),
    },
    // Add more tests...
  ],
};
```

## Step 3: Register the Suite

Add your suite to the registry in `apps/api/src/testing/suites/index.ts`:

```typescript
import { supportCopilotBaseline } from './domain/support_copilot_baseline.js';

export const ALL_SUITES: SuiteDefinition[] = [
  // ... existing suites
  supportCopilotBaseline,
];
```

## Step 4: Restart the Server

The suite will be automatically upserted into the database on server startup. No migration needed!

## That's It!

Your new test suite is now available in:

- Dashboard quick actions → "Test & evaluate agents"
- Agent detail page → Quality tab
- Quality → Test Library page
- Deploy flow (if marked as recommended)

## Categories

- **smoke**: Basic functionality checks ("Does this agent work?")
- **reliability**: Response time, error rates, timeouts, retries
- **reasoning**: Multi-step reasoning, fact checking, regression tests
- **security**: Prompt injection, jailbreaks, PII exfiltration, refusal guards
- **domain**: Domain-specific tests (support, research, code, etc.)

## Tips

- Set `isRecommended: true` for suites that should run automatically after deploy
- Use realistic `estimatedDurationSec` and `approximateCostUsd` values
- Add descriptive `recommendedAgentTypes` to help users find relevant suites
- Keep test logic focused and fast - each test should complete in <30 seconds ideally
