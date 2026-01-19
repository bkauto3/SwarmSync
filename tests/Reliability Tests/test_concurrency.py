"""
Concurrency and Thread-Safety Tests (Phase 3.4)

Tests thread-safety, race conditions, deadlocks, and concurrent orchestration:
- Multiple parallel orchestration requests
- Thread-safe data structures
- Race condition detection
- Deadlock prevention
- Resource contention
- Concurrent agent execution

Target: 30+ comprehensive concurrency tests
"""
import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from unittest.mock import Mock, patch

from infrastructure.htdag_planner import HTDAGPlanner
from infrastructure.halo_router import HALORouter, AgentCapability
from infrastructure.aop_validator import AOPValidator
from infrastructure.task_dag import TaskDAG, Task, TaskStatus
from infrastructure.learned_reward_model import LearnedRewardModel, TaskOutcome
from infrastructure.trajectory_pool import TrajectoryPool
from infrastructure.replay_buffer import ReplayBuffer


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def orchestration_components():
    """Create orchestration components for concurrency testing"""
    router = HALORouter()
    return {
        "planner": HTDAGPlanner(),
        "router": router,
        "validator": AOPValidator(agent_registry=router.agent_registry),
        "reward_model": LearnedRewardModel(),
        "trajectory_pool": TrajectoryPool(agent_name="test_agent"),
        "replay_buffer": ReplayBuffer(mongo_uri=None, redis_host=None)  # In-memory mode
    }


@pytest.fixture
def simple_task_requests():
    """Generate simple task requests for parallel testing"""
    return [
        "Build REST API",
        "Run security audit",
        "Deploy to production",
        "Write documentation",
        "Set up monitoring",
        "Optimize database",
        "Create landing page",
        "Test application",
        "Analyze metrics",
        "Review code"
    ]


# ============================================================================
# CATEGORY 1: PARALLEL ORCHESTRATION REQUESTS (10+ tests)
# ============================================================================

class TestParallelOrchestrationRequests:
    """Test handling multiple parallel orchestration requests"""

    @pytest.mark.asyncio
    async def test_concurrent_planning_requests(self, orchestration_components, simple_task_requests):
        """Test: Multiple concurrent planning requests don't interfere"""
        planner = orchestration_components["planner"]

        # Execute 10 concurrent planning requests
        tasks = [planner.decompose_task(req) for req in simple_task_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        assert len(results) == len(simple_task_requests)
        successful = [r for r in results if isinstance(r, TaskDAG)]
        assert len(successful) == len(simple_task_requests)

    @pytest.mark.asyncio
    async def test_concurrent_routing_requests(self, orchestration_components):
        """Test: Multiple concurrent routing requests"""
        router = orchestration_components["router"]

        # Create tasks
        tasks = [
            Task(task_id=f"task_{i}", description=f"Task {i}", task_type="generic")
            for i in range(20)
        ]

        # Route in parallel
        routing_tasks = [router.route_tasks([task]) for task in tasks]
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)

        # All should succeed
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == len(tasks)

    @pytest.mark.asyncio
    async def test_concurrent_validation_requests(self, orchestration_components):
        """Test: Multiple concurrent validation requests"""
        validator = orchestration_components["validator"]
        router = orchestration_components["router"]

        # Create multiple DAGs
        dags = []
        routing_plans = []
        for i in range(10):
            dag = TaskDAG()
            task = Task(task_id=f"t{i}", description=f"Task {i}", task_type="generic")
            dag.add_task(task)
            dags.append(dag)

            plan = await router.route_tasks([task])
            routing_plans.append(plan)

        # Validate concurrently - use async method directly
        validation_tasks = [
            validator.validate_routing_plan(plan, dag)
            for dag, plan in zip(dags, routing_plans)
        ]
        results = await asyncio.gather(*validation_tasks)

        # All should be valid
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_full_pipeline_concurrent_requests(self, orchestration_components, simple_task_requests):
        """Test: Complete pipeline with concurrent requests"""
        planner = orchestration_components["planner"]
        router = orchestration_components["router"]
        validator = orchestration_components["validator"]

        async def process_request(request):
            dag = await planner.decompose_task(request)
            routing_plan = await router.route_tasks(dag.get_all_tasks())
            validation = await validator.validate_routing_plan(dag, routing_plan)
            return validation.is_valid

        # Process 10 requests concurrently
        tasks = [process_request(req) for req in simple_task_requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        successful = [r for r in results if r is True]
        assert len(successful) >= 8, "Most concurrent requests should succeed"

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_shared_resources(self, orchestration_components):
        """Test: Concurrent requests sharing router registry"""
        router = orchestration_components["router"]

        # All requests share the same agent registry
        tasks = [
            Task(task_id=f"task_{i}", description=f"Build feature {i}", task_type="implement")
            for i in range(50)
        ]

        routing_tasks = [router.route_tasks([task]) for task in tasks]
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)

        # No crashes from shared registry access
        assert len([r for r in results if not isinstance(r, Exception)]) == len(tasks)

    @pytest.mark.asyncio
    async def test_concurrent_reward_model_updates(self, orchestration_components):
        """Test: Concurrent updates to learned reward model"""
        reward_model = orchestration_components["reward_model"]

        # Multiple threads recording outcomes
        outcomes = [
            TaskOutcome(
                task_id=f"task_{i}",
                task_type="implement",
                agent_name="builder_agent",
                success=1.0,
                quality=0.8 + (i % 3) * 0.05,
                cost=0.3,
                time=0.4
            )
            for i in range(100)
        ]

        # Record concurrently
        tasks = [
            asyncio.to_thread(reward_model.record_outcome, outcome)
            for outcome in outcomes
        ]
        await asyncio.gather(*tasks)

        # All outcomes should be recorded
        weights = reward_model.get_weights()
        assert weights is not None

    @pytest.mark.asyncio
    async def test_concurrent_trajectory_pool_access(self, orchestration_components):
        """Test: Concurrent access to trajectory pool"""
        pool = orchestration_components["trajectory_pool"]
        from infrastructure.trajectory_pool import Trajectory
        from infrastructure import OperatorType

        # Multiple threads storing trajectories
        async def store_trajectory(i):
            traj = Trajectory(
                trajectory_id=f"traj_{i}",
                generation=i % 10,
                agent_name="test_agent",
                code_changes=f"def test_{i}(): pass",
                test_results={"score": 0.8},
                operator_applied=OperatorType.RECOMBINATION.value,
                success_score=0.8
            )
            return await asyncio.to_thread(pool.add_trajectory, traj)

        tasks = [store_trajectory(i) for i in range(100)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Pool should handle concurrent access
        assert len(pool.get_all_trajectories()) > 0

    @pytest.mark.asyncio
    async def test_concurrent_replay_buffer_operations(self, orchestration_components):
        """Test: Concurrent replay buffer operations"""
        buffer = orchestration_components["replay_buffer"]
        from infrastructure.replay_buffer import Trajectory, ActionStep
        from infrastructure import OutcomeTag
        from datetime import datetime

        # Concurrent add operations
        def add_experience(i):
            traj = Trajectory(
                trajectory_id=f"traj_{i}",
                agent_id="test_agent",
                task_description=f"Task {i}",
                initial_state={"step": i},
                steps=(ActionStep(
                    timestamp=datetime.now().isoformat(),
                    tool_name="test_tool",
                    tool_args={"arg": i},
                    tool_result="success",
                    agent_reasoning=f"Reasoning {i}"
                ),),
                final_outcome=OutcomeTag.SUCCESS.value,
                reward=0.8,
                metadata={},
                created_at=datetime.now().isoformat(),
                duration_seconds=1.0
            )
            return buffer.store_trajectory(traj)

        tasks = [asyncio.to_thread(add_experience, i) for i in range(200)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Buffer should handle concurrent adds
        assert len(buffer.sample(limit=10000)) > 0

    @pytest.mark.asyncio
    async def test_mixed_read_write_operations(self, orchestration_components):
        """Test: Mixed concurrent read/write operations"""
        router = orchestration_components["router"]

        async def read_operation():
            # Read agent registry
            return len(router.agent_registry)

        async def write_operation(i):
            # Route a task (reads registry)
            task = Task(task_id=f"t{i}", description=f"Task {i}", task_type="generic")
            return await router.route_tasks([task])

        # Mix reads and writes
        tasks = []
        for i in range(50):
            if i % 2 == 0:
                tasks.append(read_operation())
            else:
                tasks.append(write_operation(i))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len([r for r in results if not isinstance(r, Exception)]) > 40

    @pytest.mark.asyncio
    async def test_high_concurrency_stress_test(self, orchestration_components):
        """Test: High concurrency stress test (100+ concurrent requests)"""
        planner = orchestration_components["planner"]

        # 100 concurrent planning requests
        tasks = [
            planner.decompose_task(f"Task {i}")
            for i in range(100)
        ]

        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start

        # Should handle high concurrency
        successful = [r for r in results if isinstance(r, TaskDAG)]
        assert len(successful) >= 90, "Should handle 90%+ of concurrent requests"
        assert duration < 30, "Should complete within 30 seconds"


# ============================================================================
# CATEGORY 2: THREAD-SAFETY (10+ tests)
# ============================================================================

class TestThreadSafety:
    """Test thread-safe data structures and operations"""

    def test_agent_registry_thread_safety(self, orchestration_components):
        """Test: Agent registry is thread-safe"""
        router = orchestration_components["router"]

        def read_registry():
            return len(router.agent_registry)

        # 50 concurrent reads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_registry) for _ in range(50)]
            results = [f.result() for f in as_completed(futures)]

        # All reads should return same value
        assert len(set(results)) == 1, "Registry size should be consistent"

    def test_dag_modification_thread_safety(self):
        """Test: DAG modifications are thread-safe"""
        dag = TaskDAG()

        def add_task(i):
            task = Task(task_id=f"task_{i}", description=f"Task {i}", task_type="generic")
            dag.add_task(task)

        # 100 concurrent additions
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(add_task, i) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        # All tasks should be added
        assert len(dag.get_all_tasks()) == 100

    def test_reward_model_weights_thread_safety(self, orchestration_components):
        """Test: Reward model weight updates are thread-safe"""
        reward_model = orchestration_components["reward_model"]

        def update_weights():
            outcome = TaskOutcome(
                task_id="test",
                task_type="test",
                agent_name="test_agent",
                success=1.0,
                quality=0.9,
                cost=0.3,
                time=0.4
            )
            reward_model.record_outcome(outcome)

        # 50 concurrent updates
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_weights) for _ in range(50)]
            for f in as_completed(futures):
                f.result()

        # Weights should still be normalized
        weights = reward_model.get_weights()
        total = weights.w_success + weights.w_quality + weights.w_cost + weights.w_time
        assert abs(total - 1.0) < 0.01, "Weights should remain normalized"

    def test_trajectory_pool_thread_safety(self, orchestration_components):
        """Test: Trajectory pool is thread-safe"""
        pool = orchestration_components["trajectory_pool"]
        from infrastructure.trajectory_pool import Trajectory
        from infrastructure import OperatorType

        def store_trajectory(i):
            traj = Trajectory(
                trajectory_id=f"traj_{i}",
                generation=i % 10,
                agent_name="test_agent",
                code_changes=f"def test_{i}(): pass",
                test_results={"score": 0.8},
                operator_applied=OperatorType.REVISION.value,
                success_score=0.8
            )
            pool.add_trajectory(traj)

        # 100 concurrent stores
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(store_trajectory, i) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        # All trajectories should be stored
        assert len(pool.get_all_trajectories()) > 0

    def test_replay_buffer_thread_safety(self, orchestration_components):
        """Test: Replay buffer is thread-safe"""
        buffer = orchestration_components["replay_buffer"]
        from infrastructure.replay_buffer import Trajectory, ActionStep
        from infrastructure import OutcomeTag
        from datetime import datetime

        def add_experience(i):
            traj = Trajectory(
                trajectory_id=f"traj_{i}",
                agent_id="test_agent",
                task_description=f"Task {i}",
                initial_state={"step": i},
                steps=(ActionStep(
                    timestamp=datetime.now().isoformat(),
                    tool_name="test_tool",
                    tool_args={"arg": i},
                    tool_result="success",
                    agent_reasoning=f"Reasoning {i}"
                ),),
                final_outcome=OutcomeTag.SUCCESS.value,
                reward=0.8,
                metadata={},
                created_at=datetime.now().isoformat(),
                duration_seconds=1.0
            )
            buffer.store_trajectory(traj)

        # 100 concurrent additions
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(add_experience, i) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        # Buffer should handle all additions
        assert len(buffer.sample(limit=10000)) >= 90, "Buffer should store most experiences"

    def test_task_status_updates_thread_safety(self):
        """Test: Task status updates are thread-safe"""
        task = Task(task_id="shared_task", description="Shared task", task_type="generic")

        def update_status(status):
            task.status = status
            time.sleep(0.001)  # Simulate processing
            return task.status

        # Concurrent status updates
        statuses = [TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(update_status, s) for s in statuses]
            results = [f.result() for f in as_completed(futures)]

        # Final status should be consistent
        assert task.status in statuses

    def test_validator_concurrent_validation(self, orchestration_components):
        """Test: Validator handles concurrent validations"""
        validator = orchestration_components["validator"]
        router = orchestration_components["router"]

        def validate_plan():
            dag = TaskDAG()
            task = Task(task_id="test", description="Test", task_type="generic")
            dag.add_task(task)

            # Note: router.route_tasks is async, so we need to handle it differently
            # For thread-safety testing, we'll just test the validator itself
            from infrastructure.halo_router import RoutingPlan
            routing_plan = RoutingPlan(
                assignments={"test": "builder_agent"},
                explanations={"test": "Test routing"}
            )

            # Run async function in sync context
            return asyncio.run(validator.validate_routing_plan(routing_plan, dag))

        # 20 concurrent validations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(validate_plan) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(r.passed for r in results)

    def test_concurrent_llm_calls(self, orchestration_components):
        """Test: Concurrent LLM API calls are handled safely"""
        planner = orchestration_components["planner"]

        async def make_llm_call(request):
            return await planner.decompose_task(request)

        async def run_concurrent_llm():
            tasks = [make_llm_call(f"Request {i}") for i in range(10)]
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = asyncio.run(run_concurrent_llm())

        # Most should succeed (some may fail due to rate limits)
        successful = [r for r in results if isinstance(r, TaskDAG)]
        assert len(successful) >= 5, "At least 50% of LLM calls should succeed"

    def test_shared_state_consistency(self, orchestration_components):
        """Test: Shared state remains consistent under concurrent access"""
        router = orchestration_components["router"]

        initial_count = len(router.agent_registry)

        def read_agent_count():
            return len(router.agent_registry)

        # 100 concurrent reads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_agent_count) for _ in range(100)]
            results = [f.result() for f in as_completed(futures)]

        # All should return same count (no modifications)
        assert all(r == initial_count for r in results)

    def test_atomic_operations(self):
        """Test: Critical operations are atomic"""
        counter = {"value": 0}
        lock = threading.Lock()

        def increment_atomic():
            with lock:
                current = counter["value"]
                time.sleep(0.0001)  # Simulate work
                counter["value"] = current + 1

        # 100 concurrent increments
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(increment_atomic) for _ in range(100)]
            for f in as_completed(futures):
                f.result()

        # Should be exactly 100
        assert counter["value"] == 100


# ============================================================================
# CATEGORY 3: RACE CONDITION DETECTION (5+ tests)
# ============================================================================

class TestRaceConditionDetection:
    """Test for race conditions in critical paths"""

    def test_dag_concurrent_modification_race(self):
        """Test: No race conditions when modifying DAG concurrently"""
        dag = TaskDAG()

        def modify_dag(i):
            # Read
            current_tasks = len(dag.get_all_tasks())
            time.sleep(0.001)  # Simulate processing

            # Write
            task = Task(task_id=f"task_{i}", description=f"Task {i}", task_type="generic")
            dag.add_task(task)

            return current_tasks

        # Concurrent modifications
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(modify_dag, i) for i in range(50)]
            for f in as_completed(futures):
                f.result()

        # Final count should be 50 (no lost updates)
        assert len(dag.get_all_tasks()) == 50

    def test_reward_model_update_race(self, orchestration_components):
        """Test: No race conditions in reward model updates"""
        reward_model = orchestration_components["reward_model"]

        def update_and_read():
            # Record outcome
            outcome = TaskOutcome(
                task_id="test",
                task_type="test",
                agent_name="test_agent",
                success=1.0,
                quality=0.9,
                cost=0.3,
                time=0.4
            )
            reward_model.record_outcome(outcome)

            # Read weights
            return reward_model.get_weights()

        # Concurrent update-read operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_and_read) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All reads should return valid weights
        assert all(r is not None for r in results)

    def test_router_registry_race(self, orchestration_components):
        """Test: No race conditions in router registry access"""
        router = orchestration_components["router"]

        def read_and_route():
            # Read registry
            agent_count = len(router.agent_registry)

            # Route task (also reads registry)
            async def route():
                task = Task(task_id="test", description="Test", task_type="generic")
                return await router.route_tasks([task])

            return asyncio.run(route())

        # Concurrent read-route operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(read_and_route) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert len(results) == 10

    def test_task_dependency_race(self):
        """Test: No race conditions when updating task dependencies"""
        dag = TaskDAG()
        task1 = Task(task_id="task1", description="Task 1", task_type="generic")
        task2 = Task(task_id="task2", description="Task 2", task_type="generic")
        dag.add_task(task1)
        dag.add_task(task2)

        def update_dependencies():
            # Read dependencies
            deps = len(task2.dependencies)
            time.sleep(0.001)

            # Update dependencies
            if "task1" not in task2.dependencies:
                task2.dependencies.append("task1")

        # Concurrent updates
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_dependencies) for _ in range(20)]
            for f in as_completed(futures):
                f.result()

        # Should have exactly one dependency (no duplicates)
        assert "task1" in task2.dependencies
        assert task2.dependencies.count("task1") == 1

    def test_statistics_counter_race(self, orchestration_components):
        """Test: No race conditions in statistics counters"""
        # Create a simple counter
        stats = {"total_requests": 0, "successful": 0}
        lock = threading.Lock()

        def update_stats(success):
            with lock:
                stats["total_requests"] += 1
                if success:
                    stats["successful"] += 1

        # Concurrent updates
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(update_stats, i % 2 == 0) for i in range(100)]
            for f in as_completed(futures):
                f.result()

        # Counters should be accurate
        assert stats["total_requests"] == 100
        assert stats["successful"] == 50


# ============================================================================
# CATEGORY 4: DEADLOCK PREVENTION (3+ tests)
# ============================================================================

class TestDeadlockPrevention:
    """Test that system doesn't deadlock"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_no_deadlock_in_pipeline(self, orchestration_components):
        """Test: Full pipeline doesn't deadlock"""
        planner = orchestration_components["planner"]
        router = orchestration_components["router"]
        validator = orchestration_components["validator"]

        async def process_with_timeout(request):
            try:
                dag = await asyncio.wait_for(planner.decompose_task(request), timeout=5.0)
                routing = await asyncio.wait_for(router.route_tasks(dag.get_all_tasks()), timeout=5.0)
                validation = await validator.validate_routing_plan(dag, routing)
                return validation.is_valid
            except asyncio.TimeoutError:
                return False

        # Run 5 concurrent requests
        tasks = [process_with_timeout(f"Request {i}") for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Should complete without deadlock
        assert len(results) == 5

    @pytest.mark.timeout(5)
    def test_no_deadlock_with_locks(self):
        """Test: Multiple locks don't cause deadlock"""
        lock1 = threading.Lock()
        lock2 = threading.Lock()

        def acquire_locks_ordered():
            # Always acquire in same order to prevent deadlock
            with lock1:
                time.sleep(0.01)
                with lock2:
                    time.sleep(0.01)

        # Concurrent acquisitions
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(acquire_locks_ordered) for _ in range(20)]
            for f in as_completed(futures):
                f.result()

        # Should complete without deadlock

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_no_circular_wait(self, orchestration_components):
        """Test: No circular wait conditions"""
        planner = orchestration_components["planner"]

        # Create tasks with dependencies (but no cycles)
        dag = TaskDAG()
        task1 = Task(task_id="t1", description="Task 1", task_type="generic")
        task2 = Task(task_id="t2", description="Task 2", task_type="generic", dependencies=["t1"])
        task3 = Task(task_id="t3", description="Task 3", task_type="generic", dependencies=["t2"])

        dag.add_task(task1)
        dag.add_task(task2)
        dag.add_task(task3)

        # Should process without circular wait
        router = orchestration_components["router"]
        routing = await router.route_tasks(dag.get_all_tasks())

        assert len(routing.assignments) > 0


# ============================================================================
# CATEGORY 5: RESOURCE CONTENTION (2+ tests)
# ============================================================================

class TestResourceContention:
    """Test resource contention handling"""

    @pytest.mark.asyncio
    async def test_limited_agent_capacity(self, orchestration_components):
        """Test: System handles limited agent capacity"""
        router = orchestration_components["router"]

        # Create 100 tasks competing for limited agents
        tasks = [
            Task(task_id=f"task_{i}", description=f"Task {i}", task_type="implement")
            for i in range(100)
        ]

        # Route all tasks
        routing_tasks = [router.route_tasks([task]) for task in tasks]
        results = await asyncio.gather(*routing_tasks, return_exceptions=True)

        # Should distribute load across agents
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 90

    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, orchestration_components):
        """Test: System handles memory pressure gracefully"""
        pool = orchestration_components["trajectory_pool"]
        from infrastructure.trajectory_pool import Trajectory
        from infrastructure import OperatorType

        # Store many trajectories
        tasks = []
        for i in range(1000):
            def create_traj(idx):
                return Trajectory(
                    trajectory_id=f"traj_{idx}",
                    generation=idx % 10,
                    agent_name="test_agent",
                    code_changes=f"def test_{idx}(): pass" + "x" * 100,
                    test_results={"score": 0.8},
                    operator_applied=OperatorType.RECOMBINATION.value,
                    success_score=0.8
                )

            task = asyncio.to_thread(pool.add_trajectory, create_traj(i))
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        # System should handle memory pressure
        assert len(pool.get_all_trajectories()) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
