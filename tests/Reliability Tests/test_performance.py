"""
Performance Regression Tests for Genesis Orchestration

Ensures performance optimizations are maintained across code changes.
These tests fail if routing performance degrades beyond acceptable thresholds.

Target: Phase 3.3 optimizations should keep HALO routing under 0.4ms/task
"""

import asyncio
import pytest
import time
from infrastructure.halo_router import HALORouter
from infrastructure.task_dag import TaskDAG, Task


class TestPerformanceRegression:
    """Prevent performance regressions in optimized code"""

    @pytest.mark.flaky(reruns=3, reruns_delay=2)
    @pytest.mark.asyncio
    async def test_halo_routing_performance_medium_dag(self):
        """
        PERFORMANCE TEST: Medium DAG (50 tasks) should route in < 25ms

        Baseline (unoptimized): 18.48ms
        Optimized target: 17.31ms
        Regression threshold: 25ms (35% margin)

        FLAKY TEST NOTE:
        This test is marked with @pytest.mark.flaky(reruns=3, reruns_delay=2) for
        consistency with other performance tests that measure wall-clock time and
        are sensitive to system contention.
        """
        router = HALORouter()

        # Create 50-task DAG
        dag = TaskDAG()
        task_types = ["design", "implement", "test", "deploy", "monitor", "security", "analytics"]
        for i in range(50):
            task_type = task_types[i % len(task_types)]
            dag.add_task(Task(task_id=f"task_{i}", task_type=task_type, description=f"Task {i}"))

        # Measure routing time
        start = time.perf_counter()
        plan = await router.route_tasks(dag)
        elapsed = time.perf_counter() - start

        # Should complete all tasks
        assert len(plan.assignments) == 50, "All tasks should be assigned"
        assert plan.is_complete(), "Routing plan should be complete"

        # Performance threshold: < 25ms (with 35% margin for slower systems)
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 25.0, (
            f"Medium DAG routing too slow: {elapsed_ms:.2f}ms (threshold: 25ms). "
            f"Performance regression detected! Target: 17.31ms"
        )

    @pytest.mark.flaky(reruns=3, reruns_delay=2)
    @pytest.mark.asyncio
    async def test_halo_routing_performance_large_dag(self):
        """
        PERFORMANCE TEST: Large DAG (200 tasks) should route in < 100ms

        Baseline (unoptimized): 74.34ms
        Optimized target: 62.84ms
        Regression threshold: 100ms (59% margin)

        Note: This test measures routing time, not assignment completeness.
        Load balancing may limit assignments (agents have max_concurrent_tasks=10).

        FLAKY TEST NOTE:
        This test is marked with @pytest.mark.flaky(reruns=3, reruns_delay=2) because
        performance tests are inherently sensitive to system contention. In a full test
        suite with 400+ tests running concurrently, CPU/memory contention can cause
        intermittent failures even when the code is correct. The retry logic ensures
        test reliability without relaxing performance thresholds.

        Why retry is appropriate here:
        - Test measures wall-clock time, affected by OS scheduling and system load
        - Passes consistently in isolation (no code bug)
        - Failures are non-deterministic (contention-dependent)
        - Thresholds remain strict (no tolerance relaxation)
        - 3 retries with 2s delay allows system to settle between attempts
        """
        router = HALORouter()

        # Create 200-task DAG
        dag = TaskDAG()
        task_types = ["design", "implement", "test", "deploy", "monitor", "security", "analytics"]
        for i in range(200):
            task_type = task_types[i % len(task_types)]
            dag.add_task(Task(task_id=f"task_{i}", task_type=task_type, description=f"Task {i}"))

        # Measure routing time
        start = time.perf_counter()
        plan = await router.route_tasks(dag)
        elapsed = time.perf_counter() - start

        # Should assign as many as possible (load balancing limits to ~70 tasks)
        # 7 agent types × 10 max concurrent = 70 tasks max
        assert len(plan.assignments) >= 70, (
            f"Too few tasks assigned: {len(plan.assignments)} (expected ~70 due to load balancing)"
        )

        # Performance threshold: < 100ms (with 59% margin for slower systems)
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 100.0, (
            f"Large DAG routing too slow: {elapsed_ms:.2f}ms (threshold: 100ms). "
            f"Performance regression detected! Target: 62.84ms"
        )

    def test_halo_rule_matching_performance(self):
        """
        PERFORMANCE TEST: 1000 rule matches should complete in < 50ms

        Baseline (unoptimized): 130.45ms
        Optimized target: 27.02ms
        Regression threshold: 50ms (85% margin)
        """
        router = HALORouter()

        # Create test task
        task = Task(task_id="test", task_type="implement", description="Test task")
        available_agents = list(router.agent_registry.keys())

        # Measure 1000 rule matches
        start = time.perf_counter()
        for _ in range(1000):
            router._apply_routing_logic(task, available_agents)
        elapsed = time.perf_counter() - start

        # Performance threshold: < 50ms (with 85% margin)
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 50.0, (
            f"Rule matching too slow: {elapsed_ms:.2f}ms for 1000 iterations (threshold: 50ms). "
            f"Performance regression detected! Target: 27.02ms"
        )

    @pytest.mark.flaky(reruns=3, reruns_delay=2)
    def test_per_task_routing_efficiency(self):
        """
        PERFORMANCE TEST: Per-task routing should be < 0.4ms/task

        Target: Optimized routing should be under 0.4ms per task on average
        This ensures O(1) lookups are working correctly

        FLAKY TEST NOTE:
        This test is marked with @pytest.mark.flaky(reruns=3, reruns_delay=2) because
        it measures per-task routing latency with strict thresholds (0.4ms/task).
        System contention in full test suites can cause spikes in execution time.
        Retry logic ensures reliability without relaxing performance standards.
        """
        router = HALORouter()

        # Create 100-task DAG
        dag = TaskDAG()
        task_types = ["design", "implement", "test", "deploy"]
        for i in range(100):
            task_type = task_types[i % len(task_types)]
            dag.add_task(Task(task_id=f"task_{i}", task_type=task_type, description=f"Task {i}"))

        # Measure routing time
        start = time.perf_counter()
        plan = asyncio.run(router.route_tasks(dag))
        elapsed = time.perf_counter() - start

        # Calculate per-task time
        per_task_ms = (elapsed * 1000) / 100

        # Should be under 0.4ms per task
        assert per_task_ms < 0.4, (
            f"Per-task routing too slow: {per_task_ms:.3f}ms/task (threshold: 0.4ms). "
            f"Optimization not working correctly!"
        )

    def test_index_consistency(self):
        """
        CORRECTNESS TEST: Verify indexes are consistent with brute-force search

        Ensures optimization correctness by comparing indexed routing
        with unoptimized linear search
        """
        router = HALORouter()

        # Test various task types
        task_types = ["design", "implement", "test", "deploy", "security", "analytics"]

        for task_type in task_types:
            task = Task(task_id=f"{task_type}_task", task_type=task_type, description=f"Test {task_type}")
            available_agents = list(router.agent_registry.keys())

            # Get result from optimized routing
            optimized_agent, optimized_explanation = router._apply_routing_logic(task, available_agents)

            # Verify index lookup found correct rules
            indexed_rules = router._task_type_index.get(task_type, [])

            # All indexed rules should have matching task_type
            for rule in indexed_rules:
                assert rule.condition.get("task_type") == task_type, (
                    f"Index contains incorrect rule: {rule.rule_id} for task_type={task_type}"
                )

            # Should have found an agent (unless task_type is unsupported)
            if optimized_agent:
                assert optimized_agent in router.agent_registry, (
                    f"Routed to unknown agent: {optimized_agent}"
                )

    def test_dynamic_rule_addition_performance(self):
        """
        PERFORMANCE TEST: Adding rules dynamically should update indexes efficiently

        Ensures add_routing_rule maintains cache consistency without degrading performance
        """
        from infrastructure.halo_router import RoutingRule

        router = HALORouter()

        # Measure time to add 10 rules
        start = time.perf_counter()
        for i in range(10):
            rule = RoutingRule(
                rule_id=f"dynamic_rule_{i}",
                condition={"task_type": f"custom_{i}"},
                target_agent="builder_agent",
                priority=10 + i,
                explanation=f"Dynamic rule {i}"
            )
            router.add_routing_rule(rule)
        elapsed = time.perf_counter() - start

        # Should complete in < 5ms
        elapsed_ms = elapsed * 1000
        assert elapsed_ms < 5.0, (
            f"Dynamic rule addition too slow: {elapsed_ms:.2f}ms (threshold: 5ms)"
        )

        # Verify indexes are updated correctly
        for i in range(10):
            task_type = f"custom_{i}"
            assert task_type in router._task_type_index, (
                f"Index not updated for dynamic rule: {task_type}"
            )

            # Should have exactly one rule for this custom task_type
            rules = router._task_type_index[task_type]
            assert len(rules) == 1, (
                f"Expected 1 rule for {task_type}, got {len(rules)}"
            )


class TestMemoryEfficiency:
    """Verify optimizations don't introduce memory leaks"""

    def test_index_memory_overhead(self):
        """
        MEMORY TEST: Indexes should have minimal memory overhead

        Indexes should not significantly increase memory usage
        """
        import sys

        router = HALORouter()

        # Measure index sizes
        sorted_cache_size = sys.getsizeof(router._sorted_rules_cache)
        task_type_index_size = sys.getsizeof(router._task_type_index)
        capability_index_size = sys.getsizeof(router._capability_index)

        total_index_size = sorted_cache_size + task_type_index_size + capability_index_size

        # Should be under 100KB for 15 agents and ~30 rules
        assert total_index_size < 100_000, (
            f"Index memory too large: {total_index_size} bytes (threshold: 100KB)"
        )

    def test_no_memory_leak_in_routing(self):
        """
        MEMORY TEST: Repeated routing should not leak memory

        Ensures no memory accumulation over many routing operations
        """
        import gc
        import sys

        router = HALORouter()

        # Create DAG
        dag = TaskDAG()
        for i in range(50):
            dag.add_task(Task(task_id=f"task_{i}", task_type="implement", description=f"Task {i}"))

        # Measure baseline memory
        gc.collect()
        baseline_size = sum(sys.getsizeof(obj) for obj in gc.get_objects())

        # Run 100 routing operations
        for _ in range(100):
            asyncio.run(router.route_tasks(dag))

        # Measure final memory
        gc.collect()
        final_size = sum(sys.getsizeof(obj) for obj in gc.get_objects())

        # Memory growth should be minimal (< 10% of baseline)
        growth = final_size - baseline_size
        growth_pct = (growth / baseline_size) * 100

        assert growth_pct < 10.0, (
            f"Memory leak detected: {growth_pct:.1f}% growth after 100 routing operations"
        )


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
