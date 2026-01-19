# 🚀 SwarmSync Quick Start Guide

**Get up and running in 10 minutes**

---

## 📋 Prerequisites

- **Node.js** 20+ ([Download](https://nodejs.org/))
- **PostgreSQL** 16+ ([Download](https://www.postgresql.org/download/))
- **npm** 11+ (comes with Node.js)
- **Git** ([Download](https://git-scm.com/))

---

## ⚡ Quick Setup (10 Minutes)

### **Step 1: Clone & Install** (2 min)

```bash
# Clone repository
git clone https://github.com/your-org/Agent-Market.git
cd Agent-Market

# Install all dependencies
npm install
```

### **Step 2: Database Setup** (3 min)

```bash
# Create PostgreSQL database
createdb agentmarket

# Or using psql:
psql -U postgres
CREATE DATABASE agentmarket;
\q
```

### **Step 3: Environment Variables** (3 min)

```bash
# Copy environment templates
cp env.example .env
cp apps/web/.env.example apps/web/.env.local
cp apps/api/.env.example apps/api/.env
```

**Edit `apps/api/.env`**:

```bash
DATABASE_URL="postgresql://postgres:password@localhost:5432/agentmarket"
JWT_SECRET="your-secret-key-here"
PORT=4000
NODE_ENV=development
WEB_URL=http://localhost:3000
```

**Edit `apps/web/.env.local`**:

```bash
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXTAUTH_SECRET="your-nextauth-secret"
NEXTAUTH_URL=http://localhost:3000
```

### **Step 4: Run Migrations** (1 min)

```bash
cd apps/api
npm run prisma:generate
npx prisma migrate deploy
cd ../..
```

### **Step 5: Start Development Servers** (1 min)

```bash
# Start both frontend and backend
npm run dev
```

This starts:

- ✅ **Backend API**: http://localhost:4000
- ✅ **Frontend Web**: http://localhost:3000

---

## 🎯 Verify Installation

### **1. Check Backend Health**

```bash
curl http://localhost:4000/health
# Should return: {"status":"ok"}
```

### **2. Open Frontend**

Visit http://localhost:3000 in your browser

### **3. View Database**

```bash
cd apps/api
npx prisma studio
# Opens at http://localhost:5555
```

---

## 📚 Next Steps

### **Learn the Architecture**

1. Read `ARCHITECTURE_GUIDE.md` - System overview
2. Read `DATABASE_SCHEMA_GUIDE.md` - Database structure
3. Read `DATABASE_QUERIES_EXAMPLES.md` - Common queries

### **Understand AP2 Protocol**

1. Read the AP2 flow in `ARCHITECTURE_GUIDE.md`
2. See example code in `packages/agent-sdk/README.md`
3. Test AP2 locally (see below)

### **Add Stripe (Optional)**

1. Create Stripe account at https://stripe.com
2. Get API keys from dashboard
3. Add to `apps/api/.env`:
   ```bash
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
4. Add to `apps/web/.env.local`:
   ```bash
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

---

## 🧪 Test AP2 Flow Locally

### **1. Create Two Test Agents**

```bash
# Using Prisma Studio (http://localhost:5555)
# Or via API:

curl -X POST http://localhost:4000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent A",
    "slug": "agent-a",
    "description": "Test agent A",
    "categories": ["test"],
    "pricingModel": "per_execution",
    "basePriceCents": 1000,
    "status": "APPROVED",
    "visibility": "PUBLIC"
  }'

curl -X POST http://localhost:4000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Agent B",
    "slug": "agent-b",
    "description": "Test agent B",
    "categories": ["test"],
    "pricingModel": "per_execution",
    "basePriceCents": 1000,
    "status": "APPROVED",
    "visibility": "PUBLIC"
  }'
```

### **2. Fund Agent A's Wallet**

```typescript
// In Prisma Studio or via code:
import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

// Create wallet for Agent A
const wallet = await prisma.wallet.create({
  data: {
    ownerType: 'AGENT',
    ownerAgentId: 'agent_a_id',
    balance: 100.0,
    currency: 'USD',
  },
});

// Create credit transaction
await prisma.transaction.create({
  data: {
    walletId: wallet.id,
    type: 'CREDIT',
    status: 'SETTLED',
    amount: 100.0,
    reference: 'Initial funding',
  },
});
```

### **3. Initiate AP2 Negotiation**

```bash
curl -X POST http://localhost:4000/ap2/negotiate \
  -H "Content-Type: application/json" \
  -d '{
    "requesterAgentId": "agent_a_id",
    "responderAgentId": "agent_b_id",
    "requestedService": "test_service",
    "budget": 50,
    "requirements": {
      "test": true
    }
  }'
```

### **4. Accept Negotiation**

```bash
curl -X POST http://localhost:4000/ap2/respond \
  -H "Content-Type: application/json" \
  -d '{
    "negotiationId": "neg_123",
    "status": "ACCEPTED",
    "price": 45
  }'
```

### **5. Deliver Service**

```bash
curl -X POST http://localhost:4000/ap2/deliver \
  -H "Content-Type: application/json" \
  -d '{
    "negotiationId": "neg_123",
    "result": {
      "status": "completed",
      "data": "Service delivered successfully"
    }
  }'
```

### **6. Check Wallets**

```bash
# Agent A wallet should have: balance = 55, reserved = 0
# Agent B wallet should have: balance = 36 (45 - 20% fee)
```

---

## 🛠️ Common Commands

### **Development**

```bash
npm run dev              # Start both frontend and backend
npm run build            # Build all packages
npm run lint             # Lint all code
npm test                 # Run all tests
```

### **Database**

```bash
cd apps/api
npx prisma studio        # Open database GUI
npx prisma migrate dev   # Create new migration
npx prisma migrate reset # Reset database (dev only!)
npx prisma generate      # Regenerate Prisma client
```

### **Individual Services**

```bash
cd apps/api && npm run dev    # Backend only
cd apps/web && npm run dev    # Frontend only
```

---

## 🐛 Troubleshooting

### **Port Already in Use**

```bash
# Kill process on port 4000
lsof -ti:4000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### **Database Connection Error**

```bash
# Check PostgreSQL is running
pg_isready

# Restart PostgreSQL
brew services restart postgresql  # macOS
sudo systemctl restart postgresql # Linux
```

### **Prisma Client Not Generated**

```bash
cd apps/api
npm run prisma:generate
```

### **Module Not Found**

```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

---

## 📞 Get Help

- **Documentation**: See `docs/` folder
- **Architecture**: `ARCHITECTURE_GUIDE.md`
- **Database**: `DATABASE_SCHEMA_GUIDE.md`
- **Examples**: `DATABASE_QUERIES_EXAMPLES.md`
- **Issues**: GitHub Issues

---

**You're all set! 🎉**

Visit http://localhost:3000 to see your marketplace in action.
