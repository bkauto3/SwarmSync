from __future__ import annotations

import os
import pytest

from agentmarket_testkit.retry import retry_with_exponential_backoff
from agentmarket_testkit.sdk import AgentMarketSDK

EXPECTED_PLAN_SLUGS = ["starter", "growth", "scale", "pro", "enterprise"]


def _stripe_ready() -> bool:
    required = [
        "STRIPE_SECRET_KEY",
        "GROWTH_SWARM_SYNC_TIER_PRICE_ID",
        "GROWTH_SWARM_SYNC_TIER_PRODUCT_ID",
    ]
    return all(os.getenv(key) for key in required)


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_billing_plans_seeded_and_sorted(agentmarket_sdk: AgentMarketSDK) -> None:
    plans = await agentmarket_sdk.list_billing_plans()
    assert [plan["slug"] for plan in plans] == EXPECTED_PLAN_SLUGS


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_apply_free_plan_sets_subscription(agentmarket_sdk: AgentMarketSDK) -> None:
    subscription = await agentmarket_sdk.apply_billing_plan("starter")
    assert subscription["plan"]["slug"] == "starter"
    assert subscription["status"] == "ACTIVE"

    persisted = await agentmarket_sdk.get_billing_subscription()
    assert persisted is not None
    assert persisted["plan"]["slug"] == "starter"


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_paid_plan_checkout_returns_url_when_stripe_ready(agentmarket_sdk: AgentMarketSDK) -> None:
    if not _stripe_ready():
        pytest.skip("Stripe keys are not configured in this environment")

    session = await agentmarket_sdk.create_checkout_session(
        "growth",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
    )
    assert session["checkoutUrl"]
