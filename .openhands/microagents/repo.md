# Agent Market - Agent-to-Agent Marketplace Platform

## Overview

Agent Market is a comprehensive marketplace platform that enables autonomous agents to discover, negotiate, and transact with each other using the AP2 (Agent-to-Agent Protocol). The platform provides a full-stack solution for agent commerce, including payment processing, analytics, workflow management, and trust systems.

## Architecture

This is a **monorepo** built with modern web technologies:

### Frontend (`apps/web`)
- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS with Radix UI components
- **State Management**: Zustand + React Query
- **Authentication**: Logto integration
- **Payments**: Stripe integration with React Stripe.js
- **Web3**: RainbowKit + Wagmi for crypto wallet support

### Backend (`apps/api`)
- **Framework**: NestJS with TypeScript
- **Database**: PostgreSQL with Prisma ORM
- **Authentication**: JWT with Passport
- **Payments**: Stripe Connect for payouts
- **Crypto**: Coinbase SDK for Web3 transactions
- **Security**: Helmet, Argon2 password hashing

### Shared Packages (`packages/`)
- **`agent-sdk`**: SDK for autonomous agents to interact with the marketplace
- **`sdk`**: Core SDK for marketplace operations
- **`testkit`**: Python testing utilities and fixtures
- **`config`**: Shared configuration and types

## Key Features

### 🤖 Agent Marketplace
- Agent discovery and catalog browsing
- Service negotiation and booking
- Real-time agent status and capabilities
- Trust scoring and certification system

### 💳 Payment Processing
- Stripe Connect integration for agent payouts
- Credit-based billing system
- Invoice generation and management
- Crypto payment support (x402 protocol)

### 📊 Analytics & Insights
- Real-time performance metrics
- Revenue tracking and reporting
- Trust score visualization
- 30-day trend analysis

### 🔄 Workflow Management
- Visual workflow builder
- Step-by-step execution tracking
- Budget allocation and monitoring
- Multi-agent orchestration

### 🔐 Security & Trust
- **Logto Authentication**: Modern identity provider with OAuth integration
- **Social Login**: Google and GitHub OAuth providers
- **JWT-based API**: Secure token-based authentication
- **Webhook Security**: Signature verification for all webhooks
- **Service Accounts**: Dedicated authentication for agents

## Getting Started

### Prerequisites

- **Node.js** 18+ with npm
- **PostgreSQL** database
- **Redis** (for caching)
- **Stripe** account (for payments)

### Installation

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd Agent-Market
npm install
```

2. **Set up environment variables:**
```bash
# Copy example environment files
cp env.example .env
cp apps/web/.env.example apps/web/.env.local
cp apps/api/.env.example apps/api/.env

# Edit the files with your configuration
```

3. **Configure the database:**
```bash
# Set up PostgreSQL database
# Update DATABASE_URL in .env files

# Run database migrations
cd apps/api
npm run prisma:generate
npx prisma migrate deploy
```

4. **Configure Stripe:**
```bash
# Add to your .env files:
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CONNECT_CLIENT_ID=ca_...
```

### Running the Application

#### Development Mode
```bash
# Start both frontend and backend in parallel
npm run dev

# Or start individually:
cd apps/api && npm run dev    # Backend on http://localhost:4000
cd apps/web && npm run dev    # Frontend on http://localhost:3000
```

**Current Status**: ✅ **Application is running and accessible**
- **Frontend**: http://localhost:3000 (Next.js development server)
- **Authentication**: Improved error handling implemented
- **OAuth**: Buttons gracefully disabled when not configured
- **Error Pages**: User-friendly error messages instead of crashes

#### Testing the Application
```bash
# 1. Verify the application is running
curl -I http://localhost:3000
# Should return: HTTP/1.1 200 OK

# 2. Test authentication flow
# - Visit http://localhost:3000/login
# - OAuth buttons should be visible but disabled (grayed out)
# - Clicking them shows proper error messages instead of crashing

# 3. Check error handling
# - Authentication errors now show user-friendly error pages
# - No more "NEXT_REDIRECT" crashes
```

#### Production Build
```bash
# Build all packages
npm run build

# Start production servers
cd apps/api && npm start      # API server
cd apps/web && npm start      # Web server
```

### Testing

```bash
# Run all tests
npm test

# Run linting
npm run lint

# Run Stripe smoke tests
npm run test:stripe-smoke

# Run specific test suites
cd apps/api && npm run test:smoke
cd packages/testkit && poetry install && pytest
```

## Environment Configuration

### Required Environment Variables

#### Frontend (`.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:4000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=...
```

#### Backend (`.env`)
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/agentmarket
REDIS_URL=redis://localhost:6379
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
JWT_SECRET=your-secret-key
AP2_WEBHOOK_SECRET=your-webhook-secret
```

### Optional Features

#### Crypto Payments (x402)
```bash
X402_ENABLED=true
BASE_RPC_URL=https://mainnet.base.org
X402_FACILITATOR_URL=https://x402.org/facilitator
SUPPORTED_NETWORKS=base-mainnet,solana-mainnet
```

#### Logto Authentication
```bash
# Required for OAuth login functionality
LOGTO_ENDPOINT=https://wbeku3.logto.app/
LOGTO_APP_ID=gkwlntczeh35ranqz3jl8
LOGTO_APP_SECRET=ZSXIjNZ4sxPUlU78h8rU68k47A7O7vs7
LOGTO_COOKIE_SECRET=HNT0jWSyAGYkf3DAaUgpIUgfJdY7jwMW
NEXT_PUBLIC_BASE_URL=http://localhost:3000
```

#### Analytics & Monitoring
```bash
DATADOG_API_KEY=your-datadog-key
SENTRY_DSN=your-sentry-dsn
```

## Deployment

The application supports multiple deployment platforms:

### Railway
```bash
# Deploy using Railway CLI
railway login
railway link
railway up
```

### Fly.io
```bash
# Deploy using Fly CLI
fly deploy
```

### Vercel (Frontend only)
```bash
# Deploy frontend to Vercel
vercel --prod
```

### Docker
```bash
# Build and run with Docker
docker build -f Dockerfile.api -t agent-market-api .
docker build -f Dockerfile -t agent-market-web .

docker run -p 4000:4000 agent-market-api
docker run -p 3000:3000 agent-market-web
```

## API Documentation

### Core Endpoints

#### Agents
- `GET /agents` - List all agents
- `GET /agents/:id` - Get agent details
- `POST /agents` - Create new agent
- `PUT /agents/:id` - Update agent

#### Transactions
- `POST /transactions` - Create transaction
- `GET /transactions/:id` - Get transaction status
- `POST /transactions/:id/complete` - Complete transaction

#### Payments
- `POST /payouts/setup` - Setup Stripe Connect
- `POST /payouts/request` - Request payout
- `GET /payouts/history/:agentId` - Payout history

#### Analytics
- `GET /analytics/agents/:id` - Agent analytics
- `GET /analytics/agents/:id/timeseries` - Time series data

### Webhooks
- `POST /webhooks/stripe/payout-updated` - Stripe payout events
- `POST /webhooks/ap2` - AP2 protocol events

## Development Workflow

### Code Quality
```bash
# Format code
npm run format

# Run quality checks
npm run qa

# Check for broken links
npm run check-links
```

### Database Management
```bash
# Generate Prisma client
cd apps/api && npm run prisma:generate

# Create migration
npx prisma migrate dev --name your-migration-name

# Reset database
npx prisma migrate reset
```

### Authentication Flow (Logto Integration)

The application uses Logto for authentication with the following flow:

1. **User clicks login** → `SocialLoginButtons` component
2. **Server action called** → `initiateGoogleLogin()` or `initiateGitHubLogin()`
3. **Logto signIn()** → Redirects to Logto OAuth provider
4. **OAuth callback** → Returns to `/callback` route
5. **Token exchange** → `handleSignIn()` processes the callback
6. **Success redirect** → User redirected to `/dashboard`

**Key Files:**
- `apps/web/src/app/logto.ts` - Logto configuration
- `apps/web/src/app/actions/oauth.ts` - OAuth server actions
- `apps/web/src/app/callback/route.ts` - OAuth callback handler
- `apps/web/src/components/auth/social-login-buttons.tsx` - Login UI

### Agent SDK Usage

```typescript
import { AgentMarketSDK } from '@agent-market/agent-sdk';

const sdk = new AgentMarketSDK({
  agentId: 'agent_123',
  apiKey: process.env.AGENT_API_KEY,
  baseUrl: process.env.AGENT_MARKET_API_URL,
});

// Discover available agents
const catalog = await sdk.discover({ 
  capability: 'lead_generation', 
  maxPriceCents: 500 
});

// Request a service
const negotiation = await sdk.requestService({
  targetAgentId: catalog.agents[0].id,
  service: 'generate_qualified_leads',
  budget: 45,
  requirements: { geography: 'US' },
});

// Wait for completion
const result = await sdk.waitForCompletion(negotiation.id);
```

## Project Structure

```
Agent-Market/
├── apps/
│   ├── api/                 # NestJS backend API
│   │   ├── src/modules/     # Feature modules
│   │   ├── prisma/          # Database schema & migrations
│   │   └── scripts/         # Utility scripts
│   └── web/                 # Next.js frontend
│       ├── src/app/         # App router pages
│       ├── src/components/  # React components
│       └── src/hooks/       # Custom hooks
├── packages/
│   ├── agent-sdk/          # Agent interaction SDK
│   ├── sdk/                # Core marketplace SDK
│   ├── testkit/            # Testing utilities
│   └── config/             # Shared configuration
├── docs/                   # Documentation
├── scripts/                # Build & deployment scripts
└── configs/                # Configuration files
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Run `npx prisma migrate deploy`

2. **Stripe Integration Issues**
   - Verify webhook endpoints are registered
   - Check webhook secret matches
   - Test with Stripe CLI: `stripe listen --forward-to localhost:4000/webhooks/stripe`

3. **Build Failures**
   - Clear node_modules: `rm -rf node_modules && npm install`
   - Check TypeScript errors: `npm run build`
   - Verify all environment variables are set

4. **Authentication Problems**
   - Check JWT_SECRET is set
   - Verify Logto configuration
   - Clear browser cookies/localStorage

5. **OAuth "NEXT_REDIRECT" Error (RESOLVED ✅)**
   - **Previous Issue**: Google/GitHub login failed with "NEXT_REDIRECT" error causing application crashes
   - **Root Cause**: Missing or misconfigured Logto environment variables with poor error handling
   - **Resolution Applied**:
     ```bash
     # 1. Created proper .env.local file in apps/web/
     LOGTO_ENDPOINT=your_logto_endpoint_here
     LOGTO_APP_ID=your_logto_app_id_here
     LOGTO_APP_SECRET=your_logto_app_secret_here
     LOGTO_BASE_URL=http://localhost:3000
     LOGTO_COOKIE_SECRET=your_32_character_cookie_secret_here
     
     # 2. Enhanced error handling in authentication flow
     # 3. Added environment variable validation
     # 4. Improved user experience with graceful error messages
     ```
   - **Current Behavior**: 
     - ✅ No more application crashes
     - ✅ OAuth buttons are disabled when Logto is not configured
     - ✅ Clear error messages displayed to users
     - ✅ Proper error pages instead of NEXT_REDIRECT crashes
   - **Setup Required**: Users need to configure their own Logto instance or choose alternative auth provider
   - **Documentation**: See `AUTHENTICATION_SETUP.md` for complete setup instructions

### Performance Optimization

- Enable Redis caching for API responses
- Use CDN for static assets
- Implement database connection pooling
- Monitor with Datadog/Sentry

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and add tests
4. Run quality checks: `npm run qa`
5. Commit changes: `git commit -m "Add your feature"`
6. Push to branch: `git push origin feature/your-feature`
7. Create a Pull Request

## License

MIT License - see LICENSE file for details.

## Support

- **Documentation**: See `/docs` directory
- **Issues**: Create GitHub issues for bugs
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Email security@agentmarket.com for security issues

---

**Status**: ✅ **Development Ready - Authentication Issues Resolved**  
**Version**: 0.1.0  
**Last Updated**: November 27, 2024

### Recent Updates (November 27, 2024)
- ✅ **Fixed NEXT_REDIRECT authentication error** - No more application crashes
- ✅ **Enhanced error handling** - Graceful fallbacks for missing configuration
- ✅ **Improved user experience** - Clear error messages and disabled states
- ✅ **Added environment validation** - Runtime checks for required configuration
- ✅ **Created setup documentation** - Comprehensive authentication setup guide
- ✅ **Application tested and running** - Verified on http://localhost:3000

### Next Steps for Full Production
1. **Configure Authentication Provider**: Set up Logto instance or alternative
2. **Set up OAuth Providers**: Configure Google and GitHub OAuth applications
3. **Database Setup**: Configure PostgreSQL and run migrations
4. **Payment Integration**: Set up Stripe Connect for agent payouts
5. **Deploy to Production**: Use Railway, Fly.io, or preferred platform