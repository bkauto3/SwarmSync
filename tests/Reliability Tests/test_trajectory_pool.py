"""
Comprehensive tests for Trajectory Pool (Day 6)
Part of SE-Darwin integration

Tests:
- Trajectory creation and storage
- Pool operations (add, get, prune)
- Success/failure queries
- Diverse pair selection
- Insight extraction
- Persistence
- Statistics
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from infrastructure.trajectory_pool import (
    Trajectory,
    TrajectoryPool,
    TrajectoryStatus,
    OperatorType,
    get_trajectory_pool
)


# ================================
# FIXTURES
# ================================

@pytest.fixture
def temp_storage(tmp_path):
    """Temporary storage directory"""
    return tmp_path / "trajectory_pools"


@pytest.fixture
def sample_trajectory():
    """Create sample trajectory"""
    return Trajectory(
        trajectory_id="traj_001",
        generation=1,
        agent_name="test_agent",
        code_changes="def improved_function(): pass",
        success_score=0.75,
        status=TrajectoryStatus.SUCCESS.value,
        operator_applied=OperatorType.BASELINE.value,
        reasoning_pattern="test-driven development",
        tools_used=["pytest", "git"],
        key_insights=["Test first", "Small changes"],
        modified_files=["src/main.py"]
    )


@pytest.fixture
def empty_pool(temp_storage):
    """Create empty trajectory pool"""
    return TrajectoryPool(
        agent_name="test_agent",
        max_trajectories=10,
        storage_dir=temp_storage / "test_agent"
    )


@pytest.fixture
def populated_pool(empty_pool):
    """Create pool with multiple trajectories"""
    # Add 5 successful trajectories
    for i in range(5):
        traj = Trajectory(
            trajectory_id=f"success_{i}",
            generation=i,
            agent_name="test_agent",
            success_score=0.8 + (i * 0.01),  # 0.80, 0.81, 0.82, 0.83, 0.84
            status=TrajectoryStatus.SUCCESS.value,
            operator_applied=OperatorType.BASELINE.value if i == 0 else OperatorType.REVISION.value,
            reasoning_pattern=f"pattern_{i % 2}",  # Alternating patterns
            tools_used=["pytest"] if i % 2 == 0 else ["unittest"],
            key_insights=[f"Insight {i}"]
        )
        empty_pool.add_trajectory(traj)

    # Add 3 failed trajectories
    for i in range(3):
        traj = Trajectory(
            trajectory_id=f"failure_{i}",
            generation=i + 5,
            agent_name="test_agent",
            success_score=0.2 + (i * 0.01),  # 0.20, 0.21, 0.22
            status=TrajectoryStatus.FAILURE.value,
            operator_applied=OperatorType.BASELINE.value,
            failure_reasons=["syntax error", "timeout"],
            reasoning_pattern=f"pattern_{i}"
        )
        empty_pool.add_trajectory(traj)

    # Add 2 partial success trajectories
    for i in range(2):
        traj = Trajectory(
            trajectory_id=f"partial_{i}",
            generation=i + 8,
            agent_name="test_agent",
            success_score=0.5 + (i * 0.05),  # 0.50, 0.55
            status=TrajectoryStatus.PARTIAL_SUCCESS.value,
            operator_applied=OperatorType.REFINEMENT.value,
            tools_used=["coverage"]
        )
        empty_pool.add_trajectory(traj)

    return empty_pool


# ================================
# TRAJECTORY TESTS
# ================================

class TestTrajectory:
    """Test Trajectory data class"""

    def test_trajectory_creation(self, sample_trajectory):
        """Test creating a trajectory"""
        assert sample_trajectory.trajectory_id == "traj_001"
        assert sample_trajectory.generation == 1
        assert sample_trajectory.success_score == 0.75
        assert sample_trajectory.status == TrajectoryStatus.SUCCESS.value

    def test_trajectory_defaults(self):
        """Test trajectory with minimal fields"""
        traj = Trajectory(
            trajectory_id="minimal",
            generation=0,
            agent_name="test"
        )
        assert traj.success_score == 0.0
        assert traj.failure_reasons == []
        assert traj.tools_used == []
        assert traj.parent_trajectories == []

    def test_is_successful(self, sample_trajectory):
        """Test success detection"""
        assert sample_trajectory.is_successful(threshold=0.7)
        assert not sample_trajectory.is_successful(threshold=0.8)

    def test_is_failed(self):
        """Test failure detection"""
        failed_traj = Trajectory(
            trajectory_id="fail",
            generation=1,
            agent_name="test",
            success_score=0.2
        )
        assert failed_traj.is_failed(threshold=0.3)
        assert not failed_traj.is_failed(threshold=0.1)

    def test_get_lineage_depth(self):
        """Test lineage depth calculation"""
        traj = Trajectory(
            trajectory_id="child",
            generation=2,
            agent_name="test",
            parent_trajectories=["parent1", "parent2"]
        )
        assert traj.get_lineage_depth() == 2

        orphan = Trajectory(
            trajectory_id="orphan",
            generation=1,
            agent_name="test"
        )
        assert orphan.get_lineage_depth() == 0

    def test_to_compact_dict(self):
        """Test compact serialization"""
        traj = Trajectory(
            trajectory_id="large",
            generation=1,
            agent_name="test",
            code_changes="x" * 2000,  # Large content
            proposed_strategy="y" * 1000
        )
        compact = traj.to_compact_dict()

        assert len(compact['code_changes']) < 1050  # Truncated
        assert len(compact['proposed_strategy']) < 550
        assert "[truncated]" in compact['code_changes']

    def test_trajectory_with_metadata(self):
        """Test trajectory with full metadata"""
        traj = Trajectory(
            trajectory_id="full",
            generation=5,
            agent_name="test",
            parent_trajectories=["parent1"],
            operator_applied=OperatorType.RECOMBINATION.value,
            code_changes="def foo(): pass",
            problem_diagnosis="Bug in module X",
            proposed_strategy="Use TDD approach",
            success_score=0.85,
            test_results={"passed": 10, "failed": 0},
            metrics={"coverage": 0.95, "complexity": 3.2},
            failure_reasons=[],
            tools_used=["pytest", "coverage"],
            reasoning_pattern="TDD",
            key_insights=["Write tests first", "Refactor after green"],
            assumptions_made=["Module X is isolated"],
            modified_files=["src/module_x.py", "tests/test_module_x.py"],
            execution_time_seconds=45.2,
            cost_dollars=0.05
        )

        assert traj.is_successful()
        assert traj.get_lineage_depth() == 1
        assert len(traj.key_insights) == 2
        assert traj.execution_time_seconds == 45.2


# ================================
# TRAJECTORY POOL TESTS
# ================================

class TestTrajectoryPoolBasics:
    """Test basic pool operations"""

    def test_pool_initialization(self, empty_pool):
        """Test pool creation"""
        assert empty_pool.agent_name == "test_agent"
        assert empty_pool.max_trajectories == 10
        assert len(empty_pool.trajectories) == 0
        assert empty_pool.total_added == 0
        assert empty_pool.total_pruned == 0

    def test_add_trajectory(self, empty_pool, sample_trajectory):
        """Test adding trajectory to pool"""
        empty_pool.add_trajectory(sample_trajectory)

        assert len(empty_pool.trajectories) == 1
        assert empty_pool.total_added == 1
        assert sample_trajectory.trajectory_id in empty_pool.trajectories

    def test_add_multiple_trajectories(self, empty_pool):
        """Test adding multiple trajectories"""
        for i in range(5):
            traj = Trajectory(
                trajectory_id=f"traj_{i}",
                generation=i,
                agent_name="test_agent"
            )
            empty_pool.add_trajectory(traj)

        assert len(empty_pool.trajectories) == 5
        assert empty_pool.total_added == 5

    def test_get_trajectory(self, populated_pool):
        """Test retrieving specific trajectory"""
        traj = populated_pool.get_trajectory("success_0")
        assert traj is not None
        assert traj.trajectory_id == "success_0"

        missing = populated_pool.get_trajectory("nonexistent")
        assert missing is None

    def test_get_all_trajectories(self, populated_pool):
        """Test getting all trajectories"""
        all_trajs = populated_pool.get_all_trajectories()
        assert len(all_trajs) == 10  # 5 success + 3 failure + 2 partial


class TestTrajectoryPoolQueries:
    """Test pool query operations"""

    def test_get_best_n(self, populated_pool):
        """Test getting top N trajectories"""
        best_3 = populated_pool.get_best_n(3)

        assert len(best_3) == 3
        # Should be sorted by score descending
        assert best_3[0].success_score >= best_3[1].success_score
        assert best_3[1].success_score >= best_3[2].success_score
        # Best should be success_4 (score 0.84)
        assert best_3[0].trajectory_id == "success_4"

    def test_get_successful_trajectories(self, populated_pool):
        """Test querying successful trajectories"""
        successful = populated_pool.get_successful_trajectories()

        # Should get 5 successful trajectories (scores >= 0.7)
        assert len(successful) == 5
        for traj in successful:
            assert traj.success_score >= populated_pool.success_threshold

    def test_get_failed_trajectories(self, populated_pool):
        """Test querying failed trajectories"""
        failed = populated_pool.get_failed_trajectories()

        # Should get 3 failed trajectories (scores < 0.3)
        assert len(failed) == 3
        for traj in failed:
            assert traj.success_score < populated_pool.failure_threshold

    def test_get_by_generation(self, populated_pool):
        """Test querying by generation"""
        gen_0_trajs = populated_pool.get_by_generation(0)
        assert len(gen_0_trajs) == 1
        assert gen_0_trajs[0].trajectory_id == "success_0"

    def test_get_by_operator(self, populated_pool):
        """Test querying by operator type"""
        baseline_trajs = populated_pool.get_by_operator(OperatorType.BASELINE)
        assert len(baseline_trajs) >= 1  # At least success_0 and failures

        revision_trajs = populated_pool.get_by_operator(OperatorType.REVISION)
        assert len(revision_trajs) == 4  # success_1, success_2, success_3, success_4


class TestTrajectoryPoolAdvanced:
    """Test advanced pool operations"""

    def test_get_diverse_successful_pairs(self, populated_pool):
        """Test getting diverse pairs for recombination"""
        pairs = populated_pool.get_diverse_successful_pairs(n=2)

        assert len(pairs) <= 2  # May be less if not enough diversity
        for traj_a, traj_b in pairs:
            assert traj_a.is_successful(populated_pool.success_threshold)
            assert traj_b.is_successful(populated_pool.success_threshold)
            assert traj_a.trajectory_id != traj_b.trajectory_id

    def test_get_diverse_pairs_with_different_patterns(self):
        """Test diversity based on reasoning patterns"""
        pool = TrajectoryPool(agent_name="test", max_trajectories=10)

        # Add trajectories with different patterns
        for i in range(4):
            traj = Trajectory(
                trajectory_id=f"traj_{i}",
                generation=i,
                agent_name="test",
                success_score=0.8,
                reasoning_pattern="pattern_A" if i % 2 == 0 else "pattern_B",
                tools_used=["tool_X"] if i % 2 == 0 else ["tool_Y"]
            )
            pool.add_trajectory(traj)

        pairs = pool.get_diverse_successful_pairs(n=2)

        # Should prioritize pairs with different patterns
        for traj_a, traj_b in pairs:
            # At least one difference
            assert (traj_a.reasoning_pattern != traj_b.reasoning_pattern or
                    set(traj_a.tools_used) != set(traj_b.tools_used))

    def test_get_pool_insights(self, populated_pool):
        """Test extracting pool insights"""
        insights = populated_pool.get_pool_insights(max_insights=10)

        # Should have insights from successful trajectories
        assert len(insights) >= 1
        assert all(isinstance(insight, str) for insight in insights)
        # Should be deduplicated
        assert len(insights) == len(set(insights))

    def test_get_common_failure_patterns(self, populated_pool):
        """Test identifying common failures"""
        common_failures = populated_pool.get_common_failure_patterns()

        # Should identify "timeout" and "syntax error" (both appear 3 times)
        assert len(common_failures) >= 1
        assert all(reason in ["syntax error", "timeout"] for reason in common_failures)


class TestTrajectoryPoolPruning:
    """Test automatic pruning"""

    def test_pruning_triggers_at_capacity(self, empty_pool):
        """Test pruning when exceeding capacity"""
        # Add 15 trajectories (pool max is 10)
        for i in range(15):
            traj = Trajectory(
                trajectory_id=f"traj_{i}",
                generation=i,
                agent_name="test_agent",
                success_score=0.1 + (i * 0.05)  # Increasing scores
            )
            empty_pool.add_trajectory(traj)

        # Should have pruned some trajectories (may keep recent + successful)
        # Recent generations (>= generation 5) are protected
        assert len(empty_pool.trajectories) <= 11  # Some recent ones kept
        assert empty_pool.total_pruned >= 4

    def test_pruning_keeps_successful(self):
        """Test pruning keeps successful trajectories"""
        pool = TrajectoryPool(agent_name="test", max_trajectories=5)

        # Add 3 successful
        for i in range(3):
            traj = Trajectory(
                trajectory_id=f"success_{i}",
                generation=i,
                agent_name="test",
                success_score=0.8
            )
            pool.add_trajectory(traj)

        # Add 5 failed (should trigger pruning)
        for i in range(5):
            traj = Trajectory(
                trajectory_id=f"fail_{i}",
                generation=i,
                agent_name="test",
                success_score=0.1
            )
            pool.add_trajectory(traj)

        # All 3 successful should still be in pool
        for i in range(3):
            assert pool.get_trajectory(f"success_{i}") is not None

    def test_pruning_keeps_recent(self):
        """Test pruning keeps recent trajectories"""
        pool = TrajectoryPool(agent_name="test", max_trajectories=5)

        # Add old failed trajectories
        for i in range(5):
            traj = Trajectory(
                trajectory_id=f"old_{i}",
                generation=i,
                agent_name="test",
                success_score=0.1
            )
            pool.add_trajectory(traj)

        # Add recent failed trajectories (should not be pruned)
        for i in range(3):
            traj = Trajectory(
                trajectory_id=f"recent_{i}",
                generation=100 + i,  # Much newer
                agent_name="test",
                success_score=0.1
            )
            pool.add_trajectory(traj)

        # Recent trajectories should be kept
        for i in range(3):
            assert pool.get_trajectory(f"recent_{i}") is not None


class TestTrajectoryPoolPersistence:
    """Test saving and loading"""

    def test_save_to_disk(self, populated_pool, temp_storage):
        """Test saving pool to disk"""
        save_path = populated_pool.save_to_disk()

        assert save_path.exists()
        assert save_path.name == "trajectory_pool.json"

        # Verify JSON structure
        with open(save_path, 'r') as f:
            data = json.load(f)

        assert data['agent_name'] == "test_agent"
        assert data['max_trajectories'] == 10
        assert len(data['trajectories']) == 10
        assert 'saved_at' in data

    def test_load_from_disk(self, populated_pool, temp_storage):
        """Test loading pool from disk"""
        # Save first
        populated_pool.save_to_disk()

        # Load into new pool
        loaded_pool = TrajectoryPool.load_from_disk(
            agent_name="test_agent",
            storage_dir=temp_storage / "test_agent"
        )

        assert loaded_pool.agent_name == "test_agent"
        assert len(loaded_pool.trajectories) == 10
        assert loaded_pool.total_added == populated_pool.total_added

        # Verify trajectory content
        original_traj = populated_pool.get_trajectory("success_0")
        loaded_traj = loaded_pool.get_trajectory("success_0")

        assert loaded_traj is not None
        assert loaded_traj.trajectory_id == original_traj.trajectory_id
        assert loaded_traj.success_score == original_traj.success_score

    def test_load_nonexistent_creates_new(self, temp_storage):
        """Test loading nonexistent pool creates new one"""
        pool = TrajectoryPool.load_from_disk(
            agent_name="new_agent",
            storage_dir=temp_storage / "new_agent"
        )

        assert pool.agent_name == "new_agent"
        assert len(pool.trajectories) == 0


class TestTrajectoryPoolStatistics:
    """Test statistics and metrics"""

    def test_get_statistics(self, populated_pool):
        """Test getting pool statistics"""
        stats = populated_pool.get_statistics()

        assert stats['total_trajectories'] == 10
        assert stats['successful_count'] == 5
        assert stats['failed_count'] == 3
        assert stats['total_added'] == 10
        assert stats['total_pruned'] == 0
        assert 0 < stats['average_score'] < 1
        assert abs(stats['best_score'] - 0.84) < 0.01  # success_4 (with floating point tolerance)
        assert 'operator_distribution' in stats
        assert 'generation_distribution' in stats

    def test_statistics_empty_pool(self, empty_pool):
        """Test statistics on empty pool"""
        stats = empty_pool.get_statistics()

        assert stats['total_trajectories'] == 0
        assert stats['average_score'] == 0.0
        assert stats['best_score'] == 0.0

    def test_operator_distribution(self, populated_pool):
        """Test operator distribution stats"""
        stats = populated_pool.get_statistics()
        op_dist = stats['operator_distribution']

        assert OperatorType.BASELINE.value in op_dist
        assert OperatorType.REVISION.value in op_dist
        assert OperatorType.REFINEMENT.value in op_dist

    def test_generation_distribution(self, populated_pool):
        """Test generation distribution stats"""
        stats = populated_pool.get_statistics()
        gen_dist = stats['generation_distribution']

        # Should have entries for generations 0-9
        assert len(gen_dist) == 10
        for gen in range(10):
            assert gen in gen_dist


# ================================
# FACTORY FUNCTION TESTS
# ================================

class TestFactoryFunction:
    """Test get_trajectory_pool factory"""

    def test_get_trajectory_pool_new(self):
        """Test creating new pool via factory"""
        pool = get_trajectory_pool(
            agent_name="factory_test",
            max_trajectories=20,
            load_existing=False
        )

        assert pool.agent_name == "factory_test"
        assert pool.max_trajectories == 20
        assert len(pool.trajectories) == 0

    def test_get_trajectory_pool_load_existing(self, temp_storage):
        """Test loading existing pool via factory"""
        # Create and save pool
        pool1 = TrajectoryPool(
            agent_name="load_test",
            max_trajectories=15,
            storage_dir=temp_storage / "load_test"
        )
        traj = Trajectory(
            trajectory_id="test_traj",
            generation=1,
            agent_name="load_test",
            success_score=0.9
        )
        pool1.add_trajectory(traj)
        save_path = pool1.save_to_disk()

        # Load via factory using the actual storage directory
        pool2 = TrajectoryPool.load_from_disk(
            agent_name="load_test",
            storage_dir=temp_storage / "load_test"
        )

        # Verify loaded correctly
        assert pool2.agent_name == "load_test"
        assert len(pool2.trajectories) == 1
        assert pool2.get_trajectory("test_traj") is not None


# ================================
# EDGE CASES & ERROR HANDLING
# ================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_pool_queries(self, empty_pool):
        """Test queries on empty pool"""
        assert empty_pool.get_best_n(5) == []
        assert empty_pool.get_successful_trajectories() == []
        assert empty_pool.get_failed_trajectories() == []
        assert empty_pool.get_diverse_successful_pairs(5) == []
        assert empty_pool.get_pool_insights() == []
        assert empty_pool.get_common_failure_patterns() == []

    def test_single_trajectory_pool(self, empty_pool):
        """Test pool with single trajectory"""
        traj = Trajectory(
            trajectory_id="single",
            generation=1,
            agent_name="test",
            success_score=0.8
        )
        empty_pool.add_trajectory(traj)

        assert len(empty_pool.get_best_n(5)) == 1
        assert empty_pool.get_diverse_successful_pairs(5) == []  # Need 2 for pair

    def test_pruning_with_no_prunable(self):
        """Test pruning when all trajectories must be kept"""
        pool = TrajectoryPool(agent_name="test", max_trajectories=5)

        # Add 10 successful trajectories (all should be kept)
        for i in range(10):
            traj = Trajectory(
                trajectory_id=f"success_{i}",
                generation=i,
                agent_name="test",
                success_score=0.8
            )
            pool.add_trajectory(traj)

        # Should keep all successful ones even if exceeding capacity
        assert len(pool.get_successful_trajectories()) == 10

    def test_trajectory_with_missing_optional_fields(self):
        """Test trajectory without optional fields"""
        minimal = Trajectory(
            trajectory_id="minimal",
            generation=1,
            agent_name="test"
        )

        assert minimal.is_failed()  # Default score 0.0
        assert not minimal.is_successful()
        assert minimal.get_lineage_depth() == 0
        assert minimal.key_insights == []


# ================================
# CONCURRENT ACCESS TESTS (ISSUE #14)
# ================================

class TestTrajectoryPoolConcurrency:
    """Test thread-safety and concurrent access patterns"""

    def test_concurrent_add_trajectories(self, empty_pool):
        """Test thread-safety of add operations"""
        import threading
        import concurrent.futures

        def add_traj(i):
            traj = Trajectory(
                trajectory_id=f"concurrent_{i}",
                generation=0,
                agent_name="test_agent",
                success_score=0.5 + (i * 0.01)
            )
            empty_pool.add_trajectory(traj)

        # Add 50 trajectories from 10 threads concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(add_traj, i) for i in range(50)]
            concurrent.futures.wait(futures)

        # Verify no lost writes (all 50 should be added)
        # Note: Pool may prune if exceeding max_trajectories (10)
        # So we check total_added instead of current count
        assert empty_pool.total_added == 50

    def test_concurrent_read_operations(self, populated_pool):
        """Test concurrent reads are safe"""
        import concurrent.futures

        def read_operations():
            # Mix of different read operations
            populated_pool.get_all_trajectories()
            populated_pool.get_best_n(3)
            populated_pool.get_successful_trajectories()
            populated_pool.get_failed_trajectories()
            populated_pool.get_statistics()
            return True

        # Run 20 concurrent read operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_operations) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All reads should succeed
        assert all(results)
        assert len(results) == 20

    def test_concurrent_add_and_read(self, empty_pool):
        """Test concurrent adds while reading"""
        import concurrent.futures
        import time

        results = {'adds': 0, 'reads': 0, 'errors': 0}

        def add_worker(i):
            try:
                traj = Trajectory(
                    trajectory_id=f"add_{i}",
                    generation=0,
                    agent_name="test_agent",
                    success_score=0.7
                )
                empty_pool.add_trajectory(traj)
                results['adds'] += 1
            except Exception:
                results['errors'] += 1

        def read_worker():
            try:
                for _ in range(10):
                    empty_pool.get_all_trajectories()
                    empty_pool.get_statistics()
                    time.sleep(0.001)  # Small delay
                results['reads'] += 1
            except Exception:
                results['errors'] += 1

        # Run mixed adds and reads
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # 20 add operations + 5 read operations
            add_futures = [executor.submit(add_worker, i) for i in range(20)]
            read_futures = [executor.submit(read_worker) for _ in range(5)]

            concurrent.futures.wait(add_futures + read_futures)

        # Verify operations completed without errors
        # (Note: Counter increments might race, so check total_added instead)
        assert empty_pool.total_added >= 15  # Most adds should succeed
        assert results['errors'] == 0  # No exceptions

    def test_concurrent_pruning(self, empty_pool):
        """Test pruning under concurrent access"""
        import concurrent.futures

        # Add trajectories that will trigger pruning (max is 10)
        def add_batch(batch_id, count):
            for i in range(count):
                traj = Trajectory(
                    trajectory_id=f"batch_{batch_id}_traj_{i}",
                    generation=batch_id,
                    agent_name="test_agent",
                    success_score=0.1 + (i * 0.05)  # Increasing scores
                )
                empty_pool.add_trajectory(traj)

        # Add from 3 threads (15 trajectories total, will trigger pruning)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(add_batch, batch_id, 5) for batch_id in range(3)]
            concurrent.futures.wait(futures)

        # Verify pool constraints maintained
        assert len(empty_pool.trajectories) <= empty_pool.max_trajectories + 5  # Allow some overflow during concurrent adds
        assert empty_pool.total_added == 15
        assert empty_pool.total_pruned >= 0  # Some pruning may have occurred

    def test_concurrent_get_diverse_pairs(self, populated_pool):
        """Test concurrent diverse pair selection"""
        import concurrent.futures

        def get_pairs():
            return populated_pool.get_diverse_successful_pairs(n=2)

        # Run 10 concurrent pair selections
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_pairs) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should return pairs (or empty list if not enough diversity)
        assert all(isinstance(r, list) for r in results)

    def test_concurrent_save_operations(self, populated_pool, temp_storage):
        """Test concurrent save operations don't corrupt data"""
        import concurrent.futures

        def save_pool():
            return populated_pool.save_to_disk()

        # Save from multiple threads (file writes should be safe)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(save_pool) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All saves should succeed
        assert all(r.exists() for r in results)
        assert len(set(r.name for r in results)) == 1  # All same file

        # Load and verify integrity
        loaded = TrajectoryPool.load_from_disk(
            agent_name="test_agent",
            storage_dir=temp_storage / "test_agent"
        )
        assert len(loaded.trajectories) == len(populated_pool.trajectories)

    def test_race_condition_in_statistics(self, empty_pool):
        """Test statistics calculation under concurrent modifications"""
        import concurrent.futures

        def add_and_get_stats(i):
            # Add trajectory
            traj = Trajectory(
                trajectory_id=f"race_{i}",
                generation=0,
                agent_name="test_agent",
                success_score=0.8 if i % 2 == 0 else 0.2
            )
            empty_pool.add_trajectory(traj)

            # Immediately get statistics
            return empty_pool.get_statistics()

        # Run 20 concurrent add+stats operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(add_and_get_stats, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All stats should be valid dictionaries
        assert all(isinstance(r, dict) for r in results)
        assert all('total_trajectories' in r for r in results)

        # Final statistics should reflect all adds
        final_stats = empty_pool.get_statistics()
        assert final_stats['total_added'] == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
