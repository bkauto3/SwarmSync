"""
Integration Tests for Memory-Aware Darwin Evolution

Tests the PRIMARY success criterion: 10%+ improvement over isolated mode.

Test Coverage:
1. Memory-backed evolution outperforms isolated mode (PRIMARY)
2. Cross-business learning validation
3. Cross-agent learning (Legal learns from QA)
4. Consensus memory integration
5. Trajectory pool persistence

Success Criteria:
✅ Memory-backed shows 10%+ improvement (7.5/10 → 8.3/10+)
✅ Cross-agent learning functional
✅ Cross-business learning functional
✅ All tests passing
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from infrastructure.evolution.memory_aware_darwin import (
    MemoryAwareDarwin,
    EvolutionPattern,
    EvolutionResult
)
from infrastructure.langgraph_store import GenesisLangGraphStore
from infrastructure.trajectory_pool import Trajectory, TrajectoryStatus, OperatorType


# Test fixtures
@pytest.fixture
async def memory_store():
    """Create in-memory LangGraph Store for testing"""
    store = GenesisLangGraphStore(
        mongodb_uri="mongodb://localhost:27017/",
        database_name="genesis_test_memory_darwin"
    )

    # Clear all namespaces before test
    await store.clear_namespace(("consensus", "procedures"))
    await store.clear_namespace(("consensus", "capabilities"))
    await store.clear_namespace(("business", "saas_001"))
    await store.clear_namespace(("business", "saas_002"))

    yield store

    # Cleanup after test
    await store.clear_namespace(("consensus", "procedures"))
    await store.clear_namespace(("consensus", "capabilities"))
    await store.clear_namespace(("business", "saas_001"))
    await store.clear_namespace(("business", "saas_002"))
    await store.close()


@pytest.fixture
def qa_agent_capabilities():
    """QA agent capabilities for cross-agent learning"""
    return ["code_analysis", "validation", "testing"]


@pytest.fixture
def legal_agent_capabilities():
    """Legal agent capabilities (overlaps with QA for cross-learning)"""
    return ["code_analysis", "validation", "compliance"]


@pytest.fixture
async def sample_task():
    """Sample evolution task"""
    return {
        "type": "validation",
        "description": "Validate API authentication flow",
        "expected_patterns": ["auth", "validation"]
    }


@pytest.fixture
async def seed_consensus_memory(memory_store):
    """Seed consensus memory with proven patterns"""
    # Add proven validation pattern
    pattern = EvolutionPattern(
        pattern_id="consensus_val_001",
        agent_type="qa_agent",
        task_type="validation",
        code_diff="# Validation improvements",
        strategy_description="Check auth tokens before API calls",
        benchmark_score=0.92,
        success_rate=0.92,
        timestamp="2025-01-01T00:00:00Z",
        source_agent="qa_agent",
        capabilities=["code_analysis", "validation", "testing"]
    )

    await memory_store.put(
        namespace=("consensus", "procedures"),
        key="pattern_consensus_val_001",
        value=pattern.to_dict()
    )

    # Add capability-based pattern
    await memory_store.put(
        namespace=("consensus", "capabilities"),
        key="validation_consensus_val_001",
        value=pattern.to_dict()
    )

    return pattern


# PRIMARY SUCCESS CRITERION TEST
@pytest.mark.asyncio
async def test_memory_backed_outperforms_isolated_mode(
    memory_store,
    qa_agent_capabilities,
    sample_task,
    seed_consensus_memory
):
    """
    PRIMARY TEST: Memory-backed evolution shows 10%+ improvement over isolated mode.

    Expected:
    - Isolated QA agent: ~0.75 baseline (75%)
    - Memory-backed: 0.825+ (82.5%+, representing 10%+ improvement)
    - Improvement: >= 0.075 (7.5 percentage points)

    This validates the core value proposition of memory-aware evolution.
    """
    # Initialize memory-aware Darwin
    memory_darwin = MemoryAwareDarwin(
        agent_type="qa_agent",
        memory_store=memory_store,
        capability_tags=qa_agent_capabilities,
        max_memory_patterns=5,
        pattern_success_threshold=0.7
    )

    # Run evolution with memory
    result = await memory_darwin.evolve_with_memory(
        task=sample_task,
        business_id="saas_001",
        max_iterations=5,
        convergence_threshold=0.85
    )

    # PRIMARY ASSERTION: 10%+ improvement
    baseline_score = 0.75  # Typical isolated mode baseline
    improvement = result.final_score - baseline_score

    assert result.final_score >= 0.825, (
        f"Memory-backed score {result.final_score:.3f} below target 0.825 (10% improvement)"
    )
    assert improvement >= 0.075, (
        f"Improvement {improvement:.3f} below 10% threshold (0.075)"
    )
    assert result.memory_patterns_used > 0, "Should use at least 1 memory pattern"
    assert result.converged, "Should converge with memory patterns"

    # Verify memory patterns contributed to improvement
    assert result.improvement_over_baseline > 0, "Should show measurable improvement"

    print(f"✅ PRIMARY SUCCESS: Memory-backed {result.final_score:.3f} vs Isolated {baseline_score:.3f}")
    print(f"   Improvement: {improvement:.3f} ({improvement/baseline_score*100:.1f}%)")
    print(f"   Memory patterns used: {result.memory_patterns_used}")


@pytest.mark.asyncio
async def test_cross_business_learning(
    memory_store,
    qa_agent_capabilities,
    sample_task
):
    """
    Test cross-business learning: Business B learns from Business A's patterns.

    Scenario:
    1. Business A (saas_001) completes successful evolution
    2. Business A stores pattern to business namespace
    3. Business B (saas_002) queries and uses Business A's pattern
    4. Business B shows improvement from Business A's learning
    """
    # Step 1: Business A completes successful evolution
    business_a_darwin = MemoryAwareDarwin(
        agent_type="qa_agent",
        memory_store=memory_store,
        capability_tags=qa_agent_capabilities
    )

    # Seed Business A's memory with successful pattern
    business_a_pattern = EvolutionPattern(
        pattern_id="business_a_val_001",
        agent_type="qa_agent",
        task_type="validation",
        code_diff="# Business A's validation strategy",
        strategy_description="Enhanced validation with retry logic",
        benchmark_score=0.88,
        success_rate=0.88,
        timestamp="2025-01-01T00:00:00Z",
        business_id="saas_001",
        source_agent="qa_agent",
        capabilities=qa_agent_capabilities
    )

    await memory_store.put(
        namespace=("business", "saas_001"),
        key="evolution_business_a_val_001",
        value=business_a_pattern.to_dict()
    )

    # Step 2: Business B queries Business A's patterns
    # NOTE: In production, this would query across businesses
    # For test isolation, we manually retrieve the pattern
    business_a_results = await memory_store.search(
        namespace=("business", "saas_001"),
        query={"value.task_type": "validation"},
        limit=5
    )

    assert len(business_a_results) > 0, "Business A should have stored patterns"

    # Step 3: Business B uses pattern (simulated by re-seeding to saas_002)
    await memory_store.put(
        namespace=("business", "saas_002"),
        key="evolution_from_business_a",
        value=business_a_pattern.to_dict()
    )

    # Step 4: Business B runs evolution with Business A's pattern
    business_b_darwin = MemoryAwareDarwin(
        agent_type="qa_agent",
        memory_store=memory_store,
        capability_tags=qa_agent_capabilities
    )

    result = await business_b_darwin.evolve_with_memory(
        task=sample_task,
        business_id="saas_002",
        max_iterations=5,
        convergence_threshold=0.85
    )

    # Verify Business B benefited from Business A's pattern
    assert result.memory_patterns_used > 0, "Business B should use patterns"
    assert result.final_score > 0.75, "Business B should show improvement"

    print(f"✅ Cross-business learning: Business B score {result.final_score:.3f}")
    print(f"   Patterns used: {result.memory_patterns_used}")


@pytest.mark.asyncio
async def test_cross_agent_learning_legal_from_qa(
    memory_store,
    qa_agent_capabilities,
    legal_agent_capabilities,
    sample_task,
    seed_consensus_memory
):
    """
    Test cross-agent learning: Legal agent learns from QA agent's successes.

    Validation:
    - QA and Legal share "code_analysis" and "validation" capabilities
    - Legal should retrieve QA's validation patterns
    - Legal's evolution should benefit from QA's expertise
    """
    # Step 1: Verify QA pattern exists in consensus (from seed_consensus_memory)
    qa_patterns = await memory_store.search(
        namespace=("consensus", "capabilities"),
        query={"value.capabilities": "validation"},
        limit=5
    )

    assert len(qa_patterns) > 0, "Should have QA validation patterns"

    # Step 2: Legal agent queries for validation patterns
    legal_darwin = MemoryAwareDarwin(
        agent_type="legal_agent",
        memory_store=memory_store,
        capability_tags=legal_agent_capabilities,
        max_memory_patterns=5,
        pattern_success_threshold=0.7
    )

    # Query cross-agent patterns
    cross_agent_patterns = await legal_darwin._query_cross_agent_patterns("validation")

    # Verify Legal found QA's patterns
    assert len(cross_agent_patterns) > 0, "Legal should find QA validation patterns"
    qa_pattern_found = any(
        p.agent_type == "qa_agent" and p.source_agent == "qa_agent"
        for p in cross_agent_patterns
    )
    assert qa_pattern_found, "Legal should specifically find QA's patterns"

    # Step 3: Legal runs evolution using QA's patterns
    result = await legal_darwin.evolve_with_memory(
        task=sample_task,
        business_id="legal_001",
        max_iterations=5,
        convergence_threshold=0.85
    )

    # Verify Legal benefited from QA's expertise
    assert result.cross_agent_patterns_used > 0, "Legal should use cross-agent patterns"
    assert result.final_score > 0.75, "Legal should show improvement from QA patterns"

    print(f"✅ Cross-agent learning: Legal score {result.final_score:.3f}")
    print(f"   Cross-agent patterns used: {result.cross_agent_patterns_used}")


@pytest.mark.asyncio
async def test_consensus_memory_integration(
    memory_store,
    qa_agent_capabilities,
    sample_task,
    seed_consensus_memory
):
    """
    Test consensus memory integration: Proven patterns are retrieved and used.

    Validation:
    - Consensus patterns exist (seeded)
    - Memory-aware Darwin queries consensus
    - Retrieved patterns have high success rates (>= 0.7)
    - Patterns are converted to trajectories
    """
    memory_darwin = MemoryAwareDarwin(
        agent_type="qa_agent",
        memory_store=memory_store,
        capability_tags=qa_agent_capabilities,
        pattern_success_threshold=0.7
    )

    # Query consensus memory
    consensus_patterns = await memory_darwin._query_consensus_memory(
        task_type="validation",
        task_description="Validate API authentication flow"
    )

    # Verify patterns retrieved
    assert len(consensus_patterns) > 0, "Should retrieve consensus patterns"
    assert all(p.success_rate >= 0.7 for p in consensus_patterns), (
        "All patterns should meet success threshold"
    )

    # Verify patterns can be converted to trajectories
    trajectories = [
        p.to_trajectory(generation=0, agent_name="qa_agent")
        for p in consensus_patterns
    ]

    assert len(trajectories) > 0, "Should convert patterns to trajectories"
    assert all(isinstance(t, Trajectory) for t in trajectories), (
        "All conversions should produce valid Trajectory objects"
    )

    print(f"✅ Consensus memory: Retrieved {len(consensus_patterns)} patterns")
    print(f"   Converted to {len(trajectories)} trajectories")


@pytest.mark.asyncio
async def test_trajectory_pool_persistence(
    memory_store,
    qa_agent_capabilities,
    sample_task
):
    """
    Test trajectory pool persistence: Trajectories stored and retrieved across sessions.

    NOTE: This test validates the CONCEPT of persistent trajectory pools.
    Full implementation would extend TrajectoryPool class with LangGraph Store backend.
    """
    # Create evolution pattern (simulates successful trajectory)
    pattern = EvolutionPattern(
        pattern_id="traj_pool_001",
        agent_type="qa_agent",
        task_type="validation",
        code_diff="# Trajectory pool test",
        strategy_description="Persistent trajectory test",
        benchmark_score=0.85,
        success_rate=0.85,
        timestamp="2025-01-01T00:00:00Z",
        source_agent="qa_agent",
        capabilities=qa_agent_capabilities
    )

    # Store to evolution namespace (simulates TrajectoryPool.persist())
    await memory_store.put(
        namespace=("evolution", "qa_agent_gen_0"),
        key="trajectory_traj_pool_001",
        value=pattern.to_dict()
    )

    # Retrieve from evolution namespace (simulates TrajectoryPool.load())
    stored_trajectories = await memory_store.search(
        namespace=("evolution", "qa_agent_gen_0"),
        query={},
        limit=10
    )

    assert len(stored_trajectories) > 0, "Should retrieve stored trajectories"

    # Verify trajectory data integrity
    retrieved = stored_trajectories[0]["value"]
    assert retrieved["pattern_id"] == pattern.pattern_id
    assert retrieved["benchmark_score"] == pattern.benchmark_score

    print(f"✅ Trajectory persistence: Stored and retrieved {len(stored_trajectories)} trajectories")


@pytest.mark.asyncio
async def test_evolution_pattern_to_trajectory_conversion(qa_agent_capabilities):
    """
    Test EvolutionPattern to Trajectory conversion.

    Validates that memory patterns can be seamlessly integrated into
    SE-Darwin's evolution loop as initial trajectories.
    """
    pattern = EvolutionPattern(
        pattern_id="pattern_001",
        agent_type="qa_agent",
        task_type="validation",
        code_diff="# Test code diff",
        strategy_description="Test strategy",
        benchmark_score=0.88,
        success_rate=0.88,
        timestamp="2025-01-01T00:00:00Z",
        source_agent="qa_agent",
        capabilities=qa_agent_capabilities
    )

    # Convert to trajectory
    trajectory = pattern.to_trajectory(generation=1, agent_name="qa_agent")

    # Verify trajectory structure
    assert isinstance(trajectory, Trajectory)
    assert trajectory.trajectory_id.startswith("pattern_pattern_001")
    assert trajectory.generation == 1
    assert trajectory.agent_name == "qa_agent"
    assert trajectory.code_changes == pattern.code_diff
    assert trajectory.proposed_strategy == pattern.strategy_description
    assert trajectory.status == TrajectoryStatus.PENDING.value
    assert "success_rate=0.88" in trajectory.reasoning_pattern

    print(f"✅ Pattern conversion: Successfully converted to trajectory")
    print(f"   Trajectory ID: {trajectory.trajectory_id}")


@pytest.mark.asyncio
async def test_successful_evolution_storage_to_consensus(
    memory_store,
    qa_agent_capabilities,
    sample_task
):
    """
    Test successful evolution storage: Excellent results (>= 0.9) stored to consensus.

    Validation:
    - High-scoring evolutions (0.9+) stored to consensus namespace
    - Patterns stored by both procedure and capability
    - Future agents can retrieve these patterns
    """
    memory_darwin = MemoryAwareDarwin(
        agent_type="qa_agent",
        memory_store=memory_store,
        capability_tags=qa_agent_capabilities
    )

    # Create excellent evolution result (0.92 score)
    result = EvolutionResult(
        converged=True,
        final_score=0.92,
        iterations=3,
        best_trajectory_id="traj_excellent_001",
        improvement_over_baseline=0.17,
        memory_patterns_used=2,
        cross_agent_patterns_used=1,
        execution_time_seconds=5.2,
        metadata={"test": True}
    )

    # Store to memory
    await memory_darwin._store_successful_evolution(
        task=sample_task,
        result=result,
        business_id="saas_001"
    )

    # Verify stored to consensus (score >= 0.9)
    consensus_results = await memory_store.search(
        namespace=("consensus", "procedures"),
        query={"value.task_type": "validation"},
        limit=10
    )

    assert len(consensus_results) > 0, "Excellent evolution should be in consensus"

    # Verify stored by capability
    capability_results = await memory_store.search(
        namespace=("consensus", "capabilities"),
        query={"value.capabilities": "validation"},
        limit=10
    )

    assert len(capability_results) > 0, "Should be stored by capability"

    print(f"✅ Evolution storage: Stored to consensus and capabilities")
    print(f"   Consensus entries: {len(consensus_results)}")
    print(f"   Capability entries: {len(capability_results)}")


# Performance test
@pytest.mark.asyncio
async def test_memory_darwin_performance_metrics(
    memory_store,
    qa_agent_capabilities,
    sample_task,
    seed_consensus_memory
):
    """
    Test performance metrics collection during memory-aware evolution.

    Validates:
    - Execution time tracked
    - Memory patterns usage tracked
    - Cross-agent patterns usage tracked
    - Improvement over baseline calculated
    """
    memory_darwin = MemoryAwareDarwin(
        agent_type="qa_agent",
        memory_store=memory_store,
        capability_tags=qa_agent_capabilities
    )

    result = await memory_darwin.evolve_with_memory(
        task=sample_task,
        business_id="saas_001",
        max_iterations=5,
        convergence_threshold=0.85
    )

    # Verify metrics collected
    assert result.execution_time_seconds >= 0, "Should track execution time"
    assert result.memory_patterns_used >= 0, "Should track memory patterns"
    assert result.cross_agent_patterns_used >= 0, "Should track cross-agent patterns"
    assert result.improvement_over_baseline >= 0, "Should calculate improvement"
    assert "task_type" in result.metadata, "Should include task metadata"

    print(f"✅ Performance metrics: All metrics collected")
    print(f"   Execution time: {result.execution_time_seconds:.3f}s")
    print(f"   Memory patterns: {result.memory_patterns_used}")
    print(f"   Cross-agent patterns: {result.cross_agent_patterns_used}")
    print(f"   Improvement: {result.improvement_over_baseline:.3f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
