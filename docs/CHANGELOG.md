# Agent-Market Changelog

## 2025-11-12

### Organization & Billing Foundations

- Added `Organization`, `OrganizationMembership`, and new wallet/agent relations so ownership is tracked across the platform.
- Introduced billing primitives (`BillingPlan`, `OrganizationSubscription`, `Invoice`) and seeded the five pricing tiers (Starter → Enterprise) with limits, take rates, and Stripe price IDs.
- Created a Billing module (API + SDK + `/billing` UI) so orgs can view plans, check usage, and upgrade via Stripe checkout.
- Added a Neon-ready analytics helper (`dashboards/neon/orgAnalytics.ts`) and REST endpoints for org-wide ROI summaries and time-series data.

### Quality & ROI Dashboards

- Built the Quality console: agent selector, certification manager, evaluation logging, outcome verification, and ROI trend view.
- Implemented organization-level analytics on the main dashboard (credit meter, quick actions, recent activity, featured agents, GMV trend).
- Added fail-safe data fetching so dashboards render even if the API is unreachable during builds.

### Evaluation Automation

- Added Genesis scenario import tooling (`scripts/import-genesis-scenarios.ts`) and auto-import in the CI workflow so Genesis orchestration scenarios feed the evaluation harness.
- Enhanced the evaluation runner to aggregate every config in `configs/evaluations/`, handle agent-tag lookups, and enforce richer pass criteria.

### Miscellaneous

- Copied the latest logo variants into `apps/web/public/logos` and surfaced them on the dashboard hero.
- Added SDK helpers for billing, analytics, and organization endpoints.
- Updated docs with the new architecture notes, billing stack, and automation references.
