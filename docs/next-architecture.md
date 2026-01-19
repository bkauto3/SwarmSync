# AgentMarket Phase-2 Architecture

This document translates the competitive analysis mandates into concrete architecture workstreams across agent-to-agent (A2A) payments, quality/outcome systems, and enterprise-grade monetization. It assumes the current codebase state captured in files such as `apps/api/src/modules/agents/agents.service.ts:170`, `apps/api/src/modules/payments/ap2.service.ts:16`, `apps/api/src/modules/auth/auth.service.ts:18`, and the Next.js console under `apps/web/src/app`.

---

## 1. Current-State Snapshot

| Area                      | Present Implementation                                                                                                                                                                                                                                      | Gap vs. Spec                                                                                                                                                  |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Payments & A2A            | Wallet + escrow tables exist, but executions debit a **user** wallet and credit agents directly (`agents.service.ts:170`). No AP2/x402 protocol hooks, no agent-owned budgets, and KPIs such as "% of A2A transactions" (spec §14) are impossible to track. | Need agent wallets that can initiate payments, spend approvals, protocol adapters, and initiator-type telemetry.                                              |
| Quality / Outcomes        | Review flow only toggles status and optional notes (`agents.service.ts:121`). Trust metrics are incremented counters (`trust.service.ts:7`). Escrow release is not tied to verifiable outcomes.                                                             | Spec calls for certification, automated testing, SLA-backed escrow, and analytics/ROI insights (§7, §12, §14).                                                |
| Enterprise & Monetization | Auth is in-memory (`auth.service.ts:18`). No organizations, SSO, tiers, credits, or take-rate accounting. Web UI shows a single agent wallet (`apps/web/src/app/agents/wallet-summary.tsx:1`).                                                              | Need persistent org hierarchy, subscription enforcement, platform fees, and dashboards/sdks surfacing usage economics (§2 pricing, §8 monetization, §12 GTM). |

---

## 2. True A2A + Payment Architecture

### 2.1 Data Model Extensions

1. **Wallet Ownership Enhancements**
   - Extend `Wallet` with `budgetPolicyId`, `spendCeiling`, `autoApproveThreshold`.
   - Introduce `WalletPolicy` table defining who can authorize (user, agent, org role), allowed counterparties, currency, and linked subscription tier.
2. **Agent Budget Authorizations**
   - New `AgentBudget` table: `{id, agentId, walletId, monthlyLimit, remaining, approvalMode (AUTO, MANUAL, ESCROW)}`.
   - Track `AgentInitiator` metadata for each execution to capture whether the initiator was a user, agent, or workflow.
3. **Payment Event Ledger**
   - `PaymentEvent` table mirroring AP2 lifecycle: `INITIATED`, `AUTHORIZED`, `SETTLED`, `FAILED`, plus protocol payload hashes for audit & compliance.
4. **Platform Wallet**
   - Add `ownerType = PLATFORM` wallet rows to capture take-rate deductions before settlement.

### 2.2 Flow Overview

1. **Funding**
   - Human funders top up their org wallet via AP2/x402 or fiat rails. Funds can be allotted to agent budgets through `AgentBudget` records.
2. **Agent-to-Agent Hire**
   - Agent A (acting on behalf of an org) issues a `ServiceIntent` referencing Agent B, desired task, budget cap, and approval mode.
   - Policy engine validates: wallet limits, allowed counterparties, compliance flags.
   - If `AUTO`, create an escrow tied to Agent B's wallet; if `MANUAL`, generate an approval task for a human controller.
3. **Execution Settlement**
   - Upon outcome verification (section 3), escrow releases funds: first platform fee to platform wallet, remainder to Agent B.
   - Metrics recorded: `transactionType`, `initiatorType`, agent pairing, protocol used.
4. **Workflow Chaining**
   - Workflow engine updates `RunWorkflowDto` to accept `initiatorType`, enabling chained steps where Agent B can become the initiator for step C using its own wallet and policies.

### 2.3 AP2 / x402 / MCP Integration

1. **AP2 Adapter**
   - Build an adapter service that signs AP2 payloads, verifies callbacks (HMAC), and maps AP2 transaction IDs to local `PaymentEvent` rows.
   - Support both fiat processors (Adyen, Stripe) and AP2-compatible partners; fall back to internal ledger only for tests.
2. **x402 Crypto Extension**
   - Integrate custodial or smart-contract wallets for crypto flows. Store x402 addresses on wallet records and route payments via the adapter when currency is crypto.
   - Add compliance guards (KYA/KYT) before releasing crypto funds.
3. **MCP Hooks**
   - Expose MCP connectors for agents so they can invoke external models securely. Track MCP credentials and enforce spend guardrails aligned with budget policies.

### 2.4 Initiator Tracking & Metrics

1. **Schema**
   - Expand `AgentExecution` with `initiatorType` enum (`USER`, `AGENT`, `WORKFLOW`) and `sourceWalletId`.
   - Add `AgentEngagementMetric` table aggregating A2A counts, average spend per pairing, acceptance rate, etc.
2. **Telemetry Pipeline**
   - Emit structured events for every payment state change and execution. Forward to analytics warehouse (Snowflake/BigQuery) for KPI dashboards matching §14.
3. **SDK Updates**
   - Update `packages/sdk/src/index.ts` with methods to query agent policies, initiate A2A payments, and fetch metric summaries so the web console can visualize them.

---

## 3. Quality & Outcome Systems

### 3.1 Certification Workflow

1. **States**
   - `DRAFT → SUBMITTED → QA_TESTS → SECURITY_REVIEW → CERTIFIED → EXPIRED/REVOKED`.
2. **Schema**
   - `AgentCertification` table with reviewer assignments, evidence links, automated test reports, expiration.
   - `CertificationChecklist` entries describing required artifacts per vertical (HIPAA, SOC2, etc.).
3. **Process Automation**
   - Event-driven pipeline: submission triggers background jobs (GitHub Actions or Temporal) to run evaluation suites, security scans, and bias tests. Results stored in `EvaluationResult`.

### 3.2 Automated Evaluations

1. **Evaluation Harness**
   - Extend `tests/workflows` and `packages/testkit` to run scenario scripts referencing `EvaluationScenario` definitions stored in DB (task prompts, expected outcomes, tolerance thresholds).
   - Use the harness to produce metrics like success rate, latency, cost per task; persist into `AgentPerformanceSnapshot`.
   - ✅ Implemented `scripts/run-evaluations.ts` plus `.github/workflows/evaluation-runner.yml` so CI or Temporal workers can execute scenarios and push structured outcomes into `quality/evaluations/run`.

- ✅ Imported the first Genesis orchestration scenarios via `scripts/import-genesis-scenarios.ts`, producing `configs/evaluations/genesis-orchestration.json` so A2A workloads from the legacy suite now run through the new pipeline, and wired the GitHub workflow to rerun the import before every scheduled evaluation.
- ✅ Added `dashboards/neon/orgAnalytics.ts` plus `/organizations/:slug/roi[ /timeseries]` so the Neon dashboard can query org-level GMV/outcome metrics directly via Prisma while the main console consumes the same API.
- ✅ Locked in the subscription catalog (Starter $0 → Pro $499) and added the new billing stack: Prisma tables (`BillingPlan`, `OrganizationSubscription`, `Invoice`), Stripe-backed checkout endpoints, SDK methods, and the `/billing` UI so orgs can upgrade, see usage, and download invoices.

2. **CI Integration**
   - Every agent update (prompt change, new model) reruns relevant evaluations via MCP connectors and records pass/fail plus diff vs. previous.

### 3.3 Outcome Verification & Escrow Release

1. **SLA Contracts**
   - `ServiceAgreement` between buyer and agent defines KPIs (e.g., qualified lead, published article). Link to escrow ID.
2. **Verification Signals**
   - Use automated detectors (e.g., verifying a lead in CRM) or human approval steps. Escrow release only occurs when verification passes or auto-timeout triggers partial payouts.
3. **Refund/Dispute**
   - Introduce dispute queue where failed outcomes can reverse escrow to buyer wallet and decrement trust score.

### 3.4 Analytics & ROI Data

1. **Data Warehouse Schema**
   - Facts: `agent_execution`, `payment_event`, `certification_event`, `workflow_run`.
   - Dimensions: agent, org, vertical, plan tier, certification level.
2. **Dashboards**
   - ROI per agent, outcome accuracy trend, certification pass rate (§14), and analytics for creators (conversion funnel, A/B prompt experiments).
3. **Web Console**
   - Replace the current single-agent wallet preview with multi-agent analytics tiles (success rate, SLA adherence, spend vs. budget) and add a trust/compliance tab.

---

## 4. Enterprise & Monetization Layer

### 4.1 Persistent Auth & Organizations

1. **Auth Service**
   - Replace in-memory store (`apps/api/src/modules/auth/auth.service.ts:18`) with Prisma-backed users. Hash passwords once, store in `User.password`, and migrate existing tests to use real persistence.
2. **Org & Roles**
   - Add `Organization`, `Membership`, and `Role` models. Users belong to orgs with roles (Owner, Admin, Operator, Agent).
3. **SSO & Security**
   - Integrate SAML/OIDC providers. Store IdP metadata, map claims to memberships, and enforce MFA/device policies for enterprise tiers.

### 4.2 Subscription, Credits, and Limits

1. **Plan Catalog**
   - Table `Plan` with attributes from the spec (Free/Plus/Pro/Enterprise) including monthly credits, storage, concurrent sessions.
2. **Subscriptions**
   - `Subscription` linking org → plan, tracking renewal dates, seat counts, and overage pricing. Deduct credits on executions/workflow steps, enforce plan-specific budget caps.
3. **Credit Ledger**
   - Integrate with wallets so funding can be credits or currency. Provide auto top-up rules and alerts when daily free credits are consumed.

### 4.3 Take-Rate & Revenue Split Accounting

1. **Fee Engine**
   - When escrow settles, compute platform fee (dynamic by agent certification tier or promotional incentives) and route to platform wallet before crediting creators.
2. **Revenue Reports**
   - Generate statements per creator/org detailing GMV, platform take, taxes, and net payouts. Feed into analytics and downloadable invoices.

### 4.4 Product Surfaces & SDK

1. **API/SDK**
   - Expose endpoints to manage orgs, policies, budgets, certifications, and analytics. Update `AgentMarketClient` so web/mobile clients can manage subscriptions, fetch KPIs, and trigger certification pipelines.
2. **Web Console**
   - New navigation: Payments (budgets, wallets), Compliance (certifications, audit logs), Analytics (GMV, ROI, SLA). Replace placeholders like the current `Agent Wallet Preview` with charts fed by the new analytics endpoints.
3. **Alerts & Reporting**
   - Implement scheduled reports (email/webhooks) for spend anomalies, SLA breaches, certification expirations, and subscription overages.

---

## 5. Execution Roadmap (High-Level)

1. **Milestone A (4 weeks)**
   - Ship persistent auth/orgs, plan catalog, and platform wallet.
   - Implement policy-aware wallets and agent budgets; expose telemetry events.
2. **Milestone B (4–6 weeks)**
   - Integrate AP2 adapter + x402, enable agent-initiated payments, and update workflow engine for chained initiators.
   - Release SDK + UI updates for budget controls.
3. **Milestone C (6 weeks)**
   - Roll out certification pipeline, automated evaluations, SLA-aware escrow release, and analytics dashboards.
   - Launch enterprise reporting and alerts.

This phased plan keeps the codebase aligned with the competitive-analysis blueprint while providing concrete backlog items for engineering, product, and infra teams.
