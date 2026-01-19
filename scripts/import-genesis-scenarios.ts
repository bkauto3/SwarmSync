#!/usr/bin/env tsx
import fs from 'node:fs';
import path from 'node:path';

import * as YAML from 'yaml';

interface CliOptions {
  inputs: string[];
  output: string;
  vertical?: string;
  limit?: number;
  agentTags?: string[];
  agentNameIncludes?: string;
}

interface GenesisScenario {
  id?: string;
  name?: string;
  priority?: string;
  category?: string;
  tags?: string[];
  input?: Record<string, unknown>;
  expected_output?: {
    contains?: string[];
    min_length?: number;
  };
  performance?: {
    max_latency_ms?: number;
    max_tokens?: number;
  };
  judge?: {
    model?: string;
    criteria?: string[];
  };
  cost_estimate?: number;
  description?: string;
}

const DEFAULT_OUTPUT = path.join('configs', 'evaluations', 'genesis-import.json');

function parseArgs(): CliOptions {
  const args = process.argv.slice(2);
  const options: CliOptions = {
    inputs: [],
    output: DEFAULT_OUTPUT,
  };

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    switch (arg) {
      case '--input':
      case '-i': {
        const nextValue = args[++i];
        if (nextValue) {
          options.inputs.push(nextValue);
        }
        break;
      }
      case '--output':
      case '-o':
        options.output = args[++i] ?? DEFAULT_OUTPUT;
        break;
      case '--vertical':
      case '-v':
        options.vertical = args[++i];
        break;
      case '--limit':
      case '-l':
        options.limit = Number.parseInt(args[++i] ?? '', 10);
        break;
      case '--agentTags':
        options.agentTags = (args[++i] ?? '')
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean);
        break;
      case '--agentNameIncludes':
        options.agentNameIncludes = args[++i];
        break;
      default:
        break;
    }
  }

  if (options.inputs.length === 0) {
    throw new Error('Missing required --input path to at least one genesis YAML file.');
  }

  return options;
}

interface ScenarioContainerMeta {
  priority?: string;
  vertical?: string;
  agent?: string;
  name?: string;
}

function resolveScenarioContainer(parsed: Record<string, unknown>): {
  container?: Record<string, unknown>;
  meta?: ScenarioContainerMeta;
} {
  if (Array.isArray((parsed as { scenarios?: unknown[] }).scenarios)) {
    return {
      container: parsed,
      meta: {
        priority: (parsed as { priority?: string }).priority,
        vertical: (parsed as { name?: string }).name,
        agent: (parsed as { agent?: string }).agent,
      },
    };
  }

  for (const value of Object.values(parsed)) {
    if (
      value &&
      typeof value === 'object' &&
      Array.isArray((value as { scenarios?: unknown[] }).scenarios)
    ) {
      return {
        container: value as Record<string, unknown>,
        meta: {
          priority: (value as { priority?: string }).priority,
          vertical: (value as { name?: string }).name,
          agent: (value as { agent?: string }).agent,
        },
      };
    }
  }

  return { container: undefined, meta: undefined };
}

function loadGenesisScenarios(filePath: string, limit?: number) {
  const absolutePath = path.resolve(filePath);
  if (!fs.existsSync(absolutePath)) {
    throw new Error(`Scenario file not found: ${absolutePath}`);
  }

  const raw = fs.readFileSync(absolutePath, 'utf-8');
  const parsed = YAML.parse(raw) as Record<string, unknown>;
  const { container, meta } = resolveScenarioContainer(parsed);

  if (!container) {
    throw new Error(`No scenarios found in ${absolutePath}`);
  }

  const scenarios: GenesisScenario[] = Array.isArray(
    (container as { scenarios?: GenesisScenario[] }).scenarios,
  )
    ? ((container as { scenarios?: GenesisScenario[] }).scenarios ?? [])
    : [];

  if (!Array.isArray(scenarios) || scenarios.length === 0) {
    throw new Error(`No scenarios found in ${absolutePath}`);
  }

  const limited =
    typeof limit === 'number' && Number.isFinite(limit) ? scenarios.slice(0, limit) : scenarios;

  return {
    meta: {
      priority: meta?.priority,
      vertical: meta?.vertical ?? meta?.agent,
      agent: meta?.agent,
    },
    scenarios: limited,
  };
}

function transformScenario(
  scenario: GenesisScenario,
  options: CliOptions,
  defaults: { priority?: string; vertical?: string; agent?: string },
) {
  const resolvedVertical = options.vertical ?? defaults.vertical ?? defaults.agent ?? 'general';

  return {
    sourceId: scenario.id,
    scenarioName: scenario.name,
    priority: scenario.priority ?? defaults.priority ?? null,
    vertical: resolvedVertical,
    agentTags: scenario.tags?.length ? scenario.tags : options.agentTags,
    agentNameIncludes: options.agentNameIncludes,
    input: scenario.input ?? {},
    expectedOutputIncludes: scenario.expected_output?.contains ?? [],
    minOutputLength: scenario.expected_output?.min_length,
    tolerances: {
      maxLatencyMs: scenario.performance?.max_latency_ms,
      maxTokens: scenario.performance?.max_tokens,
    },
    successCriteria: scenario.judge?.criteria ?? [],
    judgeModel: scenario.judge?.model,
    costEstimate: scenario.cost_estimate,
    notes: scenario.description ?? scenario.category,
    category: scenario.category,
  };
}

function main() {
  const options = parseArgs();
  const outputScenarios = options.inputs.flatMap((inputPath) => {
    const { scenarios, meta } = loadGenesisScenarios(inputPath, options.limit);
    const defaults = {
      priority: meta.priority,
      vertical: meta.vertical,
      agent: meta.agent,
    };
    return scenarios.map((scenario) => transformScenario(scenario, options, defaults));
  });

  const outputPath = path.resolve(options.output);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(outputScenarios, null, 2)}\n`);

  // eslint-disable-next-line no-console
  console.log(`Wrote ${outputScenarios.length} scenarios to ${outputPath}`);
}

main();
