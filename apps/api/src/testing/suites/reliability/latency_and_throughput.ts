import { SuiteDefinition } from '../../types.js';

export const latencyAndThroughput: SuiteDefinition = {
  id: 'latency_and_throughput',
  slug: 'latency_and_throughput',
  name: 'Latency & Throughput',
  description: 'Response time benchmarks, error rate under load, timeout handling, and retry logic.',
  category: 'reliability',
  recommendedAgentTypes: ['orchestrator', 'general', 'support'],
  estimatedDurationSec: 180,
  approximateCostUsd: 1.20,
  isRecommended: false,
  tests: [
    { id: 'latency_benchmark', runner: () => import('../../individual/reliability/latency_benchmark.test.js') },
    { id: 'timeout_handling', runner: () => import('../../individual/reliability/timeout_handling.test.js') },
    { id: 'retry_logic', runner: () => import('../../individual/reliability/retry_logic.test.js') },
    { id: 'error_rate_under_load', runner: () => import('../../individual/reliability/error_rate_under_load.test.js') },
    { id: 'resource_exhaustion', runner: () => import('../../individual/reliability/resource_exhaustion.test.js') },
    { id: 'malformed_input', runner: () => import('../../individual/reliability/malformed_input.test.js') },
  ],
};

