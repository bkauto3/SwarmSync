#!/usr/bin/env tsx
import fs from 'node:fs';
import path from 'node:path';

import { Agent, AgentExecutionResponse, createAgentMarketClient } from '@agent-market/sdk';

interface ScenarioDefinition {
  agentId?: string;
  agentSlug?: string;
  agentTags?: string[];
  agentNameIncludes?: string;
  scenarioName: string;
  vertical?: string;
  input?: Record<string, unknown>;
  expectedOutputIncludes?: string[];
  minOutputLength?: number;
  budget?: number;
  notes?: string;
}

const SCENARIO_PATH =
  process.env.EVALUATION_SCENARIOS_FILE ?? path.join('configs', 'evaluations');
const API_URL = process.env.API_URL ?? 'http://localhost:4000';
const API_TOKEN = process.env.API_TOKEN;
const INITIATOR_ID = process.env.EVALUATION_INITIATOR_ID;

if (!INITIATOR_ID) {
  console.error('EVALUATION_INITIATOR_ID environment variable is required.');
  process.exit(1);
}

async function main() {
  const scenarios = loadScenarios();
  if (scenarios.length === 0) {
    console.warn('No evaluation scenarios found.');
    return;
  }

  const client = createAgentMarketClient({
    baseUrl: API_URL,
    apiKey: API_TOKEN,
  });

  const agents = await client.listAgents();

  for (const scenario of scenarios) {
    const agent = resolveAgent(agents, scenario);
    if (!agent) {
      console.warn(`Skipping scenario "${scenario.scenarioName}" because agent was not found.`);
      continue;
    }

    const execution = await executeScenario(client, agent, scenario);
    const passed = evaluateOutput(execution, scenario);
    const latencyMs = execution.execution.completedAt
      ? new Date(execution.execution.completedAt).getTime() -
        new Date(execution.execution.createdAt).getTime()
      : 0;

    await client.runEvaluation({
      agentId: agent.id,
      scenarioName: scenario.scenarioName,
      vertical: scenario.vertical,
      input: scenario.input,
      expected: scenario.expectedOutputIncludes
        ? { includes: scenario.expectedOutputIncludes }
        : undefined,
      logs: {
        executionId: execution.execution.id,
        notes: scenario.notes,
      },
      latencyMs,
      cost: Number(execution.paymentTransaction.amount),
      passed,
    });

    console.log(
      `Recorded evaluation for ${agent.name} • ${scenario.scenarioName} • status:${passed ? 'PASSED' : 'FAILED'}`,
    );
  }
}

function loadScenarios(): ScenarioDefinition[] {
  const targetPath = path.resolve(SCENARIO_PATH);
  if (!fs.existsSync(targetPath)) {
    console.warn(`Scenario path not found: ${targetPath}`);
    return [];
  }

  const stat = fs.statSync(targetPath);
  if (stat.isDirectory()) {
    const files = fs.readdirSync(targetPath).filter((file) => file.endsWith('.json'));
    const collected: ScenarioDefinition[] = [];
    for (const file of files) {
      collected.push(...loadScenarioFile(path.join(targetPath, file)));
    }
    return collected;
  }

  return loadScenarioFile(targetPath);
}

function loadScenarioFile(filePath: string): ScenarioDefinition[] {
  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(raw) as ScenarioDefinition[] | ScenarioDefinition;
    return Array.isArray(data) ? data : [data];
  } catch (error) {
    console.warn(`Failed to parse scenarios from ${filePath}:`, error);
    return [];
  }
}

function resolveAgent(agents: Agent[], scenario: ScenarioDefinition) {
  if (scenario.agentId) {
    return agents.find((agent) => agent.id === scenario.agentId);
  }

  if (scenario.agentSlug) {
    return agents.find((agent) => agent.slug === scenario.agentSlug);
  }

  if (scenario.agentNameIncludes) {
    const query = scenario.agentNameIncludes.toLowerCase();
    const byName = agents.find((agent) => agent.name.toLowerCase().includes(query));
    if (byName) {
      return byName;
    }
  }

  if (scenario.agentTags?.length) {
    const normalizedTags = scenario.agentTags.map((tag) => tag.toLowerCase());
    const match = agents.find((agent) => {
      const agentTags = [...(agent.tags ?? []), ...(agent.categories ?? [])].map((tag) =>
        tag.toLowerCase(),
      );
      return normalizedTags.some((tag) => agentTags.includes(tag));
    });
    if (match) {
      return match;
    }
  }

  if (agents.length > 0) {
    console.warn(
      `Falling back to first available agent (${agents[0].name}) for scenario "${scenario.scenarioName}".`,
    );
    return agents[0];
  }

  return undefined;
}

async function executeScenario(
  client: ReturnType<typeof createAgentMarketClient>,
  agent: Agent,
  scenario: ScenarioDefinition,
): Promise<AgentExecutionResponse> {
  return client.executeAgent(agent.id, INITIATOR_ID, scenario.input ?? {}, {
    budget: scenario.budget ?? 5,
    jobReference: `eval-${Date.now()}`,
  });
}

function evaluateOutput(execution: AgentExecutionResponse, scenario: ScenarioDefinition) {
  if (execution.execution.status !== 'SUCCEEDED') {
    return false;
  }

  const outputContent = JSON.stringify(execution.execution.output ?? {}).toLowerCase();
  if (scenario.expectedOutputIncludes?.length) {
    const includesAll = scenario.expectedOutputIncludes.every((fragment) =>
      outputContent.includes(fragment.toLowerCase()),
    );
    if (!includesAll) {
      return false;
    }
  }

  if (scenario.minOutputLength) {
    const outputLength = outputContent.length;
    if (outputLength < scenario.minOutputLength) {
      return false;
    }
  }

  return true;
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
