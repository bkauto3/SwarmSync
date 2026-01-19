"""
AgentOccam integration tests.

These tests exercise the lightweight AgentOccam search client that was
introduced for test-time branching. The real AgentOccam workflow calls
into hosted models; here we rely on deterministic stand-ins so the
suite runs inside the sandbox.
"""

import asyncio
import pytest

from infrastructure.agentoccam_client import AgentOccamClient, AgentOccamConfig


@pytest.mark.asyncio
async def test_agent_occam_selects_highest_scoring_branch():
    """Best candidate should be returned when evaluator is provided."""
    responses = iter(
        [
            "Quick outline of the solution.",
            "Detailed plan with clear milestones and owners.",
            "Medium depth response with partial coverage.",
        ]
    )

    async def mock_model(prompt, temperature, context):
        return next(responses)

    score_table = {
        "Quick outline of the solution.": 0.42,
        "Detailed plan with clear milestones and owners.": 0.93,
        "Medium depth response with partial coverage.": 0.71,
    }

    async def mock_evaluator(response, context, branch):
        return score_table[response]

    config = AgentOccamConfig(
        max_branches=3,
        temperatures=(0.2, 0.5, 0.8),
        rerank_top_k=2,
        trace_candidates=True,
    )
    client = AgentOccamClient(config)

    result = await client.run_search(
        prompt="Draft a GTM plan.",
        model_fn=mock_model,
        evaluator_fn=mock_evaluator,
    )

    assert result["best_response"] == "Detailed plan with clear milestones and owners."
    assert result["telemetry"]["total_candidates"] == 3
    # Ensure reranked list keeps the top-scoring candidate first
    assert result["candidates"][0]["response"] == result["best_response"]
    expected_score = 0.93 + config.exploration_bonus / 2  # branch index 1
    assert result["candidates"][0]["score"] == pytest.approx(expected_score)


@pytest.mark.asyncio
async def test_agent_occam_handles_branch_failures_and_baseline():
    """Failures should not abort search; baseline is incorporated."""
    call_counter = {"count": 0}

    async def flaky_model(prompt, temperature, context):
        if call_counter["count"] < 2:
            call_counter["count"] += 1
            raise RuntimeError("LLM transient error")
        return "Recovered branch solution with solid reasoning."

    async def baseline_model(prompt, context):
        return "Baseline deterministic response."

    async def evaluator(response, context, branch):
        return 0.88 if "Recovered" in response else 0.4

    config = AgentOccamConfig(
        max_branches=3,
        temperatures=(0.3, 0.6, 0.9),
        baseline_weight=0.05,
        trace_candidates=True,
    )
    client = AgentOccamClient(config)

    result = await client.run_search(
        prompt="Summarize deployment blockers.",
        model_fn=flaky_model,
        evaluator_fn=evaluator,
        baseline_fn=baseline_model,
    )

    assert result["best_response"] == "Recovered branch solution with solid reasoning."
    assert result["telemetry"]["baseline_included"] is True

    baseline_candidates = [
        c for c in result["all_candidates"] if c["branch_index"] == "baseline"
    ]
    assert baseline_candidates, "Baseline candidate should be tracked"
    # Only one successful branch plus the baseline should be recorded
    assert result["telemetry"]["total_candidates"] == 2


@pytest.mark.asyncio
async def test_agent_occam_respects_timeout_budget():
    """Search stops when runtime exceeds the configured timeout."""
    call_counter = {"count": 0}

    async def slow_model(prompt, temperature, context):
        if call_counter["count"] == 0:
            call_counter["count"] += 1
            return "Fast response before timeout."
        call_counter["count"] += 1
        await asyncio.sleep(0.05)
        return f"Slow branch {call_counter['count']}"

    config = AgentOccamConfig(
        max_branches=4,
        temperatures=(0.2, 0.4, 0.6, 0.8),
        timeout_seconds=0.02,
        trace_candidates=True,
    )
    client = AgentOccamClient(config)

    result = await client.run_search(
        prompt="Generate three improvements.",
        model_fn=slow_model,
    )

    assert result["telemetry"]["timeout_reached"] is True
    # We should not exceed two candidates due to the aggressive timeout
    assert result["telemetry"]["total_candidates"] <= 2
    assert result["best_response"] == "Fast response before timeout."
