&nbsp;Moving Agents To Swarm Sync

1\. Get the backend ready–runs on neon database

&nbsp; npm run prisma:migrate deploy --workspace @agent-market/api npm run dev --workspace @agent-market/api

Stripe keys: add your test STRIPE_SECRET_KEY and NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY to .env / Fly secrets so wallet flows don’t crash when the code touches payments.

Once the API is running locally (or deployed), the pytest suite can hit it.

2\. Stage the agents

copy each agent from the Claude-Code-Clean -Code project (YAML/specs/scripts) into a payload the Nest API expects (see sample_agent_payload in packages/testkit):

{ "name": "...", "description": "...", "categories": \["..."], "tags": \["..."], "pricingModel": "...", "creatorId": "..."}

You can:

Call the API directly (POST /agents).

Use the new SDK in packages/testkit (AgentMarketSDK.create_agent()).

Build a migration script (JSON import) to batch them.

3\. Run the lifecycle suite on each agent

With the API running:

.\\.venv\\Scripts\\activatepytest tests/agents/test_agent_lifecycle.py -q

Once that’s stable, we’ll add more cases (submit/review variations, execution errors) and then bring over the workflow and payments suites from Genesis.

4\. What still needs porting from Genesis

The agents probably rely on integrations (RAG, OCR, etc.). As you migrate each one, map the dependencies:

External services (OpenAI, Anthropic, search APIs). Ensure the new environment has the necessary env vars/mocks.

Artifacts (prompt files, model configs). Copy them into equivalent directories in Agent-Market.

Workflow references (if an agent participates in orchestration flows). Note them so we can port the related workflow tests in the next phase.

5\. Document the migration

Keep a checklist/spreadsheet:

Agent name

Creation status in new API

Tests passing (lifecycle, workflow, payments)

Outstanding integration gaps

Once you have the API + DB live, start with one agent to validate the pipeline, then batch the rest. If you hit schema mismatches or integration blockers, send me a sample payload/log and I’ll help patch the service or fixtures.

&nbsp; genesis.idea.generate → business_idea_generator

&nbsp; genesis.build → builder_agent

&nbsp; genesis.deploy → deploy_agent

&nbsp; genesis.qa → qa_agent

&nbsp; → research_agent

&nbsp; → spec_agent

&nbsp; → architect_agent

&nbsp; → frontend_agent

&nbsp; → backend_agent

&nbsp; → security_agent

&nbsp; → monitoring_agent

&nbsp; → maintenance_agent

&nbsp; → seo_agent

&nbsp; → content_agent

&nbsp; → marketing_agent

&nbsp; → sales_agent

&nbsp; → support_agent

&nbsp; → analyst_agent

&nbsp; → finance_agent

&nbsp; → pricing_agent

&nbsp; → analytics_agent

&nbsp; → email_agent

&nbsp; → billing_agent

&nbsp; → commerce_agent

&nbsp; → darwin_agent

&nbsp; → domain_name_agent

&nbsp; → legal_agent

&nbsp; → onboarding_agent

&nbsp; → genesis_meta_agent
