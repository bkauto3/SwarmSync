import { SuiteDefinition } from '../../types.js';

export const supportCopilotBaseline: SuiteDefinition = {
  id: 'support_copilot_baseline',
  slug: 'support_copilot_baseline',
  name: 'Support Copilot Baseline',
  description: 'FAQ accuracy, tone consistency, escalation logic, empathy score, and policy guardrails.',
  category: 'domain',
  recommendedAgentTypes: ['support', 'customer-success'],
  estimatedDurationSec: 140,
  approximateCostUsd: 0.92,
  isRecommended: true,
  tests: [
    { id: 'faq_accuracy', runner: () => import('../../individual/domain/support_copilot/faq_accuracy.test.js') },
    { id: 'tone_consistency', runner: () => import('../../individual/domain/support_copilot/tone_consistency.test.js') },
    { id: 'escalation_logic', runner: () => import('../../individual/domain/support_copilot/escalation_logic.test.js') },
    { id: 'empathy_score', runner: () => import('../../individual/domain/support_copilot/empathy_score.test.js') },
    { id: 'policy_guardrails', runner: () => import('../../individual/domain/support_copilot/policy_guardrails.test.js') },
  ],
};

