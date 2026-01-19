# Genesis Test Integration Plan

## Current Status

**Agent-Market Tests (Current):**

- `tests/a2a/test_agent_to_agent_payments.py` - Basic A2A payment tests
- `tests/agents/test_agent_lifecycle.py` - Agent CRUD tests
- `tests/billing/test_billing_plans.py` - Billing plan tests
- `tests/workflows/test_workflow_runs.py` - Workflow execution tests

**Genesis-Rebuild Tests (Source):**

- 150+ comprehensive test files covering:
  - A2A integration, security, advanced scenarios
  - Payments (Stripe, webhooks, refunds)
  - Security (adversarial, agent security, production security)
  - Performance benchmarks
  - Orchestration (comprehensive, e2e, phase1)
  - Memory, RAG, vector databases
  - OCR, vision models
  - And much more...

## Integration Strategy

### Phase 1: Critical Path Tests (Week 1)

**Priority: HIGH - These protect core business logic**

1. **A2A Tests** (from `Genesis-Rebuild/tests/test_a2a_*.py`)
   - `test_a2a_integration.py` → `tests/a2a/test_a2a_integration.py`
   - `test_a2a_security.py` → `tests/a2a/test_a2a_security.py`
   - `test_a2a_advanced.py` → `tests/a2a/test_a2a_advanced.py`
   - **Action**: Port these to use `AgentMarketSDK` from `packages/testkit`

2. **Payment Tests** (from `Genesis-Rebuild/tests/payments/`)
   - Stripe integration tests
   - Webhook validation
   - Refund flows
   - **Action**: Adapt to use our billing service endpoints

3. **Security Tests** (from `Genesis-Rebuild/tests/test_security*.py`)
   - `test_security.py` - Core security
   - `test_security_agent.py` - Agent security
   - `test_production_security.py` - Production hardening
   - **Action**: Port to test our API security endpoints

### Phase 2: Marketplace & Agent Tests (Week 2)

**Priority: MEDIUM - These ensure marketplace quality**

1. **Marketplace Tests** (from `Genesis-Rebuild/tests/marketplace/`)
   - Agent discovery
   - Agent verification
   - Agent reviews
   - **Action**: Map to our agent marketplace endpoints

2. **Agent Lifecycle Tests** (from `Genesis-Rebuild/tests/genesis/`)
   - Agent creation workflows
   - Agent deployment
   - Agent execution
   - **Action**: Enhance existing `test_agent_lifecycle.py`

### Phase 3: Quality & Analytics Tests (Week 3)

**Priority: MEDIUM - These ensure data quality**

1. **Evaluation Tests** (from `Genesis-Rebuild/tests/test_eval*.py`)
   - Evaluation patches
   - Power sampling
   - Failure rationale tracking
   - **Action**: Port to test our quality/evaluation endpoints

2. **Analytics Tests** (from `Genesis-Rebuild/tests/backend/test_revenue_api.py`)
   - ROI calculations
   - Revenue tracking
   - **Action**: Test our analytics endpoints

### Phase 4: Performance & Advanced Features (Week 4+)

**Priority: LOW - These are nice-to-have but not blocking**

1. **Performance Tests** (from `Genesis-Rebuild/tests/test_performance*.py`)
   - Benchmarks
   - Load testing
   - **Action**: Add as nightly CI jobs

2. **Advanced Features** (various files)
   - OCR tests
   - Vision model tests
   - Memory/RAG tests
   - **Action**: Port as features are implemented

## Implementation Steps

### Step 1: Update Test Infrastructure

1. Ensure `packages/testkit` has all necessary fixtures
2. Update `tests/conftest.py` to match Genesis patterns
3. Add test data generators from Genesis

### Step 2: Port Critical Tests

1. Start with A2A integration tests
2. Adapt to use our SDK/API structure
3. Ensure they run in CI

### Step 3: Automate Test Execution

1. Add `turbo test` command for Python tests
2. Integrate with CI/CD pipeline
3. Add test reporting

## File Mapping

### A2A Tests

```
Genesis-Rebuild/tests/test_a2a_integration.py
  → tests/a2a/test_a2a_integration.py

Genesis-Rebuild/tests/test_a2a_security.py
  → tests/a2a/test_a2a_security.py

Genesis-Rebuild/tests/test_a2a_advanced.py
  → tests/a2a/test_a2a_advanced.py
```

### Payment Tests

```
Genesis-Rebuild/tests/payments/test_stripe_integration.py
  → tests/payments/test_stripe_integration.py

Genesis-Rebuild/tests/backend/test_revenue_api.py
  → tests/payments/test_revenue_api.py
```

### Security Tests

```
Genesis-Rebuild/tests/test_security.py
  → tests/security/test_security.py

Genesis-Rebuild/tests/test_security_agent.py
  → tests/security/test_security_agent.py

Genesis-Rebuild/tests/test_production_security.py
  → tests/security/test_production_security.py
```

## Next Actions

1. ✅ Fix TypeScript build error (DONE)
2. 🔄 Start porting A2A integration tests
3. ⏳ Set up test infrastructure enhancements
4. ⏳ Create test execution automation
