'use client';

import Link from 'next/link';
import { useEffect, useState, useTransition } from 'react';

import { Button } from '@/components/ui/button';
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

export default function PublicTestA2APage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [requesterId, setRequesterId] = useState('');
  const [responderId, setResponderId] = useState('');
  const [service, setService] = useState('Generate a summary of the top 3 AI trends in 2024');
  const [budget, setBudget] = useState(25);
  const [price, setPrice] = useState(20);
  const [status, setStatus] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [isPending, startTransition] = useTransition();
  const [needsAuth, setNeedsAuth] = useState(false);

  useEffect(() => {
    // Try to load agents (will fail if not authenticated, show login prompt)
    agentsApi
      .list({ showAll: 'true' })
      .then((data) => {
        setAgents(data);
        if (data.length >= 2) {
          // Check URL params for prefilled agents
          const urlParams = new URLSearchParams(window.location.search);
          const reqId = urlParams.get('requester');
          const respId = urlParams.get('responder');
          
          if (reqId && data.find(a => a.id === reqId)) {
            setRequesterId(reqId);
          } else {
            setRequesterId(data[0].id);
          }
          
          if (respId && data.find(a => a.id === respId)) {
            setResponderId(respId);
          } else {
            setResponderId(data[1].id);
          }
        }
      })
      .catch((error) => {
        console.error('Failed to load agents:', error);
        setNeedsAuth(true);
      });
  }, []);

  const addLog = (message: string) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const runFullTest = () => {
    if (!requesterId || !responderId || requesterId === responderId) {
      addLog('❌ Please select two different agents');
      return;
    }

    if (needsAuth) {
      addLog('❌ Please login to run tests. <a href="/login">Login here</a>');
      return;
    }

    setLogs([]);
    setStatus('Running...');

    startTransition(async () => {
      try {
        // Step 0: Ensure wallets are funded
        addLog('💰 Step 0: Checking and funding agent wallets...');
        
        try {
          const requesterWallet = (await walletsApi.getAgentWallet(requesterId)) as {
            id: string;
            balance: string | number;
          };
          const currentBalance = parseFloat(String(requesterWallet.balance || '0'));
          addLog(`   Requester wallet balance: $${currentBalance.toFixed(2)}`);
          
          if (currentBalance < budget + 5) {
            const fundAmount = budget + 20;
            addLog(`   Funding requester wallet with $${fundAmount}...`);
            await walletsApi.fundWallet(requesterWallet.id, fundAmount, 'Test funding for A2A negotiation');
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
            await walletsApi.fundWallet(responderWallet.id, 10, 'Test funding for A2A negotiation');
            addLog(`   ✅ Responder wallet funded to $10`);
          } else {
            addLog(`   ✅ Responder wallet has sufficient funds`);
          }
        } catch (walletError) {
          addLog(`   ⚠️  Wallet check/funding failed: ${walletError instanceof Error ? walletError.message : 'Unknown error'}`);
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
            const response = error.response as { json: () => Promise<unknown> };
            const body = await response.json().catch(() => ({}));
            addLog(`   Error details: ${JSON.stringify(body)}`);
          } catch {
            // Ignore JSON parse errors
          }
        }
        setStatus('❌ Test failed');
      }
    });
  };

  return (
    <div className="min-h-screen bg-black">
      <div className="mx-auto max-w-4xl space-y-8 px-4 py-12">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-white">🚀 Live A2A Transaction Demo</h1>
          <p className="text-lg text-slate-400">
            Watch two AI agents negotiate, create escrow, and complete a transaction — no login required
          </p>
          {needsAuth && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm text-amber-800">
                To run the full test, please <Link href="/login" className="font-semibold underline">login</Link> or{' '}
                <Link href="/register" className="font-semibold underline">create an account</Link>
              </p>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-white/10 bg-white/5 shadow-lg p-6 space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-white">Requester Agent</span>
              <select
                value={requesterId}
                onChange={(e) => setRequesterId(e.target.value)}
                disabled={agents.length === 0}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none disabled:bg-white/5"
              >
                {agents.length === 0 ? (
                  <option>Loading agents...</option>
                ) : (
                  agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))
                )}
              </select>
            </label>

            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-white">Responder Agent</span>
              <select
                value={responderId}
                onChange={(e) => setResponderId(e.target.value)}
                disabled={agents.length === 0}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none disabled:bg-white/5"
              >
                {agents.length === 0 ? (
                  <option>Loading agents...</option>
                ) : (
                  agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))
                )}
              </select>
            </label>
          </div>

          <label className="flex flex-col gap-2">
            <span className="text-sm font-semibold text-white">Service Request</span>
            <textarea
              value={service}
              onChange={(e) => setService(e.target.value)}
              rows={3}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
            />
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-white">Budget ($)</span>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-white">Acceptance Price ($)</span>
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
              />
            </label>
          </div>

          <Button
            type="button"
            onClick={runFullTest}
            disabled={isPending || agents.length < 2 || needsAuth}
            className="w-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc] text-black hover:shadow-[0_20px_45px_-15px_rgba(0,0,0,0.75)] text-lg py-6"
            size="lg"
          >
            {isPending ? 'Running Test...' : '🚀 Run Full A2A Test'}
          </Button>

          {status && (
            <div
              className={`rounded-lg border p-4 ${
                status.startsWith('✅')
                  ? 'border-emerald-500/40 bg-emerald-50 text-emerald-800'
                  : 'border-red-500/40 bg-red-50 text-red-800'
              }`}
            >
              {status}
            </div>
          )}

          {logs.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-white">Test Logs:</h3>
              <div className="max-h-96 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-4 font-mono text-xs text-gray-800">
                {logs.map((log, i) => (
                  <div key={i} className="mb-1">
                    {log}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="text-center">
          <Link href="/" className="text-sm text-gray-600 hover:text-gray-900 underline">
            ← Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}

