/**
 * Test Suite Registry
 * Auto-discovers all test suites and upserts them into the database on app startup
 */

import { PrismaClient } from '@prisma/client';

import { SuiteDefinition } from '../types.js';
// Import all suite definitions
import { researchAgentBaseline } from './domain/research_agent_baseline.js';
import { supportCopilotBaseline } from './domain/support_copilot_baseline.js';
import { reasoningBenchmark } from './reasoning/reasoning_benchmark.js';
import { latencyAndThroughput } from './reliability/latency_and_throughput.js';
import { securitySanityCheck } from './security/security_sanity_check.js';
import { swarmSmokeTest } from './smoke/swarm_smoke_test.js';

// Registry of all suites
export const ALL_SUITES: SuiteDefinition[] = [
  swarmSmokeTest,
  latencyAndThroughput,
  reasoningBenchmark,
  securitySanityCheck,
  supportCopilotBaseline,
  researchAgentBaseline,
];

/**
 * Upsert all test suites into the database
 * Called on app startup to ensure all suites are registered
 * Gracefully handles missing table (migration not run yet)
 */
export async function upsertTestSuites(prisma: PrismaClient): Promise<void> {
  try {
    // Check if TestSuite table exists by trying a simple query
    await prisma.$queryRaw`SELECT 1 FROM "TestSuite" LIMIT 1`;
  } catch (error: unknown) {
    // Table doesn't exist - log warning and skip
    if (error && typeof error === 'object' && 'code' in error && error.code === 'P2021') {
      // eslint-disable-next-line no-console
      console.warn('TestSuite table does not exist. Skipping test suite registration. Run migrations to enable testing features.');
      return;
    }
    // Re-throw if it's a different error
    throw error;
  }

  // Table exists, proceed with upserts
  for (const suite of ALL_SUITES) {
    try {
      await prisma.testSuite.upsert({
        where: { slug: suite.slug },
        update: {
          name: suite.name,
          description: suite.description,
          category: suite.category,
          recommendedAgentTypes: suite.recommendedAgentTypes,
          estimatedDurationSec: suite.estimatedDurationSec,
          approximateCostUsd: suite.approximateCostUsd,
          isRecommended: suite.isRecommended,
        },
        create: {
          id: suite.id,
          slug: suite.slug,
          name: suite.name,
          description: suite.description,
          category: suite.category,
          recommendedAgentTypes: suite.recommendedAgentTypes,
          estimatedDurationSec: suite.estimatedDurationSec,
          approximateCostUsd: suite.approximateCostUsd,
          isRecommended: suite.isRecommended,
        },
      });
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(`Failed to upsert test suite ${suite.slug}:`, error);
      // Continue with other suites even if one fails
    }
  }
}

/**
 * Get a suite definition by slug
 */
export function getSuiteBySlug(slug: string): SuiteDefinition | undefined {
  return ALL_SUITES.find((s) => s.slug === slug);
}

/**
 * Get all suites by category
 */
export function getSuitesByCategory(category: SuiteDefinition['category']): SuiteDefinition[] {
  return ALL_SUITES.filter((s) => s.category === category);
}

/**
 * Get recommended suites
 */
export function getRecommendedSuites(): SuiteDefinition[] {
  return ALL_SUITES.filter((s) => s.isRecommended);
}

