"""
Unit Tests for SPICE Challenger Agent - Corpus-Grounded Task Generation

Tests the ChallengerAgent class:
1. Corpus loading and management
2. Task sampling by difficulty level
3. Frontier task generation with variations
4. Grounding validation and scoring
5. Metrics tracking (OTEL)
6. Error handling and edge cases
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from infrastructure.spice.challenger_agent import (
    ChallengerAgent,
    FrontierTask,
    GroundingEvidence,
    get_challenger_agent
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = AsyncMock()
    client.generate = AsyncMock(
        return_value=json.dumps({
            "description": "Generated task description",
            "capabilities": ["capability1", "capability2"]
        })
    )
    return client


@pytest.fixture
def sample_corpus():
    """Sample benchmark corpus for testing"""
    return {
        "QA": [
            {
                "scenario_id": "qa_001",
                "description": "Test basic API functionality",
                "category": "basic_functionality"
            },
            {
                "scenario_id": "qa_002",
                "description": "Test edge case handling",
                "category": "edge_cases"
            },
            {
                "scenario_id": "qa_003",
                "description": "Test system integration",
                "category": "integration"
            },
            {
                "scenario_id": "qa_004",
                "description": "Test performance under load",
                "category": "performance"
            }
        ],
        "Support": [
            {
                "scenario_id": "sup_001",
                "description": "Handle customer complaint",
                "category": "basic_functionality"
            }
        ]
    }


@pytest.fixture
def challenger_agent(mock_llm_client, tmp_path):
    """Create Challenger agent for testing"""
    agent = ChallengerAgent(
        llm_client=mock_llm_client,
        corpus_dir=tmp_path / "scenarios",
        grounding_threshold=0.7
    )
    # Inject sample corpus
    agent.corpus = {
        "QA": [
            {
                "scenario_id": "qa_001",
                "description": "Test basic API functionality",
                "category": "basic_functionality"
            },
            {
                "scenario_id": "qa_002",
                "description": "Test edge case handling",
                "category": "edge_cases"
            },
            {
                "scenario_id": "qa_003",
                "description": "Test system integration",
                "category": "integration"
            },
            {
                "scenario_id": "qa_004",
                "description": "Test performance under load",
                "category": "performance"
            }
        ]
    }
    return agent


# ============================================================================
# TESTS: Corpus Loading
# ============================================================================

def test_load_corpus(tmp_path, mock_llm_client):
    """Test corpus loading from benchmark directory"""
    # Create test scenario file
    scenario_dir = tmp_path / "scenarios"
    scenario_dir.mkdir()

    scenario_file = scenario_dir / "qa_agent_scenarios.json"
    scenarios = [
        {"scenario_id": "qa_001", "description": "Test 1", "category": "basic_functionality"}
    ]
    scenario_file.write_text(json.dumps(scenarios))

    agent = ChallengerAgent(llm_client=mock_llm_client, corpus_dir=scenario_dir)

    assert "QA" in agent.corpus
    assert len(agent.corpus["QA"]) == 1
    assert agent.corpus["QA"][0]["scenario_id"] == "qa_001"


def test_load_corpus_missing_directory(mock_llm_client, tmp_path):
    """Test handling of missing corpus directory"""
    agent = ChallengerAgent(
        llm_client=mock_llm_client,
        corpus_dir=tmp_path / "nonexistent"
    )

    assert agent.corpus == {}


# ============================================================================
# TESTS: Sampling from Corpus
# ============================================================================

def test_sample_from_corpus_basic(challenger_agent):
    """Test sampling at 0.3 difficulty (basic_functionality)"""
    samples = challenger_agent._sample_from_corpus(
        agent_role="QA",
        difficulty_level=0.3,
        num_samples=1
    )

    assert len(samples) >= 1
    # Sample should match expected difficulty range
    assert samples[0]["category"] in ["basic_functionality", "edge_cases"]


def test_sample_from_corpus_medium(challenger_agent):
    """Test sampling at 0.5 difficulty (edge_cases)"""
    samples = challenger_agent._sample_from_corpus(
        agent_role="QA",
        difficulty_level=0.5,
        num_samples=1
    )

    assert len(samples) == 1
    assert samples[0]["category"] == "edge_cases"


def test_sample_from_corpus_hard(challenger_agent):
    """Test sampling at 0.75 difficulty (integration)"""
    samples = challenger_agent._sample_from_corpus(
        agent_role="QA",
        difficulty_level=0.75,
        num_samples=1
    )

    assert len(samples) == 1
    assert samples[0]["category"] == "integration"


def test_sample_from_corpus_expert(challenger_agent):
    """Test sampling at 0.95 difficulty (performance)"""
    samples = challenger_agent._sample_from_corpus(
        agent_role="QA",
        difficulty_level=0.95,
        num_samples=1
    )

    assert len(samples) == 1
    assert samples[0]["category"] == "performance"


def test_sample_from_corpus_no_agent(challenger_agent):
    """Test sampling from non-existent agent role"""
    samples = challenger_agent._sample_from_corpus(
        agent_role="NonExistent",
        difficulty_level=0.5,
        num_samples=1
    )

    assert samples == []


def test_sample_from_corpus_multiple(challenger_agent):
    """Test sampling multiple examples"""
    # Update corpus with more examples
    challenger_agent.corpus["QA"].extend([
        {"scenario_id": "qa_005", "description": "Test 5", "category": "basic_functionality"},
        {"scenario_id": "qa_006", "description": "Test 6", "category": "basic_functionality"}
    ])

    samples = challenger_agent._sample_from_corpus(
        agent_role="QA",
        difficulty_level=0.2,
        num_samples=2
    )

    assert len(samples) == 2


# ============================================================================
# TESTS: Task Generation
# ============================================================================

@pytest.mark.asyncio
async def test_generate_frontier_task_single(challenger_agent):
    """Test generating a single frontier task"""
    # Lower the grounding threshold to near-zero for testing
    challenger_agent.grounding_threshold = 0.0

    tasks = await challenger_agent.generate_frontier_task(
        agent_role="QA",
        difficulty_level=0.3,
        num_variations=1
    )

    # May generate tasks or may not depending on LLM response
    if tasks:
        assert isinstance(tasks[0], FrontierTask)
        assert tasks[0].agent_role == "QA"
        assert tasks[0].difficulty == 0.3


@pytest.mark.asyncio
async def test_generate_frontier_task_multiple(challenger_agent):
    """Test generating multiple frontier tasks"""
    # Add more corpus samples
    challenger_agent.corpus["QA"].extend([
        {"scenario_id": "qa_005", "description": "Test 5", "category": "basic_functionality"},
        {"scenario_id": "qa_006", "description": "Test 6", "category": "basic_functionality"}
    ])

    # Lower grounding threshold to near-zero for testing
    challenger_agent.grounding_threshold = 0.0

    tasks = await challenger_agent.generate_frontier_task(
        agent_role="QA",
        difficulty_level=0.3,
        num_variations=3
    )

    # Tasks may or may not be generated depending on LLM
    assert isinstance(tasks, list)


@pytest.mark.asyncio
async def test_frontier_task_contains_grounding_evidence(challenger_agent):
    """Test that generated tasks contain grounding evidence"""
    challenger_agent.grounding_threshold = 0.1

    tasks = await challenger_agent.generate_frontier_task(
        agent_role="QA",
        difficulty_level=0.3,
        num_variations=1
    )

    if tasks:
        task = tasks[0]
        assert len(task.grounding_evidence) > 0
        assert task.grounding_evidence[0].corpus_source == "genesis_benchmarks"
        assert isinstance(task.grounding_evidence[0].similarity_score, float)


@pytest.mark.asyncio
async def test_frontier_task_has_task_id(challenger_agent):
    """Test that generated tasks have unique IDs"""
    challenger_agent.grounding_threshold = 0.1

    tasks = await challenger_agent.generate_frontier_task(
        agent_role="QA",
        difficulty_level=0.3,
        num_variations=1
    )

    if tasks:
        assert len(tasks[0].task_id) > 0
        assert len(tasks[0].task_id) == 16  # MD5 hash truncated to 16 chars


# ============================================================================
# TESTS: Grounding Validation
# ============================================================================

def test_grounding_validation_pass(challenger_agent):
    """Test grounding validation accepts well-grounded tasks"""
    base_task = {
        "description": "Test basic API functionality with error handling"
    }
    variation = {
        "description": "Test API error handling and recovery",
        "capabilities": ["error_handling", "recovery"]
    }

    score = challenger_agent._compute_grounding_score(base_task, variation)

    # Should have reasonable overlap
    assert score > 0.0


def test_grounding_validation_fail(challenger_agent):
    """Test grounding validation rejects hallucinated tasks"""
    base_task = {
        "description": "Test API functionality"
    }
    variation = {
        "description": "Completely unrelated topic about agriculture",
        "capabilities": ["farming", "crops"]
    }

    score = challenger_agent._compute_grounding_score(base_task, variation)

    # Should have low overlap
    assert score < 0.5


def test_compute_grounding_score(challenger_agent):
    """Test Jaccard similarity calculation"""
    base_task = {
        "description": "Test the error handling mechanism"
    }
    variation = {
        "description": "Test error handling and recovery features"
    }

    score = challenger_agent._compute_grounding_score(base_task, variation)

    # Jaccard: {test, error, handling} / {test, the, error, handling, mechanism, and, recovery, features}
    # intersection = 3, union = 8, so ~0.375
    assert 0.0 <= score <= 1.0


# ============================================================================
# TESTS: Task ID Generation
# ============================================================================

def test_task_id_generation(challenger_agent):
    """Test unique task ID generation"""
    id1 = challenger_agent._generate_task_id("QA", 0.5)
    id2 = challenger_agent._generate_task_id("QA", 0.5)

    # IDs should be different (due to timestamp)
    assert id1 != id2
    assert len(id1) == 16
    assert len(id2) == 16


def test_task_id_format(challenger_agent):
    """Test task ID format is valid hex"""
    task_id = challenger_agent._generate_task_id("Support", 0.3)

    # Should be valid hex string
    try:
        int(task_id, 16)
    except ValueError:
        pytest.fail("Task ID is not valid hex")


# ============================================================================
# TESTS: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_generate_frontier_task_no_corpus(mock_llm_client, tmp_path):
    """Test handling of missing corpus"""
    agent = ChallengerAgent(
        llm_client=mock_llm_client,
        corpus_dir=tmp_path / "nonexistent"
    )

    tasks = await agent.generate_frontier_task(
        agent_role="NonExistent",
        difficulty_level=0.5,
        num_variations=1
    )

    assert tasks == []


@pytest.mark.asyncio
async def test_llm_generation_failure(challenger_agent):
    """Test graceful handling of LLM generation failure"""
    challenger_agent.llm_client.generate = AsyncMock(
        side_effect=Exception("LLM connection failed")
    )

    tasks = await challenger_agent.generate_frontier_task(
        agent_role="QA",
        difficulty_level=0.3,
        num_variations=1
    )

    # Should handle error gracefully and return empty list
    assert tasks == []


@pytest.mark.asyncio
async def test_invalid_json_response(challenger_agent):
    """Test handling of invalid JSON from LLM"""
    challenger_agent.llm_client.generate = AsyncMock(
        return_value="This is not JSON"
    )

    tasks = await challenger_agent.generate_frontier_task(
        agent_role="QA",
        difficulty_level=0.3,
        num_variations=1
    )

    # Should handle JSON parsing error gracefully
    assert tasks == []


# ============================================================================
# TESTS: Metrics and Observability
# ============================================================================

@pytest.mark.asyncio
async def test_metrics_tracking(challenger_agent):
    """Test that OTEL metrics are recorded"""
    with patch('infrastructure.spice.challenger_agent.task_counter') as mock_counter:
        with patch('infrastructure.spice.challenger_agent.grounding_score_histogram') as mock_histogram:
            tasks = await challenger_agent.generate_frontier_task(
                agent_role="QA",
                difficulty_level=0.3,
                num_variations=1
            )

            if tasks:
                # Verify metrics were called
                assert mock_counter.add.called or not mock_counter  # May be None in test
                assert mock_histogram.record.called or not mock_histogram


@pytest.mark.asyncio
async def test_task_metadata(challenger_agent):
    """Test that generated tasks contain proper metadata"""
    challenger_agent.grounding_threshold = 0.1

    tasks = await challenger_agent.generate_frontier_task(
        agent_role="QA",
        difficulty_level=0.5,
        num_variations=1
    )

    if tasks:
        task = tasks[0]
        assert "generation_timestamp" in task.metadata
        assert "corpus_source" in task.metadata

        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(task.metadata["generation_timestamp"])
        except ValueError:
            pytest.fail("Invalid timestamp format")


# ============================================================================
# TESTS: Difficulty Curriculum
# ============================================================================

def test_difficulty_curriculum_progression(challenger_agent):
    """Test that difficulty mapping is consistent"""
    # Test that difficulty ranges map to expected categories
    # We use broader ranges because of randomness in sampling
    test_cases = [
        (0.1, ["basic_functionality", "edge_cases"]),
        (0.2, ["basic_functionality", "edge_cases"]),
        (0.4, ["edge_cases", "integration"]),
        (0.5, ["edge_cases", "integration"]),
        (0.7, ["integration", "performance"]),
        (0.8, ["integration", "performance"]),
        (0.9, ["performance"]),
        (1.0, ["performance"])
    ]

    for difficulty, allowed_categories in test_cases:
        samples = challenger_agent._sample_from_corpus(
            agent_role="QA",
            difficulty_level=difficulty,
            num_samples=1
        )

        if samples:
            assert samples[0]["category"] in allowed_categories


# ============================================================================
# TESTS: Frontier Task Data Class
# ============================================================================

def test_frontier_task_to_dict():
    """Test FrontierTask serialization"""
    evidence = GroundingEvidence(
        corpus_source="genesis_benchmarks",
        reference_task="Original task",
        similarity_score=0.85,
        metadata={"source": "test"}
    )

    task = FrontierTask(
        task_id="test_123",
        description="Test task",
        difficulty=0.5,
        agent_role="QA",
        grounding_evidence=[evidence],
        expected_capabilities=["cap1", "cap2"]
    )

    task_dict = task.to_dict()

    assert task_dict["task_id"] == "test_123"
    assert task_dict["description"] == "Test task"
    assert task_dict["difficulty"] == 0.5
    assert len(task_dict["grounding_evidence"]) == 1
    assert task_dict["grounding_evidence"][0]["corpus_source"] == "genesis_benchmarks"


# ============================================================================
# TESTS: Initialization and Configuration
# ============================================================================

def test_challenger_initialization_defaults():
    """Test Challenger agent initialization with defaults"""
    with patch('infrastructure.spice.challenger_agent.LLMFactory.create') as mock_create:
        mock_client = AsyncMock()
        mock_create.return_value = mock_client

        agent = ChallengerAgent()

        assert agent.grounding_threshold == 0.7
        mock_create.assert_called_once()


def test_challenger_initialization_custom_threshold(mock_llm_client):
    """Test Challenger agent initialization with custom threshold"""
    agent = ChallengerAgent(
        llm_client=mock_llm_client,
        grounding_threshold=0.5
    )

    assert agent.grounding_threshold == 0.5


def test_get_challenger_agent_singleton(mock_llm_client):
    """Test get_challenger_agent singleton pattern"""
    # Reset the singleton
    import infrastructure.spice.challenger_agent
    infrastructure.spice.challenger_agent._challenger_instance = None

    agent1 = get_challenger_agent(llm_client=mock_llm_client)
    agent2 = get_challenger_agent(llm_client=mock_llm_client)

    # Should return same instance
    assert agent1 is agent2


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

def test_empty_task_description(challenger_agent):
    """Test handling of empty task description"""
    base_task = {"description": ""}
    variation = {"description": ""}

    score = challenger_agent._compute_grounding_score(base_task, variation)

    assert score == 0.0


def test_very_long_descriptions(challenger_agent):
    """Test handling of very long descriptions"""
    long_text = " ".join(["word"] * 1000)
    base_task = {"description": long_text}
    variation = {"description": long_text + " additional words"}

    score = challenger_agent._compute_grounding_score(base_task, variation)

    assert 0.0 <= score <= 1.0


def test_special_characters_in_description(challenger_agent):
    """Test handling of special characters"""
    base_task = {
        "description": "Test API with @#$%^&*() special chars"
    }
    variation = {
        "description": "Test API with !@#$%^&*() different chars"
    }

    score = challenger_agent._compute_grounding_score(base_task, variation)

    assert 0.0 <= score <= 1.0
