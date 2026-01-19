# Deployment Playbook – AgentMarket MVP

This playbook covers the steps to promote the AgentMarket MVP to a Fly.io environment. It assumes a fresh workstation with the repository already cloned.

## 1. Prerequisites

1. Install Node.js 20+ and npm 10+ (project uses `npm@11.6.2` via `packageManager`).
2. Install the Fly CLI and authenticate: `fly auth login`.
3. Provision managed Postgres for the API (Fly Postgres or external cluster). Capture the connection URL.
4. Ensure Stripe sandbox keys are available if payments are exercised (not required for base deployment).

## 2. Environment Configuration

Create `.env` files for each app (copy from `env.example`):

```bash
cp env.example .env
```

Populate at minimum:

```
DATABASE_URL=postgresql://<user>:<password>@<host>/<database>
JWT_SECRET=<strong-random-string>
NEXT_PUBLIC_API_URL=https://<api-app>.fly.dev
STRIPE_SECRET_KEY=sk_test_xxx              # server-side secret
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
```

For Fly, configure secrets:

```bash
fly secrets set \
  DATABASE_URL=... \
  JWT_SECRET=... \
  STRIPE_SECRET_KEY=... \
  STRIPE_WEBHOOK_SECRET=optional_if_used

# Web app (run in apps/web)
fly secrets set \
  NEXT_PUBLIC_API_URL=https://<api-app>.fly.dev \
  NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
```

## 3. Install & Build

```bash
npm install
npm run build              # turbo builds api + web + sdk
```

## 4. Database Migration

```bash
npm run prisma:generate --workspace @agent-market/api
DATABASE_URL=... npm run prisma:migrate deploy --workspace @agent-market/api
```

_During CI/CD the migration command should run before the app is started._

## 5. Quality Gates

```bash
npm run lint
npm test                              # unit + e2e suites
npm run test:smoke --workspace @agent-market/api \
  API_BASE_URL=https://<staging-api>.fly.dev \
  SMOKE_PARALLELISM=4 SMOKE_ITERATIONS=5
```

The smoke script exercises `/health`, `POST /auth/register`, and `POST /auth/login` with light concurrency. Failures indicate the API is not ready for traffic.

## 6. Deploy API (NestJS)

```bash
cd apps/api
fly launch --no-deploy   # first time only, configure image & app name
fly deploy
```

Key runtime variables:

```
DATABASE_URL
JWT_SECRET
NODE_ENV=production
PORT=8080
```

Expose port 8080 internally and let Fly handle HTTPS edge termination.

## 7. Deploy Web (Next.js)

Configure `NEXT_PUBLIC_API_URL` to the deployed API URL and deploy the web app (Edge or Node runtime):

```bash
cd ../web
fly launch --no-deploy
fly deploy
```

For a slimmer deployment, build locally and ship static assets via Fly’s CDN:

```bash
npm run build --workspace @agent-market/web
fly deploy --remote-only
```

## 8. Post-Deployment Validation

1. Run `npm run test:smoke` against the production API.
2. Hit the web console `/agents` page and confirm the Anthropic-inspired layout loads with Fly.io palette.
3. Validate new agent creation workflow end-to-end (create → list → wallet summary).
4. Capture Fly metrics dashboards (machines, logs, and release activity) for the launch log.

## 9. Rollback

Fly CLI keeps release history. Use `fly releases` to identify the previous stable release and run:

```bash
fly releases --status failed     # double-check
fly deploy --image <previous-image>
```

For urgent rollback, scale the problematic deployment to zero and redeploy the last known good image.

## 10. Automation Hooks

- Add the commands above to GitHub Actions (CI runs `npm run lint`, `npm test`, `npm run test:smoke` pointing at a staging API).
- Trigger Fly deploy via `fly deploy --strategy immediate` once CI passes and migrations succeed.

---

**Artifacts to archive after each deploy**

- CI build log & smoke test output
- Prisma migration version
- Fly release ID and machine allocation
- Manual verification checklist results (see `docs/qa-readiness.md`)
