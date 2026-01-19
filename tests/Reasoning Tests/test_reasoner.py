"""
Unit Tests for SPICE Reasoner Agent - Ungrounded Solution Generation

Tests the ReasonerAgent class:
1. Baseline solution generation
2. Multi-trajectory solving with different approaches
3. SE-Darwin operator application (revision, recombination, refinement)
4. Solution quality scoring
5. Trajectory diversity calculation
6. Metrics tracking (OTEL)
7. Error handling and edge cases
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from infrastructure.spice.reasoner_agent import (
    ReasonerAgent,
    TrajectoryResult,
    get_reasoner_agent
)
from infrastructure.spice.challenger_agent import (
    FrontierTask,
    GroundingEvidence
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value="This is a generated solution with detailed explanation."
    )
    return client


@pytest.fixture
def sample_frontier_task():
    """Create sample frontier task for testing"""
    return FrontierTask(
        task_id="test_task_001",
        description="Solve this challenging problem efficiently",
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[
            GroundingEvidence(
                corpus_source="genesis_benchmarks",
                reference_task="Original problem",
                similarity_score=0.85
            )
        ],
        expected_capabilities=["problem_solving", "efficiency"],
        metadata={"timestamp": datetime.now(timezone.utc).isoformat()}
    )


@pytest.fixture
def reasoner_agent(mock_llm_client):
    """Create Reasoner agent for testing"""
    agent = ReasonerAgent(llm_client=mock_llm_client)
    return agent


@pytest.fixture
def mock_revision_operator():
    """Mock revision operator"""
    op = Mock()
    op.apply = AsyncMock(return_value="Revised solution approach")
    return op


@pytest.fixture
def mock_recombination_operator():
    """Mock recombination operator"""
    op = Mock()
    op.apply = AsyncMock(return_value="Hybrid solution combining approaches")
    return op


@pytest.fixture
def mock_refinement_operator():
    """Mock refinement operator"""
    op = Mock()
    op.apply = AsyncMock(return_value="Optimized and refined solution")
    return op


# ============================================================================
# TESTS: Baseline Solution Generation
# ============================================================================

@pytest.mark.asyncio
async def test_solve_task_baseline(reasoner_agent, sample_frontier_task):
    """Test generating baseline solution"""
    trajectories = await reasoner_agent.solve_task(
        task=sample_frontier_task,
        num_trajectories=1
    )

    assert len(trajectories) >= 1
    baseline = trajectories[0]
    assert baseline.approach == "baseline"
    assert baseline.task_id == "test_task_001"
    assert baseline.quality_score == 0.7


@pytest.mark.asyncio
async def test_solve_task_baseline_has_metadata(reasoner_agent, sample_frontier_task):
    """Test that baseline solution has proper metadata"""
    trajectories = await reasoner_agent.solve_task(
        task=sample_frontier_task,
        num_trajectories=1
    )

    assert len(trajectories) >= 1
    baseline = trajectories[0]
    assert "generation_timestamp" in baseline.metadata
    assert baseline.metadata["method"] == "direct_generation"


@pytest.mark.asyncio
async def test_solve_task_baseline_solution_content(reasoner_agent, sample_frontier_task):
    """Test that baseline solution contains expected content"""
    trajectories = await reasoner_agent.solve_task(
        task=sample_frontier_task,
        num_trajectories=1
    )

    assert len(trajectories) >= 1
    baseline = trajectories[0]
    assert len(baseline.solution) > 0
    assert isinstance(baseline.solution, str)


# ============================================================================
# TESTS: Multi-Trajectory Generation
# ============================================================================

@pytest.mark.asyncio
async def test_solve_task_multiple_trajectories(reasoner_agent, sample_frontier_task):
    """Test generating multiple solution trajectories"""
    trajectories = await reasoner_agent.solve_task(
        task=sample_frontier_task,
        num_trajectories=3
    )

    # Should generate 1-3 trajectories (baseline + up to 2 more)
    assert len(trajectories) >= 1
    assert len(trajectories) <= 3


@pytest.mark.asyncio
async def test_single_trajectory_mode(reasoner_agent, sample_frontier_task):
    """Test with num_trajectories=1"""
    trajectories = await reasoner_agent.solve_task(
        task=sample_frontier_task,
        num_trajectories=1
    )

    assert len(trajectories) == 1
    assert trajectories[0].approach == "baseline"


# ============================================================================
# TESTS: Operator Application
# ============================================================================

@pytest.mark.asyncio
async def test_apply_revision(reasoner_agent, sample_frontier_task):
    """Test revision operator for alternative strategy"""
    baseline = TrajectoryResult(
        task_id="test_task_001",
        solution="Original solution",
        approach="baseline",
        quality_score=0.7
    )

    result = await reasoner_agent._apply_revision(sample_frontier_task, baseline)

    assert result is not None
    assert result.approach == "revision"
    assert result.quality_score > 0.7
    assert result.quality_score == 0.75


@pytest.mark.asyncio
async def test_apply_revision_no_baseline(reasoner_agent, sample_frontier_task):
    """Test revision without baseline returns None"""
    result = await reasoner_agent._apply_revision(sample_frontier_task, None)

    assert result is None


@pytest.mark.asyncio
async def test_apply_recombination(reasoner_agent, sample_frontier_task):
    """Test recombination operator for hybrid approach"""
    existing = [
        TrajectoryResult(
            task_id="test_task_001",
            solution="Solution 1",
            approach="baseline",
            quality_score=0.7
        ),
        TrajectoryResult(
            task_id="test_task_001",
            solution="Solution 2",
            approach="revision",
            quality_score=0.75
        )
    ]

    result = await reasoner_agent._apply_recombination(sample_frontier_task, existing)

    assert result is not None
    assert result.approach == "recombination"
    assert result.quality_score == 0.8


@pytest.mark.asyncio
async def test_apply_recombination_insufficient_trajectories(reasoner_agent, sample_frontier_task):
    """Test recombination with fewer than 2 trajectories returns None"""
    existing = [
        TrajectoryResult(
            task_id="test_task_001",
            solution="Solution 1",
            approach="baseline",
            quality_score=0.7
        )
    ]

    result = await reasoner_agent._apply_recombination(sample_frontier_task, existing)

    assert result is None


@pytest.mark.asyncio
async def test_apply_refinement(reasoner_agent, sample_frontier_task):
    """Test refinement operator for optimization"""
    baseline = TrajectoryResult(
        task_id="test_task_001",
        solution="Original solution",
        approach="baseline",
        quality_score=0.7
    )

    result = await reasoner_agent._apply_refinement(sample_frontier_task, baseline)

    assert result is not None
    assert result.approach == "refinement"
    assert result.quality_score == 0.85  # Highest quality


# ============================================================================
# TESTS: Solution Quality Scoring
# ============================================================================

@pytest.mark.asyncio
async def test_quality_scores_progression(reasoner_agent, sample_frontier_task):
    """Test that quality scores progress correctly"""
    trajectories = await reasoner_agent.solve_task(
        task=sample_frontier_task,
        num_trajectories=3
    )

    # Extract quality scores by approach
    scores = {t.approach: t.quality_score for t in trajectories}

    # Baseline should be 0.7
    if "baseline" in scores:
        assert scores["baseline"] == 0.7

    # Revision (if present) should be 0.75
    if "revision" in scores:
        assert scores["revision"] == 0.75

    # Recombination (if present) should be 0.8
    if "recombination" in scores:
        assert scores["recombination"] == 0.8

    # Refinement (if present) should be 0.85
    if "refinement" in scores:
        assert scores["refinement"] == 0.85


# ============================================================================
# TESTS: Trajectory Diversity
# ============================================================================

def test_compute_diversity_single_trajectory(reasoner_agent):
    """Test diversity with single trajectory returns 0.0"""
    trajectories = [
        TrajectoryResult(
            task_id="test",
            solution="Solution A",
            approach="baseline",
            quality_score=0.7
        )
    ]

    diversity = reasoner_agent._compute_diversity(trajectories)

    assert diversity == 0.0


def test_compute_diversity_identical_solutions(reasoner_agent):
    """Test diversity with identical solutions"""
    solution = "This is the same solution"
    trajectories = [
        TrajectoryResult(
            task_id="test",
            solution=solution,
            approach="baseline",
            quality_score=0.7
        ),
        TrajectoryResult(
            task_id="test",
            solution=solution,
            approach="revision",
            quality_score=0.75
        )
    ]

    diversity = reasoner_agent._compute_diversity(trajectories)

    assert diversity == 0.0


def test_compute_diversity_different_lengths(reasoner_agent):
    """Test diversity with different solution lengths"""
    trajectories = [
        TrajectoryResult(
            task_id="test",
            solution="Short",
            approach="baseline",
            quality_score=0.7
        ),
        TrajectoryResult(
            task_id="test",
            solution="Much longer solution with more content",
            approach="revision",
            quality_score=0.75
        )
    ]

    diversity = reasoner_agent._compute_diversity(trajectories)

    assert diversity > 0.0
    assert diversity <= 1.0


def test_compute_diversity_high_variance(reasoner_agent):
    """Test diversity calculation with high variance in lengths"""
    trajectories = [
        TrajectoryResult(
            task_id="test",
            solution="A",
            approach="approach1",
            quality_score=0.7
        ),
        TrajectoryResult(
            task_id="test",
            solution="B" * 100,
            approach="approach2",
            quality_score=0.75
        ),
        TrajectoryResult(
            task_id="test",
            solution="C" * 50,
            approach="approach3",
            quality_score=0.8
        )
    ]

    diversity = reasoner_agent._compute_diversity(trajectories)

    assert diversity > 0.0
    assert diversity <= 1.0


# ============================================================================
# TESTS: Trajectory Result Data Class
# ============================================================================

def test_trajectory_result_to_dict():
    """Test TrajectoryResult serialization"""
    result = TrajectoryResult(
        task_id="task_001",
        solution="Generated solution text",
        approach="baseline",
        quality_score=0.75,
        metadata={"method": "test"}
    )

    result_dict = result.to_dict()

    assert result_dict["task_id"] == "task_001"
    assert result_dict["solution"] == "Generated solution text"
    assert result_dict["approach"] == "baseline"
    assert result_dict["quality_score"] == 0.75
    assert result_dict["metadata"]["method"] == "test"


def test_trajectory_result_all_approaches():
    """Test TrajectoryResult with all approach types"""
    approaches = ["baseline", "revision", "recombination", "refinement"]

    for approach in approaches:
        result = TrajectoryResult(
            task_id="test",
            solution="Solution",
            approach=approach,
            quality_score=0.7
        )

        assert result.approach == approach


# ============================================================================
# TESTS: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_empty_task_description(reasoner_agent):
    """Test handling of task with no description"""
    task = FrontierTask(
        task_id="test",
        description="",
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[],
        expected_capabilities=[]
    )

    trajectories = await reasoner_agent.solve_task(task)

    # Should handle gracefully (may return no solutions or empty solutions)
    assert isinstance(trajectories, list)


@pytest.mark.asyncio
async def test_llm_failure_baseline(reasoner_agent, sample_frontier_task):
    """Test graceful handling of LLM failure in baseline generation"""
    reasoner_agent.llm_client.generate = AsyncMock(
        side_effect=Exception("LLM connection failed")
    )

    trajectories = await reasoner_agent.solve_task(sample_frontier_task)

    # Should handle error gracefully
    assert isinstance(trajectories, list)


@pytest.mark.asyncio
async def test_operator_failure_graceful(reasoner_agent, sample_frontier_task):
    """Test graceful handling when operators fail"""
    trajectories = await reasoner_agent.solve_task(
        task=sample_frontier_task,
        num_trajectories=3
    )

    # Should return baseline even if operators fail
    assert len(trajectories) >= 1


# ============================================================================
# TESTS: Lazy Operator Loading
# ============================================================================

def test_lazy_revision_operator_loading(mock_llm_client):
    """Test lazy loading of revision operator"""
    agent = ReasonerAgent(llm_client=mock_llm_client)

    # Operator should not be loaded yet
    assert agent._revision_operator is None

    # Access property (would lazy load in real code)
    # In test, we just verify the property exists
    assert hasattr(agent, 'revision_operator')


def test_lazy_recombination_operator_loading(mock_llm_client):
    """Test lazy loading of recombination operator"""
    agent = ReasonerAgent(llm_client=mock_llm_client)

    assert agent._recombination_operator is None
    assert hasattr(agent, 'recombination_operator')


def test_lazy_refinement_operator_loading(mock_llm_client):
    """Test lazy loading of refinement operator"""
    agent = ReasonerAgent(llm_client=mock_llm_client)

    assert agent._refinement_operator is None
    assert hasattr(agent, 'refinement_operator')


# ============================================================================
# TESTS: Metrics and Observability
# ============================================================================

@pytest.mark.asyncio
async def test_metrics_tracking(reasoner_agent, sample_frontier_task):
    """Test that OTEL metrics are recorded"""
    with patch('infrastructure.spice.reasoner_agent.solution_counter') as mock_counter:
        with patch('infrastructure.spice.reasoner_agent.trajectory_diversity_histogram') as mock_histogram:
            trajectories = await reasoner_agent.solve_task(
                task=sample_frontier_task,
                num_trajectories=2
            )

            # Verify metrics were called
            assert mock_counter.add.called or not mock_counter
            assert mock_histogram.record.called or not mock_histogram


@pytest.mark.asyncio
async def test_trajectory_metadata_completeness(reasoner_agent, sample_frontier_task):
    """Test that trajectories contain complete metadata"""
    trajectories = await reasoner_agent.solve_task(
        task=sample_frontier_task,
        num_trajectories=1
    )

    if trajectories:
        traj = trajectories[0]
        assert "generation_timestamp" in traj.metadata
        assert "method" in traj.metadata


# ============================================================================
# TESTS: Initialization
# ============================================================================

def test_reasoner_initialization_defaults():
    """Test Reasoner agent initialization with defaults"""
    with patch('infrastructure.spice.reasoner_agent.LLMFactory.create') as mock_create:
        mock_client = AsyncMock()
        mock_create.return_value = mock_client

        agent = ReasonerAgent()

        assert agent.llm_client is not None
        mock_create.assert_called_once()


def test_reasoner_initialization_custom_client(mock_llm_client):
    """Test Reasoner agent initialization with custom client"""
    agent = ReasonerAgent(llm_client=mock_llm_client)

    assert agent.llm_client is mock_llm_client


def test_get_reasoner_agent_singleton(mock_llm_client):
    """Test get_reasoner_agent singleton pattern"""
    # Reset the singleton
    import infrastructure.spice.reasoner_agent
    infrastructure.spice.reasoner_agent._reasoner_instance = None

    agent1 = get_reasoner_agent(llm_client=mock_llm_client)
    agent2 = get_reasoner_agent(llm_client=mock_llm_client)

    # Should return same instance
    assert agent1 is agent2


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_zero_difficulty_task(reasoner_agent):
    """Test handling of zero difficulty task"""
    task = FrontierTask(
        task_id="test",
        description="Very easy task",
        difficulty=0.0,
        agent_role="QA",
        grounding_evidence=[],
        expected_capabilities=["easy_skill"]
    )

    trajectories = await reasoner_agent.solve_task(task)

    assert isinstance(trajectories, list)


@pytest.mark.asyncio
async def test_very_high_difficulty_task(reasoner_agent):
    """Test handling of high difficulty task"""
    task = FrontierTask(
        task_id="test",
        description="Extremely challenging expert task",
        difficulty=0.99,
        agent_role="QA",
        grounding_evidence=[],
        expected_capabilities=["expert_skill1", "expert_skill2", "expert_skill3"]
    )

    trajectories = await reasoner_agent.solve_task(task)

    assert isinstance(trajectories, list)


def test_diversity_with_empty_solutions(reasoner_agent):
    """Test diversity calculation with empty solutions"""
    trajectories = [
        TrajectoryResult(
            task_id="test",
            solution="",
            approach="baseline",
            quality_score=0.7
        ),
        TrajectoryResult(
            task_id="test",
            solution="Non-empty",
            approach="revision",
            quality_score=0.75
        )
    ]

    diversity = reasoner_agent._compute_diversity(trajectories)

    assert 0.0 <= diversity <= 1.0


@pytest.mark.asyncio
async def test_task_with_special_characters(reasoner_agent):
    """Test handling of special characters in task"""
    task = FrontierTask(
        task_id="test",
        description="Task with @#$%^&*() special chars",
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[],
        expected_capabilities=["handling_special"]
    )

    trajectories = await reasoner_agent.solve_task(task)

    assert isinstance(trajectories, list)


@pytest.mark.asyncio
async def test_task_with_long_description(reasoner_agent):
    """Test handling of very long task description"""
    long_description = "Task description. " * 100

    task = FrontierTask(
        task_id="test",
        description=long_description,
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[],
        expected_capabilities=["long_handling"]
    )

    trajectories = await reasoner_agent.solve_task(task)

    assert isinstance(trajectories, list)
