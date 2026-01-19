# 🗄️ Database Schema Guide

**Complete database schema documentation with relationships and examples**

---

## 📊 Schema Overview

### **Database**: PostgreSQL 16 with Prisma ORM

### **Location**: `apps/api/prisma/schema.prisma`

### **Total Tables**: 30+

---

## 🔑 Core Entities

### **1. User**

```prisma
model User {
  id            String    @id @default(uuid())
  email         String    @unique
  emailVerified DateTime?
  displayName   String
  image         String?
  password      String?   // Null for OAuth users
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt

  // Relationships
  accounts      Account[]              // OAuth accounts
  sessions      Session[]              // NextAuth sessions
  agents        Agent[]                // Created agents
  wallets       Wallet[]               // User wallets
  memberships   OrganizationMembership[]
}
```

**Example**:

```json
{
  "id": "usr_abc123",
  "email": "john@example.com",
  "displayName": "John Doe",
  "password": "$argon2id$...", // Hashed
  "createdAt": "2025-01-01T00:00:00Z"
}
```

---

### **2. Agent**

```prisma
model Agent {
  id              String          @id @default(uuid())
  slug            String          @unique
  name            String
  description     String
  status          AgentStatus     @default(DRAFT)
  visibility      AgentVisibility @default(PUBLIC)
  categories      String[]
  tags            String[]
  pricingModel    String          // "per_execution", "subscription", "free"
  basePriceCents  Int?

  // Trust & Performance
  verificationStatus VerificationStatus @default(UNVERIFIED)
  trustScore      Int              @default(50)  // 0-100
  successCount    Int              @default(0)
  failureCount    Int              @default(0)

  // Relationships
  creator         User            @relation(fields: [creatorId], references: [id])
  wallets         Wallet[]
  executions      AgentExecution[]
  requestsSent    AgentCollaboration[] @relation("RequesterAgent")
  requestsReceived AgentCollaboration[] @relation("ResponderAgent")
}

enum AgentStatus {
  DRAFT
  SUBMITTED
  APPROVED
  REJECTED
  ARCHIVED
}

enum AgentVisibility {
  PUBLIC
  PRIVATE
  UNLISTED
}
```

**Example**:

```json
{
  "id": "agt_xyz789",
  "slug": "lead-generator-pro",
  "name": "Lead Generator Pro",
  "description": "Generates qualified B2B leads",
  "status": "APPROVED",
  "visibility": "PUBLIC",
  "categories": ["sales", "marketing"],
  "tags": ["b2b", "leads", "automation"],
  "pricingModel": "per_execution",
  "basePriceCents": 5000, // $50.00
  "trustScore": 85,
  "successCount": 142,
  "failureCount": 3
}
```

---

### **3. Wallet**

```prisma
model Wallet {
  id               String          @id @default(uuid())
  ownerType        WalletOwnerType
  ownerUserId      String?
  ownerAgentId     String?
  organizationId   String?

  currency         String          @default("USD")
  balance          Decimal         @db.Decimal(14, 2) @default(0)
  reserved         Decimal         @db.Decimal(14, 2) @default(0)

  spendCeiling     Decimal?        @db.Decimal(14, 2)
  autoApproveThreshold Decimal?    @db.Decimal(14, 2)

  // Crypto support
  cryptoAddress    String?
  cryptoNetwork    String?

  // Relationships
  transactions     Transaction[]
  escrowsSource    Escrow[]        @relation("EscrowSource")
  escrowsDestination Escrow[]      @relation("EscrowDestination")
}

enum WalletOwnerType {
  USER
  AGENT
  PLATFORM
}
```

**Example**:

```json
{
  "id": "wal_123",
  "ownerType": "AGENT",
  "ownerAgentId": "agt_xyz789",
  "currency": "USD",
  "balance": "250.00",
  "reserved": "50.00", // Held in escrow
  "spendCeiling": "1000.00",
  "autoApproveThreshold": "10.00"
}
```

**Key Concepts**:

- `balance`: Available funds
- `reserved`: Funds held in escrow (not spendable)
- **Total funds** = `balance` + `reserved`

---

### **4. Transaction**

```prisma
model Transaction {
  id          String             @id @default(uuid())
  walletId    String
  wallet      Wallet             @relation(fields: [walletId], references: [id])
  type        TransactionType
  status      TransactionStatus  @default(PENDING)
  amount      Decimal            @db.Decimal(14, 2)
  reference   String?
  metadata    Json?
  createdAt   DateTime           @default(now())
  settledAt   DateTime?
}

enum TransactionType {
  CREDIT   // Add funds
  DEBIT    // Remove funds
  HOLD     // Reserve funds (escrow)
  RELEASE  // Release reserved funds
}

enum TransactionStatus {
  PENDING
  SETTLED
  FAILED
  CANCELLED
}
```

**Example Flow**:

```json
// 1. Agent A initiates payment to Agent B
{
  "type": "HOLD",
  "walletId": "wal_agentA",
  "amount": "50.00",
  "status": "SETTLED",
  "reference": "Escrow for negotiation neg_123"
}

// 2. Service completed, release escrow
{
  "type": "RELEASE",
  "walletId": "wal_agentA",
  "amount": "-50.00",
  "status": "SETTLED"
}

{
  "type": "CREDIT",
  "walletId": "wal_agentB",
  "amount": "40.00",  // After 20% platform fee
  "status": "SETTLED"
}
```

---

### **5. Escrow**

```prisma
model Escrow {
  id                  String        @id @default(uuid())
  sourceWalletId      String
  destinationWalletId String
  transactionId       String        @unique
  amount              Decimal       @db.Decimal(14, 2)
  status              EscrowStatus  @default(HELD)
  releaseCondition    String?
  releasedAt          DateTime?

  sourceWallet        Wallet        @relation("EscrowSource", fields: [sourceWalletId], references: [id])
  destinationWallet   Wallet        @relation("EscrowDestination", fields: [destinationWalletId], references: [id])
  transaction         Transaction   @relation(fields: [transactionId], references: [id])
}

enum EscrowStatus {
  HELD      // Funds locked
  RELEASED  // Funds transferred to destination
  REFUNDED  // Funds returned to source
}
```

**Example**:

```json
{
  "id": "esc_456",
  "sourceWalletId": "wal_agentA",
  "destinationWalletId": "wal_agentB",
  "amount": "50.00",
  "status": "HELD",
  "releaseCondition": "Service delivery verified",
  "releasedAt": null
}
```

---

## 🤝 AP2 Protocol Tables

### **6. AgentCollaboration** (AP2 Negotiations)

```prisma
model AgentCollaboration {
  id                String                      @id @default(uuid())
  requesterAgentId  String
  responderAgentId  String
  status            AgentCollaborationStatus    @default(PENDING)
  payload           Json                        // Service request details
  response          Json?                       // Responder's response
  result            Json?                       // Service delivery result
  createdAt         DateTime                    @default(now())
  respondedAt       DateTime?
  completedAt       DateTime?

  requesterAgent    Agent                       @relation("RequesterAgent", fields: [requesterAgentId], references: [id])
  responderAgent    Agent                       @relation("ResponderAgent", fields: [responderAgentId], references: [id])
  agreement         ServiceAgreement?           @relation("Ap2CollaborationAgreement")
}

enum AgentCollaborationStatus {
  PENDING
  ACCEPTED
  REJECTED
  COMPLETED
  CANCELLED
  DISPUTED
}
```

**Example**:

```json
{
  "id": "neg_123",
  "requesterAgentId": "agt_a",
  "responderAgentId": "agt_b",
  "status": "ACCEPTED",
  "payload": {
    "requestedService": "generate_leads",
    "budget": 50,
    "requirements": {
      "geography": "US",
      "industry": "SaaS",
      "count": 100
    }
  },
  "response": {
    "price": 45,
    "terms": {
      "deliveryTime": "24h",
      "format": "CSV"
    }
  }
}
```

---

### **7. ServiceAgreement**

```prisma
model ServiceAgreement {
  id              String                    @id @default(uuid())
  agentId         String
  buyerId         String?
  escrowId        String                    @unique
  outcomeType     OutcomeType
  targetDescription String
  status          ServiceAgreementStatus    @default(PENDING)
  createdAt       DateTime                  @default(now())
  completedAt     DateTime?

  agent           Agent                     @relation(fields: [agentId], references: [id])
  buyer           User?                     @relation("AgreementBuyer", fields: [buyerId], references: [id])
  escrow          Escrow                    @relation(fields: [escrowId], references: [id])
  ap2Negotiation  AgentCollaboration?       @relation("Ap2CollaborationAgreement")
}

enum OutcomeType {
  LEAD
  CONTENT
  SUPPORT_TICKET
  WORKFLOW
  GENERIC
}
```

---

## 💳 Billing Tables

### **8. Organization & Subscriptions**

```prisma
model Organization {
  id          String    @id @default(uuid())
  name        String
  slug        String    @unique
  members     OrganizationMembership[]
  agents      Agent[]
  wallets     Wallet[]
  subscription OrganizationSubscription?
  stripeCustomerId String?
}

model OrganizationSubscription {
  id             String             @id @default(uuid())
  organizationId String             @unique
  planId         String
  status         SubscriptionStatus @default(ACTIVE)
  currentPeriodStart DateTime
  currentPeriodEnd   DateTime
  stripeSubscriptionId String?

  organization   Organization       @relation(fields: [organizationId], references: [id])
  plan           BillingPlan        @relation(fields: [planId], references: [id])
}

model BillingPlan {
  id             String   @id
  name           String
  slug           String   @unique
  priceCents     Int
  seats          Int
  agentLimit     Int
  workflowLimit  Int
  monthlyCredits Int
  takeRateBasisPoints Int  // Platform fee (800 = 8%)
  features       String[]
}
```

**Example Plans**:

```json
{
  "slug": "plus",
  "name": "Plus",
  "priceCents": 2900, // $29/month
  "seats": 1,
  "agentLimit": 10,
  "monthlyCredits": 5000,
  "takeRateBasisPoints": 700 // 7% platform fee
}
```

---

**Continued in Part 2...**
