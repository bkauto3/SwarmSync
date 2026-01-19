from __future__ import annotations

import json
from decimal import Decimal
from typing import Awaitable, Callable, Dict

import httpx
import pytest

from agentmarket_testkit.retry import retry_with_exponential_backoff
from agentmarket_testkit.sdk import AgentMarketSDK
from agentmarket_testkit.utils import new_uuid


def _decimal_balance(snapshot: Dict[str, object]) -> Decimal:
    value = snapshot.get("balance", "0")
    return Decimal(str(value))


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_agent_to_agent_execution_transfers_funds(
    agentmarket_sdk: AgentMarketSDK,
    approved_agent_factory: Callable[..., Awaitable[Dict[str, object]]],
    wallet_linker: Callable[[str], Awaitable[None]],
    registered_user: Dict[str, str],
    reviewer_user: Dict[str, str],
) -> None:
    seller_agent = await approved_agent_factory(creator_id=registered_user["id"], name_prefix="Seller Agent")
    buyer_agent = await approved_agent_factory(creator_id=reviewer_user["id"], name_prefix="Buyer Agent")

    seller_wallet = await agentmarket_sdk.ensure_agent_wallet(seller_agent["id"])
    buyer_wallet = await agentmarket_sdk.ensure_agent_wallet(buyer_agent["id"])
    await wallet_linker(seller_wallet["id"])
    await wallet_linker(buyer_wallet["id"])

    await agentmarket_sdk.fund_wallet(buyer_wallet["id"], amount=50.0, reference="a2a-seed")
    baseline_seller = await agentmarket_sdk.get_wallet(seller_wallet["id"])
    baseline_buyer = await agentmarket_sdk.get_wallet(buyer_wallet["id"])

    budget = 18.5
    execution = await agentmarket_sdk.execute_agent(
        seller_agent["id"],
        {
            "initiatorId": reviewer_user["id"],
            "initiatorType": "AGENT",
            "initiatorAgentId": buyer_agent["id"],
            "input": json.dumps({"task": "cross-agent purchase", "buyer": buyer_agent["name"]}),
            "jobReference": f"a2a-transfer-{new_uuid()}",
            "budget": budget,
        },
    )

    execution_record = execution["execution"]
    payment_transaction = execution["paymentTransaction"]

    assert execution_record["initiatorType"] == "AGENT"
    assert execution_record["sourceWalletId"] == buyer_wallet["id"]
    assert payment_transaction["status"] == "SETTLED"
    assert pytest.approx(float(payment_transaction["amount"])) == pytest.approx(budget)

    updated_seller = await agentmarket_sdk.get_wallet(seller_wallet["id"])
    updated_buyer = await agentmarket_sdk.get_wallet(buyer_wallet["id"])

    seller_gain = _decimal_balance(updated_seller) - _decimal_balance(baseline_seller)
    buyer_spend = _decimal_balance(baseline_buyer) - _decimal_balance(updated_buyer)

    assert pytest.approx(float(seller_gain)) == pytest.approx(budget)
    assert pytest.approx(float(buyer_spend)) == pytest.approx(budget)


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_agent_initiator_requires_funds(
    agentmarket_sdk: AgentMarketSDK,
    approved_agent_factory: Callable[..., Awaitable[Dict[str, object]]],
    wallet_linker: Callable[[str], Awaitable[None]],
    registered_user: Dict[str, str],
    reviewer_user: Dict[str, str],
) -> None:
    seller_agent = await approved_agent_factory(creator_id=registered_user["id"], name_prefix="Seller Agent")
    buyer_agent = await approved_agent_factory(creator_id=reviewer_user["id"], name_prefix="Buyer Agent")

    buyer_wallet = await agentmarket_sdk.ensure_agent_wallet(buyer_agent["id"])
    await wallet_linker(buyer_wallet["id"])

    with pytest.raises(httpx.HTTPStatusError) as error_info:
        await agentmarket_sdk.execute_agent(
            seller_agent["id"],
            {
                "initiatorId": reviewer_user["id"],
                "initiatorType": "AGENT",
                "initiatorAgentId": buyer_agent["id"],
                "input": json.dumps({"task": "should fail"}),
                "jobReference": f"a2a-denied-{new_uuid()}",
                "budget": 99.0,
            },
        )

    response = error_info.value.response
    assert response.status_code == 400
    assert "Insufficient" in response.text
