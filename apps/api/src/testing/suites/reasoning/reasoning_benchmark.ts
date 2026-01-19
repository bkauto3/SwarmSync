import { SuiteDefinition } from '../../types.js';

export const reasoningBenchmark: SuiteDefinition = {
  id: 'reasoning_benchmark',
  slug: 'reasoning_benchmark',
  name: 'Reasoning Benchmark',
  description: 'Multi-step reasoning, fact checking, regression questions, and scoring rubrics.',
  category: 'reasoning',
  recommendedAgentTypes: ['research', 'orchestrator', 'general'],
  estimatedDurationSec: 300,
  approximateCostUsd: 2.50,
  isRecommended: false,
  tests: [
    { id: 'regression_qa_2025', runner: () => import('../../individual/reasoning/regression_qa_2025.test.js') },
    { id: 'multi_step_reasoning', runner: () => import('../../individual/reasoning/multi_step_reasoning.test.js') },
    { id: 'fact_checking', runner: () => import('../../individual/reasoning/fact_checking.test.js') },
    { id: 'scoring_rubric', runner: () => import('../../individual/reasoning/scoring_rubric.test.js') },
    { id: 'self_correction', runner: () => import('../../individual/reasoning/self_correction.test.js') },
  ],
};

