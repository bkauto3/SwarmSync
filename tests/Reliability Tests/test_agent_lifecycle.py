from __future__ import annotations

import httpx
import pytest

from agentmarket_testkit.retry import retry_with_exponential_backoff
from agentmarket_testkit.sdk import AgentMarketSDK
from agentmarket_testkit.utils import new_uuid, unique_agent_name


async def _fund_initiator_wallet(
    sdk: AgentMarketSDK,
    initiator_id: str,
    amount: float,
    reference: str = "integration-test",
) -> None:
    wallet = await sdk.ensure_user_wallet(initiator_id)
    await sdk.fund_wallet(wallet["id"], amount=max(amount, 1.0), reference=reference)


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=6)
async def test_agent_lifecycle_happy_path(
    agentmarket_sdk: AgentMarketSDK,
    sample_agent_payload: dict[str, object],
    submission_payload: dict[str, object],
    review_payload: dict[str, object],
    execution_payload: dict[str, object],
) -> None:
    agent = await agentmarket_sdk.create_agent(sample_agent_payload)
    assert agent["status"] == "DRAFT"
    assert agent["creatorId"] == sample_agent_payload["creatorId"]

    pending_agent = await agentmarket_sdk.submit_agent(agent["id"], submission_payload)
    assert pending_agent["status"] == "PENDING"

    review_result = await agentmarket_sdk.review_agent(agent["id"], review_payload)
    assert review_result["agent"]["status"] == review_payload["targetStatus"]
    assert review_result["review"]["status"] == review_payload["reviewStatus"]

    await _fund_initiator_wallet(
        agentmarket_sdk,
        execution_payload["initiatorId"],
        float(execution_payload["budget"]),
    )
    execution_result = await agentmarket_sdk.execute_agent(agent["id"], execution_payload)
    execution = execution_result["execution"]
    payment = execution_result["paymentTransaction"]

    assert execution["status"] == "SUCCEEDED"
    assert execution["initiatorId"] == execution_payload["initiatorId"]
    assert execution["input"] == {"task": "demo run"}
    assert payment["status"] == "SETTLED"
    assert pytest.approx(float(payment["amount"])) == pytest.approx(execution_payload["budget"])

    executions = await agentmarket_sdk.list_executions(agent["id"])
    assert any(item["id"] == execution["id"] for item in executions)

    reviews = await agentmarket_sdk.list_reviews(agent["id"])
    assert any(item["id"] == review_result["review"]["id"] for item in reviews)


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_submit_for_review_creates_needs_work_review(
    agentmarket_sdk: AgentMarketSDK,
    sample_agent_payload: dict[str, object],
    submission_payload: dict[str, object],
) -> None:
    agent = await agentmarket_sdk.create_agent(sample_agent_payload)
    await agentmarket_sdk.submit_agent(agent["id"], submission_payload)

    reviews = await agentmarket_sdk.list_reviews(agent["id"])
    assert any(
        review["status"] == "NEEDS_WORK" and review.get("notes") == submission_payload["notes"]
        for review in reviews
    )


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_review_agent_updates_status_and_persists_review(
    agentmarket_sdk: AgentMarketSDK,
    sample_agent_payload: dict[str, object],
    submission_payload: dict[str, object],
    review_payload: dict[str, object],
) -> None:
    agent = await agentmarket_sdk.create_agent(sample_agent_payload)
    await agentmarket_sdk.submit_agent(agent["id"], submission_payload)

    review_result = await agentmarket_sdk.review_agent(agent["id"], review_payload)
    assert review_result["agent"]["status"] == review_payload["targetStatus"]

    stored_agent = await agentmarket_sdk.get_agent(agent["id"])
    assert stored_agent["status"] == review_payload["targetStatus"]

    reviews = await agentmarket_sdk.list_reviews(agent["id"])
    assert any(item["id"] == review_result["review"]["id"] for item in reviews)


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_execute_agent_requires_valid_json(
    agentmarket_sdk: AgentMarketSDK,
    sample_agent_payload: dict[str, object],
    execution_payload: dict[str, object],
) -> None:
    agent = await agentmarket_sdk.create_agent(sample_agent_payload)

    bad_payload = dict(execution_payload)
    bad_payload["input"] = "not-json:::"
    bad_payload["jobReference"] = f"job-{new_uuid()}"

    await _fund_initiator_wallet(
        agentmarket_sdk,
        bad_payload["initiatorId"],
        float(bad_payload["budget"]),
        reference="invalid-json-case",
    )

    with pytest.raises(httpx.HTTPStatusError) as exc:
        await agentmarket_sdk.execute_agent(agent["id"], bad_payload)
    assert exc.value.response.status_code == 400
    payload = exc.value.response.json()
    message_field = payload.get("message", "")
    if isinstance(message_field, list):
        joined = " ".join(str(part) for part in message_field)
    else:
        joined = str(message_field)
    assert joined, "Expected validation message in response payload"
    assert "JSON" in joined.upper()


@pytest.mark.asyncio
async def test_agent_operations_return_404_for_missing_agent(
    agentmarket_sdk: AgentMarketSDK,
    submission_payload: dict[str, object],
    review_payload: dict[str, object],
    execution_payload: dict[str, object],
) -> None:
    missing_id = new_uuid()

    with pytest.raises(httpx.HTTPStatusError) as get_exc:
        await agentmarket_sdk.get_agent(missing_id)
    assert get_exc.value.response.status_code == 404

    with pytest.raises(httpx.HTTPStatusError) as submit_exc:
        await agentmarket_sdk.submit_agent(missing_id, submission_payload)
    assert submit_exc.value.response.status_code == 404

    with pytest.raises(httpx.HTTPStatusError) as review_exc:
        await agentmarket_sdk.review_agent(missing_id, review_payload)
    assert review_exc.value.response.status_code == 404

    with pytest.raises(httpx.HTTPStatusError) as execute_exc:
        await agentmarket_sdk.execute_agent(missing_id, execution_payload)
    assert execute_exc.value.response.status_code == 404


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_update_agent_mutates_optional_fields(
    agentmarket_sdk: AgentMarketSDK,
    sample_agent_payload: dict[str, object],
) -> None:
    agent = await agentmarket_sdk.create_agent(sample_agent_payload)

    update_payload = {
        "description": "Updated description for integration coverage.",
        "tags": ["automation", "qa"],
        "categories": ["qa", "integration"],
        "pricingModel": "usage-based",
        "visibility": "PRIVATE",
    }

    updated_agent = await agentmarket_sdk.update_agent(agent["id"], update_payload)
    assert updated_agent["description"] == update_payload["description"]
    assert updated_agent["tags"] == update_payload["tags"]
    assert updated_agent["categories"] == update_payload["categories"]
    assert updated_agent["pricingModel"] == update_payload["pricingModel"]
    assert updated_agent["visibility"] == update_payload["visibility"]

    stored_agent = await agentmarket_sdk.get_agent(agent["id"])
    assert stored_agent["description"] == update_payload["description"]
    assert stored_agent["visibility"] == "PRIVATE"


@pytest.mark.asyncio
@retry_with_exponential_backoff(attempts=4)
async def test_list_agents_supports_filters(
    agentmarket_sdk: AgentMarketSDK,
    sample_agent_payload: dict[str, object],
    submission_payload: dict[str, object],
    review_payload: dict[str, object],
) -> None:
    pending_agent = await agentmarket_sdk.create_agent(sample_agent_payload)
    await agentmarket_sdk.submit_agent(pending_agent["id"], dict(submission_payload))

    second_payload = dict(sample_agent_payload)
    second_payload["name"] = unique_agent_name("Workflow QA")
    second_payload["categories"] = ["workflow"]
    second_payload["tags"] = ["automation"]

    approved_agent = await agentmarket_sdk.create_agent(second_payload)
    await agentmarket_sdk.submit_agent(approved_agent["id"], dict(submission_payload))

    review_input = dict(review_payload)
    review_input["notes"] = "Ready for catalogue."
    await agentmarket_sdk.review_agent(approved_agent["id"], review_input)

    pending_list = await agentmarket_sdk.list_agents(status="PENDING")
    assert any(agent["id"] == pending_agent["id"] for agent in pending_list)
    assert all(agent["id"] != approved_agent["id"] for agent in pending_list)

    approved_list = await agentmarket_sdk.list_agents(status="APPROVED")
    assert any(agent["id"] == approved_agent["id"] for agent in approved_list)

    workflow_category = await agentmarket_sdk.list_agents(category="workflow")
    assert any(agent["id"] == approved_agent["id"] for agent in workflow_category)
