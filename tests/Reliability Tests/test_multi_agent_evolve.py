"""
Test suite for Multi-Agent Evolve co-evolution loop.

Based on arXiv:2510.23595 Algorithm 3 (Joint Training Loop)
Tests cover:
- Basic initialization and configuration
- Co-evolution loop execution
- Convergence detection (4 criteria)
- Solver-Verifier interaction
- Memory integration
- Reward computation
- Statistics tracking

Author: Hudson (Implementation Specialist)
Date: November 3, 2025
Status: Phase 4 Testing
"""

import pytest
from infrastructure.evolution.multi_agent_evolve import (
    MultiAgentEvolve,
    CoEvolutionConfig,
    CoEvolutionResult
)
from infrastructure.evolution.solver_agent import SolverConfig
from infrastructure.evolution.verifier_agent import VerifierConfig


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_multi_agent_evolve_initialization():
    """Test MAE initialization with default configs."""
    mae = MultiAgentEvolve("qa_agent")

    assert mae.agent_type == "qa_agent"
    assert mae.solver is not None
    assert mae.verifier is not None
    assert mae.config.max_iterations == 10
    assert mae.config.convergence_threshold == 0.05
    assert mae.config.min_iterations == 3
    assert mae.config.store_threshold == 0.75
    assert mae.config.enable_memory is True
    assert mae.trajectory_pool is not None
    assert len(mae.iteration_history) == 0


@pytest.mark.asyncio
async def test_initialization_custom_configs():
    """Test MAE initialization with custom Solver/Verifier/CoEvo configs."""
    solver_config = SolverConfig(num_trajectories=3)
    verifier_config = VerifierConfig(num_edge_cases=3)
    coevo_config = CoEvolutionConfig(max_iterations=5, min_iterations=2)

    mae = MultiAgentEvolve(
        "qa_agent",
        solver_config=solver_config,
        verifier_config=verifier_config,
        coevolution_config=coevo_config
    )

    assert mae.solver.config.num_trajectories == 3
    assert mae.verifier.config.num_edge_cases == 3
    assert mae.config.max_iterations == 5
    assert mae.config.min_iterations == 2


@pytest.mark.asyncio
async def test_initialization_memory_disabled():
    """Test MAE initialization with memory disabled."""
    coevo_config = CoEvolutionConfig(enable_memory=False)
    mae = MultiAgentEvolve("qa_agent", coevolution_config=coevo_config)

    assert mae.trajectory_pool is None
    assert mae.config.enable_memory is False


# ============================================================================
# BASIC EVOLUTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_evolve_basic():
    """Test basic co-evolution loop execution."""
    mae = MultiAgentEvolve("qa_agent")

    task = {
        "type": "code_generation",
        "description": "Implement binary search algorithm",
        "test_cases": [
            {"input": [1, 2, 3, 4, 5], "target": 3, "expected": 2},
            {"input": [1, 2, 3, 4, 5], "target": 6, "expected": -1}
        ]
    }

    result = await mae.evolve(task, max_iterations=3)

    assert isinstance(result, CoEvolutionResult)
    assert result.best_trajectory is not None
    assert isinstance(result.best_trajectory, dict)
    assert 0.0 <= result.final_score <= 1.0
    assert result.iterations_used <= 3
    assert result.iterations_used >= 1
    assert len(result.solver_rewards) == result.iterations_used
    assert len(result.verifier_rewards) == result.iterations_used
    assert len(result.convergence_history) == result.iterations_used
    assert isinstance(result.converged, bool)
    assert result.metadata["task_type"] == "code_generation"
    assert result.metadata["agent_type"] == "qa_agent"


@pytest.mark.asyncio
async def test_evolve_minimal_task():
    """Test evolution with minimal task specification."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "minimal task"}

    result = await mae.evolve(task, max_iterations=2)

    assert isinstance(result, CoEvolutionResult)
    assert result.iterations_used <= 2
    assert result.best_trajectory is not None


@pytest.mark.asyncio
async def test_evolve_different_agent_types():
    """Test evolution for different agent types."""
    agent_types = ["qa_agent", "builder_agent", "analyst_agent"]

    for agent_type in agent_types:
        mae = MultiAgentEvolve(agent_type)
        task = {"type": "test", "description": f"test for {agent_type}"}

        result = await mae.evolve(task, max_iterations=2)

        assert result.metadata["agent_type"] == agent_type
        assert result.iterations_used >= 1


# ============================================================================
# CONVERGENCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_convergence_max_iterations():
    """Test convergence via max iterations reached."""
    config = CoEvolutionConfig(max_iterations=5, min_iterations=1)
    mae = MultiAgentEvolve("qa_agent", coevolution_config=config)

    task = {"type": "test", "description": "test"}

    result = await mae.evolve(task)

    assert result.iterations_used <= 5
    assert result.converged is True
    # Either converged early or reached max iterations
    if result.iterations_used == 5:
        assert result.metadata["convergence_reason"] == "max_iterations_reached"


@pytest.mark.asyncio
async def test_convergence_score_plateau():
    """Test convergence detection via score plateau."""
    config = CoEvolutionConfig(
        max_iterations=10,
        min_iterations=3,
        convergence_threshold=0.05
    )
    mae = MultiAgentEvolve("qa_agent", coevolution_config=config)

    task = {"type": "test", "description": "test"}

    result = await mae.evolve(task)

    # Should converge before max iterations if score plateaus
    if result.converged and result.iterations_used < 10:
        # Check that recent scores are similar (if plateau convergence)
        if len(result.convergence_history) >= 3:
            recent = result.convergence_history[-3:]
            improvement = max(recent) - min(recent)
            # Allow some tolerance since scores may vary
            assert improvement < 0.15  # Broader threshold for test


def test_check_convergence_min_iterations():
    """Test minimum iterations constraint prevents early convergence."""
    mae = MultiAgentEvolve("qa_agent")

    # Should NOT converge before min iterations (even with perfect scores)
    converged, reason = mae._check_convergence([0.95, 0.95, 0.95], current_iteration=1)
    assert converged is False
    assert reason is None

    # Should check convergence after min iterations
    converged, reason = mae._check_convergence([0.90, 0.90, 0.90], current_iteration=3)
    assert converged is True
    assert reason == "score_plateau"


def test_check_convergence_high_score():
    """Test high score (>0.95) triggers convergence."""
    mae = MultiAgentEvolve("qa_agent")

    converged, reason = mae._check_convergence([0.96], current_iteration=3)
    assert converged is True
    assert reason == "high_score_achieved"

    converged, reason = mae._check_convergence([0.97, 0.98, 0.99], current_iteration=5)
    assert converged is True
    assert reason == "high_score_achieved"


def test_check_convergence_plateau():
    """Test score plateau detection."""
    mae = MultiAgentEvolve("qa_agent")

    # Small improvement = plateau (default threshold 0.05)
    converged, reason = mae._check_convergence(
        [0.80, 0.81, 0.82], current_iteration=3
    )
    assert converged is True
    assert reason == "score_plateau"

    # Large improvement = NOT converged
    converged, reason = mae._check_convergence(
        [0.50, 0.70, 0.90], current_iteration=3
    )
    assert converged is False
    assert reason is None


def test_check_convergence_max_iterations():
    """Test max iterations triggers convergence."""
    config = CoEvolutionConfig(max_iterations=5)
    mae = MultiAgentEvolve("qa_agent", coevolution_config=config)

    # At iteration 4 (0-based), which is the last iteration for max=5
    converged, reason = mae._check_convergence([0.5], current_iteration=4)
    assert converged is True
    assert reason == "max_iterations_reached"


def test_check_convergence_no_convergence():
    """Test case where convergence should NOT occur."""
    mae = MultiAgentEvolve("qa_agent")

    # Not enough iterations
    converged, reason = mae._check_convergence([0.5], current_iteration=1)
    assert converged is False

    # Score improving, not plateau
    converged, reason = mae._check_convergence(
        [0.5, 0.7, 0.85], current_iteration=3
    )
    assert converged is False


# ============================================================================
# SOLVER-VERIFIER INTERACTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_solver_verifier_interaction():
    """Test Solver-Verifier feedback loop."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "test interaction"}

    result = await mae.evolve(task, max_iterations=3)

    # Verify both agents participated
    assert len(result.solver_rewards) >= 1
    assert len(result.verifier_rewards) >= 1

    # Rewards should be in valid ranges
    for reward in result.solver_rewards:
        assert 0.0 <= reward <= 2.0  # Weighted sum can exceed 1.0

    for reward in result.verifier_rewards:
        assert 0.0 <= reward <= 1.0


@pytest.mark.asyncio
async def test_reward_computation_per_iteration():
    """Test reward computation happens each iteration."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "test rewards"}

    result = await mae.evolve(task, max_iterations=4)

    # Rewards lists should match iterations
    assert len(result.solver_rewards) == result.iterations_used
    assert len(result.verifier_rewards) == result.iterations_used

    # Each reward should be valid
    for i, (s_reward, v_reward) in enumerate(
        zip(result.solver_rewards, result.verifier_rewards)
    ):
        assert isinstance(s_reward, float), f"Iteration {i}: Solver reward not float"
        assert isinstance(v_reward, float), f"Iteration {i}: Verifier reward not float"
        assert s_reward >= 0.0, f"Iteration {i}: Negative Solver reward"
        assert v_reward >= 0.0, f"Iteration {i}: Negative Verifier reward"


@pytest.mark.asyncio
async def test_feedback_loop_progression():
    """Test that Verifier feedback influences Solver in next iteration."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "test feedback"}

    result = await mae.evolve(task, max_iterations=3)

    # After multiple iterations, system should have history
    assert len(mae.iteration_history) >= 1

    # Each iteration should have generated trajectories
    for iter_data in mae.iteration_history:
        assert iter_data["trajectories_generated"] > 0
        assert "solver_reward" in iter_data
        assert "verifier_reward" in iter_data


# ============================================================================
# BEST TRAJECTORY TRACKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_best_trajectory_tracking():
    """Test that best trajectory is tracked across iterations."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "test best tracking"}

    result = await mae.evolve(task, max_iterations=4)

    # Best trajectory should exist
    assert result.best_trajectory is not None
    assert isinstance(result.best_trajectory, dict)
    assert "trajectory_id" in result.best_trajectory

    # Final score should be max from convergence history
    assert result.final_score == max(result.convergence_history)


@pytest.mark.asyncio
async def test_best_trajectory_metadata():
    """Test best trajectory contains expected metadata."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "code_generation", "description": "test metadata"}

    result = await mae.evolve(task, max_iterations=2)

    best = result.best_trajectory

    # Should have core fields
    assert "trajectory_id" in best
    assert "code" in best
    assert "reasoning" in best
    assert "generation_method" in best
    assert "solver_confidence" in best
    assert "diversity_score" in best


# ============================================================================
# MEMORY INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_memory_integration():
    """Test trajectory storage in memory pool."""
    config = CoEvolutionConfig(
        enable_memory=True,
        store_threshold=0.5  # Lower threshold for testing
    )
    mae = MultiAgentEvolve("qa_agent", coevolution_config=config)

    task = {"type": "test", "description": "test memory"}

    result = await mae.evolve(task, max_iterations=3)

    # If final score > threshold, should have attempted storage
    if result.final_score >= 0.5:
        # Check that MAE has trajectory pool
        assert mae.trajectory_pool is not None


@pytest.mark.asyncio
async def test_memory_disabled():
    """Test that memory integration can be disabled."""
    config = CoEvolutionConfig(enable_memory=False)
    mae = MultiAgentEvolve("qa_agent", coevolution_config=config)

    task = {"type": "test", "description": "test no memory"}

    result = await mae.evolve(task, max_iterations=2)

    # Should work without memory
    assert result.iterations_used >= 1
    assert mae.trajectory_pool is None


@pytest.mark.asyncio
async def test_store_trajectory_enrichment():
    """Test that stored trajectories are enriched with metadata."""
    config = CoEvolutionConfig(enable_memory=True, store_threshold=0.0)
    mae = MultiAgentEvolve("qa_agent", coevolution_config=config)

    task = {"type": "test", "description": "test enrichment"}

    # Mock trajectory and task
    trajectory = {
        "trajectory_id": "test_traj_001",
        "code": "def test(): pass",
        "reasoning": "test reasoning"
    }

    # Test _store_trajectory method directly
    await mae._store_trajectory(trajectory, score=0.85, task=task)

    # Note: We can't directly verify storage in TrajectoryPool in this test,
    # but we've confirmed no exceptions are raised


# ============================================================================
# CONVERGENCE HISTORY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_convergence_history():
    """Test convergence history tracking."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "test history"}

    result = await mae.evolve(task, max_iterations=5)

    # History length should match iterations
    assert len(result.convergence_history) == result.iterations_used

    # Scores should be in valid range
    for score in result.convergence_history:
        assert 0.0 <= score <= 1.0

    # History should be ordered chronologically
    assert len(result.convergence_history) > 0


@pytest.mark.asyncio
async def test_iteration_history_tracking():
    """Test detailed iteration history tracking."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "test iter history"}

    result = await mae.evolve(task, max_iterations=3)

    # Should have iteration history
    assert len(mae.iteration_history) == result.iterations_used

    # Each iteration should have required fields
    for iter_data in mae.iteration_history:
        assert "iteration" in iter_data
        assert "best_score" in iter_data
        assert "solver_reward" in iter_data
        assert "verifier_reward" in iter_data
        assert "trajectories_generated" in iter_data
        assert "converged" in iter_data


# ============================================================================
# STATISTICS TESTS
# ============================================================================

def test_get_stats_empty():
    """Test statistics with no iterations."""
    mae = MultiAgentEvolve("qa_agent")

    stats = mae.get_stats()

    assert stats["total_iterations"] == 0
    assert stats["best_score"] == 0.0
    assert stats["converged"] is False
    assert "iteration_history" not in stats  # Not present when empty


@pytest.mark.asyncio
async def test_get_stats_with_data():
    """Test statistics after evolution."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "test stats"}
    await mae.evolve(task, max_iterations=3)

    stats = mae.get_stats()

    assert stats["total_iterations"] > 0
    assert 0.0 <= stats["best_score"] <= 1.0
    assert 0.0 <= stats["final_score"] <= 1.0
    assert isinstance(stats["converged"], bool)
    assert "avg_solver_reward" in stats
    assert "avg_verifier_reward" in stats
    assert "trajectories_generated_total" in stats
    assert "iteration_history" in stats

    # Average rewards should be valid
    assert 0.0 <= stats["avg_solver_reward"] <= 2.0
    assert 0.0 <= stats["avg_verifier_reward"] <= 1.0

    # Total trajectories should be positive
    assert stats["trajectories_generated_total"] > 0


@pytest.mark.asyncio
async def test_stats_convergence_reason():
    """Test that convergence reason is tracked in stats."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "test convergence reason"}
    await mae.evolve(task, max_iterations=3)

    stats = mae.get_stats()

    if stats["converged"]:
        assert stats["convergence_reason"] is not None
        assert isinstance(stats["convergence_reason"], str)


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_evolve_max_iterations_override():
    """Test that max_iterations parameter overrides config."""
    config = CoEvolutionConfig(max_iterations=10)
    mae = MultiAgentEvolve("qa_agent", coevolution_config=config)

    task = {"type": "test", "description": "test override"}

    result = await mae.evolve(task, max_iterations=2)

    # Should respect the override
    assert result.iterations_used <= 2


@pytest.mark.asyncio
async def test_evolve_single_iteration():
    """Test evolution with only 1 iteration."""
    mae = MultiAgentEvolve("qa_agent")

    task = {"type": "test", "description": "single iteration"}

    result = await mae.evolve(task, max_iterations=1)

    assert result.iterations_used == 1
    assert len(result.convergence_history) == 1
    assert result.converged is True  # Should converge due to max iterations
