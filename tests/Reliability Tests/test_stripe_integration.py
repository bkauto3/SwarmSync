"""
Stripe Integration Tests
========================

Comprehensive tests for Stripe payment system:
- Payment flow tests (checkout, completion, success)
- Webhook validation and processing
- Refund handling
- Revenue calculation accuracy
- Connect account management
- Payout automation
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

# Skip tests if stripe not available
pytest.importorskip("stripe", reason="stripe library required for payment tests")

from infrastructure.payments.stripe_manager import (
    StripeManager,
    StripeAccount,
    StripeProduct,
    StripeCheckoutSession,
    WebhookEvent,
    PaymentStatus,
)
from infrastructure.payments.pricing_optimizer import (
    PricingOptimizer,
    PricingStrategy,
    PricingRecommendation,
    ABTestResult,
    RevenueOptimization,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def stripe_manager():
    """Stripe manager with mock API key."""
    return StripeManager(api_key="sk_test_mock_key_123")


@pytest.fixture
def pricing_optimizer():
    """Pricing optimizer instance."""
    return PricingOptimizer(default_margin=0.30)


@pytest.fixture
def mock_stripe_account():
    """Mock Stripe account."""
    mock = Mock()
    mock.id = "acct_test_123"
    mock.charges_enabled = True
    mock.payouts_enabled = True
    mock.email = "business@example.com"
    return mock


@pytest.fixture
def mock_stripe_product():
    """Mock Stripe product."""
    mock_product = Mock()
    mock_product.id = "prod_test_123"
    
    mock_price = Mock()
    mock_price.id = "price_test_123"
    
    return mock_product, mock_price


@pytest.fixture
def mock_checkout_session():
    """Mock Stripe checkout session."""
    mock = Mock()
    mock.id = "cs_test_123"
    mock.amount_total = 2900  # $29.00
    mock.currency = "usd"
    mock.payment_intent = "pi_test_123"
    mock.url = "https://checkout.stripe.com/test"
    return mock


@pytest.fixture
def sample_webhook_payload():
    """Sample Stripe webhook payload."""
    return {
        "id": "evt_test_123",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_123",
                "amount": 2900,
                "currency": "usd",
                "status": "succeeded",
                "metadata": {
                    "genesis_business_id": "biz_001"
                }
            }
        }
    }


# ============================================================================
# STRIPE CONNECT TESTS
# ============================================================================

class TestStripeConnect:
    """Tests for Stripe Connect account management."""
    
    @pytest.mark.asyncio
    async def test_create_connect_account(self, stripe_manager, mock_stripe_account):
        """Test creating Stripe Connect account."""
        with patch('stripe.Account.create', return_value=mock_stripe_account):
            account = await stripe_manager.create_connect_account(
                business_id="biz_001",
                business_name="Test Business",
                email="business@example.com"
            )
            
            assert account.account_id == "acct_test_123"
            assert account.business_id == "biz_001"
            assert account.charges_enabled is True
            assert account.payouts_enabled is True
    
    @pytest.mark.asyncio
    async def test_get_account_onboarding_link(self, stripe_manager, mock_stripe_account):
        """Test generating account onboarding link."""
        # Set up account
        stripe_manager._accounts["biz_001"] = StripeAccount(
            account_id="acct_test_123",
            business_id="biz_001",
            business_name="Test Business",
            email="test@example.com"
        )
        
        mock_link = Mock()
        mock_link.url = "https://connect.stripe.com/setup/test"
        
        with patch('stripe.AccountLink.create', return_value=mock_link):
            url = await stripe_manager.get_account_onboarding_link(
                business_id="biz_001",
                return_url="https://example.com/success",
                refresh_url="https://example.com/refresh"
            )
            
            assert "connect.stripe.com" in url
    
    @pytest.mark.asyncio
    async def test_get_business_balance(self, stripe_manager):
        """Test retrieving business Stripe balance."""
        stripe_manager._accounts["biz_001"] = StripeAccount(
            account_id="acct_test_123",
            business_id="biz_001",
            business_name="Test",
            email="test@example.com"
        )
        
        mock_balance = Mock()
        mock_balance.available = [Mock(amount=5000, currency="usd")]
        mock_balance.pending = [Mock(amount=1000, currency="usd")]
        
        with patch('stripe.Balance.retrieve', return_value=mock_balance):
            balance = await stripe_manager.get_business_balance("biz_001")
            
            assert balance['available'][0]['amount'] == 50.0
            assert balance['pending'][0]['amount'] == 10.0


# ============================================================================
# PRODUCT CREATION TESTS
# ============================================================================

class TestProductCreation:
    """Tests for Stripe product and price creation."""
    
    @pytest.mark.asyncio
    async def test_create_product_subscription(self, stripe_manager, mock_stripe_product):
        """Test creating subscription product."""
        mock_product, mock_price = mock_stripe_product
        
        with patch('stripe.Product.create', return_value=mock_product):
            with patch('stripe.Price.create', return_value=mock_price):
                product = await stripe_manager.create_product(
                    business_id="biz_001",
                    name="Premium Plan",
                    description="Full access to all features",
                    price_cents=2900,
                    interval="month"
                )
                
                assert product.product_id == "prod_test_123"
                assert product.price_id == "price_test_123"
                assert product.price_cents == 2900
                assert product.interval == "month"
    
    @pytest.mark.asyncio
    async def test_create_product_one_time(self, stripe_manager, mock_stripe_product):
        """Test creating one-time payment product."""
        mock_product, mock_price = mock_stripe_product
        
        with patch('stripe.Product.create', return_value=mock_product):
            with patch('stripe.Price.create', return_value=mock_price):
                product = await stripe_manager.create_product(
                    business_id="biz_001",
                    name="Digital Product",
                    description="One-time purchase",
                    price_cents=4999,
                    interval="one_time"
                )
                
                assert product.interval == "one_time"
                assert product.price_cents == 4999


# ============================================================================
# CHECKOUT SESSION TESTS
# ============================================================================

class TestCheckoutSessions:
    """Tests for Stripe checkout sessions."""
    
    @pytest.mark.asyncio
    async def test_create_checkout_session(self, stripe_manager, mock_checkout_session):
        """Test creating checkout session."""
        with patch('stripe.checkout.Session.create', return_value=mock_checkout_session):
            session = await stripe_manager.create_checkout_session(
                business_id="biz_001",
                price_id="price_test_123",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
                customer_email="customer@example.com"
            )
            
            assert session.session_id == "cs_test_123"
            assert session.amount_total == 2900
            assert session.status == PaymentStatus.PENDING
            assert session.customer_email == "customer@example.com"


# ============================================================================
# WEBHOOK TESTS
# ============================================================================

class TestWebhooks:
    """Tests for Stripe webhook processing."""
    
    @pytest.mark.asyncio
    async def test_process_webhook_payment_succeeded(self, stripe_manager, sample_webhook_payload):
        """Test processing payment succeeded webhook."""
        payload = json.dumps(sample_webhook_payload).encode()
        signature = "test_signature"
        
        # Mock webhook verification
        mock_event = Mock()
        mock_event.__getitem__ = lambda self, key: sample_webhook_payload.get(key)
        mock_event.get = lambda key, default=None: sample_webhook_payload.get(key, default)
        
        with patch('stripe.Webhook.construct_event', return_value=sample_webhook_payload):
            event = await stripe_manager.process_webhook(payload, signature)
            
            assert event.event_type == "payment_intent.succeeded"
            assert event.business_id == "biz_001"
    
    @pytest.mark.asyncio
    async def test_webhook_signature_verification(self, stripe_manager):
        """Test webhook signature verification."""
        payload = b'{"id": "evt_test", "type": "test"}'
        signature = "t=123,v1=abc123"
        
        # Should return False without proper secret
        is_valid = stripe_manager.verify_webhook_signature(payload, signature)
        # With no secret configured, should warn but not crash
        assert isinstance(is_valid, bool)
    
    @pytest.mark.asyncio
    async def test_handle_checkout_completed(self, stripe_manager):
        """Test checkout.session.completed event handling."""
        # Create test session
        stripe_manager._sessions["cs_test_123"] = StripeCheckoutSession(
            session_id="cs_test_123",
            business_id="biz_001",
            product_id="price_123",
            status=PaymentStatus.PENDING
        )
        
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_status": "paid",
                    "metadata": {"genesis_business_id": "biz_001"}
                }
            },
            "id": "evt_test"
        }
        
        await stripe_manager._handle_checkout_completed(event, "biz_001")
        
        # Session should be marked as succeeded
        assert stripe_manager._sessions["cs_test_123"].status == PaymentStatus.SUCCEEDED
        assert stripe_manager._sessions["cs_test_123"].completed_at is not None
    
    @pytest.mark.asyncio
    async def test_handle_refund(self, stripe_manager):
        """Test refund event handling."""
        # Set up initial revenue
        stripe_manager._revenue_by_business["biz_001"] = 100.0
        
        event = {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_test_123",
                    "amount_refunded": 2900,
                    "currency": "usd",
                    "payment_intent": "pi_test_123",
                    "metadata": {"genesis_business_id": "biz_001"}
                }
            },
            "id": "evt_test"
        }
        
        await stripe_manager._handle_refund(event, "biz_001")
        
        # Revenue should be reduced
        assert stripe_manager._revenue_by_business["biz_001"] == 100.0 - 29.0


# ============================================================================
# REVENUE TRACKING TESTS
# ============================================================================

class TestRevenueTracking:
    """Tests for revenue tracking and calculation."""
    
    @pytest.mark.asyncio
    async def test_track_revenue(self, stripe_manager):
        """Test revenue tracking."""
        await stripe_manager.track_revenue(
            business_id="biz_001",
            amount_cents=2900,
            currency="usd",
            payment_intent_id="pi_test_123"
        )
        
        assert stripe_manager._revenue_by_business["biz_001"] == 29.0
        
        # Add more revenue
        await stripe_manager.track_revenue(
            business_id="biz_001",
            amount_cents=4900,
            currency="usd"
        )
        
        assert stripe_manager._revenue_by_business["biz_001"] == 78.0
    
    @pytest.mark.asyncio
    async def test_get_revenue(self, stripe_manager):
        """Test getting revenue summary."""
        # Track some revenue
        await stripe_manager.track_revenue("biz_001", 5000)
        await stripe_manager.track_revenue("biz_001", 3000)
        await stripe_manager.track_revenue("biz_001", -1000)  # Refund
        
        revenue = await stripe_manager.get_revenue("biz_001")
        
        assert revenue['business_id'] == "biz_001"
        assert revenue['total_revenue'] == 70.0  # 50 + 30 - 10
    
    @pytest.mark.asyncio
    async def test_revenue_accuracy_with_refunds(self, stripe_manager):
        """Test revenue calculation accuracy with refunds."""
        # Scenario: 3 payments, 1 refund
        await stripe_manager.track_revenue("biz_001", 2900)  # $29
        await stripe_manager.track_revenue("biz_001", 9900)  # $99
        await stripe_manager.track_revenue("biz_001", 2900)  # $29
        await stripe_manager.track_revenue("biz_001", -2900)  # -$29 refund
        
        revenue = await stripe_manager.get_revenue("biz_001")
        
        # Expected: 29 + 99 + 29 - 29 = 128
        assert revenue['total_revenue'] == 128.0


# ============================================================================
# PAYOUT TESTS
# ============================================================================

class TestPayouts:
    """Tests for automated payout processing."""
    
    @pytest.mark.asyncio
    async def test_schedule_payout(self, stripe_manager):
        """Test scheduling payout to Connect account."""
        # Set up Connect account
        stripe_manager._accounts["biz_001"] = StripeAccount(
            account_id="acct_test_123",
            business_id="biz_001",
            business_name="Test",
            email="test@example.com",
            payouts_enabled=True
        )
        
        mock_payout = Mock()
        mock_payout.id = "po_test_123"
        mock_payout.status = "pending"
        mock_payout.arrival_date = 1234567890
        
        with patch('stripe.Payout.create', return_value=mock_payout):
            payout = await stripe_manager.schedule_payout(
                business_id="biz_001",
                amount_cents=10000,
                currency="usd"
            )
            
            assert payout['payout_id'] == "po_test_123"
            assert payout['amount'] == 100.0
            assert payout['status'] == "pending"
    
    @pytest.mark.asyncio
    async def test_automatic_payouts(self, stripe_manager):
        """Test automatic payout processing."""
        # Set up businesses with revenue
        stripe_manager._revenue_by_business = {
            "biz_001": 150.0,  # Above threshold ($100)
            "biz_002": 50.0,   # Below threshold
            "biz_003": 200.0,  # Above threshold
        }
        
        # Set up Connect accounts
        for biz_id in ["biz_001", "biz_003"]:
            stripe_manager._accounts[biz_id] = StripeAccount(
                account_id=f"acct_{biz_id}",
                business_id=biz_id,
                business_name=f"Business {biz_id}",
                email=f"{biz_id}@example.com",
                payouts_enabled=True
            )
        
        mock_payout = Mock()
        mock_payout.id = "po_test"
        mock_payout.status = "pending"
        mock_payout.arrival_date = 1234567890
        
        with patch('stripe.Payout.create', return_value=mock_payout):
            payouts = await stripe_manager.process_automatic_payouts()
            
            # Should process 2 payouts (biz_001 and biz_003)
            assert len(payouts) == 2
            
            # Revenue should be reset after payout
            assert stripe_manager._revenue_by_business["biz_001"] == 0.0
            assert stripe_manager._revenue_by_business["biz_003"] == 0.0
            # biz_002 below threshold, should not be paid out
            assert stripe_manager._revenue_by_business["biz_002"] == 50.0


# ============================================================================
# PRICING OPTIMIZER TESTS
# ============================================================================

class TestPricingOptimizer:
    """Tests for pricing optimization."""
    
    @pytest.mark.asyncio
    async def test_cost_plus_pricing(self, pricing_optimizer):
        """Test cost-plus pricing strategy."""
        costs = {
            "llm_costs": 10.0,
            "infrastructure": 5.0,
            "deployment": 2.0
        }
        
        recommendation = await pricing_optimizer.recommend_pricing(
            business_id="biz_001",
            costs=costs,
            current_price=20.0
        )
        
        # Total cost: $17, margin: 30% → price should be $17 / 0.7 = $24.29
        assert recommendation.recommended_price >= 24.0
        assert recommendation.strategy == PricingStrategy.COST_PLUS
    
    @pytest.mark.asyncio
    async def test_competitive_pricing(self, pricing_optimizer):
        """Test competitive pricing strategy."""
        costs = {"total": 10.0}
        competitor_prices = [29.0, 39.0, 49.0, 35.0, 42.0]
        
        recommendation = await pricing_optimizer.recommend_pricing(
            business_id="biz_001",
            costs=costs,
            competitor_prices=competitor_prices,
            current_price=50.0
        )
        
        # Should recommend median competitor price (~39)
        assert recommendation.strategy == PricingStrategy.COMPETITIVE
        assert 35.0 <= recommendation.recommended_price <= 45.0
    
    @pytest.mark.asyncio
    async def test_value_based_pricing(self, pricing_optimizer):
        """Test value-based pricing strategy."""
        costs = {"total": 10.0}
        
        recommendation = await pricing_optimizer.recommend_pricing(
            business_id="biz_001",
            costs=costs,
            customer_value_estimate=200.0,  # High customer value
            current_price=30.0
        )
        
        # Should use value-based pricing (30% of $200 = $60)
        assert recommendation.strategy == PricingStrategy.VALUE_BASED
        assert recommendation.recommended_price >= 50.0


# ============================================================================
# A/B TESTING TESTS
# ============================================================================

class TestABTesting:
    """Tests for pricing A/B testing."""
    
    @pytest.mark.asyncio
    async def test_start_ab_test(self, pricing_optimizer):
        """Test starting A/B test."""
        test_id = await pricing_optimizer.start_ab_test(
            business_id="biz_001",
            variant_a_price=29.0,
            variant_b_price=39.0,
            traffic_split=0.5
        )
        
        assert test_id.startswith("abtest_biz_001")
        assert test_id in pricing_optimizer._active_ab_tests
    
    @pytest.mark.asyncio
    async def test_ab_test_recording(self, pricing_optimizer):
        """Test recording A/B test events."""
        test_id = await pricing_optimizer.start_ab_test(
            business_id="biz_001",
            variant_a_price=29.0,
            variant_b_price=39.0
        )
        
        # Record views
        await pricing_optimizer.record_ab_test_event(test_id, "a", "view")
        await pricing_optimizer.record_ab_test_event(test_id, "a", "view")
        await pricing_optimizer.record_ab_test_event(test_id, "b", "view")
        
        # Record conversions
        await pricing_optimizer.record_ab_test_event(test_id, "a", "conversion", amount=29.0)
        await pricing_optimizer.record_ab_test_event(test_id, "b", "conversion", amount=39.0)
        
        test_data = pricing_optimizer._active_ab_tests[test_id]
        
        assert test_data['variant_a_views'] == 2
        assert test_data['variant_b_views'] == 1
        assert test_data['variant_a_conversions'] == 1
        assert test_data['variant_b_conversions'] == 1
        assert test_data['variant_a_revenue'] == 29.0
        assert test_data['variant_b_revenue'] == 39.0
    
    @pytest.mark.asyncio
    async def test_analyze_ab_test(self, pricing_optimizer):
        """Test A/B test analysis and winner determination."""
        test_id = await pricing_optimizer.start_ab_test(
            business_id="biz_001",
            variant_a_price=29.0,
            variant_b_price=39.0
        )
        
        # Simulate test data: Variant A has better conversion
        test_data = pricing_optimizer._active_ab_tests[test_id]
        test_data['variant_a_views'] = 100
        test_data['variant_b_views'] = 100
        test_data['variant_a_conversions'] = 20  # 20% conversion
        test_data['variant_b_conversions'] = 10  # 10% conversion
        test_data['variant_a_revenue'] = 580.0  # 20 × $29
        test_data['variant_b_revenue'] = 390.0  # 10 × $39
        
        result = await pricing_optimizer.analyze_ab_test(test_id)
        
        # Variant A should win (higher total revenue despite lower price)
        assert result.winner == "a"
        assert result.variant_a_revenue > result.variant_b_revenue


# ============================================================================
# REVENUE OPTIMIZATION TESTS
# ============================================================================

class TestRevenueOptimization:
    """Tests for revenue optimization."""
    
    @pytest.mark.asyncio
    async def test_optimize_revenue_basic(self, pricing_optimizer):
        """Test basic revenue optimization."""
        current_prices = {
            "free": 0.0,
            "standard": 29.0,
            "premium": 99.0
        }
        
        current_users = {
            "free": 1000,
            "standard": 50,
            "premium": 10
        }
        
        costs = {
            "llm_costs": 500.0,
            "infrastructure": 200.0
        }
        
        optimization = await pricing_optimizer.optimize_revenue(
            business_id="biz_001",
            current_prices_by_tier=current_prices,
            current_users_by_tier=current_users,
            costs=costs
        )
        
        # Current revenue: (50 × 29) + (10 × 99) = 1450 + 990 = 2440
        assert optimization.current_monthly_revenue == 2440.0
        assert len(optimization.recommendations) > 0
        assert "free" in optimization.pricing_adjustments
    
    @pytest.mark.asyncio
    async def test_optimize_revenue_underpriced(self, pricing_optimizer):
        """Test optimization when prices don't cover costs."""
        current_prices = {
            "standard": 10.0  # Too low
        }
        
        current_users = {
            "standard": 100
        }
        
        costs = {
            "total": 1500.0  # High costs
        }
        
        optimization = await pricing_optimizer.optimize_revenue(
            business_id="biz_001",
            current_prices_by_tier=current_prices,
            current_users_by_tier=current_users,
            costs=costs
        )
        
        # Should recommend significant price increase
        assert optimization.pricing_adjustments["standard"] > 20.0
        assert any("doesn't cover costs" in rec for rec in optimization.recommendations)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestEndToEndPaymentFlow:
    """End-to-end payment flow tests."""
    
    @pytest.mark.asyncio
    async def test_complete_payment_flow(self, stripe_manager, mock_stripe_account, mock_stripe_product, mock_checkout_session):
        """Test complete payment flow from account creation to payout."""
        # Step 1: Create Connect account
        with patch('stripe.Account.create', return_value=mock_stripe_account):
            account = await stripe_manager.create_connect_account(
                business_id="biz_001",
                business_name="Test Business",
                email="business@example.com"
            )
            assert account.account_id == "acct_test_123"
        
        # Step 2: Create product
        mock_product, mock_price = mock_stripe_product
        with patch('stripe.Product.create', return_value=mock_product):
            with patch('stripe.Price.create', return_value=mock_price):
                product = await stripe_manager.create_product(
                    business_id="biz_001",
                    name="Premium Plan",
                    description="Test",
                    price_cents=2900
                )
                assert product.product_id == "prod_test_123"
        
        # Step 3: Create checkout session
        with patch('stripe.checkout.Session.create', return_value=mock_checkout_session):
            session = await stripe_manager.create_checkout_session(
                business_id="biz_001",
                price_id=product.price_id,
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel"
            )
            assert session.session_id == "cs_test_123"
        
        # Step 4: Simulate payment success (webhook)
        await stripe_manager.track_revenue("biz_001", 2900)
        
        # Step 5: Verify revenue
        revenue = await stripe_manager.get_revenue("biz_001")
        assert revenue['total_revenue'] == 29.0
    
    @pytest.mark.asyncio
    async def test_pricing_optimization_flow(self, pricing_optimizer):
        """Test complete pricing optimization flow."""
        # Step 1: Get pricing recommendation
        costs = {"llm": 10.0, "infra": 5.0}
        competitor_prices = [29.0, 39.0, 49.0]
        
        rec = await pricing_optimizer.recommend_pricing(
            business_id="biz_001",
            costs=costs,
            competitor_prices=competitor_prices,
            current_price=25.0
        )
        
        assert rec.recommended_price > 0
        
        # Step 2: Run A/B test with recommended price
        test_id = await pricing_optimizer.start_ab_test(
            business_id="biz_001",
            variant_a_price=25.0,  # Current
            variant_b_price=rec.recommended_price  # Recommended
        )
        
        assert test_id in pricing_optimizer._active_ab_tests
        
        # Step 3: Simulate test data
        for _ in range(100):
            variant = "a" if random.random() < 0.5 else "b"
            await pricing_optimizer.record_ab_test_event(test_id, variant, "view")
            if random.random() < 0.15:  # 15% conversion
                amount = 25.0 if variant == "a" else rec.recommended_price
                await pricing_optimizer.record_ab_test_event(test_id, variant, "conversion", amount)
        
        # Step 4: Analyze results
        result = await pricing_optimizer.analyze_ab_test(test_id)
        
        assert result.winner in ["a", "b", "tie"]
        assert result.statistical_significance >= 0


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""
    
    @pytest.mark.asyncio
    async def test_stripe_not_enabled(self):
        """Test graceful handling when Stripe not configured."""
        manager = StripeManager(api_key=None)
        
        with pytest.raises(RuntimeError, match="Stripe not enabled"):
            await manager.create_connect_account("biz_001", "Test", "test@example.com")
    
    @pytest.mark.asyncio
    async def test_payout_without_connect_account(self, stripe_manager):
        """Test payout fails without Connect account."""
        with pytest.raises(ValueError, match="No Stripe account found"):
            await stripe_manager.schedule_payout("biz_999", 10000)
    
    @pytest.mark.asyncio
    async def test_revenue_for_nonexistent_business(self, stripe_manager):
        """Test getting revenue for business that doesn't exist."""
        revenue = await stripe_manager.get_revenue("biz_999")
        
        # Should return empty revenue, not crash
        assert revenue['total_revenue'] == 0.0
        assert revenue['business_id'] == "biz_999"
    
    def test_price_sensitivity_insufficient_data(self, pricing_optimizer):
        """Test price sensitivity analysis with insufficient data."""
        result = pricing_optimizer.analyze_price_sensitivity(
            business_id="biz_001",
            price_history=[(29.0, 10)]  # Only 1 data point
        )
        
        # Should return default elasticity
        assert result['elasticity'] == -1.2
        assert result['confidence'] == "low"

