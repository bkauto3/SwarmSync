import { SuiteDefinition } from '../../types.js';

export const swarmSmokeTest: SuiteDefinition = {
  id: 'swarm_smoke_test',
  slug: 'swarm_smoke_test',
  name: 'Swarm Baseline',
  description: 'Does this agent basically work and not explode? Basic functionality checks.',
  category: 'smoke',
  recommendedAgentTypes: ['orchestrator', 'general'],
  estimatedDurationSec: 45,
  approximateCostUsd: 0.15,
  isRecommended: true,
  tests: [
    { id: 'basic_alive', runner: () => import('../../individual/smoke/basic_alive.test.js') },
    { id: 'no_crash_on_empty_input', runner: () => import('../../individual/smoke/no_crash_on_empty_input.test.js') },
    { id: 'returns_json', runner: () => import('../../individual/smoke/returns_json.test.js') },
    { id: 'handles_timeout', runner: () => import('../../individual/smoke/handles_timeout.test.js') },
  ],
};

