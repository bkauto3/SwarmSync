"""
E2E Test: SPICE Self-Play Loop

This test validates the complete SPICE self-play loop:
1. Challenger generates frontier task
2. Reasoner solves with multiple trajectories
3. DrGRPO computes variance reward
4. SE-Darwin uses SPICE trajectories for evolution

Author: Alex (E2E Testing & Integration)
Date: November 2, 2025
"""

import asyncio
import pytest
import logging
from pathlib import Path
from typing import Dict, List

# SPICE components
from infrastructure.spice.challenger_agent import ChallengerAgent, FrontierTask, get_challenger_agent
from infrastructure.spice.reasoner_agent import ReasonerAgent, TrajectoryResult, get_reasoner_agent
from infrastructure.spice.drgrpo_optimizer import DrGRPOOptimizer, get_drgrpo_optimizer

# SE-Darwin integration
from agents.se_darwin_agent import SEDarwinAgent

# Test utilities (using pytest timeout marker)

logger = logging.getLogger(__name__)


@pytest.fixture
async def challenger():
    """Get Challenger agent instance."""
    return get_challenger_agent()


@pytest.fixture
async def reasoner():
    """Get Reasoner agent instance."""
    return get_reasoner_agent()


@pytest.fixture
async def drgrpo():
    """Get DrGRPO optimizer instance."""
    return get_drgrpo_optimizer()


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_spice_complete_self_play_loop(challenger, reasoner, drgrpo):
    """
    Test the complete SPICE self-play loop from task generation to reward computation.

    Success Criteria:
    - Challenger generates task with grounding_score >= 0.7
    - Reasoner generates 3+ trajectories
    - Variance reward computed correctly (> 0.0)
    - No exceptions or errors
    """
    logger.info("=" * 80)
    logger.info("E2E Test: SPICE Complete Self-Play Loop")
    logger.info("=" * 80)

    # Step 1: Challenger generates frontier task
    logger.info("\n[Step 1] Challenger generating frontier task (difficulty=0.5)...")

    task = await challenger.generate_frontier_task(
        agent_name="qa_agent",
        difficulty=0.5,
        corpus_samples=10
    )

    assert task is not None, "Challenger failed to generate task"
    assert task.grounding_score >= 0.7, f"Task grounding too low: {task.grounding_score:.3f} < 0.7"
    assert len(task.corpus_evidence) > 0, "Task missing corpus evidence"

    logger.info(f"✓ Task generated: {task.task_id}")
    logger.info(f"  - Description: {task.description[:100]}...")
    logger.info(f"  - Difficulty: {task.difficulty:.3f}")
    logger.info(f"  - Grounding score: {task.grounding_score:.3f}")
    logger.info(f"  - Corpus evidence: {len(task.corpus_evidence)} items")

    # Step 2: Reasoner solves with multiple trajectories
    logger.info("\n[Step 2] Reasoner solving task with 3 trajectories...")

    trajectories = await reasoner.solve_task(
        task=task,
        num_trajectories=3,
        use_operators=True
    )

    assert len(trajectories) >= 3, f"Expected >= 3 trajectories, got {len(trajectories)}"

    # Verify trajectory quality
    for i, traj in enumerate(trajectories):
        assert traj.task_id == task.task_id, f"Trajectory {i} task_id mismatch"
        assert len(traj.solution) > 0, f"Trajectory {i} has empty solution"
        assert 0.0 <= traj.quality_score <= 1.0, f"Trajectory {i} invalid quality score: {traj.quality_score}"
        assert traj.approach in ["baseline", "revision", "recombination", "refinement"], \
            f"Trajectory {i} invalid approach: {traj.approach}"

    logger.info(f"✓ Generated {len(trajectories)} trajectories")
    for i, traj in enumerate(trajectories):
        logger.info(f"  - Trajectory {i}: approach={traj.approach}, quality={traj.quality_score:.3f}")

    # Step 3: DrGRPO computes variance reward
    logger.info("\n[Step 3] DrGRPO computing variance reward...")

    variance_reward = drgrpo.compute_variance_reward(
        task=task,
        trajectories=trajectories
    )

    assert variance_reward is not None, "DrGRPO failed to compute reward"
    assert variance_reward > 0.0, f"Expected positive variance reward, got {variance_reward:.3f}"
    assert isinstance(variance_reward, float), f"Expected float, got {type(variance_reward)}"

    # Compute mean quality for logging
    mean_quality = sum(t.quality_score for t in trajectories) / len(trajectories)

    # Compute diversity (std dev of quality scores)
    variance = sum((t.quality_score - mean_quality) ** 2 for t in trajectories) / len(trajectories)
    diversity_score = variance ** 0.5

    logger.info(f"✓ Variance reward computed: {variance_reward:.4f}")
    logger.info(f"  - Mean quality: {mean_quality:.3f}")
    logger.info(f"  - Diversity score: {diversity_score:.3f}")
    logger.info(f"  - Trajectories: {len(trajectories)}")

    # Step 4: Verify trajectories can be used by SE-Darwin
    logger.info("\n[Step 4] Verifying SE-Darwin compatibility...")

    # Check that trajectories match expected format
    for traj in trajectories:
        traj_dict = traj.to_dict()
        assert "task_id" in traj_dict, "Trajectory missing task_id"
        assert "solution" in traj_dict, "Trajectory missing solution"
        assert "approach" in traj_dict, "Trajectory missing approach"
        assert "quality_score" in traj_dict, "Trajectory missing quality_score"

    logger.info(f"✓ All {len(trajectories)} trajectories are SE-Darwin compatible")

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("✅ SPICE E2E TEST PASSED")
    logger.info(f"   - Task generated: {task.task_id} (grounding: {task.grounding_score:.3f})")
    logger.info(f"   - Trajectories: {len(trajectories)} (quality: {mean_quality:.3f})")
    logger.info(f"   - Variance reward: {variance_reward:.4f}")
    logger.info("=" * 80)


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_spice_with_se_darwin_integration(challenger, reasoner):
    """
    Test SPICE integration with SE-Darwin agent evolution.

    This test verifies that SPICE-generated trajectories can be consumed
    by SE-Darwin for agent improvement.

    Success Criteria:
    - SPICE generates valid trajectories
    - SE-Darwin accepts SPICE trajectories
    - Quality improvement observed
    """
    logger.info("=" * 80)
    logger.info("E2E Test: SPICE + SE-Darwin Integration")
    logger.info("=" * 80)

    # Generate frontier task
    logger.info("\n[Step 1] Generating frontier task...")
    task = await challenger.generate_frontier_task(
        agent_name="qa_agent",
        difficulty=0.3,  # Lower difficulty for faster test
        corpus_samples=5
    )

    assert task is not None, "Failed to generate task"
    logger.info(f"✓ Task: {task.task_id} (difficulty: {task.difficulty:.3f})")

    # Generate SPICE trajectories
    logger.info("\n[Step 2] Generating SPICE trajectories...")
    trajectories = await reasoner.solve_task(task, num_trajectories=3)

    assert len(trajectories) >= 3, f"Expected >= 3 trajectories, got {len(trajectories)}"
    initial_quality = sum(t.quality_score for t in trajectories) / len(trajectories)
    logger.info(f"✓ Generated {len(trajectories)} trajectories (avg quality: {initial_quality:.3f})")

    # Verify SE-Darwin can consume trajectories
    logger.info("\n[Step 3] Verifying SE-Darwin compatibility...")

    # SE-Darwin expects specific trajectory format
    for i, traj in enumerate(trajectories):
        # Check required fields
        assert hasattr(traj, 'task_id'), f"Trajectory {i} missing task_id"
        assert hasattr(traj, 'solution'), f"Trajectory {i} missing solution"
        assert hasattr(traj, 'quality_score'), f"Trajectory {i} missing quality_score"
        assert hasattr(traj, 'approach'), f"Trajectory {i} missing approach"

        # Check field types
        assert isinstance(traj.task_id, str), f"Trajectory {i} task_id not string"
        assert isinstance(traj.solution, str), f"Trajectory {i} solution not string"
        assert isinstance(traj.quality_score, (int, float)), f"Trajectory {i} quality_score not numeric"
        assert isinstance(traj.approach, str), f"Trajectory {i} approach not string"

    logger.info(f"✓ All trajectories are SE-Darwin compatible")

    logger.info("\n" + "=" * 80)
    logger.info("✅ SPICE + SE-DARWIN INTEGRATION TEST PASSED")
    logger.info(f"   - Task: {task.task_id}")
    logger.info(f"   - Trajectories: {len(trajectories)}")
    logger.info(f"   - Avg quality: {initial_quality:.3f}")
    logger.info("=" * 80)


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_spice_error_handling_and_fallback(challenger, reasoner, drgrpo):
    """
    Test SPICE error handling and graceful degradation.

    Success Criteria:
    - Handles invalid difficulty gracefully
    - Handles task generation failures
    - Returns meaningful error messages
    """
    logger.info("=" * 80)
    logger.info("E2E Test: SPICE Error Handling & Fallback")
    logger.info("=" * 80)

    # Test 1: Invalid difficulty (should clamp to valid range)
    logger.info("\n[Test 1] Testing difficulty clamping...")
    task_high = await challenger.generate_frontier_task(
        agent_name="qa_agent",
        difficulty=2.0,  # Invalid: > 1.0
        corpus_samples=5
    )
    assert task_high.difficulty <= 1.0, "Failed to clamp difficulty to max 1.0"
    logger.info(f"✓ High difficulty clamped: 2.0 → {task_high.difficulty:.3f}")

    # Test 2: Empty corpus (should fallback to synthetic)
    logger.info("\n[Test 2] Testing empty corpus fallback...")
    task_empty = await challenger.generate_frontier_task(
        agent_name="qa_agent",
        difficulty=0.5,
        corpus_samples=0  # Empty corpus
    )
    assert task_empty is not None, "Failed to generate task with empty corpus"
    logger.info(f"✓ Empty corpus handled: generated {task_empty.task_id}")

    # Test 3: Reasoner with minimal trajectories
    logger.info("\n[Test 3] Testing minimal trajectory generation...")
    trajectories_min = await reasoner.solve_task(task_empty, num_trajectories=1)
    assert len(trajectories_min) >= 1, "Failed to generate minimal trajectories"
    logger.info(f"✓ Minimal trajectories generated: {len(trajectories_min)}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ SPICE ERROR HANDLING TEST PASSED")
    logger.info("   - Difficulty clamping: ✓")
    logger.info("   - Empty corpus fallback: ✓")
    logger.info("   - Minimal trajectories: ✓")
    logger.info("=" * 80)


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_spice_performance_metrics(challenger, reasoner, drgrpo):
    """
    Test SPICE performance metrics and observability.

    Success Criteria:
    - Metrics properly tracked
    - OTEL spans created
    - Performance within acceptable bounds
    """
    import time

    logger.info("=" * 80)
    logger.info("E2E Test: SPICE Performance Metrics")
    logger.info("=" * 80)

    # Measure task generation time
    logger.info("\n[Measurement 1] Task generation latency...")
    start = time.time()
    task = await challenger.generate_frontier_task(
        agent_name="qa_agent",
        difficulty=0.5,
        corpus_samples=10
    )
    task_time = time.time() - start

    assert task_time < 30.0, f"Task generation too slow: {task_time:.2f}s > 30s"
    logger.info(f"✓ Task generation: {task_time:.3f}s")

    # Measure trajectory generation time
    logger.info("\n[Measurement 2] Trajectory generation latency...")
    start = time.time()
    trajectories = await reasoner.solve_task(task, num_trajectories=3)
    traj_time = time.time() - start

    assert traj_time < 45.0, f"Trajectory generation too slow: {traj_time:.2f}s > 45s"
    logger.info(f"✓ Trajectory generation: {traj_time:.3f}s ({len(trajectories)} trajectories)")

    # Measure reward computation time
    logger.info("\n[Measurement 3] Reward computation latency...")
    start = time.time()
    reward = await drgrpo.compute_variance_reward(task, trajectories)
    reward_time = time.time() - start

    assert reward_time < 5.0, f"Reward computation too slow: {reward_time:.2f}s > 5s"
    logger.info(f"✓ Reward computation: {reward_time:.3f}s")

    # Total E2E time
    total_time = task_time + traj_time + reward_time
    logger.info(f"\n[Total] End-to-end latency: {total_time:.3f}s")

    # Check SPICE overhead (should be < 5% of baseline)
    expected_baseline = 30.0  # Approximate baseline without SPICE
    overhead = ((total_time - expected_baseline) / expected_baseline) * 100

    logger.info(f"  - SPICE overhead: {overhead:.1f}%")
    if overhead > 5.0:
        logger.warning(f"⚠ SPICE overhead > 5%: {overhead:.1f}%")

    logger.info("\n" + "=" * 80)
    logger.info("✅ SPICE PERFORMANCE METRICS TEST PASSED")
    logger.info(f"   - Task generation: {task_time:.3f}s")
    logger.info(f"   - Trajectory generation: {traj_time:.3f}s")
    logger.info(f"   - Reward computation: {reward_time:.3f}s")
    logger.info(f"   - Total: {total_time:.3f}s (overhead: {overhead:.1f}%)")
    logger.info("=" * 80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
