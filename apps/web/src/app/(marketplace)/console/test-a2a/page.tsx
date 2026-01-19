'use client';

import { A2ARunner, type A2AAgent } from '@/components/demo/a2a-runner';
import { agentsApi, ap2Api, walletsApi } from '@/lib/api';
import type { Agent, Ap2NegotiationPayload } from '@/lib/api';

interface NegotiationResponse {
  id: string;
  status: string;
  requesterAgent?: { id: string; name: string };
  responderAgent?: { id: string; name: string };
  escrow?: { id: string; amount: string; status: string };
  serviceAgreement?: { id: string; status: string };
}

export default function TestA2APage() {
  const fetchTestAgents = async (): Promise<A2AAgent[]> => {
    const data = (await agentsApi.list({ showAll: 'true' })) as Agent[];
    return data.map((agent) => ({
      id: agent.id,
      name: agent.name,
      description: agent.description,
    }));
  };

  const getInitialSelection = (agents: A2AAgent[]) => {
    if (typeof window === 'undefined' || agents.length === 0) {
      return null;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const reqId = urlParams.get('requester');
    const respId = urlParams.get('responder');

    let requesterId = agents[0]?.id ?? '';
    let responderId = agents[1]?.id ?? agents[0]?.id ?? '';

    if (reqId && agents.find((a) => a.id === reqId)) {
      requesterId = reqId;
    }
    if (respId && agents.find((a) => a.id === respId)) {
      responderId = respId;
    }

    return { requesterId, responderId };
  };

  const runTest = async (params: {
    agents: A2AAgent[];
    requesterId: string;
    responderId: string;
    service: string;
    budget: number;
    price: number;
    addLog: (message: string) => void;
    setStatus: (status: string) => void;
    setRunId?: (runId: string | null) => void;
    setLogs: (logs: string[]) => void;
  }) => {
    const {
      agents,
      requesterId,
      responderId,
      service,
      budget,
      price,
      addLog,
      setStatus,
    } = params;

    try {
      // Step 0: Ensure wallets are funded
      addLog('🚦 Step 0: Checking and funding agent wallets...');

      try {
        const requesterWallet = (await walletsApi.getAgentWallet(requesterId)) as {
          id: string;
          balance: string | number;
        };
        const currentBalance = parseFloat(String(requesterWallet.balance || '0'));
        addLog(`   Requester wallet balance: $${currentBalance.toFixed(2)}`);

        if (currentBalance < budget + 5) {
          const fundAmount = budget + 20; // Add extra buffer
          addLog(`   Funding requester wallet with $${fundAmount}...`);
          await walletsApi.fundWallet(
            requesterWallet.id,
            fundAmount,
            'Test funding for A2A negotiation',
          );
          addLog(`   ✅ Requester wallet funded to $${fundAmount}`);
        } else {
          addLog(`   ✅ Requester wallet has sufficient funds`);
        }

        const responderWallet = (await walletsApi.getAgentWallet(responderId)) as {
          id: string;
          balance: string | number;
        };
        const responderBalance = parseFloat(String(responderWallet.balance || '0'));
        addLog(`   Responder wallet balance: $${responderBalance.toFixed(2)}`);

        if (responderBalance < 5) {
          addLog(`   Funding responder wallet with $10...`);
          await walletsApi.fundWallet(
            responderWallet.id,
            10,
            'Test funding for A2A negotiation',
          );
          addLog(`   ✅ Responder wallet funded to $10`);
        } else {
          addLog(`   ✅ Responder wallet has sufficient funds`);
        }
      } catch (walletError) {
        addLog(
          `   ⚠️  Wallet check/funding failed: ${
            walletError instanceof Error ? walletError.message : 'Unknown error'
          }`,
        );
        addLog(`   Continuing anyway - negotiation may fail if funds are insufficient`);
      }

      // Step 1: Initiate negotiation
      addLog('\n🤝 Step 1: Initiating negotiation...');
      addLog(`   Requester: ${agents.find((a) => a.id === requesterId)?.name || requesterId}`);
      addLog(`   Responder: ${agents.find((a) => a.id === responderId)?.name || responderId}`);
      addLog(`   Service: ${service}`);
      addLog(`   Budget: $${budget}`);

      const payload: Ap2NegotiationPayload = {
        requesterAgentId: requesterId,
        responderAgentId: responderId,
        requestedService: service,
        budget,
        requirements: {
          quality: 'high',
          deadline: '1 hour',
        },
        notes: 'Automated test negotiation',
      };

      const negotiation = (await ap2Api.requestService(payload)) as NegotiationResponse;

      addLog(`✅ Negotiation created: ${negotiation.id}`);
      addLog(`   Status: ${negotiation.status}`);

      // Step 2: Accept negotiation
      await new Promise((resolve) => setTimeout(resolve, 1000));
      addLog('\n✅ Step 2: Accepting negotiation...');
      addLog(`   Price: $${price}`);

      const accepted = (await ap2Api.respondToNegotiation({
        negotiationId: negotiation.id,
        responderAgentId: responderId,
        status: 'ACCEPTED',
        price,
        estimatedDelivery: '30 minutes',
        notes: 'Accepted - will complete the task',
      })) as NegotiationResponse;

      addLog(`✅ Negotiation accepted!`);
      if (accepted.escrow) {
        addLog(`   Escrow ID: ${accepted.escrow.id}`);
        addLog(`   Escrow Amount: $${accepted.escrow.amount}`);
        addLog(`   Escrow Status: ${accepted.escrow.status}`);
      }
      if (accepted.serviceAgreement) {
        addLog(`   Service Agreement: ${accepted.serviceAgreement.id}`);
      }

      // Step 3: Deliver service
      await new Promise((resolve) => setTimeout(resolve, 1000));
      addLog('\n📦 Step 3: Delivering service...');

      await ap2Api.deliverService({
        negotiationId: negotiation.id,
        responderAgentId: responderId,
        result: {
          outcome:
            'Top 3 AI Trends in 2024:\n1. Agent-to-Agent Commerce\n2. Autonomous Workflows\n3. Outcome-Based Payments',
          completed: true,
        },
        evidence: {
          completed: true,
          result: 'Task completed successfully',
        },
        notes: 'Service delivered successfully via automated test',
      });

      addLog(`✅ Service delivered!`);

      // Step 4: Check final status
      await new Promise((resolve) => setTimeout(resolve, 1000));
      addLog('\n📊 Step 4: Checking final status...');

      const final = (await ap2Api.getNegotiation(negotiation.id)) as NegotiationResponse;

      addLog(`\n📊 Final Status:`);
      addLog(`   Negotiation ID: ${final.id}`);
      addLog(`   Status: ${final.status}`);
      if (final.escrow) {
        addLog(`   Escrow: $${final.escrow.amount} (${final.escrow.status})`);
      }
      if (final.serviceAgreement) {
        addLog(`   Service Agreement: ${final.serviceAgreement.status}`);
      }

      setStatus('✅ Test completed successfully!');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      addLog(`\n❌ Test failed: ${errorMessage}`);
      if (error instanceof Error && 'response' in error) {
        try {
          const response = (error as { response?: { json: () => Promise<unknown> } }).response;
          if (response) {
            const body = await response.json().catch(() => ({}));
            addLog(`   Error details: ${JSON.stringify(body)}`);
          }
        } catch {
          // Ignore JSON parse errors
        }
      }
      setStatus('❌ Test failed');
    }
  };

  return (
    <div className="space-y-6">
      <header className="glass-card p-8">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">Testing</p>
        <h1 className="mt-2 text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Agent-to-Agent Negotiation Test</h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--text-muted)]">
          Automatically test the full A2A flow: negotiation → acceptance → escrow → service
          delivery
        </p>
      </header>

      <div className="glass-card space-y-6 p-6">
        <A2ARunner
          mode="test"
          fetchAgents={fetchTestAgents}
          getInitialSelection={getInitialSelection}
          onRun={runTest}
        />
      </div>
    </div>
  );
}

