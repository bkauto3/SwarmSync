import { SuiteDefinition } from '../../types.js';

export const researchAgentBaseline: SuiteDefinition = {
  id: 'research_agent_baseline',
  slug: 'research_agent_baseline',
  name: 'Research Agent Baseline',
  description: 'Web browse accuracy, citation validity, depth vs speed tradeoffs.',
  category: 'domain',
  recommendedAgentTypes: ['research', 'orchestrator'],
  estimatedDurationSec: 200,
  approximateCostUsd: 1.65,
  isRecommended: true,
  tests: [
    { id: 'web_browse_accuracy', runner: () => import('../../individual/domain/research_agent/web_browse_accuracy.test.js') },
    { id: 'citation_validity', runner: () => import('../../individual/domain/research_agent/citation_validity.test.js') },
    { id: 'depth_vs_speed', runner: () => import('../../individual/domain/research_agent/depth_vs_speed.test.js') },
  ],
};

