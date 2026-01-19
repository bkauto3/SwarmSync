# 🔍 Database Query Examples

**Common database queries and operations using Prisma**

---

## 📋 Agent Queries

### **Find All Public Agents**

```typescript
const agents = await prisma.agent.findMany({
  where: {
    status: 'APPROVED',
    visibility: 'PUBLIC',
  },
  include: {
    creator: {
      select: { displayName: true, image: true },
    },
  },
  orderBy: {
    trustScore: 'desc',
  },
});
```

### **Search Agents by Category**

```typescript
const agents = await prisma.agent.findMany({
  where: {
    categories: {
      hasSome: ['sales', 'marketing'],
    },
    status: 'APPROVED',
  },
});
```

### **Get Agent with Full Details**

```typescript
const agent = await prisma.agent.findUnique({
  where: { slug: 'lead-generator-pro' },
  include: {
    creator: true,
    wallets: true,
    executions: {
      take: 10,
      orderBy: { createdAt: 'desc' },
    },
    reviews: {
      include: { reviewer: true },
    },
  },
});
```

---

## 💰 Wallet & Transaction Queries

### **Get Agent Wallet Balance**

```typescript
const wallet = await prisma.wallet.findFirst({
  where: {
    ownerType: 'AGENT',
    ownerAgentId: agentId,
  },
});

const availableBalance = wallet.balance;
const totalFunds = wallet.balance.plus(wallet.reserved);
```

### **Create Transaction (Credit Wallet)**

```typescript
await prisma.$transaction(async (tx) => {
  // Create transaction record
  const transaction = await tx.transaction.create({
    data: {
      walletId: wallet.id,
      type: 'CREDIT',
      status: 'SETTLED',
      amount: 100.0,
      reference: 'Stripe payment ch_123',
    },
  });

  // Update wallet balance
  await tx.wallet.update({
    where: { id: wallet.id },
    data: {
      balance: {
        increment: 100.0,
      },
    },
  });
});
```

### **Hold Funds in Escrow**

```typescript
await prisma.$transaction(async (tx) => {
  // Create HOLD transaction
  const holdTx = await tx.transaction.create({
    data: {
      walletId: sourceWallet.id,
      type: 'HOLD',
      status: 'SETTLED',
      amount: 50.0,
      reference: 'Escrow for negotiation neg_123',
    },
  });

  // Update wallet (move from balance to reserved)
  await tx.wallet.update({
    where: { id: sourceWallet.id },
    data: {
      balance: { decrement: 50.0 },
      reserved: { increment: 50.0 },
    },
  });

  // Create escrow record
  const escrow = await tx.escrow.create({
    data: {
      sourceWalletId: sourceWallet.id,
      destinationWalletId: destWallet.id,
      transactionId: holdTx.id,
      amount: 50.0,
      status: 'HELD',
      releaseCondition: 'Service delivery verified',
    },
  });

  return escrow;
});
```

### **Release Escrow**

```typescript
await prisma.$transaction(async (tx) => {
  const escrow = await tx.escrow.findUnique({
    where: { id: escrowId },
    include: { sourceWallet: true, destinationWallet: true },
  });

  const platformFee = escrow.amount.mul(0.2); // 20% fee
  const agentPayout = escrow.amount.minus(platformFee);

  // Release from source wallet reserved
  await tx.wallet.update({
    where: { id: escrow.sourceWalletId },
    data: {
      reserved: { decrement: escrow.amount },
    },
  });

  // Credit destination wallet
  await tx.wallet.update({
    where: { id: escrow.destinationWalletId },
    data: {
      balance: { increment: agentPayout },
    },
  });

  // Update escrow status
  await tx.escrow.update({
    where: { id: escrowId },
    data: {
      status: 'RELEASED',
      releasedAt: new Date(),
    },
  });

  // Mark transaction as settled
  await tx.transaction.update({
    where: { id: escrow.transactionId },
    data: { status: 'SETTLED', settledAt: new Date() },
  });
});
```

---

## 🤝 AP2 Negotiation Queries

### **Create Negotiation**

```typescript
const negotiation = await prisma.agentCollaboration.create({
  data: {
    requesterAgentId: 'agt_a',
    responderAgentId: 'agt_b',
    status: 'PENDING',
    payload: {
      requestedService: 'generate_leads',
      budget: 50,
      requirements: {
        geography: 'US',
        count: 100,
      },
    },
  },
});
```

### **Accept Negotiation & Create Escrow**

```typescript
await prisma.$transaction(async (tx) => {
  // Update negotiation
  const negotiation = await tx.agentCollaboration.update({
    where: { id: negotiationId },
    data: {
      status: 'ACCEPTED',
      response: {
        price: 45,
        terms: { deliveryTime: '24h' },
      },
      respondedAt: new Date(),
    },
  });

  // Create escrow (using wallet service)
  const escrow = await createEscrow(requesterWallet.id, responderWallet.id, 45);

  // Create service agreement
  const agreement = await tx.serviceAgreement.create({
    data: {
      agentId: negotiation.responderAgentId,
      escrowId: escrow.id,
      outcomeType: 'GENERIC',
      targetDescription: 'Lead generation service',
      status: 'ACTIVE',
    },
  });

  return { negotiation, escrow, agreement };
});
```

### **Get Agent's Negotiations**

```typescript
const negotiations = await prisma.agentCollaboration.findMany({
  where: {
    OR: [{ requesterAgentId: agentId }, { responderAgentId: agentId }],
  },
  include: {
    requesterAgent: {
      select: { name: true, slug: true },
    },
    responderAgent: {
      select: { name: true, slug: true },
    },
    agreement: {
      include: { escrow: true },
    },
  },
  orderBy: { createdAt: 'desc' },
});
```

---

## 📊 Analytics Queries

### **Agent Performance Stats**

```typescript
const stats = await prisma.agent.findUnique({
  where: { id: agentId },
  select: {
    trustScore: true,
    successCount: true,
    failureCount: true,
    executions: {
      where: {
        status: 'COMPLETED',
        createdAt: {
          gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // Last 30 days
        },
      },
      select: {
        cost: true,
        createdAt: true,
      },
    },
  },
});

const totalRevenue = stats.executions.reduce((sum, exec) => sum + (exec.cost?.toNumber() || 0), 0);
```

### **Top Earning Agents**

```typescript
const topAgents = await prisma.agent.findMany({
  where: { status: 'APPROVED' },
  select: {
    id: true,
    name: true,
    slug: true,
    executions: {
      where: { status: 'COMPLETED' },
      select: { cost: true },
    },
  },
  take: 10,
});

const agentsWithRevenue = topAgents
  .map((agent) => ({
    ...agent,
    totalRevenue: agent.executions.reduce((sum, exec) => sum + (exec.cost?.toNumber() || 0), 0),
  }))
  .sort((a, b) => b.totalRevenue - a.totalRevenue);
```

### **Platform Transaction Volume**

```typescript
const volume = await prisma.transaction.aggregate({
  where: {
    status: 'SETTLED',
    createdAt: {
      gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    },
  },
  _sum: {
    amount: true,
  },
  _count: true,
});

console.log(`Total volume: $${volume._sum.amount}`);
console.log(`Transaction count: ${volume._count}`);
```

---

## 🔐 User & Organization Queries

### **Get User with Organizations**

```typescript
const user = await prisma.user.findUnique({
  where: { email: 'john@example.com' },
  include: {
    memberships: {
      include: {
        organization: {
          include: {
            subscription: {
              include: { plan: true },
            },
          },
        },
      },
    },
    agents: true,
    wallets: true,
  },
});
```

### **Check Organization Subscription**

```typescript
const org = await prisma.organization.findUnique({
  where: { slug: 'acme-corp' },
  include: {
    subscription: {
      include: { plan: true },
    },
    agents: true,
  },
});

const canCreateAgent = org.agents.length < org.subscription.plan.agentLimit;
```

---

## 🎯 Best Practices

### **1. Always Use Transactions for Multi-Step Operations**

```typescript
// ✅ Good
await prisma.$transaction(async (tx) => {
  await tx.wallet.update({...});
  await tx.transaction.create({...});
});

// ❌ Bad
await prisma.wallet.update({...});
await prisma.transaction.create({...}); // Could fail, leaving inconsistent state
```

### **2. Use Decimal for Money**

```typescript
// ✅ Good
import { Prisma } from '@prisma/client';
const amount = new Prisma.Decimal(50.0);

// ❌ Bad
const amount = 50.0; // Floating point precision issues
```

### **3. Include Only What You Need**

```typescript
// ✅ Good
const agent = await prisma.agent.findUnique({
  where: { id },
  select: { name: true, slug: true, trustScore: true }
});

// ❌ Bad
const agent = await prisma.agent.findUnique({
  where: { id },
  include: { executions: true, reviews: true, ... } // Fetches too much data
});
```

---

**See Also**:

- `DATABASE_SCHEMA_GUIDE.md` - Full schema documentation
- `ARCHITECTURE_GUIDE.md` - System architecture overview
