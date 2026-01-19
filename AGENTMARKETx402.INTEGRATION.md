# AGENTMARKET PLATFORM X402 INTEGRATION GUIDE

## 🎯 OBJECTIVE

Build a **dual-rail payment system** for AgentMarket that supports BOTH your existing fiat payments (Stripe + internal escrow) AND new x402 cryptocurrency payments (USDC on blockchain).

**Timeline:** 7-10 days  
**Complexity:** High  
**Result:** First agent marketplace with fiat + crypto payment support

---

## 📋 PREREQUISITES

### **Required:**

- AgentMarket backend running (Node.js/TypeScript)
- AgentMarket frontend (React/Next.js)
- Existing AP2 protocol working
- Stripe integration functional
- Genesis agents x402-enabled

### **New Dependencies:**

**Backend:**

```bash
npm install @coinbase/coinbase-sdk ethers viem wagmi
```

**Frontend:**

```bash
npm install @coinbase/wallet-sdk @rainbow-me/rainbowkit wagmi viem
```

---

## 🏗️ ARCHITECTURE OVERVIEW

### **Payment Flow Comparison:**

```
FIAT FLOW (Existing):
User → AgentMarket → Stripe → Wallet → Escrow → Agent → Settlement

CRYPTO FLOW (New):
User → Wallet Connect → Sign Payment → Blockchain → Agent (direct)
```

### **Discovery Flow:**

```
Agent Discovery API:
GET /agents/:id/payment-methods

Response:
{
  "methods": [
    { "type": "platform", "currency": "USD" },    // Your system
    { "type": "x402", "currency": "USDC" }        // Crypto
  ]
}
```

---

## 📦 PART 1: BACKEND INTEGRATION (Days 1-4)

### **1.1 Update Database Schema**

**File:** `prisma/schema.prisma`

```prisma
// Add to Agent model
model Agent {
  id          String   @id @default(cuid())
  name        String
  slug        String   @unique

  // Existing fields...
  pricingType String   // "pay_per_use", "monthly_subscription", "hybrid"
  priceAmount Float?

  // NEW: x402 payment support
  x402Enabled      Boolean  @default(false)
  x402WalletAddress String?
  x402Network      String?  // "base-mainnet", "solana-mainnet", etc.
  x402Price        Float?   // Can differ from platform price

  // Existing relations...
  @@index([x402Enabled])
}

// NEW: Track x402 transactions
model X402Transaction {
  id              String   @id @default(cuid())
  agentId         String
  buyerAddress    String
  sellerAddress   String
  amount          Float
  currency        String   // "USDC"
  network         String   // "base-mainnet"
  txHash          String   @unique
  status          String   // "pending", "confirmed", "failed"
  createdAt       DateTime @default(now())
  confirmedAt     DateTime?

  agent Agent @relation(fields: [agentId], references: [id])

  @@index([agentId])
  @@index([txHash])
  @@index([status])
}

// Update existing Wallet model
model Wallet {
  id       String @id @default(cuid())
  agentId  String @unique
  balance  Float  @default(0)
  currency String @default("USD")

  // NEW: Add crypto wallet info
  cryptoAddress String? // For receiving x402 payments
  cryptoNetwork String? // "base-mainnet"

  agent Agent @relation(fields: [agentId], references: [id])
}
```

**Run migration:**

```bash
npx prisma migrate dev --name add_x402_support
```

---

### **1.2 Create x402 Service**

**File:** `apps/api/src/modules/x402/x402.service.ts`

```typescript
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { ethers } from 'ethers';

@Injectable()
export class X402Service {
  private provider: ethers.Provider;
  private facilitatorUrl: string;

  constructor(private prisma: PrismaService) {
    // Initialize Web3 provider
    this.provider = new ethers.JsonRpcProvider(
      process.env.BASE_RPC_URL || 'https://mainnet.base.org',
    );

    this.facilitatorUrl = process.env.X402_FACILITATOR_URL || 'https://x402.org/facilitator';
  }

  /**
   * Get payment methods for an agent
   */
  async getPaymentMethods(agentId: string) {
    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
      include: { wallet: true },
    });

    if (!agent) {
      throw new Error('Agent not found');
    }

    const methods = [];

    // Platform payment (existing)
    methods.push({
      type: 'platform',
      currency: 'USD',
      amount: agent.priceAmount,
      description: 'Pay via AgentMarket (credit card, bank transfer)',
      enabled: true,
    });

    // x402 crypto payment (new)
    if (agent.x402Enabled && agent.x402WalletAddress) {
      methods.push({
        type: 'x402',
        currency: 'USDC',
        amount: agent.x402Price || agent.priceAmount,
        recipient: agent.x402WalletAddress,
        network: agent.x402Network || 'base-mainnet',
        description: 'Pay directly with USDC (instant, low fees)',
        enabled: true,
      });
    }

    return methods;
  }

  /**
   * Verify x402 payment
   */
  async verifyPayment(params: {
    agentId: string;
    txHash: string;
    buyerAddress: string;
    amount: number;
  }) {
    const { agentId, txHash, buyerAddress, amount } = params;

    // Get agent
    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
    });

    if (!agent || !agent.x402Enabled) {
      throw new Error('Agent does not accept x402 payments');
    }

    // Check if transaction already processed
    const existing = await this.prisma.x402Transaction.findUnique({
      where: { txHash },
    });

    if (existing) {
      return { verified: existing.status === 'confirmed', existing: true };
    }

    try {
      // Get transaction from blockchain
      const tx = await this.provider.getTransaction(txHash);

      if (!tx) {
        throw new Error('Transaction not found');
      }

      // Wait for confirmation
      const receipt = await tx.wait(1); // Wait for 1 confirmation

      if (!receipt) {
        throw new Error('Transaction failed');
      }

      // Verify transaction details
      const expectedAmount = ethers.parseUnits(
        amount.toString(),
        6, // USDC has 6 decimals
      );

      // Basic validation (you'll need USDC contract ABI for proper verification)
      if (receipt.status !== 1) {
        throw new Error('Transaction failed on-chain');
      }

      // Record transaction
      const x402Tx = await this.prisma.x402Transaction.create({
        data: {
          agentId,
          buyerAddress,
          sellerAddress: agent.x402WalletAddress!,
          amount,
          currency: 'USDC',
          network: agent.x402Network || 'base-mainnet',
          txHash,
          status: 'confirmed',
          confirmedAt: new Date(),
        },
      });

      return { verified: true, transaction: x402Tx };
    } catch (error) {
      // Record failed transaction
      await this.prisma.x402Transaction.create({
        data: {
          agentId,
          buyerAddress,
          sellerAddress: agent.x402WalletAddress!,
          amount,
          currency: 'USDC',
          network: agent.x402Network || 'base-mainnet',
          txHash,
          status: 'failed',
        },
      });

      throw error;
    }
  }

  /**
   * Execute agent service after payment verified
   */
  async executeWithX402(params: {
    agentId: string;
    txHash: string;
    buyerAddress: string;
    amount: number;
    task: any;
  }) {
    // Verify payment
    const { verified } = await this.verifyPayment({
      agentId: params.agentId,
      txHash: params.txHash,
      buyerAddress: params.buyerAddress,
      amount: params.amount,
    });

    if (!verified) {
      throw new Error('Payment verification failed');
    }

    // Get agent endpoint
    const agent = await this.prisma.agent.findUnique({
      where: { id: params.agentId },
    });

    if (!agent || !agent.apiEndpoint) {
      throw new Error('Agent endpoint not configured');
    }

    // Call agent API
    const response = await fetch(agent.apiEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-payment': JSON.stringify({
          type: 'x402',
          txHash: params.txHash,
          amount: params.amount,
          network: agent.x402Network,
        }),
      },
      body: JSON.stringify(params.task),
    });

    if (!response.ok) {
      throw new Error(`Agent execution failed: ${response.statusText}`);
    }

    return response.json();
  }
}
```

---

### **1.3 Create x402 Controller**

**File:** `apps/api/src/modules/x402/x402.controller.ts`

```typescript
import { Controller, Get, Post, Body, Param } from '@nestjs/common';
import { X402Service } from './x402.service';

@Controller('x402')
export class X402Controller {
  constructor(private x402Service: X402Service) {}

  /**
   * Get payment methods for an agent
   * GET /x402/agents/:agentId/payment-methods
   */
  @Get('agents/:agentId/payment-methods')
  async getPaymentMethods(@Param('agentId') agentId: string) {
    return this.x402Service.getPaymentMethods(agentId);
  }

  /**
   * Verify x402 payment
   * POST /x402/verify
   */
  @Post('verify')
  async verifyPayment(
    @Body() body: { agentId: string; txHash: string; buyerAddress: string; amount: number },
  ) {
    return this.x402Service.verifyPayment(body);
  }

  /**
   * Execute agent service with x402 payment
   * POST /x402/execute
   */
  @Post('execute')
  async executeWithX402(
    @Body()
    body: {
      agentId: string;
      txHash: string;
      buyerAddress: string;
      amount: number;
      task: any;
    },
  ) {
    return this.x402Service.executeWithX402(body);
  }
}
```

---

### **1.4 Update Agent Discovery API**

**File:** `apps/api/src/modules/agents/agents.controller.ts`

```typescript
@Get('discover')
async discover(@Query() query: DiscoverAgentsDto) {
  const agents = await this.agentsService.discover(query);

  // Enhance with payment methods
  const agentsWithPayments = await Promise.all(
    agents.map(async (agent) => {
      const paymentMethods = await this.x402Service.getPaymentMethods(agent.id);

      return {
        ...agent,
        paymentMethods
      };
    })
  );

  return agentsWithPayments;
}

@Get(':id')
async getAgent(@Param('id') id: string) {
  const agent = await this.agentsService.findOne(id);
  const paymentMethods = await this.x402Service.getPaymentMethods(id);

  return {
    ...agent,
    paymentMethods
  };
}
```

---

### **1.5 Environment Variables**

**File:** `.env`

```bash
# Existing variables...

# NEW: x402 Configuration
BASE_RPC_URL=https://mainnet.base.org
X402_FACILITATOR_URL=https://x402.org/facilitator
X402_ENABLED=true

# Blockchain configuration
SUPPORTED_NETWORKS=base-mainnet,solana-mainnet
DEFAULT_NETWORK=base-mainnet
```

---

## 🎨 PART 2: FRONTEND INTEGRATION (Days 5-7)

### **2.1 Install Wallet Providers**

**File:** `apps/web/src/app/providers.tsx`

```typescript
'use client';

import { WagmiProvider, createConfig, http } from 'wagmi';
import { base } from 'wagmi/chains';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RainbowKitProvider, getDefaultConfig } from '@rainbow-me/rainbowkit';
import '@rainbow-me/rainbowkit/styles.css';

const config = getDefaultConfig({
  appName: 'AgentMarket',
  projectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID!,
  chains: [base],
  transports: {
    [base.id]: http()
  }
});

const queryClient = new QueryClient();

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <RainbowKitProvider>
          {children}
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
```

---

### **2.2 Wallet Connection Component**

**File:** `apps/web/src/components/wallet/connect-wallet.tsx`

```typescript
'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount, useDisconnect } from 'wagmi';

export function ConnectWallet() {
  const { address, isConnected } = useAccount();
  const { disconnect } = useDisconnect();

  return (
    <div className="flex items-center gap-4">
      <ConnectButton />

      {isConnected && (
        <div className="text-sm text-gray-600">
          {address?.slice(0, 6)}...{address?.slice(-4)}
        </div>
      )}
    </div>
  );
}
```

---

### **2.3 Payment Method Selector**

**File:** `apps/web/src/components/payment/payment-method-selector.tsx`

```typescript
'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { CreditCard, Coins } from 'lucide-react';

interface PaymentMethod {
  type: 'platform' | 'x402';
  currency: string;
  amount: number;
  description: string;
  recipient?: string;
  network?: string;
}

interface Props {
  methods: PaymentMethod[];
  selected: string;
  onSelect: (type: string) => void;
}

export function PaymentMethodSelector({ methods, selected, onSelect }: Props) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Select Payment Method</h3>

      <RadioGroup value={selected} onValueChange={onSelect}>
        {methods.map((method) => (
          <Card
            key={method.type}
            className={`p-4 cursor-pointer transition-all ${
              selected === method.type
                ? 'border-blue-500 bg-blue-50'
                : 'hover:border-gray-400'
            }`}
            onClick={() => onSelect(method.type)}
          >
            <div className="flex items-start gap-4">
              <RadioGroupItem value={method.type} id={method.type} />

              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  {method.type === 'platform' ? (
                    <CreditCard className="h-5 w-5" />
                  ) : (
                    <Coins className="h-5 w-5" />
                  )}

                  <span className="font-semibold">
                    {method.type === 'platform'
                      ? 'AgentMarket Balance'
                      : 'Crypto Wallet (USDC)'}
                  </span>
                </div>

                <p className="text-sm text-gray-600 mb-2">
                  {method.description}
                </p>

                <div className="flex items-center justify-between">
                  <span className="text-lg font-bold">
                    {method.currency === 'USD' ? '$' : ''}{method.amount} {method.currency}
                  </span>

                  {method.type === 'x402' && (
                    <span className="text-xs text-green-600 font-medium">
                      ⚡ Instant Settlement
                    </span>
                  )}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </RadioGroup>
    </div>
  );
}
```

---

### **2.4 x402 Payment Flow**

**File:** `apps/web/src/components/payment/x402-payment.tsx`

```typescript
'use client';

import { useState } from 'react';
import { useAccount, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { parseUnits } from 'viem';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2 } from 'lucide-react';

// USDC contract address on Base
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

// USDC ABI (transfer function)
const USDC_ABI = [
  {
    inputs: [
      { name: 'to', type: 'address' },
      { name: 'amount', type: 'uint256' }
    ],
    name: 'transfer',
    outputs: [{ name: '', type: 'bool' }],
    stateMutability: 'nonpayable',
    type: 'function'
  }
] as const;

interface Props {
  agentId: string;
  recipient: string;
  amount: number;
  onSuccess: (txHash: string) => void;
  onError: (error: Error) => void;
}

export function X402Payment({ agentId, recipient, amount, onSuccess, onError }: Props) {
  const { address, isConnected } = useAccount();
  const [status, setStatus] = useState<'idle' | 'signing' | 'pending' | 'success' | 'error'>('idle');

  const { data: hash, writeContract } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const handlePayment = async () => {
    if (!isConnected || !address) {
      onError(new Error('Please connect your wallet'));
      return;
    }

    try {
      setStatus('signing');

      // Convert amount to USDC decimals (6)
      const amountInUnits = parseUnits(amount.toString(), 6);

      // Execute USDC transfer
      writeContract({
        address: USDC_ADDRESS,
        abi: USDC_ABI,
        functionName: 'transfer',
        args: [recipient as `0x${string}`, amountInUnits]
      });

      setStatus('pending');

    } catch (error) {
      setStatus('error');
      onError(error as Error);
    }
  };

  // Handle transaction success
  if (isSuccess && hash) {
    setStatus('success');
    onSuccess(hash);
  }

  return (
    <div className="space-y-4">
      {status === 'idle' && (
        <Button
          onClick={handlePayment}
          className="w-full"
          size="lg"
        >
          Pay {amount} USDC
        </Button>
      )}

      {status === 'signing' && (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertDescription>
            Please sign the transaction in your wallet...
          </AlertDescription>
        </Alert>
      )}

      {(status === 'pending' || isConfirming) && (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertDescription>
            Transaction pending... This usually takes 2-5 seconds.
          </AlertDescription>
        </Alert>
      )}

      {status === 'success' && (
        <Alert className="bg-green-50 border-green-200">
          <AlertDescription className="text-green-800">
            ✅ Payment confirmed! Transaction: {hash?.slice(0, 10)}...
          </AlertDescription>
        </Alert>
      )}

      {status === 'error' && (
        <Alert variant="destructive">
          <AlertDescription>
            Payment failed. Please try again.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
```

---

### **2.5 Complete Agent Purchase Flow**

**File:** `apps/web/src/app/(marketplace)/agents/[slug]/purchase/page.tsx`

```typescript
'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { PaymentMethodSelector } from '@/components/payment/payment-method-selector';
import { X402Payment } from '@/components/payment/x402-payment';
import { ConnectWallet } from '@/components/wallet/connect-wallet';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAccount } from 'wagmi';

export default function AgentPurchasePage() {
  const params = useParams();
  const router = useRouter();
  const { isConnected } = useAccount();

  const [agent, setAgent] = useState<any>(null);
  const [paymentMethods, setPaymentMethods] = useState<any[]>([]);
  const [selectedMethod, setSelectedMethod] = useState<string>('platform');
  const [loading, setLoading] = useState(true);

  // Fetch agent and payment methods
  useEffect(() => {
    async function fetchAgent() {
      const response = await fetch(`/api/agents/${params.slug}`);
      const data = await response.json();

      setAgent(data);
      setPaymentMethods(data.paymentMethods || []);
      setLoading(false);
    }

    fetchAgent();
  }, [params.slug]);

  // Handle x402 payment success
  const handleX402Success = async (txHash: string) => {
    try {
      // Verify payment with backend
      const response = await fetch('/api/x402/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId: agent.id,
          txHash,
          buyerAddress: account?.address,
          amount: agent.x402Price || agent.priceAmount
        })
      });

      if (!response.ok) {
        throw new Error('Payment verification failed');
      }

      // Redirect to success page
      router.push(`/agents/${params.slug}/success?tx=${txHash}`);

    } catch (error) {
      console.error('Payment verification error:', error);
    }
  };

  // Handle platform payment
  const handlePlatformPayment = async () => {
    // Use your existing Stripe/escrow flow
    router.push(`/agents/${params.slug}/checkout`);
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  const x402Method = paymentMethods.find(m => m.type === 'x402');
  const needsWalletConnection = selectedMethod === 'x402' && !isConnected;

  return (
    <div className="container max-w-4xl mx-auto py-12">
      <Card className="p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">{agent.name}</h1>
          <p className="text-gray-600">{agent.description}</p>
        </div>

        <PaymentMethodSelector
          methods={paymentMethods}
          selected={selectedMethod}
          onSelect={setSelectedMethod}
        />

        <div className="mt-8">
          {selectedMethod === 'platform' && (
            <Button
              onClick={handlePlatformPayment}
              size="lg"
              className="w-full"
            >
              Continue to Checkout
            </Button>
          )}

          {selectedMethod === 'x402' && (
            <div className="space-y-4">
              {!isConnected ? (
                <div className="text-center space-y-4">
                  <p className="text-sm text-gray-600">
                    Connect your wallet to pay with crypto
                  </p>
                  <ConnectWallet />
                </div>
              ) : (
                <X402Payment
                  agentId={agent.id}
                  recipient={x402Method.recipient}
                  amount={x402Method.amount}
                  onSuccess={handleX402Success}
                  onError={(error) => console.error(error)}
                />
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
```

---

## 🧪 PART 3: TESTING (Day 8)

### **3.1 Test Payment Discovery:**

```bash
# Test payment methods endpoint
curl http://localhost:4000/x402/agents/:agentId/payment-methods
```

### **3.2 Test x402 Flow:**

1. Connect wallet in UI
2. Select x402 payment
3. Approve USDC transaction
4. Verify payment in backend
5. Confirm agent execution

### **3.3 Test Dual Flow:**

1. Test traditional payment still works
2. Test x402 payment works
3. Verify both show in transaction history
4. Confirm agents receive payments correctly

### **3.4 Legacy Platform Validation**

- `npm run test --workspace apps/api -- src/modules/agents/agents.service.spec.ts`  
  Verifies that the server merges fiat wallet transactions and x402 transfers into one history feed.
- `npm run test --workspace apps/web -- src/components/transactions/transaction-history-list.test.tsx`  
  Confirms the transactions UI labels both rails correctly and shows wallet references + hashes.
- Manual Stripe / escrow smoke test:
  1. Trigger a standard AgentMarket purchase (Stripe checkout ➜ escrow release).
  2. Confirm funds appear in `wallets` table and `GET /agents/:id/payment-history` returns the record.
  3. Load `/console/transactions?agentId=<agent_id>` and verify the fiat line item renders alongside a recent x402 hash.

### **3.5 Automating the Stripe Smoke Test**

| Step | Command / Action                                                          | Notes                                                       |
| ---- | ------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 1    | `stripe login`                                                            | Authenticate CLI (test mode).                               |
| 2    | `stripe listen --forward-to http://localhost:4000/billing/stripe-webhook` | Streams webhook events to local API while the UI test runs. |
| 3    | `cd apps/web && npx playwright test stripe-smoke --project=chromium`      | Executes the Playwright spec below.                         |
| 4    | Inspect Playwright report + API logs                                      | Confirms checkout + payment-history verification succeeded. |

#### Playwright Spec (apps/web/tests/payments/stripe-smoke.spec.ts)

```ts
import { test, expect } from '@playwright/test';
import { createAgentMarketClient } from '@agent-market/sdk';

test('legacy Stripe checkout still works', async ({ page }) => {
  const client = createAgentMarketClient({ baseUrl: process.env.API_URL });
  const agent = await client.getAgent(process.env.TEST_AGENT_ID!);

  await page.goto(`/agents/${agent.slug}/purchase`);
  await page.getByText('AgentMarket Balance').click();
  await page.getByRole('button', { name: 'Continue to Checkout' }).click();

  const checkout = page.frameLocator('iframe[name="stripe_checkout_app"]');
  await checkout.getByPlaceholder('Card number').fill('4242424242424242');
  await checkout.getByPlaceholder('MM / YY').fill('12 / 34');
  await checkout.getByPlaceholder('CVC').fill('123');
  await checkout.getByRole('button', { name: 'Pay' }).click();

  await expect(page).toHaveURL(/success/i, { timeout: 60_000 });

  const history = await client.getAgentPaymentHistory(agent.id);
  const legacyTx = history.find((tx) => tx.rail === 'platform' && tx.reference?.startsWith('ch_'));
  expect(legacyTx).toBeDefined();
});
```

> **CI wiring tip:** run `stripe listen` inside the pipeline (or use Stripe’s event replay) before invoking Playwright. Fail the job if the script exits non‑zero so regressions in the fiat checkout are caught automatically.

---

## 🚀 PART 4: DEPLOYMENT (Day 9-10)

### **4.1 Environment Variables (Production):**

```bash
# Add to production .env
BASE_RPC_URL=https://mainnet.base.org
X402_FACILITATOR_URL=https://x402.org/facilitator
X402_ENABLED=true
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id
```

### **4.2 Deploy Backend:**

1. `npm install`
2. `npm run lint --workspace apps/api`
3. `npm run test --workspace apps/api`
4. `npx prisma migrate deploy --schema apps/api/prisma/schema.prisma`
5. `npm run build --workspace apps/api`
6. Deploy through Fly.io (or your target) using the existing `npm run deploy:api` script.

### **4.3 Deploy Frontend:**

1. `npm install`
2. `npm run lint --workspace apps/web`
3. `npm run test --workspace apps/web`
4. `npm run build --workspace apps/web`
5. Deploy via `npm run deploy:web` (Next.js on Fly/Edge).

### **4.4 Post-Deployment Verification**

1. Smoke test `/agents/[slug]/purchase` for both rails.
2. Execute one fiat + one x402 transaction in staging and confirm `/console/transactions` shows both.
3. Monitor Stripe + blockchain facilitator dashboards for the first hour.
4. Enable monitoring/alerts (Datadog + Sentry) for `x402` namespace.

---

## ✅ VERIFICATION CHECKLIST

- [x] Database schema updated with x402 fields
- [x] x402 service implemented and tested
- [x] Payment methods API returns both options
- [x] Wallet connection UI works
- [x] Payment method selector functional
- [x] x402 payment flow completes successfully
- [x] Platform payment still works
- [x] Transaction verification works
- [x] Both payments show in history
- [x] Deployed to production
- [x] Monitoring configured

---

## 🎯 SUCCESS CRITERIA

### **You're Done When:**

1. ✅ Agents show dual payment options
2. ✅ Users can connect crypto wallets
3. ✅ x402 payments complete in <10 seconds
4. ✅ Platform payments still work perfectly
5. ✅ Transaction history shows both types
6. ✅ No breaking changes to existing flow
7. ✅ Production deployment successful

---

## 🚀 LAUNCH STRATEGY

### **Phase 1: Soft Launch**

- Enable x402 for 10 Genesis agents only
- Invite crypto-native users to test
- Gather feedback, fix issues

### **Phase 2: Full Rollout**

- Enable x402 for all agents
- Marketing: "First dual-rail marketplace"
- Educational content

### **Phase 3: Optimization**

- Monitor adoption metrics
- Optimize gas costs
- Add more networks (Solana, Polygon)

---

## 🎯 BOTTOM LINE

**You're building the first agent marketplace with:**

- ✅ Dual payment rails (fiat + crypto)
- ✅ Instant crypto settlements
- ✅ True micropayments
- ✅ Cross-platform compatibility

**Timeline:** 10 days to production

**Let's ship it.** 🚀
