"""
Test suite for Genesis Meta-Agent Stripe Integration.

Tests real Stripe API integration for autonomous business billing:
- Customer creation
- Subscription creation with $5/month fixed pricing
- Subscription cancellation on business takedown
- Error handling and retry logic
- Metrics tracking

Author: Thon (Python Specialist)
Date: November 3, 2025
"""

import asyncio
import os
import pytest
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime

# Import Genesis Meta-Agent
from infrastructure.genesis_meta_agent import (
    GenesisMetaAgent,
    BusinessRequirements,
    BusinessType
)


# ============================================================================
# FIXTURES
# ============================================================================

def create_test_requirements(**kwargs):
    """Helper to create BusinessRequirements with defaults."""
    req = object.__new__(BusinessRequirements)
    req.name = kwargs.get("name", "TestSaaS Pro")
    req.description = kwargs.get("description", "Professional SaaS testing application")
    req.business_type = kwargs.get("business_type", "saas")
    req.target_audience = kwargs.get("target_audience", "software developers")
    req.monetization = kwargs.get("monetization", "subscription")
    req.mvp_features = kwargs.get("mvp_features", ["user authentication", "dashboard", "API access"])
    req.tech_stack = kwargs.get("tech_stack", ["python", "fastapi", "postgresql"])
    req.success_metrics = kwargs.get("success_metrics", {"users": "1000", "revenue": "$5000"})
    req.estimated_time = kwargs.get("estimated_time", "< 8 hours")
    return req


@pytest.fixture
def business_requirements():
    """Standard business requirements for testing."""
    return create_test_requirements()


@pytest.fixture
def stripe_customer_response():
    """Mock Stripe Customer.create() response."""
    return {
        "id": "cus_test_12345",
        "object": "customer",
        "name": "TestSaaS Pro",
        "description": "Genesis autonomous business: Professional SaaS testing application",
        "metadata": {
            "business_id": "test-business-123",
            "business_type": "saas",
            "genesis_created": datetime.now().isoformat(),
            "autonomous": "true"
        },
        "created": 1699000000
    }


@pytest.fixture
def stripe_subscription_response():
    """Mock Stripe Subscription.create() response."""
    return {
        "id": "sub_test_67890",
        "object": "subscription",
        "customer": "cus_test_12345",
        "status": "active",
        "items": {
            "data": [{
                "price": {
                    "unit_amount": 500,  # $5.00 USD
                    "currency": "usd",
                    "recurring": {"interval": "month"}
                }
            }]
        },
        "metadata": {
            "business_id": "test-business-123",
            "business_name": "TestSaaS Pro",
            "business_type": "saas"
        },
        "created": 1699000000,
        "current_period_start": 1699000000,
        "current_period_end": 1701592000
    }


# ============================================================================
# UNIT TESTS: Stripe Customer Creation
# ============================================================================

@pytest.mark.asyncio
async def test_create_stripe_customer_success(business_requirements, stripe_customer_response):
    """Test successful Stripe customer creation."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    loop = asyncio.get_running_loop()

    with patch('stripe.Customer.create', return_value=stripe_customer_response):
        # Execute
        customer = await meta_agent._create_stripe_customer(
            business_id="test-business-123",
            requirements=business_requirements,
            loop=loop
        )

        # Verify
        assert customer is not None
        assert customer["id"] == "cus_test_12345"
        assert customer["name"] == "TestSaaS Pro"
        assert customer["metadata"]["business_type"] == "saas"
        assert customer["metadata"]["autonomous"] == "true"


@pytest.mark.asyncio
async def test_create_stripe_customer_with_long_name(stripe_customer_response):
    """Test customer creation truncates name to Stripe's 100-char limit."""
    # Setup
    long_name = "A" * 150  # 150 characters
    requirements = create_test_requirements(
        name=long_name,
        description="Test",
        business_type="saas",
        target_audience="developers",
        mvp_features=["auth"],
        tech_stack=["python"],
        success_metrics={"users": "100"}
    )

    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    loop = asyncio.get_running_loop()

    with patch('stripe.Customer.create', return_value=stripe_customer_response) as mock_create:
        # Execute
        await meta_agent._create_stripe_customer(
            business_id="test-123",
            requirements=requirements,
            loop=loop
        )

        # Verify name was truncated to 100 chars
        call_args = mock_create.call_args[1]
        assert len(call_args["name"]) == 100


@pytest.mark.asyncio
async def test_create_stripe_customer_failure():
    """Test customer creation handles API errors gracefully."""
    # Setup
    requirements = create_test_requirements(
        name="FailTest",
        description="Test"
    )

    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    loop = asyncio.get_running_loop()

    with patch('stripe.Customer.create', side_effect=Exception("Stripe API error")):
        # Execute
        customer = await meta_agent._create_stripe_customer(
            business_id="test-123",
            requirements=requirements,
            loop=loop
        )

        # Verify returns None on failure
        assert customer is None


# ============================================================================
# UNIT TESTS: Stripe Subscription Creation
# ============================================================================

@pytest.mark.asyncio
async def test_create_stripe_subscription_success(stripe_subscription_response):
    """Test successful Stripe subscription creation with $5/month pricing."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    loop = asyncio.get_running_loop()

    with patch('stripe.Subscription.create', return_value=stripe_subscription_response):
        # Execute
        subscription = await meta_agent._create_stripe_subscription(
            customer_id="cus_test_12345",
            business_id="test-business-123",
            business_type="saas",
            business_name="TestSaaS Pro",
            loop=loop
        )

        # Verify
        assert subscription is not None
        assert subscription["id"] == "sub_test_67890"
        assert subscription["status"] == "active"
        assert subscription["customer"] == "cus_test_12345"

        # Verify pricing is $5/month
        price_data = subscription["items"]["data"][0]["price"]
        assert price_data["unit_amount"] == 500  # $5.00 in cents
        assert price_data["currency"] == "usd"
        assert price_data["recurring"]["interval"] == "month"


@pytest.mark.asyncio
async def test_create_stripe_subscription_correct_metadata(stripe_subscription_response):
    """Test subscription includes correct metadata."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    loop = asyncio.get_running_loop()

    with patch('stripe.Subscription.create', return_value=stripe_subscription_response) as mock_create:
        # Execute
        await meta_agent._create_stripe_subscription(
            customer_id="cus_test_12345",
            business_id="test-business-123",
            business_type="saas",
            business_name="TestSaaS Pro",
            loop=loop
        )

        # Verify metadata passed to Stripe
        call_args = mock_create.call_args[1]
        assert call_args["metadata"]["business_id"] == "test-business-123"
        assert call_args["metadata"]["business_name"] == "TestSaaS Pro"
        assert call_args["metadata"]["business_type"] == "saas"


@pytest.mark.asyncio
async def test_create_stripe_subscription_failure():
    """Test subscription creation handles API errors gracefully."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    loop = asyncio.get_running_loop()

    with patch('stripe.Subscription.create', side_effect=Exception("Stripe API error")):
        # Execute
        subscription = await meta_agent._create_stripe_subscription(
            customer_id="cus_test_12345",
            business_id="test-123",
            business_type="saas",
            business_name="TestSaaS Pro",
            loop=loop
        )

        # Verify returns None on failure
        assert subscription is None


# ============================================================================
# INTEGRATION TESTS: Full Payment Flow
# ============================================================================

@pytest.mark.asyncio
async def test_maybe_create_stripe_payment_full_flow(
    business_requirements,
    stripe_customer_response,
    stripe_subscription_response
):
    """Test complete Stripe payment flow: customer + subscription creation."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    with patch('stripe.Customer.create', return_value=stripe_customer_response), \
         patch('stripe.Subscription.create', return_value=stripe_subscription_response):

        # Execute
        subscription_id = await meta_agent._maybe_create_stripe_payment(
            business_id="test-business-123",
            requirements=business_requirements
        )

        # Verify
        assert subscription_id == "sub_test_67890"

        # Verify deployment record updated
        record = meta_agent._deployment_records.get("test-business-123")
        assert record is not None
        assert record["stripe_customer_id"] == "cus_test_12345"
        assert record["stripe_subscription_id"] == "sub_test_67890"
        assert record["subscription_status"] == "active"
        assert record["monthly_price_usd"] == 5.0


@pytest.mark.asyncio
async def test_maybe_create_stripe_payment_retry_on_failure(
    business_requirements,
    stripe_customer_response,
    stripe_subscription_response
):
    """Test payment creation retries on transient failures."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    # Simulate failure on first attempt, success on second
    customer_call_count = 0
    def customer_create_side_effect(*args, **kwargs):
        nonlocal customer_call_count
        customer_call_count += 1
        if customer_call_count == 1:
            raise Exception("Transient network error")
        return stripe_customer_response

    with patch('stripe.Customer.create', side_effect=customer_create_side_effect), \
         patch('stripe.Subscription.create', return_value=stripe_subscription_response):

        # Execute
        subscription_id = await meta_agent._maybe_create_stripe_payment(
            business_id="test-business-123",
            requirements=business_requirements
        )

        # Verify retry succeeded
        assert subscription_id == "sub_test_67890"
        assert customer_call_count == 2  # Failed once, succeeded on retry


@pytest.mark.asyncio
async def test_maybe_create_stripe_payment_max_retries_exceeded(business_requirements):
    """Test payment creation fails after max retries."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    with patch('stripe.Customer.create', side_effect=Exception("Persistent API error")):
        # Execute
        subscription_id = await meta_agent._maybe_create_stripe_payment(
            business_id="test-business-123",
            requirements=business_requirements
        )

        # Verify returns None after 3 retries
        assert subscription_id is None


@pytest.mark.asyncio
async def test_maybe_create_stripe_payment_disabled():
    """Test payment creation skipped when Stripe disabled."""
    # Setup (Stripe disabled)
    meta_agent = GenesisMetaAgent(
        enable_payments=False
    )

    requirements = create_test_requirements(name="Test")

    # Execute
    subscription_id = await meta_agent._maybe_create_stripe_payment(
        business_id="test-123",
        requirements=requirements
    )

    # Verify skipped
    assert subscription_id is None


# ============================================================================
# INTEGRATION TESTS: Subscription Cancellation
# ============================================================================

@pytest.mark.asyncio
async def test_takedown_business_cancels_subscription():
    """Test business takedown cancels Stripe subscription."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    # Create deployment record with subscription
    business_id = "test-business-123"
    meta_agent._deployment_records[business_id] = {
        "business_id": business_id,
        "business_name": "TestBusiness",
        "business_type": "saas",
        "stripe_customer_id": "cus_test_12345",
        "stripe_subscription_id": "sub_test_67890"
    }

    with patch('stripe.Subscription.cancel', return_value={"status": "canceled"}), \
         patch('stripe.Customer.delete', return_value={"deleted": True}):

        # Execute
        result = await meta_agent.takedown_business(
            business_id=business_id,
            reason="test_cleanup"
        )

        # Verify
        assert result["stripe"] == "cancelled"


@pytest.mark.asyncio
async def test_takedown_business_handles_subscription_cancel_error():
    """Test takedown handles subscription cancellation errors gracefully."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    business_id = "test-business-123"
    meta_agent._deployment_records[business_id] = {
        "business_id": business_id,
        "business_name": "TestBusiness",
        "stripe_subscription_id": "sub_test_67890"
    }

    with patch('stripe.Subscription.cancel', side_effect=Exception("Stripe API error")):
        # Execute
        result = await meta_agent.takedown_business(
            business_id=business_id,
            reason="test_cleanup"
        )

        # Verify error recorded
        assert "error" in result["stripe"]


@pytest.mark.asyncio
async def test_takedown_business_legacy_payment_intent():
    """Test takedown handles legacy payment_intent records (backward compatibility)."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    business_id = "test-business-legacy"
    meta_agent._deployment_records[business_id] = {
        "business_id": business_id,
        "business_name": "LegacyBusiness",
        "stripe_payment_intent_id": "pi_test_12345"  # Old format
    }

    with patch('stripe.PaymentIntent.cancel', return_value={"status": "canceled"}):
        # Execute
        result = await meta_agent.takedown_business(
            business_id=business_id,
            reason="test_cleanup"
        )

        # Verify legacy intent was cancelled
        assert result["stripe"] == "cancelled_legacy"


# ============================================================================
# METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_stripe_metrics_recorded_on_success(
    business_requirements,
    stripe_customer_response,
    stripe_subscription_response
):
    """Test Stripe success metrics are recorded correctly."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    with patch('stripe.Customer.create', return_value=stripe_customer_response), \
         patch('stripe.Subscription.create', return_value=stripe_subscription_response), \
         patch('infrastructure.genesis_meta_agent.stripe_subscriptions_total') as mock_sub_metric, \
         patch('infrastructure.genesis_meta_agent.stripe_revenue_total') as mock_rev_metric:

        # Execute
        await meta_agent._maybe_create_stripe_payment(
            business_id="test-business-123",
            requirements=business_requirements
        )

        # Verify metrics recorded
        mock_sub_metric.labels.assert_called_with(status="success")
        mock_sub_metric.labels().inc.assert_called_once()

        mock_rev_metric.labels.assert_called_with(business_type="saas")
        mock_rev_metric.labels().inc.assert_called_with(5.0)


@pytest.mark.asyncio
async def test_stripe_metrics_recorded_on_failure(business_requirements):
    """Test Stripe failure metrics are recorded correctly."""
    # Setup
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    with patch('stripe.Customer.create', side_effect=Exception("API error")), \
         patch('infrastructure.genesis_meta_agent.stripe_subscriptions_total') as mock_metric:

        # Execute (will fail all retries)
        await meta_agent._maybe_create_stripe_payment(
            business_id="test-business-123",
            requirements=business_requirements
        )

        # Verify failure metric recorded
        mock_metric.labels.assert_called_with(status="failed")
        mock_metric.labels().inc.assert_called_once()


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_record_stripe_subscription_creates_new_record():
    """Test _record_stripe_subscription creates new deployment record if missing."""
    # Setup
    meta_agent = GenesisMetaAgent(enable_payments=True)

    # Execute
    meta_agent._record_stripe_subscription(
        business_id="new-business-123",
        customer_id="cus_test_12345",
        subscription_id="sub_test_67890",
        business_name="NewBusiness"
    )

    # Verify
    record = meta_agent._deployment_records["new-business-123"]
    assert record is not None
    assert record["stripe_customer_id"] == "cus_test_12345"
    assert record["stripe_subscription_id"] == "sub_test_67890"
    assert record["monthly_price_usd"] == 5.0


@pytest.mark.asyncio
async def test_record_stripe_subscription_updates_existing_record():
    """Test _record_stripe_subscription updates existing deployment record."""
    # Setup
    meta_agent = GenesisMetaAgent(enable_payments=True)

    # Pre-existing record
    meta_agent._deployment_records["existing-123"] = {
        "business_id": "existing-123",
        "business_name": "ExistingBusiness",
        "vercel_url": "https://existing.vercel.app"
    }

    # Execute
    meta_agent._record_stripe_subscription(
        business_id="existing-123",
        customer_id="cus_test_99999",
        subscription_id="sub_test_88888",
        business_name="ExistingBusiness"
    )

    # Verify original data preserved
    record = meta_agent._deployment_records["existing-123"]
    assert record["vercel_url"] == "https://existing.vercel.app"

    # Verify Stripe data added
    assert record["stripe_customer_id"] == "cus_test_99999"
    assert record["stripe_subscription_id"] == "sub_test_88888"


# ============================================================================
# REAL API TESTS (Conditional - requires test keys)
# ============================================================================

@pytest.mark.skipif(
    not os.getenv("STRIPE_SECRET_KEY") or "test" not in os.getenv("STRIPE_SECRET_KEY", "").lower(),
    reason="Real Stripe test key not configured"
)
@pytest.mark.asyncio
async def test_real_stripe_customer_creation():
    """
    Test REAL Stripe customer creation (requires test key).

    WARNING: This creates a real Stripe customer object in test mode.
    Cleanup happens automatically via Stripe test mode retention policies.
    """
    # Setup with REAL Stripe test key
    meta_agent = GenesisMetaAgent(
        enable_payments=True,
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY")
    )

    requirements = create_test_requirements(
        name="Real Test Business",
        description="Testing real Stripe integration",
        mvp_features=["auth", "api"]
    )

    loop = asyncio.get_running_loop()

    # Execute REAL API call
    customer = await meta_agent._create_stripe_customer(
        business_id=f"test-real-{datetime.now().timestamp()}",
        requirements=requirements,
        loop=loop
    )

    # Verify
    assert customer is not None
    assert customer["id"].startswith("cus_")
    assert customer["object"] == "customer"

    # Cleanup (delete test customer)
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        stripe.Customer.delete(customer["id"])
    except Exception as e:
        print(f"Warning: Failed to cleanup test customer: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
