/**
 * Test script for agent-to-agent negotiation and payment flow
 * This simulates an agent hiring another agent to complete a task
 */

import ky from 'ky';

const API_URL = process.env.API_URL || 'http://localhost:4000';
const API_BASE = `${API_URL}/api/v1`;

// You'll need to set this from your browser's cookies after logging in
const AUTH_TOKEN = process.env.AUTH_TOKEN || '';

const api = ky.create({
  prefixUrl: API_BASE,
  headers: {
    ...(AUTH_TOKEN ? { Authorization: `Bearer ${AUTH_TOKEN}` } : {}),
    'Content-Type': 'application/json',
  },
});

interface Agent {
  id: string;
  name: string;
  slug: string;
  status: string;
}

interface NegotiationResponse {
  id: string;
  status: string;
  requesterAgent: { id: string; name: string };
  responderAgent: { id: string; name: string };
  escrow?: { id: string; amount: string; status: string };
  serviceAgreement?: { id: string; status: string };
}

async function listAgents(): Promise<Agent[]> {
  console.log('📋 Fetching available agents...');
  const response = await api.get('agents', { searchParams: { showAll: 'true' } }).json<Agent[]>();
  console.log(`Found ${response.length} agents`);
  return response;
}

async function getAgentWallet(agentId: string) {
  console.log(`💰 Checking wallet for agent ${agentId}...`);
  try {
    const wallet = await api.get(`wallets/agent/${agentId}`).json();
    console.log(`Wallet balance: $${wallet.balance}`);
    return wallet;
  } catch (error) {
    console.error('Failed to get wallet:', error);
    return null;
  }
}

async function fundWallet(walletId: string, amount: number) {
  console.log(`💵 Funding wallet ${walletId} with $${amount}...`);
  try {
    const result = await api
      .post(`wallets/${walletId}/fund`, {
        json: { amount, reference: 'Test funding for A2A negotiation' },
      })
      .json();
    console.log('✅ Wallet funded successfully');
    return result;
  } catch (error) {
    console.error('Failed to fund wallet:', error);
    throw error;
  }
}

async function initiateNegotiation(
  requesterAgentId: string,
  responderAgentId: string,
  service: string,
  budget: number,
) {
  console.log(`\n🤝 Initiating negotiation...`);
  console.log(`   Requester: ${requesterAgentId}`);
  console.log(`   Responder: ${responderAgentId}`);
  console.log(`   Service: ${service}`);
  console.log(`   Budget: $${budget}`);

  try {
    const negotiation = await api
      .post('ap2/negotiate', {
        json: {
          requesterAgentId,
          responderAgentId,
          requestedService: service,
          budget,
          requirements: {
            quality: 'high',
            deadline: '1 hour',
          },
          notes: 'Automated test negotiation - please accept and complete the task',
        },
      })
      .json<NegotiationResponse>();

    console.log(`✅ Negotiation created: ${negotiation.id}`);
    console.log(`   Status: ${negotiation.status}`);
    return negotiation;
  } catch (error: any) {
    console.error('❌ Failed to create negotiation:', error.message);
    if (error.response) {
      const body = await error.response.json().catch(() => ({}));
      console.error('   Error details:', body);
    }
    throw error;
  }
}

async function checkNegotiationStatus(negotiationId: string) {
  try {
    const negotiation = await api.get(`ap2/negotiations/${negotiationId}`).json<NegotiationResponse>();
    return negotiation;
  } catch (error) {
    console.error('Failed to check negotiation status:', error);
    return null;
  }
}

async function acceptNegotiation(negotiationId: string, responderAgentId: string, price: number) {
  console.log(`\n✅ Accepting negotiation ${negotiationId} with price $${price}...`);
  try {
    const result = await api
      .post('ap2/respond', {
        json: {
          negotiationId,
          responderAgentId,
          status: 'ACCEPTED',
          price,
          estimatedDelivery: '30 minutes',
          notes: 'Accepted - will complete the task',
        },
      })
      .json<NegotiationResponse>();
    console.log('✅ Negotiation accepted! Escrow created.');
    if (result.escrow) {
      console.log(`   Escrow ID: ${result.escrow.id}`);
      console.log(`   Escrow Amount: $${result.escrow.amount}`);
    }
    return result;
  } catch (error: any) {
    console.error('❌ Failed to accept negotiation:', error.message);
    if (error.response) {
      const body = await error.response.json().catch(() => ({}));
      console.error('   Error details:', body);
    }
    throw error;
  }
}

async function deliverService(negotiationId: string, outcome: string) {
  console.log(`\n📦 Delivering service for negotiation ${negotiationId}...`);
  try {
    const result = await api
      .post('ap2/deliver', {
        json: {
          negotiationId,
          outcome,
          evidence: { completed: true, result: outcome },
        },
      })
      .json();
    console.log('✅ Service delivered');
    return result;
  } catch (error: any) {
    console.error('❌ Failed to deliver service:', error.message);
    throw error;
  }
}

async function main() {
  console.log('🚀 Starting Agent-to-Agent Negotiation Test\n');
  console.log(`API URL: ${API_BASE}`);
  console.log(`Auth: ${AUTH_TOKEN ? '✅ Token provided' : '❌ No token - some endpoints may fail'}\n`);

  try {
    // Step 1: List available agents
    const agents = await listAgents();
    if (agents.length < 2) {
      console.error('❌ Need at least 2 agents to test negotiation');
      console.log('Available agents:');
      agents.forEach((a) => console.log(`  - ${a.name} (${a.id})`));
      return;
    }

    // Step 2: Select two agents
    const requester = agents[0];
    const responder = agents[1];

    console.log(`\n📌 Selected agents:`);
    console.log(`   Requester: ${requester.name} (${requester.id})`);
    console.log(`   Responder: ${responder.name} (${responder.id})`);

    // Step 3: Check and fund wallets
    const requesterWallet = await getAgentWallet(requester.id);
    if (requesterWallet && parseFloat(requesterWallet.balance) < 10) {
      console.log('\n💰 Requester wallet needs funding...');
      await fundWallet(requesterWallet.id, 50);
    }

    const responderWallet = await getAgentWallet(responder.id);
    if (responderWallet && parseFloat(responderWallet.balance) < 1) {
      console.log('\n💰 Responder wallet needs funding...');
      await fundWallet(responderWallet.id, 10);
    }

    // Step 4: Initiate negotiation
    const negotiation = await initiateNegotiation(
      requester.id,
      responder.id,
      'Generate a summary of the top 3 AI trends in 2024',
      25.0,
    );

    // Step 5: Accept the negotiation (simulating the responder agent accepting)
    console.log('\n⏳ Waiting 2 seconds before accepting...');
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    const acceptedNegotiation = await acceptNegotiation(
      negotiation.id,
      responder.id,
      20.0, // Accept at $20 (less than the $25 budget)
    );

    // Step 6: Verify escrow was created
    if (acceptedNegotiation.escrow) {
      console.log('\n💰 Escrow Details:');
      console.log(`   ID: ${acceptedNegotiation.escrow.id}`);
      console.log(`   Amount: $${acceptedNegotiation.escrow.amount}`);
      console.log(`   Status: ${acceptedNegotiation.escrow.status}`);
    }

    if (acceptedNegotiation.serviceAgreement) {
      console.log('\n📋 Service Agreement Created:');
      console.log(`   ID: ${acceptedNegotiation.serviceAgreement.id}`);
      console.log(`   Status: ${acceptedNegotiation.serviceAgreement.status}`);
    }

    // Step 7: Deliver the service (simulating the responder agent completing the task)
    console.log('\n⏳ Waiting 2 seconds before delivering service...');
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    await deliverService(
      negotiation.id,
      'Top 3 AI Trends in 2024:\n1. Agent-to-Agent Commerce\n2. Autonomous Workflows\n3. Outcome-Based Payments',
    );

    // Step 8: Check final status
    console.log('\n⏳ Checking final status...');
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const final = await checkNegotiationStatus(negotiation.id);
    console.log('\n📊 Final Negotiation Status:');
    console.log(JSON.stringify(final, null, 2));

    console.log('\n✅ Test completed!');
  } catch (error: any) {
    console.error('\n❌ Test failed:', error.message);
    if (error.stack) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

main();

