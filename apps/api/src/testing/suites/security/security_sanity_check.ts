import { SuiteDefinition } from '../../types.js';

export const securitySanityCheck: SuiteDefinition = {
  id: 'security_sanity_check',
  slug: 'security_sanity_check',
  name: 'Security Sanity Check',
  description: 'Prompt injection, jailbreak attempts, PII exfiltration, and refusal guards.',
  category: 'security',
  recommendedAgentTypes: ['support', 'general', 'orchestrator'],
  estimatedDurationSec: 120,
  approximateCostUsd: 0.85,
  isRecommended: true,
  tests: [
    { id: 'prompt_injection_suite', runner: () => import('../../individual/security/prompt_injection_suite.test.js') },
    { id: 'prompt_injection', runner: () => import('../../individual/security/prompt_injection.test.js') },
    { id: 'jailbreak_attempts', runner: () => import('../../individual/security/jailbreak_attempts.test.js') },
    { id: 'pii_exfiltration', runner: () => import('../../individual/security/pii_exfiltration.test.js') },
    { id: 'credential_leakage', runner: () => import('../../individual/security/credential_leakage.test.js') },
    { id: 'refusal_guards', runner: () => import('../../individual/security/refusal_guards.test.js') },
  ],
};

