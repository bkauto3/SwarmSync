# QA Readiness Checklist

This document summarises the automated coverage and manual checks required before declaring the AgentMarket MVP launch-ready.

## Automated Coverage

| Layer          | Command                                                    | Purpose                                                                                                          |
| -------------- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Lint           | `npm run lint`                                             | Ensures consistent TypeScript/React style across the monorepo.                                                   |
| Unit (SDK/Web) | `npm test -- --filter @agent-market/sdk,@agent-market/web` | Vitest suites validate the web console scaffold and SDK client.                                                  |
| API e2e        | `npm test -- --filter @agent-market/api`                   | Jest e2e suites exercise `/health` and the auth register/login flow in NestJS.                                   |
| Load smoke     | `npm run test:smoke --workspace @agent-market/api`         | Parallelised calls (configurable with `SMOKE_*` env vars) stress `/health`, `/auth/register`, and `/auth/login`. |

Recommended staging smoke command:

```bash
API_BASE_URL=https://<staging-api>.fly.dev \
SMOKE_PARALLELISM=4 \
SMOKE_ITERATIONS=5 \
npm run test:smoke --workspace @agent-market/api
```

## Manual Verification

1. **Anthropic-inspired console styling** – confirm sidebar, dashboard cards, and Fly.io palette render correctly at `/`.
2. **Agent lifecycle** – create a test agent, see it appear in the list, and observe wallet summary updates.
3. **Collaboration console** – draft a collaboration request between two agents and verify success toast.
4. **Workflow builder** – configure a two-step workflow and trigger `Run Workflow`; ensure recent run log updates.
5. **Trust dashboard** – spot-check trust score and verification status values in agent list.

## Logging & Observability

- **Fly.io dashboards** – review machine restart rates, logs, and recent releases (screenshot for launch doc).
- **API logs** – tail: `fly logs -a <api-app>` during smoke to ensure no error stack traces.

## Sign-off Artifacts

- CI pipeline summary (lint + unit + e2e).
- Smoke test report (console output) attached to the release ticket.
- Updated `docs/deployment-playbook.md` with release notes, if any.
- Confirmed backup/rollback plan (Fly release ID noted).

Once all automated commands pass and manual checks are recorded, update the `qa-launch` task to `completed`.
