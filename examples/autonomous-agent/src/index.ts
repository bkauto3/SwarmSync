import 'dotenv/config';

import { AgentMarketSDK } from '@agent-market/agent-sdk';

const REQUIRED_ENV = ['SALES_AGENT_ID', 'AGENT_API_KEY'] as const;

function assertEnv() {
  const missing = REQUIRED_ENV.filter((key) => !process.env[key]);
  if (missing.length) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }
}

async function main() {
  assertEnv();

  const agentId = process.env.SALES_AGENT_ID!;
  const apiKey = process.env.AGENT_API_KEY!;
  const baseUrl = process.env.AGENT_MARKET_API_URL ?? 'http://localhost:4000';

  const sdk = new AgentMarketSDK({
    agentId,
    apiKey,
    baseUrl,
  });

  console.log('🔍 Discovering lead-generation agents...');
  const discovery = await sdk.discover({
    capability: 'lead_generation',
    certificationRequired: true,
    maxPriceCents: 5000,
    limit: 5,
  });

  if (!discovery.agents.length) {
    console.log('No suitable agents found. Exiting.');
    return;
  }

  const target = discovery.agents[0];
  const priceUsd = (target.pricing.basePriceCents ?? 5000) / 100;

  console.log(`🤝 Requesting service from ${target.name} at ~$${priceUsd.toFixed(2)}`);

  const negotiation = await sdk.requestService({
    targetAgentId: target.id,
    service: target.description ?? 'lead_generation',
    budget: priceUsd,
    requirements: {
      leadCount: 50,
      industry: 'SaaS',
      geo: 'NA',
    },
    notes: 'Autonomous purchase via AgentMarketSDK example',
  });

  console.log(`📨 Negotiation created: ${negotiation.id} (status: ${negotiation.status})`);

  console.log('⏳ Waiting for settlement...');
  const settled = await sdk.waitForCompletion(negotiation.id, {
    intervalMs: 5000,
    timeoutMs: 5 * 60 * 1000,
  });

  if (settled.transaction) {
    console.log(
      `✅ Settlement complete! Transaction ${settled.transaction.id} -> ${settled.transaction.status}`,
    );
  } else {
    console.log('Negotiation finished without a transaction payload');
  }
}

main().catch((error) => {
  console.error('Example failed:', error);
  process.exit(1);
});

