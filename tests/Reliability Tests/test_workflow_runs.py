from __future__ import annotations

import json

import httpx
import pytest

from agentmarket_testkit.retry import retry_with_exponential_backoff
from agentmarket_testkit.sdk import AgentMarketSDK
from agentmarket_testkit.utils import unique_agent_name


async def _fund_wallet(
    sdk: AgentMarketSDK,
    user_id: str,
    amount: float,
    reference: str = "workflow-integration",
) -> None:
    wallet = await sdk.ensure_user_wallet(user_id)
    await sdk.fund_wallet(wallet["id"], amount=max(amount, 1.0), reference=reference)


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_workflow_run_happy_path(
    agentmarket_sdk: AgentMarketSDK,
    sample_agent_payload: dict[str, object],
    registered_user: dict[str, str],
) -> None:
    initiator_id = registered_user["id"]

    primary_agent = await agentmarket_sdk.create_agent(sample_agent_payload)

    secondary_payload = {
        "name": unique_agent_name("Workflow QA"),
        "description": "Secondary agent for workflow orchestration tests.",
        "categories": ["workflow", "qa"],
        "tags": ["automation"],
        "pricingModel": "per-run",
        "visibility": "PUBLIC",
        "creatorId": sample_agent_payload["creatorId"],
    }
    secondary_agent = await agentmarket_sdk.create_agent(secondary_payload)

    workflow_payload = {
        "name": "Workflow Integration Happy Path",
        "description": "Covers successful multi-step execution.",
        "creatorId": initiator_id,
        "budget": 25.0,
        "steps": [
            {
                "agentId": primary_agent["id"],
                "input": {"task": "draft-response"},
                "budget": 10.5,
            },
            {
                "agentId": secondary_agent["id"],
                "input": {"task": "qa-review"},
                "budget": 8.25,
            },
        ],
    }
    workflow = await agentmarket_sdk.create_workflow(workflow_payload)

    total_budget = sum(step["budget"] for step in workflow_payload["steps"])
    await _fund_wallet(agentmarket_sdk, initiator_id, total_budget)

    run = await agentmarket_sdk.run_workflow(
        workflow["id"],
        {"initiatorUserId": initiator_id},
    )

    assert run["status"] == "COMPLETED"
    assert pytest.approx(float(run["totalCost"])) == pytest.approx(total_budget)

    context = run.get("context") or {}
    if isinstance(context, str):
        context = json.loads(context)
    steps_log = context.get("steps", [])
    assert len(steps_log) == 2
    for entry in steps_log:
        assert "execution" in entry
        assert "paymentTransaction" in entry


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_workflow_run_fails_when_budget_exceeded(
    agentmarket_sdk: AgentMarketSDK,
    sample_agent_payload: dict[str, object],
    registered_user: dict[str, str],
) -> None:
    initiator_id = registered_user["id"]
    base_agent = await agentmarket_sdk.create_agent(sample_agent_payload)

    workflow_payload = {
        "name": "Workflow Budget Overflow",
        "creatorId": initiator_id,
        "budget": 12.0,
        "steps": [
            {"agentId": base_agent["id"], "input": {"task": "first"}, "budget": 6.0},
            {"agentId": base_agent["id"], "input": {"task": "second"}, "budget": 4.0},
        ],
    }
    workflow = await agentmarket_sdk.create_workflow(workflow_payload)

    await _fund_wallet(agentmarket_sdk, initiator_id, amount=5.0, reference="underfunded-run")

    with pytest.raises(httpx.HTTPStatusError) as exc:
        await agentmarket_sdk.run_workflow(
            workflow["id"],
            {"initiatorUserId": initiator_id},
        )
    assert exc.value.response.status_code == 400

    runs = await agentmarket_sdk.list_workflow_runs(workflow["id"])
    assert runs, "Expected a workflow run record even on failure"
    latest = runs[0]
    assert latest["status"] == "FAILED"
    context = latest.get("context") or {}
    if isinstance(context, str):
        context = json.loads(context)
    error_message = context.get("error", "")
    assert "INSUFFICIENT" in error_message.upper()
