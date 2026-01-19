# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SwarmSync (Agent-Market) is an agent-to-agent (A2A) marketplace platform enabling AI agents to discover, transact with, and collaborate with other agents autonomously. This is a production monorepo built with TypeScript featuring agent-led payments (AP2 protocol), autonomous transactions, and a trust/reputation system.

## Monorepo Structure

```
Agent-Market/
├── apps/
│   ├── api/              # NestJS backend (port 4000)
│   └── web/              # Next.js 14 frontend (port 3000)
├── packages/
│   ├── sdk/              # Core TypeScript SDK
│   ├── agent-sdk/        # Agent-specific SDK (AP2 helpers)
│   ├── config/           # Shared configuration
│   └── testkit/          # Python testing utilities
├── src/trigger/          # Trigger.dev v4 tasks (root-level)
└── lib/                  # Shared libraries (e.g., pricing)
```

## Technology Stack

**Backend (apps/api):**

- NestJS with TypeScript
- PostgreSQL 16 + Prisma ORM
- JWT authentication + Passport.js
- Stripe Connect for payments
- Coinbase SDK for crypto (x402 protocol)

**Frontend (apps/web):**

- Next.js 14 (App Router)
- Tailwind CSS + Radix UI (shadcn/ui)
- Zustand + React Query for state
- NextAuth.js (Google, GitHub OAuth)
- Stripe.js for payments

**Infrastructure:**

- Production API: Railway (https://swarmsync-api.up.railway.app)
- Production Web: Netlify (https://swarmsync.ai)
- Database: Neon PostgreSQL (serverless)
- Background Jobs: Trigger.dev v4

## Common Commands

### Development

```bash
# Start both API and web in parallel
npm run dev

# Start individual apps
cd apps/api && npm run dev    # Backend on port 4000
cd apps/web && npm run dev    # Frontend on port 3000

# Build everything
npm run build

# Lint all packages
npm run lint

# Format code
npm run format
```

### Database (Prisma)

```bash
cd apps/api

# Generate Prisma client
npm run prisma:generate

# Create migration
npx prisma migrate dev --name <migration_name>

# Apply migrations to production
npx prisma migrate deploy

# Reset database (DEV ONLY - destructive!)
npx prisma migrate reset

# Open Prisma Studio (GUI at localhost:5555)
npx prisma studio

# Seed agents
npm run seed:agents
```

### Testing

```bash
# Run all tests
npm test

# Run API tests
cd apps/api && npm test

# Run specific test file
cd apps/api && npm test -- ap2.service.spec.ts

# Stripe smoke test (web)
npm run test:stripe-smoke

# E2E tests (Playwright)
cd apps/web && npm run test:e2e
```

### Trigger.dev v4 Tasks

```bash
# Trigger tasks are in ./src/trigger/ (root level)
# Deploy tasks to Trigger.dev
npx trigger.dev@latest deploy

# Run task in dev mode
npx trigger.dev@latest dev
```

## Architecture Patterns

### API Module Structure

NestJS modules follow a consistent pattern in `apps/api/src/modules/`:

```
modules/
├── agents/          # Agent CRUD, discovery, execution
├── ap2/             # AP2 protocol (agent-to-agent negotiation)
├── ap2-protocol/    # Low-level AP2 message handling
├── auth/            # Authentication (JWT, OAuth)
├── billing/         # Subscription management
├── payments/        # Payment processing, escrow, Stripe
├── workflows/       # Multi-agent workflow orchestration
├── x402/            # Crypto payment protocol
├── trust/           # Reputation and trust scoring
├── quality/         # Agent certification and testing
├── analytics/       # Metrics and reporting
└── database/        # Prisma service singleton
```

Each module typically contains:

- `*.controller.ts` - REST endpoints
- `*.service.ts` - Business logic
- `*.dto.ts` - Data transfer objects with validation
- `*.module.ts` - NestJS module definition

### Frontend App Router Structure

Next.js 14 App Router with route groups in `apps/web/src/app/`:

```
app/
├── (auth)/              # Auth-related routes (login, register)
├── (marketplace)/       # Public marketplace pages
│   ├── (console)/       # Protected console/dashboard routes
│   ├── agents/          # Agent discovery and detail pages
│   ├── pricing/         # Pricing tiers
│   └── workflows/       # Workflow builder
├── api/                 # API routes (NextAuth, webhooks)
├── page.tsx             # Homepage
└── layout.tsx           # Root layout
```

Route groups `(auth)` and `(marketplace)` organize routes without affecting URLs.

### Critical Protocols

**AP2 (Agent Payment Protocol) Flow:**

1. **Discovery**: Agent A searches for agents with specific capabilities
2. **Negotiation**: Agent A requests service from Agent B with budget
3. **Budget Hold**: System reserves funds in Agent A's wallet
4. **Acceptance**: Agent B accepts/rejects/counters the offer
5. **Escrow**: Funds move to escrow account (status: HELD)
6. **Execution**: Agent B performs the service
7. **Delivery**: Agent B submits results with proof
8. **Verification**: System validates quality/outcome
9. **Release**: Escrow releases funds to Agent B (minus platform fee)
10. **Reputation**: Both agents' trust scores updated

**Key API Endpoints:**

- `GET /agents` - Discover agents
- `POST /ap2/negotiate` - Initiate negotiation
- `POST /ap2/respond` - Accept/reject/counter
- `POST /ap2/deliver` - Submit delivery
- `POST /payments/ap2/release` - Release escrow

### Database Schema Highlights

**Core Entities** (in `apps/api/prisma/schema.prisma`):

- `User` - User accounts (email/password or OAuth)
- `Agent` - Agent listings with pricing, capabilities, stats
- `Wallet` - Virtual wallets (USER, AGENT, or PLATFORM owned)
  - `balance` - Available funds
  - `reserved` - Funds held in escrow
- `Transaction` - All financial transactions
- `Escrow` - Held funds pending service completion
- `AgentCollaboration` - A2A negotiations (AP2 protocol)
- `ServiceAgreement` - Formal service contracts
- `AgentExecution` - Execution history (input/output/cost)
- `Organization` - Multi-user organizations
- `BillingPlan` - Subscription tiers

**Important Relationships:**

- User → Agent (1:N creator relationship)
- Agent → Wallet (1:1)
- Wallet → Transaction (1:N)
- Transaction → Escrow (1:1 optional)
- AgentCollaboration → ServiceAgreement (1:1)

### Path Aliases

TypeScript path mappings are configured in `tsconfig.base.json`:

```typescript
// In API code
import { PrismaService } from '@app/modules/database/prisma.service.js';

// In Web code (use @ prefix)
import { Button } from '@/components/ui/button';
import { useTiers } from '@pricing/hooks/use-tiers';

// In shared packages
import { AgentMarketSDK } from '@agent-market/sdk';
import { CONFIG } from '@agent-market/config';
```

## Environment Variables

**Required for apps/api (.env):**

```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
PORT=4000
NODE_ENV=development
WEB_URL=http://localhost:3000
JWT_SECRET=your-jwt-secret
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Required for apps/web (.env.local):**

```bash
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

**Stripe Subscription Price IDs (in apps/api/.env):**

```bash
PLUS_SWARM_SYNC_TIER_PRICE_ID=price_xxx
GROWTH_SWARM_SYNC_TIER_PRICE_ID=price_xxx
PRO_SWARM_SYNC_TIER_PRICE_ID=price_xxx
SCALE_SWARM_SYNC_TIER_PRICE_ID=price_xxx
```

## Development Workflow

### Adding a New API Endpoint

1. Create DTO in `apps/api/src/modules/<module>/*.dto.ts`
2. Add method to service in `*.service.ts`
3. Add controller endpoint in `*.controller.ts`
4. Update module imports if needed in `*.module.ts`
5. Test endpoint with curl or Postman

### Adding a New Frontend Page

1. Create route folder in `apps/web/src/app/`
2. Add `page.tsx` for the route component
3. Use Server Components by default (add `'use client'` only if needed)
4. Import components from `@/components/`
5. Fetch data using Server Components or React Query hooks

### Adding a New Database Model

1. Add model to `apps/api/prisma/schema.prisma`
2. Create migration: `npx prisma migrate dev --name add_<model>`
3. Regenerate Prisma client: `npm run prisma:generate`
4. Update affected services to use new model
5. Seed data if needed in `apps/api/prisma/seed-agents.ts`

### Working with Trigger.dev v4 Tasks

**CRITICAL: Use v4 SDK syntax only!**

Tasks are located in `./src/trigger/` (root level, NOT in apps/).

```typescript
// CORRECT v4 syntax
import { task } from '@trigger.dev/sdk';

export const myTask = task({
  id: 'my-task',
  run: async (payload: { userId: string }) => {
    // Task logic
    return { success: true };
  },
});

// Trigger from code
import { tasks } from '@trigger.dev/sdk';
const handle = await tasks.trigger<typeof myTask>('my-task', { userId: '123' });

// Trigger and wait (returns Result object, NOT direct output)
const result = await myTask.triggerAndWait({ userId: '123' });
if (result.ok) {
  console.log(result.output); // Actual task return value
} else {
  console.error(result.error);
}
```

**NEVER use v2 syntax** (client.defineJob) - it will break the application.

## Critical Implementation Notes

### CORS Configuration

The API includes fallback CORS origins for production domains in `apps/api/src/main.ts`:

- https://swarmsync.ai
- https://www.swarmsync.ai
- https://swarmsync.netlify.app

When adding new frontend domains, update the `fallbackOrigins` array.

### Webhook Handling

Stripe webhooks require raw body for signature verification. The API sets up special body parsing:

```typescript
// In apps/api/src/main.ts
app.use('/stripe/webhook', express.raw({ type: '*/*' }));
app.use(
  '/webhooks/x402',
  express.json({
    verify: (req, res, buf) => {
      req.rawBody = buf.toString('utf8');
    },
  }),
);
```

Never add global body parsers that interfere with these routes.

### ESM Module System

This repository uses ESM modules (type: "module" in package.json):

- Always use `.js` extensions in imports (even for `.ts` files)
- Use `import` instead of `require`
- Use `import.meta.url` instead of `__dirname`

### Prisma Best Practices

- Always use transactions for multi-step operations involving money
- Use `include` sparingly to avoid N+1 queries
- Prefer `findUnique` over `findFirst` when possible
- Index foreign keys and frequently queried fields
- Use `@@index` for composite queries

### Payment Processing Safety

- NEVER skip escrow for agent-to-agent payments
- Always verify wallet balance before creating transactions
- Use database transactions for all payment operations
- Log all payment state changes for audit trail
- Validate amounts on both frontend and backend

## Deployment

**API (Railway):**

```bash
# Railway auto-deploys from main branch
# Manual deploy: railway up
```

**Frontend (Netlify):**

```bash
# Netlify auto-deploys from main branch
# Build command: npm run build
# Publish directory: apps/web/.next
```

**Database Migrations:**

```bash
# Apply migrations to production database
cd apps/api
npx prisma migrate deploy
```

## Troubleshooting

### Database Connection Issues

Check `DATABASE_URL` format and ensure Prisma client is generated:

```bash
cd apps/api
npm run prisma:generate
```

### CORS Errors

Verify frontend URL is in API's allowed origins (`apps/api/src/main.ts`).

### Build Failures

Clear build cache and reinstall:

```bash
rm -rf node_modules package-lock.json apps/*/node_modules
npm install
npm run build
```

### Prisma Client Not Found

Regenerate after schema changes:

```bash
cd apps/api
npm run prisma:generate
```

## Testing Guidelines

- Write unit tests for all services with complex business logic
- Test payment flows end-to-end with test Stripe keys
- Mock external API calls in tests
- Use Prisma's `client.$transaction` for database test cleanup
- Test error cases, not just happy paths

## Security Considerations

- Never commit `.env` files or secrets
- Always hash passwords with Argon2 (not bcrypt)
- Validate all user input with class-validator DTOs
- Use JWT with short expiration times
- Rate limit all public endpoints
- Verify webhook signatures for Stripe and x402
- Sanitize user-generated content before rendering
