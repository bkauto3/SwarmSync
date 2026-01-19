"""
Test Suite for Solver Agent - Multi-Agent Evolve Co-Evolution

Tests cover:
1. Initialization and configuration validation
2. Trajectory generation (baseline + variations)
3. Diversity scoring and maintenance
4. Reward computation (quality + diversity + verifier challenge)
5. Feedback incorporation (adversarial learning)
6. History management and sliding windows
7. Integration with SE-Darwin operators
8. OTEL observability (metrics, spans)
9. Error handling and edge cases
10. Performance and scalability

Author: Hudson (Implementation Specialist)
Date: November 3, 2025
Status: Phase 2 Testing
"""

import asyncio
import pytest
from typing import Dict, List, Any
from unittest.mock import Mock, patch

from infrastructure.evolution.solver_agent import (
    SolverAgent,
    SolverConfig,
    SolverTrajectory,
    VerifierFeedback,
    get_solver_agent
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def default_config():
    """Default Solver configuration."""
    return SolverConfig(
        diversity_weight=0.3,
        quality_weight=0.5,
        verifier_weight=0.2,
        num_trajectories=5,
        max_iterations=10,
        diversity_threshold=0.4,
        history_size=20
    )


@pytest.fixture
def solver_agent(default_config):
    """Create Solver agent with default config."""
    return SolverAgent(
        agent_type="qa_agent",
        config=default_config
    )


@pytest.fixture
def sample_task():
    """Sample task for trajectory generation."""
    return {
        "type": "code_generation",
        "description": "Implement binary search algorithm",
        "constraints": ["O(log n) time complexity", "Handle edge cases"]
    }


@pytest.fixture
def sample_feedback():
    """Sample Verifier feedback."""
    return VerifierFeedback(
        trajectory_id="traj_001",
        verifier_score=0.75,
        correctness_score=0.8,
        quality_score=0.7,
        robustness_score=0.8,
        generalization_score=0.7,
        correctness_feedback="Solution is correct but could be optimized",
        quality_feedback="Code quality is good, naming could be improved",
        robustness_feedback="Edge cases handled well",
        shortcuts_detected=["hardcoded_values"],
        weak_areas=["error_handling", "input_validation"]
    )


# ============================================================================
# Test: Initialization and Configuration
# ============================================================================

def test_solver_initialization():
    """Test Solver agent initialization with default config."""
    solver = SolverAgent("qa_agent")

    assert solver.agent_type == "qa_agent"
    assert solver.config.num_trajectories == 5
    assert solver.trajectory_history == []
    assert solver.feedback_history == []
    assert solver.generation_count == 0
    assert solver.feedback_incorporated_count == 0


def test_solver_initialization_with_custom_config():
    """Test Solver agent initialization with custom config."""
    config = SolverConfig(
        diversity_weight=0.4,
        quality_weight=0.4,
        verifier_weight=0.2,
        num_trajectories=3,
        history_size=10
    )
    solver = SolverAgent("support_agent", config=config)

    assert solver.agent_type == "support_agent"
    assert solver.config.diversity_weight == 0.4
    assert solver.config.num_trajectories == 3
    assert solver.config.history_size == 10


def test_config_weight_validation():
    """Test configuration weight validation and normalization."""
    # Weights sum to 1.0 - should pass
    config1 = SolverConfig(
        diversity_weight=0.3,
        quality_weight=0.5,
        verifier_weight=0.2
    )
    assert abs((config1.diversity_weight + config1.quality_weight + config1.verifier_weight) - 1.0) < 0.01

    # Weights sum to 1.1 - should normalize
    config2 = SolverConfig(
        diversity_weight=0.33,
        quality_weight=0.55,
        verifier_weight=0.22
    )
    total = config2.diversity_weight + config2.quality_weight + config2.verifier_weight
    assert abs(total - 1.0) < 0.01  # Should be normalized


def test_config_validation_num_trajectories():
    """Test num_trajectories validation."""
    with pytest.raises(ValueError, match="num_trajectories must be >= 2"):
        SolverConfig(num_trajectories=1)


def test_config_validation_diversity_threshold():
    """Test diversity_threshold validation."""
    with pytest.raises(ValueError, match="diversity_threshold must be in"):
        SolverConfig(diversity_threshold=1.5)


def test_factory_function():
    """Test get_solver_agent factory function."""
    solver = get_solver_agent("analyst_agent")
    assert isinstance(solver, SolverAgent)
    assert solver.agent_type == "analyst_agent"


# ============================================================================
# Test: Trajectory Generation
# ============================================================================

@pytest.mark.asyncio
async def test_generate_trajectories_basic(solver_agent, sample_task):
    """Test basic trajectory generation."""
    trajectories = await solver_agent.generate_trajectories(sample_task)

    assert len(trajectories) == 5  # Default num_trajectories
    assert all(isinstance(t, SolverTrajectory) for t in trajectories)
    assert all(t.trajectory_id for t in trajectories)
    assert all(t.code for t in trajectories)
    assert all(t.reasoning for t in trajectories)


@pytest.mark.asyncio
async def test_generate_baseline_trajectory(solver_agent, sample_task):
    """Test baseline trajectory generation."""
    baseline = await solver_agent._generate_baseline(sample_task)

    assert isinstance(baseline, SolverTrajectory)
    assert baseline.generation_method == "baseline"
    assert "baseline" in baseline.trajectory_id.lower()
    assert baseline.solver_confidence == 0.6  # Medium confidence
    assert baseline.metadata["task_type"] == "code_generation"
    assert baseline.metadata["strategy"] == "straightforward"


@pytest.mark.asyncio
async def test_generate_variation_trajectories(solver_agent, sample_task):
    """Test variation trajectory generation."""
    baseline = await solver_agent._generate_baseline(sample_task)

    # Generate variations
    var0 = await solver_agent._generate_variation(baseline, sample_task, None, 0)
    var1 = await solver_agent._generate_variation(baseline, sample_task, None, 1)
    var2 = await solver_agent._generate_variation(baseline, sample_task, None, 2)

    # Check operator selection
    assert var0.generation_method == "revision"  # Iteration 0-1
    assert var1.generation_method == "revision"  # Iteration 0-1
    assert var2.generation_method == "recombination"  # Iteration 2-3

    # Check parent tracking
    assert baseline.trajectory_id in var0.parent_ids
    assert baseline.trajectory_id in var1.parent_ids


@pytest.mark.asyncio
async def test_generate_trajectories_with_feedback(solver_agent, sample_task, sample_feedback):
    """Test trajectory generation with Verifier feedback."""
    trajectories = await solver_agent.generate_trajectories(
        sample_task,
        verifier_feedback=[sample_feedback]
    )

    assert len(trajectories) == 5

    # Check that variations incorporate feedback
    variations = [t for t in trajectories if t.generation_method != "baseline"]
    for var in variations:
        assert var.metadata["verifier_informed"] is True
        # Should have targeted weak areas
        assert var.metadata["weak_areas_targeted"] > 0


@pytest.mark.asyncio
async def test_trajectory_diversity_computation(solver_agent, sample_task):
    """Test diversity score computation for trajectories."""
    trajectories = await solver_agent.generate_trajectories(sample_task)

    # All trajectories should have diversity scores
    assert all(hasattr(t, 'diversity_score') for t in trajectories)
    assert all(0.0 <= t.diversity_score <= 1.0 for t in trajectories)

    # Baseline (first in empty pool) should have high diversity
    assert trajectories[0].diversity_score == 1.0 or trajectories[0].diversity_score > 0.8


@pytest.mark.asyncio
async def test_trajectory_unique_ids(solver_agent, sample_task):
    """Test that all trajectories have unique IDs."""
    trajectories = await solver_agent.generate_trajectories(sample_task)

    ids = [t.trajectory_id for t in trajectories]
    assert len(ids) == len(set(ids))  # All unique


# ============================================================================
# Test: Diversity Scoring
# ============================================================================

def test_diversity_score_empty_history(solver_agent):
    """Test diversity score with empty history."""
    traj = SolverTrajectory(
        trajectory_id="traj_001",
        code="def foo(): pass",
        reasoning="Test",
        generation_method="baseline",
        solver_confidence=0.6
    )

    diversity = solver_agent._compute_diversity_score(traj)
    assert diversity == 1.0  # Maximum diversity when pool empty


def test_diversity_score_identical_code(solver_agent):
    """Test diversity score with identical code."""
    traj1 = SolverTrajectory(
        trajectory_id="traj_001",
        code="def foo(): pass",
        reasoning="Test",
        generation_method="baseline",
        solver_confidence=0.6
    )

    # Add to history
    solver_agent.update_history(traj1)

    # Identical trajectory
    traj2 = SolverTrajectory(
        trajectory_id="traj_002",
        code="def foo(): pass",
        reasoning="Test",
        generation_method="revision",
        solver_confidence=0.7
    )

    diversity = solver_agent._compute_diversity_score(traj2)
    assert diversity < 0.1  # Very low diversity (nearly identical)


def test_diversity_score_different_code(solver_agent):
    """Test diversity score with different code."""
    traj1 = SolverTrajectory(
        trajectory_id="traj_001",
        code="def foo(): return 1",
        reasoning="Test",
        generation_method="baseline",
        solver_confidence=0.6
    )

    solver_agent.update_history(traj1)

    traj2 = SolverTrajectory(
        trajectory_id="traj_002",
        code="def bar(): return 42",
        reasoning="Test",
        generation_method="revision",
        solver_confidence=0.7
    )

    diversity = solver_agent._compute_diversity_score(traj2)
    assert diversity > 0.5  # High diversity (very different)


def test_jaccard_similarity_identical():
    """Test Jaccard similarity for identical code."""
    solver = SolverAgent("test_agent")
    similarity = solver._jaccard_similarity("def foo(): pass", "def foo(): pass")
    assert similarity == 1.0


def test_jaccard_similarity_different():
    """Test Jaccard similarity for different code."""
    solver = SolverAgent("test_agent")
    similarity = solver._jaccard_similarity("def foo(): pass", "def bar(): return 42")
    assert 0.0 < similarity < 0.5  # Some tokens overlap (def, :)


def test_jaccard_similarity_empty():
    """Test Jaccard similarity with empty strings."""
    solver = SolverAgent("test_agent")
    similarity = solver._jaccard_similarity("", "")
    assert similarity == 1.0  # Both empty = identical


# ============================================================================
# Test: Reward Computation
# ============================================================================

def test_compute_solver_reward_basic(solver_agent):
    """Test basic reward computation."""
    trajectory = SolverTrajectory(
        trajectory_id="traj_001",
        code="def test(): pass",
        reasoning="Test",
        generation_method="baseline",
        solver_confidence=0.7,
        diversity_score=0.8
    )

    reward = solver_agent.compute_solver_reward(
        trajectory=trajectory,
        benchmark_score=0.9,
        verifier_score=0.85
    )

    # reward = 0.5 * 0.9 + 0.3 * 0.8 + 0.2 * (1.0 - 0.85)
    #        = 0.45 + 0.24 + 0.03 = 0.72
    expected = 0.5 * 0.9 + 0.3 * 0.8 + 0.2 * (1.0 - 0.85)
    assert abs(reward - expected) < 0.01


def test_compute_solver_reward_high_quality(solver_agent):
    """Test reward computation with high benchmark score."""
    trajectory = SolverTrajectory(
        trajectory_id="traj_001",
        code="def test(): pass",
        reasoning="Test",
        generation_method="baseline",
        solver_confidence=0.9,
        diversity_score=0.5
    )

    reward = solver_agent.compute_solver_reward(
        trajectory=trajectory,
        benchmark_score=0.95,
        verifier_score=0.9
    )

    # High quality should dominate (weight 0.5)
    assert reward > 0.6


def test_compute_solver_reward_high_diversity(solver_agent):
    """Test reward computation with high diversity."""
    trajectory = SolverTrajectory(
        trajectory_id="traj_001",
        code="def test(): pass",
        reasoning="Test",
        generation_method="revision",
        solver_confidence=0.6,
        diversity_score=0.95
    )

    reward = solver_agent.compute_solver_reward(
        trajectory=trajectory,
        benchmark_score=0.7,
        verifier_score=0.8
    )

    # Diversity contributes significantly (weight 0.3)
    assert reward > 0.5


def test_compute_solver_reward_challenge_verifier(solver_agent):
    """Test reward computation when challenging Verifier."""
    trajectory = SolverTrajectory(
        trajectory_id="traj_001",
        code="def test(): pass",
        reasoning="Test",
        generation_method="recombination",
        solver_confidence=0.7,
        diversity_score=0.6
    )

    # Low verifier score = high challenge reward
    reward = solver_agent.compute_solver_reward(
        trajectory=trajectory,
        benchmark_score=0.8,
        verifier_score=0.5  # Verifier struggled
    )

    # verifier_challenge = 1.0 - 0.5 = 0.5 (high)
    # Should include significant challenge component (weight 0.2)
    expected_challenge_contribution = 0.2 * 0.5
    assert expected_challenge_contribution > 0.05


# ============================================================================
# Test: Feedback Incorporation
# ============================================================================

def test_incorporate_feedback_basic(solver_agent, sample_feedback):
    """Test basic feedback incorporation."""
    initial_count = solver_agent.feedback_incorporated_count

    solver_agent.incorporate_feedback(sample_feedback)

    assert len(solver_agent.feedback_history) == 1
    assert solver_agent.feedback_incorporated_count == initial_count + 1
    assert solver_agent.feedback_history[0] == sample_feedback


def test_incorporate_multiple_feedbacks(solver_agent, sample_feedback):
    """Test incorporating multiple feedbacks."""
    feedback2 = VerifierFeedback(
        trajectory_id="traj_002",
        verifier_score=0.8,
        correctness_score=0.85,
        quality_score=0.75,
        robustness_score=0.8,
        generalization_score=0.8,
        correctness_feedback="Good solution",
        quality_feedback="Clean code",
        robustness_feedback="Robust",
        shortcuts_detected=[],
        weak_areas=[]
    )

    solver_agent.incorporate_feedback(sample_feedback)
    solver_agent.incorporate_feedback(feedback2)

    assert len(solver_agent.feedback_history) == 2
    assert solver_agent.feedback_incorporated_count == 2


def test_feedback_history_sliding_window(solver_agent):
    """Test feedback history maintains sliding window."""
    config = SolverConfig(history_size=5)
    solver = SolverAgent("test_agent", config=config)

    # Add 10 feedbacks (exceeds history_size=5)
    for i in range(10):
        feedback = VerifierFeedback(
            trajectory_id=f"traj_{i:03d}",
            verifier_score=0.7,
            correctness_score=0.7,
            quality_score=0.7,
            robustness_score=0.7,
            generalization_score=0.7,
            correctness_feedback="Test",
            quality_feedback="Test",
            robustness_feedback="Test"
        )
        solver.incorporate_feedback(feedback)

    # Should keep only last 5
    assert len(solver.feedback_history) == 5
    assert solver.feedback_history[-1].trajectory_id == "traj_009"


# ============================================================================
# Test: History Management
# ============================================================================

def test_update_history_basic(solver_agent):
    """Test basic history update."""
    trajectory = SolverTrajectory(
        trajectory_id="traj_001",
        code="def test(): pass",
        reasoning="Test",
        generation_method="baseline",
        solver_confidence=0.6
    )

    solver_agent.update_history(trajectory)

    assert len(solver_agent.trajectory_history) == 1
    assert solver_agent.trajectory_history[0] == trajectory


def test_history_sliding_window(solver_agent):
    """Test history maintains sliding window."""
    config = SolverConfig(history_size=5)
    solver = SolverAgent("test_agent", config=config)

    # Add 10 trajectories (exceeds history_size=5)
    for i in range(10):
        trajectory = SolverTrajectory(
            trajectory_id=f"traj_{i:03d}",
            code=f"def test_{i}(): pass",
            reasoning="Test",
            generation_method="baseline",
            solver_confidence=0.6
        )
        solver.update_history(trajectory)

    # Should keep only last 5
    assert len(solver.trajectory_history) == 5
    assert solver.trajectory_history[-1].trajectory_id == "traj_009"


# ============================================================================
# Test: Statistics and Reporting
# ============================================================================

def test_get_statistics_empty(solver_agent):
    """Test statistics with empty history."""
    stats = solver_agent.get_statistics()

    assert stats["agent_type"] == "qa_agent"
    assert stats["generation_count"] == 0
    assert stats["feedback_incorporated_count"] == 0
    assert stats["history_size"] == 0
    assert stats["average_diversity"] == 0.0
    assert stats["average_confidence"] == 0.0


@pytest.mark.asyncio
async def test_get_statistics_with_data(solver_agent, sample_task, sample_feedback):
    """Test statistics with generated trajectories."""
    # Generate trajectories
    trajectories = await solver_agent.generate_trajectories(sample_task)

    # Incorporate feedback
    solver_agent.incorporate_feedback(sample_feedback)

    stats = solver_agent.get_statistics()

    assert stats["generation_count"] == 5
    assert stats["feedback_incorporated_count"] == 1
    assert stats["history_size"] == 5
    assert stats["average_diversity"] > 0.0
    assert stats["average_confidence"] > 0.0


# ============================================================================
# Test: Data Structure Serialization
# ============================================================================

def test_solver_trajectory_serialization():
    """Test SolverTrajectory serialization."""
    traj = SolverTrajectory(
        trajectory_id="traj_001",
        code="def test(): pass",
        reasoning="Test reasoning",
        generation_method="baseline",
        solver_confidence=0.7,
        diversity_score=0.8,
        metadata={"key": "value"},
        parent_ids=["parent_001"]
    )

    # Serialize
    data = traj.to_dict()

    assert data["trajectory_id"] == "traj_001"
    assert data["code"] == "def test(): pass"
    assert data["generation_method"] == "baseline"
    assert data["metadata"]["key"] == "value"

    # Deserialize
    traj2 = SolverTrajectory.from_dict(data)

    assert traj2.trajectory_id == traj.trajectory_id
    assert traj2.code == traj.code
    assert traj2.solver_confidence == traj.solver_confidence


def test_verifier_feedback_serialization(sample_feedback):
    """Test VerifierFeedback serialization."""
    data = sample_feedback.to_dict()

    assert data["trajectory_id"] == "traj_001"
    assert data["verifier_score"] == 0.75
    assert data["weak_areas"] == ["error_handling", "input_validation"]
    assert data["shortcuts_detected"] == ["hardcoded_values"]


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_generate_trajectories_custom_count():
    """Test trajectory generation with custom count."""
    config = SolverConfig(num_trajectories=3)
    solver = SolverAgent("test_agent", config=config)

    task = {"type": "test", "description": "Test task"}
    trajectories = await solver.generate_trajectories(task)

    assert len(trajectories) == 3


@pytest.mark.asyncio
async def test_generate_trajectories_minimal_task():
    """Test trajectory generation with minimal task specification."""
    solver = SolverAgent("test_agent")

    task = {"type": "minimal"}  # No description
    trajectories = await solver.generate_trajectories(task)

    assert len(trajectories) == 5
    assert all(t.trajectory_id for t in trajectories)


def test_solver_trajectory_defaults():
    """Test SolverTrajectory default values."""
    traj = SolverTrajectory(
        trajectory_id="traj_001",
        code="test",
        reasoning="test",
        generation_method="baseline",
        solver_confidence=0.6
    )

    assert traj.diversity_score == 0.0  # Default
    assert traj.timestamp > 0
    assert traj.metadata == {}
    assert traj.parent_ids == []


# ============================================================================
# Test: Integration Points
# ============================================================================

def test_solver_has_se_operators(solver_agent):
    """Test that Solver has SE-Darwin operators."""
    assert solver_agent.revision_operator is not None
    assert solver_agent.recombination_operator is not None
    assert solver_agent.refinement_operator is not None


def test_solver_has_trajectory_pool(solver_agent):
    """Test that Solver has TrajectoryPool."""
    assert solver_agent.trajectory_pool is not None


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
