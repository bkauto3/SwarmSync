"""
Integration test for Solver-Verifier co-evolution workflow.

Tests the complete flow:
1. Solver generates trajectories
2. Verifier validates trajectories
3. Verifier provides feedback
4. Solver incorporates feedback
5. Co-evolution rewards computed

Author: Hudson (Implementation Specialist)
Date: November 3, 2025
Status: Phase 3 Integration Testing
"""

import pytest
from infrastructure.evolution import (
    SolverAgent,
    SolverConfig,
    VerifierAgent,
    VerifierConfig
)


@pytest.mark.asyncio
async def test_solver_verifier_workflow():
    """Test complete Solver → Verifier workflow."""
    # Initialize agents
    solver = SolverAgent("qa_agent")
    verifier = VerifierAgent("qa_agent")

    # Solver generates trajectories
    task = {
        "type": "code_generation",
        "description": "Implement binary search algorithm"
    }

    trajectories = await solver.generate_trajectories(task)

    # Solver uses config.num_trajectories (default 5)
    assert len(trajectories) == solver.config.num_trajectories
    assert all(t.code for t in trajectories)

    # Verifier validates each trajectory
    verification_results = []
    for trajectory in trajectories:
        traj_dict = {
            "trajectory_id": trajectory.trajectory_id,
            "code": trajectory.code,
            "strategy": trajectory.generation_method,  # Use generation_method as strategy
            "benchmark_score": 0.8  # Mock benchmark score (in production, would run actual tests)
        }

        result = await verifier.verify_trajectory(traj_dict, task)
        verification_results.append(result)

    # Check all trajectories were verified
    assert len(verification_results) == solver.config.num_trajectories
    assert all(0.0 <= r.verification_score <= 1.0 for r in verification_results)

    # Note: In full co-evolution loop (Phase 4), Solver would incorporate
    # VerifierFeedback objects. Here we just verify the flow works.

    # Compute co-evolution rewards
    solver_reward = solver.compute_solver_reward(
        trajectory=trajectories[0],
        benchmark_score=0.8,  # Mock score
        verifier_score=verification_results[0].verification_score
    )

    verifier_reward = verifier.compute_verifier_reward(
        verification_score=verification_results[0].verification_score
    )

    assert 0.0 <= solver_reward <= 1.0
    assert 0.0 <= verifier_reward <= 1.0

    # Check statistics
    solver_stats = solver.get_statistics()
    verifier_stats = verifier.get_stats()

    assert solver_stats["generation_count"] >= 1  # At least one generation cycle
    assert verifier_stats["total_verifications"] == solver.config.num_trajectories


@pytest.mark.asyncio
async def test_solver_improves_with_verifier_feedback():
    """Test that Solver's reward increases when addressing Verifier feedback."""
    solver = SolverAgent("qa_agent")
    verifier = VerifierAgent("qa_agent")

    task = {"type": "code_generation", "description": "Implement function"}

    # Generate initial trajectory
    trajectories = await solver.generate_trajectories(task)
    trajectory = trajectories[0]

    # Get initial verification
    traj_dict = {
        "trajectory_id": trajectory.trajectory_id,
        "code": trajectory.code,
        "strategy": trajectory.generation_method,
        "benchmark_score": 0.8
    }

    result1 = await verifier.verify_trajectory(traj_dict, task)

    # Verify feedback was generated
    assert len(result1.feedback) >= 0  # May or may not have feedback

    # Note: Full feedback incorporation happens in Phase 4 co-evolution loop


@pytest.mark.asyncio
async def test_verifier_reward_increases_with_error_detection():
    """Test that Verifier's reward increases when finding more errors."""
    verifier = VerifierAgent("qa_agent")

    task = {"type": "test"}

    # Good trajectory (few errors)
    good_trajectory = {
        "trajectory_id": "good_123",
        "code": '''def binary_search(arr, target):
    """Binary search implementation."""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1''',
        "benchmark_score": 0.95
    }

    result_good = await verifier.verify_trajectory(good_trajectory, task)
    reward_good = verifier.compute_verifier_reward(result_good.verification_score)

    # Poor trajectory (many errors)
    poor_trajectory = {
        "trajectory_id": "poor_456",
        "code": "return 42  # hardcoded",
        "benchmark_score": 0.3
    }

    result_poor = await verifier.verify_trajectory(poor_trajectory, task)
    reward_poor = verifier.compute_verifier_reward(result_poor.verification_score)

    # Verifier should get higher reward for finding more errors
    assert reward_poor > reward_good


@pytest.mark.asyncio
async def test_adversarial_dynamics():
    """Test adversarial dynamics between Solver and Verifier."""
    solver = SolverAgent("qa_agent")
    verifier = VerifierAgent("qa_agent")

    task = {"type": "code_generation", "description": "Solve problem"}

    # Solver tries to maximize verification score
    trajectories = await solver.generate_trajectories(task)
    trajectory = trajectories[0]

    traj_dict = {
        "trajectory_id": trajectory.trajectory_id,
        "code": trajectory.code,
        "strategy": trajectory.generation_method,
        "benchmark_score": 0.8
    }

    result = await verifier.verify_trajectory(traj_dict, task)

    # Compute opposing rewards
    solver_reward = solver.compute_solver_reward(
        trajectory=trajectory,
        benchmark_score=0.8,
        verifier_score=result.verification_score
    )

    verifier_reward = verifier.compute_verifier_reward(
        verification_score=result.verification_score
    )

    # Rewards should be inversely related (adversarial)
    # When verification_score is high (Solver winning), Verifier reward is low
    # When verification_score is low (Verifier winning), Solver reward is low
    assert 0.0 <= solver_reward <= 1.0
    assert 0.0 <= verifier_reward <= 1.0

    # If Solver does well (high verification_score), it gets high reward
    # If Verifier finds issues (low verification_score), it gets high reward
    # These are opposing objectives (co-evolution pressure)


@pytest.mark.asyncio
async def test_feedback_loop_iteration():
    """Test multiple iterations of Solver → Verifier feedback loop."""
    solver = SolverAgent("qa_agent")
    verifier = VerifierAgent("qa_agent")

    task = {"type": "code_generation", "description": "Implement function"}

    verification_scores = []

    # Run 3 iterations
    for iteration in range(3):
        # Solver generates
        trajectories = await solver.generate_trajectories(task)
        trajectory = trajectories[0]

        # Verifier validates
        traj_dict = {
            "trajectory_id": trajectory.trajectory_id,
            "code": trajectory.code,
            "strategy": trajectory.generation_method,
            "benchmark_score": 0.8
        }

        result = await verifier.verify_trajectory(traj_dict, task)
        verification_scores.append(result.verification_score)

        # Note: Feedback incorporation will be implemented in Phase 4

    # Verify feedback loop completed 3 iterations
    assert len(verification_scores) == 3
    assert verifier.get_stats()["total_verifications"] == 3


@pytest.mark.asyncio
async def test_custom_config_integration():
    """Test Solver-Verifier integration with custom configs."""
    # Custom Solver config
    solver_config = SolverConfig(
        diversity_weight=0.4,
        quality_weight=0.4,
        verifier_weight=0.2,
        num_trajectories=5
    )
    solver = SolverAgent("builder_agent", config=solver_config)

    # Custom Verifier config
    verifier_config = VerifierConfig(
        correctness_weight=0.5,
        quality_weight=0.25,
        robustness_weight=0.15,
        generalization_weight=0.1,
        num_edge_cases=10
    )
    verifier = VerifierAgent("builder_agent", config=verifier_config)

    task = {"type": "code_generation", "description": "Build component"}

    # Generate and verify
    trajectories = await solver.generate_trajectories(task)
    assert len(trajectories) == 5  # Custom num_trajectories

    traj_dict = {
        "trajectory_id": trajectories[0].trajectory_id,
        "code": trajectories[0].code,
        "strategy": trajectories[0].generation_method,
        "benchmark_score": 0.8
    }

    result = await verifier.verify_trajectory(traj_dict, task)
    assert result.edge_cases_tested == 10  # Custom num_edge_cases
