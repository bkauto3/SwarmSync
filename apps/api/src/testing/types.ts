/**
 * Core types for the Agent Testing & Quality platform
 */

export interface SuiteDefinition {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: 'smoke' | 'reliability' | 'reasoning' | 'security' | 'domain';
  recommendedAgentTypes: string[];
  estimatedDurationSec: number;
  approximateCostUsd: number;
  isRecommended: boolean;
  tests: TestDefinition[];
}

export interface TestDefinition {
  id: string;
  runner: () => Promise<{ default: TestRunner } | TestRunner>;
}

export interface TestRunner {
  run(params: TestRunParams): Promise<TestResult>;
}

export interface TestRunParams {
  agentId: string;
  suiteId: string;
  testId: string;
  userId: string;
}

export interface TestResult {
  passed: boolean;
  score: number; // 0-100
  latencyMs?: number;
  costUsd?: number;
  error?: string;
  details?: Record<string, unknown>;
  logs?: string[];
}

export interface TestRunProgress {
  runId: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  currentTest?: string;
  completedTests: number;
  totalTests: number;
  score?: number;
  error?: string;
}

