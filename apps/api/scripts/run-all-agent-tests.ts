/**
 * Script to run all test suites on all agents and generate badges
 * 
 * Usage: tsx scripts/run-all-agent-tests.ts
 * 
 * This script:
 * 1. Fetches all agents
 * 2. Fetches all test suites
 * 3. Runs each suite on each agent
 * 4. Generates badges based on results:
 *    - Security Passed / Failed
 *    - Latency A / B / C (based on response time)
 *    - Reasoning A / B / C (based on accuracy)
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

interface TestResult {
  agentId: string;
  suiteId: string;
  category: string;
  passed: boolean;
  latencyMs?: number;
  accuracy?: number;
}

async function getAllAgents() {
  return prisma.agent.findMany({
    where: {
      status: 'APPROVED',
    },
    select: {
      id: true,
      name: true,
    },
  });
}

async function getAllTestSuites() {
  // Test suites are stored in the database
  // For now, we'll use a hardcoded list based on categories
  return [
    { id: 'security', category: 'security', name: 'Security Tests' },
    { id: 'latency', category: 'smoke', name: 'Latency Tests' }, // Using smoke category for latency
    { id: 'reasoning', category: 'reasoning', name: 'Reasoning Tests' },
  ];
}

async function runTestSuite(agentId: string, suiteId: string): Promise<TestResult | null> {
  try {
    // Start a test run
    const run = await prisma.testRun.create({
      data: {
        agentId,
        suiteId,
        status: 'RUNNING',
      },
    });

    // Wait for test to complete (in real implementation, this would poll or use webhooks)
    // For now, we'll simulate by waiting a bit
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // Get the latest test run results
    const completedRun = await prisma.testRun.findUnique({
      where: { id: run.id },
      include: {
        results: true,
      },
    });

    if (!completedRun || completedRun.status !== 'COMPLETED') {
      return null;
    }

    const results = completedRun.results || [];
    const passed = results.every((r: { passed: boolean }) => r.passed);
    const avgLatency = results.reduce((sum: number, r: { latencyMs?: number }) => sum + (r.latencyMs || 0), 0) / results.length;
    const accuracy = results.filter((r: { passed: boolean }) => r.passed).length / results.length;

    return {
      agentId,
      suiteId,
      category: suiteId,
      passed,
      latencyMs: avgLatency,
      accuracy: accuracy * 100,
    };
  } catch (error) {
    console.error(`Failed to run test ${suiteId} on agent ${agentId}:`, error);
    return null;
  }
}

function generateBadges(results: TestResult[]): string[] {
  const badges: string[] = [];

  const securityResult = results.find((r) => r.category === 'security');
  const latencyResult = results.find((r) => r.category === 'latency');
  const reasoningResult = results.find((r) => r.category === 'reasoning');

  // Security badge
  if (securityResult) {
    if (securityResult.passed) {
      badges.push('Security Passed');
    } else {
      badges.push('Security Failed');
    }
  }

  // Latency badge (A = <500ms, B = 500-1000ms, C = >1000ms)
  if (latencyResult && latencyResult.latencyMs !== undefined) {
    if (latencyResult.latencyMs < 500) {
      badges.push('Latency A');
    } else if (latencyResult.latencyMs < 1000) {
      badges.push('Latency B');
    } else {
      badges.push('Latency C');
    }
  }

  // Reasoning badge (A = >90%, B = 70-90%, C = <70%)
  if (reasoningResult && reasoningResult.accuracy !== undefined) {
    if (reasoningResult.accuracy >= 90) {
      badges.push('Reasoning A');
    } else if (reasoningResult.accuracy >= 70) {
      badges.push('Reasoning B');
    } else {
      badges.push('Reasoning C');
    }
  }

  return badges;
}

async function updateAgentBadges(agentId: string, badges: string[]) {
  await prisma.agent.update({
    where: { id: agentId },
    data: {
      badges,
    },
  });
}

async function main() {
  console.log('🚀 Starting comprehensive agent testing...\n');

  try {
    const agents = await getAllAgents();
    const suites = await getAllTestSuites();

    console.log(`Found ${agents.length} agents and ${suites.length} test suites\n`);

    for (const agent of agents) {
      console.log(`\n📋 Testing agent: ${agent.name} (${agent.id})`);
      const results: TestResult[] = [];

      for (const suite of suites) {
        console.log(`  Running ${suite.name}...`);
        const result = await runTestSuite(agent.id, suite.id);
        if (result) {
          results.push(result);
          console.log(`    ✅ ${suite.name}: ${result.passed ? 'PASSED' : 'FAILED'}${result.latencyMs ? ` (${result.latencyMs.toFixed(0)}ms)` : ''}${result.accuracy ? ` (${result.accuracy.toFixed(1)}% accuracy)` : ''}`);
        } else {
          console.log(`    ❌ ${suite.name}: Failed to run`);
        }
      }

      // Generate badges from results
      const badges = generateBadges(results);
      await updateAgentBadges(agent.id, badges);

      console.log(`  🏆 Badges: ${badges.join(', ')}`);
    }

    console.log('\n✅ All tests completed!');
  } catch (error) {
    console.error('❌ Error running tests:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

main();

