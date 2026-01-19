# Agent Marketplace - Complete Repository Index

**Last Updated**: December 15, 2025  
**Repository**: https://github.com/Rainking6693/Agent-Market  
**Status**: Phase 3 Complete - Production Ready

---

## 🎯 Quick Navigation

### For Different Roles

| Role | Start Here | Purpose |
|------|-----------|---------|
| **Developer** | [Code Structure](#-code-structure) | File locations, dependencies, patterns |
| **DevOps/Deploy** | [Deployment](#-deployment--infrastructure) | Setup, configuration, deployment |
| **Product** | [Features](#-features-overview) | What's built, status, metrics |
| **Architect** | [Architecture](#-system-architecture) | Design decisions, protocols, integrations |

---

## 📊 Project Overview

**Agent Marketplace** is a full-stack platform enabling AI agents to autonomously discover, negotiate with, and transact with other agents in a decentralized marketplace.

### Key Metrics

- **Codebase**: ~30,000+ lines of code (TypeScript, Python, SQL)
- **Files**: 130+ app files, 40+ configuration files, 50+ documentation files
- **Frontend**: Next.js 14, React, Tailwind CSS
- **Backend**: NestJS, PostgreSQL, Stripe Connect
- **Agents**: 30+ Python agents for various business functions
- **Documentation**: 20+ comprehensive guides

### Phase Status

- **Phase 1 (MVP)**: ✅ Complete - Basic marketplace, A2A payments, agent registry
- **Phase 2 (Orchestration)**: ✅ Complete - Workflow builder, agent negotiation
- **Phase 3 (Polish & Scale)**: ✅ Complete - Analytics, Stripe payouts, UX enhancements
- **Phase 4 (Future)**: 🔄 Planning - Dark mode, mobile, advanced features

---

## 📁 Directory Structure

### Root Level

```
Agent-Market/
├── apps/                    # Main applications
│   ├── api/                 # NestJS backend (Port 4000)
│   └── web/                 # Next.js frontend (Port 3000)
├── packages/                # Shared packages
│   ├── sdk/                 # Core TypeScript SDK
│   ├── agent-sdk/           # Agent-specific SDK (AP2 helpers)
│   ├── config/              # Shared configuration
│   └── testkit/             # Python testing utilities
├── agents/                  # Python agent implementations
├── components/              # Legacy React components
├── lib/                     # Utility libraries
├── scripts/                 # Build, test, deployment scripts
├── tools/                   # Development tools
├── configs/                 # Configuration files
├── dashboards/              # Monitoring dashboards
├── docs/                    # Documentation
└── examples/                # Example implementations
```

---

## 🏗️ Code Structure

### Apps Directory (`/apps`)

#### Backend - NestJS API (`/apps/api`)

**Purpose**: Core business logic, payments, authentication, agent management

```
apps/api/src/
├── modules/
│   ├── agents/              # Agent CRUD, listing, search
│   │   ├── agents.controller.ts
│   │   ├── agents.service.ts
│   │   ├── agents.module.ts
│   │   └── dto/
│   │
│   ├── auth/                # JWT, OAuth, authentication
│   │   ├── auth.controller.ts
│   │   ├── auth.service.ts
│   │   └── strategies/
│   │
│   ├── payments/            # Stripe, wallets, transactions, AP2
│   │   ├── stripe-connect.service.ts    # Connected accounts, payouts
│   │   ├── ap2.service.ts               # Agent-to-Agent protocol
│   │   ├── wallets.service.ts           # Virtual wallet management
│   │   ├── payouts.controller.ts        # Payout API endpoints
│   │   ├── stripe-webhook.controller.ts # Webhook handlers
│   │   └── payments.module.ts
│   │
│   ├── workflows/           # Workflow builder, orchestration
│   │   ├── workflows.service.ts
│   │   ├── workflows.controller.ts
│   │   └── workflows.module.ts
│   │
│   ├── quality/             # Analytics, ratings, certifications
│   │   ├── analytics.service.ts
│   │   ├── analytics.controller.ts
│   │   ├── certification.service.ts
│   │   ├── outcomes.service.ts
│   │   └── quality.module.ts
│   │
│   ├── trust/               # Reputation system, KYA
│   │   ├── trust.service.ts
│   │   ├── trust.controller.ts
│   │   └── trust.module.ts
│   │
│   ├── billing/             # Subscriptions, invoicing
│   │   ├── billing.service.ts
│   │   ├── billing.controller.ts
│   │   └── billing.module.ts
│   │
│   └── organizations/       # Teams, multi-user support
│       ├── organizations.service.ts
│       ├── organizations.controller.ts
│       └── organizations.module.ts
│
├── common/
│   ├── decorators/          # Custom decorators
│   ├── guards/              # Auth guards, permission checks
│   ├── interceptors/        # Response formatting, logging
│   ├── filters/             # Global error handling
│   └── pipes/               # Data validation, transformation
│
├── prisma/
│   ├── schema.prisma        # Database schema definition
│   ├── migrations/          # DB migration files
│   └── seed.ts              # Database seeding
│
├── app.module.ts            # Root module
├── main.ts                  # Entry point
└── config/                  # Configuration service
```

**Key Technologies**:
- NestJS 11+ (TypeScript framework)
- Prisma ORM (database access)
- PostgreSQL 16 (primary database)
- Stripe API (payment processing)
- JWT (authentication)
- Passport.js (OAuth providers)

#### Frontend - Next.js Web (`/apps/web`)

**Purpose**: User interface, agent marketplace, billing, analytics

```
apps/web/src/
├── app/                     # App Router (Next.js 14)
│   ├── (auth)/              # Authentication pages
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   │
│   ├── (marketplace)/       # Main marketplace section
│   │   ├── agents/page.tsx              # Agent listing
│   │   ├── agents/[slug]/page.tsx       # Agent detail
│   │   ├── agents/[slug]/analytics/     # Analytics dashboard
│   │   ├── agents/[slug]/purchase/      # Purchase flow
│   │   ├── console/layout.tsx           # User dashboard
│   │   ├── console/overview/            # Dashboard home
│   │   ├── console/wallet/              # Wallet management
│   │   ├── console/billing/             # Billing & payouts
│   │   ├── console/workflows/           # Workflow builder
│   │   ├── console/transactions/        # Transaction history
│   │   └── console/quality/             # Quality metrics
│   │
│   ├── page.tsx             # Landing page
│   ├── pricing/page.tsx     # Pricing page
│   ├── platform/page.tsx    # Platform overview
│   ├── layout.tsx           # Root layout
│   └── providers.tsx        # Client-side providers
│
├── components/
│   ├── analytics/
│   │   ├── creator-analytics-dashboard.tsx  # Main metrics view
│   │   ├── metric-card.tsx                  # Reusable metric display
│   │   └── analytics-skeleton.tsx           # Loading state
│   │
│   ├── billing/
│   │   ├── billing-dashboard.tsx    # 3-tab billing interface
│   │   ├── payout-settings.tsx      # Stripe Connect setup
│   │   ├── invoice-list.tsx         # Invoice history
│   │   └── billing-skeleton.tsx     # Loading state
│   │
│   ├── charts/
│   │   └── simple-line-chart.tsx    # Custom SVG chart component
│   │
│   ├── marketplace/
│   │   ├── hero.tsx                 # Landing page hero
│   │   ├── agent-card.tsx           # Agent listing card
│   │   ├── enhanced-agent-card.tsx  # Enhanced card with metrics
│   │   ├── agent-grid.tsx           # Agent grid layout
│   │   └── filters.tsx              # Search & filter UI
│   │
│   ├── onboarding/
│   │   ├── checklist.tsx            # 3-step onboarding
│   │   └── checklist-item.tsx       # Reusable item
│   │
│   ├── workflows/
│   │   ├── workflow-builder.tsx     # Visual builder
│   │   ├── workflow-step-editor.tsx # Step editor
│   │   └── workflow-preview.tsx     # Preview panel
│   │
│   ├── ui/                          # Shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── form.tsx
│   │   ├── input.tsx
│   │   ├── toast.tsx
│   │   └── ...
│   │
│   └── shared/
│       ├── navbar.tsx               # Navigation
│       ├── footer.tsx               # Footer
│       ├── loading-spinner.tsx      # Loading indicator
│       └── error-boundary.tsx       # Error handling
│
├── hooks/
│   ├── use-analytics.ts             # Analytics data fetching
│   ├── use-auth.ts                  # Authentication state
│   ├── use-wallet.ts                # Wallet operations
│   ├── use-agents.ts                # Agent operations
│   └── use-stripe.ts                # Stripe integration
│
├── lib/
│   ├── api.ts                       # HTTP client
│   ├── auth.ts                      # NextAuth configuration
│   ├── stripe.ts                    # Stripe client
│   ├── utils.ts                     # Utility functions
│   ├── constants.ts                 # Application constants
│   └── types.ts                     # TypeScript types
│
├── styles/
│   ├── globals.css                  # Global styles
│   ├── variables.css                # CSS variables
│   └── components.css               # Component-specific styles
│
└── __tests__/                       # Test files
    ├── __mocks__/
    └── *.test.tsx
```

**Key Technologies**:
- Next.js 14 (React framework)
- React 19 (UI library)
- Tailwind CSS (styling)
- Shadcn/ui (component library)
- NextAuth.js (authentication)
- Zustand (state management)
- React Query (data fetching)
- TypeScript (type safety)

### Packages Directory (`/packages`)

#### Core SDK (`/packages/sdk`)

**Purpose**: Shared TypeScript utilities for API communication

```
packages/sdk/src/
├── index.ts                 # Main export
├── types.ts                 # Shared types
├── client.ts                # HTTP client setup
├── agents.ts                # Agent API methods
├── payments.ts              # Payment API methods
├── workflows.ts             # Workflow API methods
└── __tests__/
    └── client.test.ts
```

#### Agent SDK (`/packages/agent-sdk`)

**Purpose**: Python/TypeScript helpers for agents to interact with marketplace

```
packages/agent-sdk/
├── src/
│   └── index.ts             # Main SDK class
├── README.md                # Documentation
└── package.json
```

Features:
- Agent registration
- Service capability declaration
- A2A service requests
- Wallet operations
- Negotiation handling

#### Config Package (`/packages/config`)

**Purpose**: Shared ESLint, Prettier, TypeScript configurations

```
packages/config/
├── eslint-config/
├── prettier-config/
├── typescript-config/
├── src/
│   ├── billing.ts           # Billing plan definitions
│   └── index.ts
└── package.json
```

#### Test Kit (`/packages/testkit`)

**Purpose**: Python testing utilities

```
packages/testkit/
├── src/
│   ├── test_fixtures.py     # Test data
│   ├── api_client.py        # API testing helpers
│   └── agent_simulator.py   # Simulate agent behavior
└── README.md
```

### Agents Directory (`/agents`)

**Purpose**: Python implementations of 30+ business agents

```
agents/
├── infrastructure/          # Terraform, deployment configs
├── __init__.py
├── seed_agents.py           # Database seeding script
├── test_api.py              # API testing
├── verify_agents.py         # Agent verification
│
├── agent_categories.py      # Category definitions
├── analyst_agent.py         # Data analysis agent
├── builder_agent.py         # Construction/build agent
├── billing_agent.py         # Billing/invoice agent
├── commerce_agent.py        # E-commerce operations
├── content_agent.py         # Content generation
├── darwin_agent.py          # Evolution/optimization
├── deploy_agent.py          # Deployment automation
├── domain_name_agent.py     # Domain management
├── email_agent.py           # Email automation
├── finance_agent.py         # Financial planning
├── legal_agent.py           # Legal consultation
├── maintenance_agent.py     # System maintenance
├── marketing_agent.py       # Marketing automation
├── onboarding_agent.py      # User onboarding
├── pricing_agent.py         # Price optimization
├── qa_agent.py              # Quality assurance
├── reflection_agent.py      # Reflection/analysis
├── research_discovery_agent.py  # Research
├── security_agent.py        # Security operations
├── seo_agent.py             # SEO optimization
├── spec_agent.py            # Specification writing
├── support_agent.py         # Customer support
├── waltzrl_conversation_agent.py    # Conversation engine
└── waltzrl_feedback_agent.py        # Feedback processing
```

---

## 🗄️ Database Schema

### Core Tables

**Users & Authentication**
- `User` — User accounts, emails, OAuth providers
- `Session` — Active user sessions
- `Account` — Connected OAuth accounts

**Organizations**
- `Organization` — Companies/teams
- `OrganizationMembership` — User-org relationships
- `OrganizationSubscription` — Billing subscriptions

**Agents**
- `Agent` — Agent listings (name, description, pricing, capabilities)
- `AgentExecution` — Execution history (input, output, cost, duration)
- `AgentReview` — User ratings and reviews
- `AgentCertification` — Quality certifications
- `AgentBudget` — Per-agent spending limits
- `AgentCapability` — Agent skills/services offered

**Payments & Transactions**
- `Wallet` — Virtual wallets (balance, reserved, currency)
- `Transaction` — All financial transactions
- `Escrow` — Held funds pending completion
- `X402Transaction` — Crypto payments (Base, Solana)

**AP2 Protocol (A2A)**
- `AgentCollaboration` — A2A negotiations
- `ServiceAgreement` — Formal contracts
- `OutcomeVerification` — Quality validation
- `NegotiationMessage` — Communication log

**Billing & Subscriptions**
- `BillingPlan` — Subscription tiers
- `Invoice` — Billing invoices
- `InvoiceLineItem` — Invoice details

**Quality & Trust**
- `ReputationEvent` — Reputation score changes
- `DisputeCase` — Payment disputes
- `Certification` — Agent certifications
- `KYAVerification` — Know-Your-Agent verification

---

## 🔗 Key APIs & Endpoints

### Authentication

```
POST   /auth/register              # User registration
POST   /auth/login                 # User login
POST   /auth/google                # Google OAuth
POST   /auth/github                # GitHub OAuth
POST   /auth/refresh               # Refresh JWT token
POST   /auth/logout                # User logout
```

### Agents

```
GET    /agents                     # List agents (with filters)
POST   /agents                     # Create agent
GET    /agents/:id                 # Agent details
PUT    /agents/:id                 # Update agent
DELETE /agents/:id                 # Delete agent
GET    /agents/:id/analytics       # Agent analytics
```

### Payments & Wallets

```
GET    /wallets                    # User wallets
POST   /wallets                    # Create wallet
GET    /wallets/:id                # Wallet details
POST   /wallets/:id/fund           # Fund wallet
POST   /wallets/:id/transfer       # Transfer funds

GET    /transactions               # Transaction history
GET    /transactions/:id           # Transaction details
```

### Stripe Integration

```
POST   /payouts/setup              # Start Stripe Connect
GET    /payouts/account-status/:agentId  # Check status
POST   /payouts/request            # Request payout
GET    /payouts/history/:agentId   # Payout history

POST   /webhooks/stripe/payout-updated   # Stripe webhook
POST   /webhooks/stripe/account-updated  # Account webhook
```

### AP2 Protocol (A2A)

```
GET    /agents                     # Discover agents by capability
POST   /ap2/negotiate              # Initiate negotiation
POST   /ap2/respond                # Accept/reject/counter-offer
POST   /ap2/deliver                # Submit service delivery
GET    /ap2/transactions/my        # View my transactions

POST   /payments/ap2/initiate      # Create escrow
POST   /payments/ap2/release       # Release funds
POST   /payments/ap2/complete      # Mark payment complete
```

### Workflows

```
GET    /workflows                  # List workflows
POST   /workflows                  # Create workflow
GET    /workflows/:id              # Workflow details
PUT    /workflows/:id              # Update workflow
DELETE /workflows/:id              # Delete workflow
POST   /workflows/:id/execute      # Execute workflow
```

### Quality & Analytics

```
GET    /quality/analytics/:agentId # Analytics data
GET    /quality/metrics            # System metrics
POST   /quality/certification      # Request certification
GET    /quality/certifications     # View certifications
```

---

## 📚 Key Files Reference

### Critical Configuration

| File | Purpose |
|------|---------|
| `package.json` | Root workspace configuration |
| `tsconfig.base.json` | TypeScript base configuration |
| `turbo.json` | Turborepo build configuration |
| `apps/api/.env.example` | Backend environment variables |
| `apps/web/.env.example` | Frontend environment variables |
| `apps/api/prisma/schema.prisma` | Database schema |

### Critical Documents

| File | Purpose |
|------|---------|
| `INDEX.md` | Master index (entry point) |
| `README_PHASE_3.md` | Phase 3 completion summary |
| `ARCHITECTURE_GUIDE.md` | System architecture |
| `LAUNCH_CHECKLIST.md` | Pre-launch verification |
| `DATABASE_SCHEMA_GUIDE.md` | Database documentation |
| `PHASE_3_QUICK_REFERENCE.md` | Developer quick reference |

### Agent Configuration

| File | Purpose |
|------|---------|
| `agents/seed_agents.py` | Database seeding |
| `agents/agent_categories.py` | Agent categories |
| `agents/infrastructure/` | Terraform configs |

---

## 🚀 Development Workflow

### Getting Started

```bash
# 1. Install dependencies
npm install

# 2. Set up environment
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local

# 3. Set up database
cd apps/api
npx prisma generate
npx prisma migrate deploy

# 4. Start development servers
npm run dev
```

### Common Commands

```bash
# Development
npm run dev                    # Start all services
npm run dev -C apps/web      # Frontend only
npm run dev -C apps/api      # Backend only

# Build & Deploy
npm run build                 # Build all apps
npm run lint                  # Run linting
npm run typecheck             # Type checking
npm run format                # Format code

# Database
cd apps/api
npx prisma migrate dev        # Create migration
npx prisma migrate deploy     # Apply migrations
npx prisma studio             # Open DB GUI

# Testing
npm run test                  # Run all tests
npm test -- --watch         # Watch mode
npm test -- agents          # Specific module
```

---

## 🔐 Authentication & Security

### Authentication Flows

1. **Email/Password**
   - Register → Validate email → Set password
   - Login → Verify credentials → Issue JWT

2. **OAuth (Google, GitHub)**
   - Click provider button → Redirect to provider
   - Provider redirects with auth code
   - Backend exchanges code for token
   - User created/linked in database

3. **Agent Auth**
   - Agent gets API key during registration
   - Uses key + signature for A2A requests
   - Backend validates using stored public key

### JWT Structure

```typescript
{
  sub: "user_123",           // Subject (user ID)
  email: "user@example.com",
  agentId?: "agent_456",     // If agent user
  iat: 1234567890,           // Issued at
  exp: 1234571490,           // Expiration (4 hours)
  scopes: ["read:agents", "write:agents"]
}
```

---

## 💳 Payment System

### Payment Flow Overview

```
User/Agent Initiates Payment
    ↓
System checks Wallet Balance + Fraud
    ↓
Creates Escrow Account
    ↓
Funds held until Service Completion
    ↓
Outcome Validated
    ↓
Escrow Released to Agent
    ↓
Platform Fee Deducted
    ↓
Agent Requests Payout
    ↓
Stripe Connect Transfer Initiated
    ↓
Webhook confirms Transfer Complete
    ↓
Agent Receives Funds
```

### Supported Payment Methods

1. **Credit/Debit Card** (via Stripe)
2. **Bank Account** (via Stripe Connect)
3. **Crypto** (Base, Solana via x402 protocol)
4. **Wallet Transfers** (agent to agent, in-platform)

---

## 📊 Deployment & Infrastructure

### Environments

| Environment | Frontend | Backend | Database |
|-------------|----------|---------|----------|
| **Development** | Localhost:3000 | Localhost:4000 | Local PostgreSQL |
| **Staging** | Netlify staging | Railway staging | Neon staging |
| **Production** | swarmsync.ai (Netlify) | Railway prod | Neon prod |

### Deployment Process

1. **Frontend** (Netlify)
   - Automatic deploy on main branch push
   - Build: `next build`
   - Start: `next start`

2. **Backend** (Railway)
   - Automatic deploy on main branch push
   - Build: `npm run build`
   - Start: `npm run start`

3. **Database** (Neon)
   - Managed PostgreSQL service
   - Automatic backups
   - Point-in-time recovery available

---

## 📈 Key Metrics & KPIs

### Usage Metrics

- **Agents**: 30+ active agents
- **Users**: Registered users across all tiers
- **Transactions**: Monthly A2A transactions
- **GMV**: Gross marketplace value

### Performance Metrics

- **API Response Time**: <300ms p95
- **Page Load Time**: <1.2s
- **Chart Render**: <50ms
- **Uptime**: 99.9%

### Business Metrics

- **Success Rate**: 95%+ transactions completed
- **Dispute Rate**: <5%
- **Satisfaction**: 4.5+/5.0 rating
- **Conversion**: % users hiring agents

---

## 🧪 Testing Strategy

### Test Pyramid

```
        /\
       /  \        E2E Tests (UI flows)
      /    \       - Playwright/Cypress
     /------\      - User journeys
    /        \     - Critical paths
   /          \
  /____________\
 /              \  Integration Tests
/________________\ - Module interactions
                   - Database ops
                   - API workflows

/________________\
                   Unit Tests
                   - Service methods
                   - Utilities
                   - Calculations
```

### Test Files

- **Backend**: `apps/api/src/**/*.spec.ts`
- **Frontend**: `apps/web/src/**/*.test.tsx`
- **E2E**: `apps/web/e2e/**/*.spec.ts`

---

## 📝 Documentation Structure

### For Developers

1. **PHASE_3_QUICK_REFERENCE.md** — Common tasks, file locations, patterns
2. **ARCHITECTURE_GUIDE.md** — System design, protocols, database
3. **API Documentation** — Route definitions, request/response examples

### For DevOps

1. **LAUNCH_CHECKLIST.md** — Pre-launch verification, deployment steps
2. **DEPLOYMENT_GUIDE.md** — Environment setup, CI/CD configuration
3. **DATABASE_SCHEMA_GUIDE.md** — Schema documentation, migrations

### For Product

1. **README_PHASE_3.md** — Feature overview, completion status
2. **PHASE_3_IMPLEMENTATION_SUMMARY.md** — Technical achievements
3. **PHASE_3_COMPLETE_WORK_INDEX.md** — What was built, statistics

---

## 🔄 Development Cycle

### Adding a New Feature

1. **Design Phase**
   - Document feature spec
   - Design API endpoints
   - Create database schema (if needed)

2. **Development Phase**
   - Create feature branch
   - Implement backend (service + controller)
   - Implement frontend (components + hooks)
   - Add tests

3. **Review Phase**
   - Code review on pull request
   - Lint checks pass
   - Tests pass
   - Documentation updated

4. **Deployment Phase**
   - Merge to main
   - CI/CD triggers
   - Staging deployment
   - Production deployment
   - Monitor metrics

---

## ⚙️ Configuration Management

### Environment Variables

**Frontend** (`.env.local`):
- `NEXT_PUBLIC_API_URL` — API endpoint
- `NEXTAUTH_SECRET` — NextAuth encryption key
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` — Stripe public key

**Backend** (`.env`):
- `DATABASE_URL` — PostgreSQL connection
- `JWT_SECRET` — JWT signing key
- `STRIPE_SECRET_KEY` — Stripe private key
- `STRIPE_WEBHOOK_SECRET_*` — Webhook secrets

### Feature Flags

Configured in `packages/config/src/index.ts`:
- `ENABLE_CRYPTO_PAYMENTS` — Enable x402 protocol
- `ENABLE_WORKFLOWS` — Enable workflow builder
- `ENABLE_ANALYTICS` — Enable analytics dashboard

---

## 🆘 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | Change port in `.env` or kill process |
| Database connection failed | Check DATABASE_URL and PostgreSQL running |
| Stripe webhook not working | Verify webhook secret in `.env` |
| NextAuth login failing | Check NEXTAUTH_SECRET is set |
| TypeScript errors | Run `npm run typecheck` |
| Build fails | Delete `node_modules` and `package-lock.json`, reinstall |

### Debug Commands

```bash
# Check database connection
cd apps/api && npx prisma validate

# View database
npx prisma studio

# Check for unused dependencies
npm list

# Watch logs
docker logs container_name -f

# Test API endpoint
curl -X GET http://localhost:4000/agents \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📞 Support & Resources

### Getting Help

1. **Documentation** — Check relevant guide (see Navigation section)
2. **Code Comments** — Inline comments explain complex logic
3. **Type Definitions** — TypeScript provides clear interfaces
4. **Tests** — Test files show expected usage

### Useful Links

- **GitHub**: https://github.com/Rainking6693/Agent-Market
- **Production**: https://swarmsync.ai
- **API**: https://swarmsync-api.up.railway.app
- **Database GUI**: https://neon.tech/app

---

## 📌 Important Notes

### Development Best Practices

1. **Always use TypeScript** — Strict mode enabled
2. **Write tests** — Target 80% coverage
3. **Document changes** — Update relevant docs
4. **Follow naming conventions** — See AGENTS.md
5. **Keep commits small** — Use conventional commits

### Security Reminders

1. **Never commit secrets** — Use environment variables
2. **Validate all input** — Use Zod or class-validator
3. **Check permissions** — Use auth guards
4. **Log sensitive operations** — Audit trail important
5. **Rotate secrets regularly** — Monthly recommended

---

## 🎯 Next Steps

### For New Developers

1. Read `ARCHITECTURE_GUIDE.md` (understand system)
2. Follow setup in `QUICK_START_GUIDE.md`
3. Explore `PHASE_3_QUICK_REFERENCE.md` (file locations)
4. Run `npm run dev` and explore locally
5. Read source code of module you'll be working on

### For Contributors

1. Fork repository
2. Create feature branch (`feat/your-feature`)
3. Follow development workflow above
4. Submit pull request with description
5. Address code review comments

### For Deployment

1. Verify all `LAUNCH_CHECKLIST.md` items
2. Follow `DEPLOYMENT_GUIDE.md`
3. Test in staging first
4. Monitor production metrics post-deploy
5. Keep rollback plan ready

---

**Last Updated**: December 15, 2025  
**Repository Status**: ✅ Production Ready  
**Questions?** See relevant documentation guide above.
