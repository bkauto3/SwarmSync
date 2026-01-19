# Genesis Test Port Plan

## Objectives

- Reuse the most battle-tested Genesis suites so every onboarding agent in Agent Market runs through identical buyer-protection coverage (A2A flows, wallets, ROI, governance).
- Keep execution inside our existing toolchain (`turbo test` → `packages/testkit`) so CI, husky, and Fly deploy gates stay green without custom steps.
- Preserve parity with Genesis test intent notes so future contributors know exactly why a scenario exists.

## Source Suites & Target Mapping

### 1. Agent-to-Agent Commerce & Payments

- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/test_a2a_integration.py` + `test_a2a_security.py` + `test_a2a_advanced.py`: Port to a new `tests/a2a/` Vitest module that hits `apps/api` A2A endpoints (wallet debits, approvals, initiator attribution) through the SDK. Mirror the nine categories already enumerated in these files (single agent, multi-agent, dependency sequencing, parallelism, error traps, breaker toggles, feature flags, OTEL traces, alias mapping).
- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/payments/test_stripe_integration.py`: Translate core cases (checkout, webhook, refund, payouts) into `packages/testkit` python fixtures that call our billing service via `stripe` mocks. This feeds directly into `apps/api/src/modules/billing`.
- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/backend/test_revenue_api.py` + `tests/genesis/test_meta_agent_stripe.py`: Adapt into REST-level regression tests that validate org->invoice->payout ledger rows as we enforce plan limits.

### 2. Org / Wallet Foundations & Ownership Graph

- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/marketplace/test_agent_marketplace.py` + `test_advanced_marketplace.py`: Use as blueprints for our onboarding smoke (agent registration, workflow linking, wallet assignment, approval routing). Target location: `tests/org/marketplace.spec.ts`.
- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/genesis/test_meta_agent_business_creation.py` + `test_meta_agent_edge_cases.py`: Convert into multi-step fixtures that exercise org invites, role propagation, and workflow ownership rules within `apps/api`.
- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/tests_agents_p0_core.yaml` scenarios (now mirrored as `configs/evaluations/genesis-agents-core.json`): tie them to the automated onboarding suite so every agent proves baseline CRUD, logging, and guardrails before publish.

### 3. Quality, Evaluations, and ROI / Analytics

- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/rogue/test_rogue_e2e_integration.py` + `test_rogue_e2e_standalone.py`: Wrap into the `scripts/run-evaluations.ts` workflow as replayable end-to-end checks so new evaluation runners (Temporal, Actions) can be validated without manual payloads.
- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/test_eval_patches.py`, `tests/test_power_sampling.py`, and `tests/test_failure_rationale_tracking.py`: Bring over as targeted unit tests that confirm new metrics tables stay consistent before ROI dashboards query them.
- `Genesis-Rebuild-main/Genesis-Rebuild-main/tests/memory/test_memory_analytics.py` + `tests/backend/test_revenue_api.py`: Use to seed the Neon dashboard queries that now require org-level rollups/stateful analytics.

## Execution Plan

1. **Harness alignment (Day 0)**
   - Extend `packages/testkit` to load `.env` + Stripe keys, spin up API + worker containers, and expose helpers (`withAgent`, `withWallet`, `withOrg`).
   - Add `tests/genesis-port/README.md` documenting how to run `npm run test -- --filter genesis`.
2. **Phase 1 (A2A + Stripe critical path)**
   - Re-implement `test_a2a_integration.py` scenarios in Vitest using the SDK so they run against `apps/api` (no mocks).
   - Mirror Stripe webhook + checkout cases with `stripe-mock` or the official `stripe` npm client so we cover subscription + one-off billing plus take-rate splits.
3. **Phase 2 (Org ownership + marketplace)**
   - Backfill tests for invites, role changes, wallet linking, and catalog publishing drawing from `test_agent_marketplace.py` + meta-agent suites.
   - Ensure these run automatically when new agents onboard (tie into the existing onboarding checklist service).
4. **Phase 3 (Quality & analytics)**
   - Connect `configs/evaluations/*.json` into Temporal/GitHub Action runners and assert outputs flow into `quality_evaluations` + `service_agreements` tables.
   - Add ROI dashboard snapshot tests that query Neon through Prisma and compare against golden aggregates.
5. **Phase 4 (Performance + safety follow-ups)**
   - Select high-value suites (e.g., `tests/test_security_agent.py`, `tests/test_darwin_integration.py`, `tests/test_waltzrl_safety.py`) and add them as nightly jobs instead of pre-commit to catch regressions without blocking contributors.

## Automation Hooks

- `turbo test` should invoke two pipelines: `packages/testkit (pytest)` for python-derived suites + `apps/*` Vitest/Jest for TypeScript. We can add a `genesis` scope in `turbo.json` so CI can run `turbo run test --filter=genesis`.
- Husky pre-push hook: lightweight subset (`A2A smoke`, `Stripe checkout`, `Org invite loops`). Full Genesis parity only in CI to keep local pushes fast.
- Fly deploy gate: require green status from `genesis:a2a`, `genesis:billing`, and `genesis:analytics` pipelines before packaging images.

## Immediate Next Steps

1. Implement the shared fixtures/helpers in `packages/testkit` so both Vitest (via `tsx` helpers) and pytest can bootstrap orgs + wallets with real data.
2. Stand up the new `tests/a2a` and `tests/billing` suites using the file mappings above, starting with the exact acceptance criteria already spelled out in the Genesis files.
3. Wire CI to publish evaluation results + ROI metrics as artifacts so stakeholders can view pass/fail deltas without digging into logs.
