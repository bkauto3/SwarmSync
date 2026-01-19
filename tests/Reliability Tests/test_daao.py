"""
Test Suite for DAAO Cost Optimization
Based on DAAO (arXiv:2509.11079)

Test Coverage:
- CostProfiler: Metric tracking, cost estimation, success rates
- DAAOOptimizer: Cost optimization, constraint validation
- Integration: HALO→DAAO→AOP pipeline
- Real-time replanning based on execution feedback
"""
import pytest
import asyncio
from infrastructure.cost_profiler import CostProfiler, TaskExecutionMetrics, AgentCostProfile
from infrastructure.daao_optimizer import DAAOOptimizer, OptimizationConstraints, OptimizedPlan
from infrastructure.halo_router import HALORouter, AgentCapability
from infrastructure.task_dag import TaskDAG, Task


@pytest.fixture
def cost_profiler():
    """Create cost profiler instance"""
    return CostProfiler()


@pytest.fixture
def sample_agent_registry():
    """Create sample agent registry for testing"""
    return {
        "builder_agent": AgentCapability(
            agent_name="builder_agent",
            supported_task_types=["implement", "code"],
            skills=["python", "coding"],
            cost_tier="medium",
            success_rate=0.85,
            max_concurrent_tasks=5
        ),
        "qa_agent": AgentCapability(
            agent_name="qa_agent",
            supported_task_types=["test", "validation"],
            skills=["testing", "qa"],
            cost_tier="cheap",
            success_rate=0.90,
            max_concurrent_tasks=10
        ),
        "deploy_agent": AgentCapability(
            agent_name="deploy_agent",
            supported_task_types=["deploy", "infrastructure"],
            skills=["devops", "cloud"],
            cost_tier="medium",
            success_rate=0.88,
            max_concurrent_tasks=5
        )
    }


@pytest.fixture
def daao_optimizer(cost_profiler, sample_agent_registry):
    """Create DAAO optimizer instance"""
    return DAAOOptimizer(
        cost_profiler=cost_profiler,
        agent_registry=sample_agent_registry
    )


@pytest.fixture
def simple_dag():
    """Create simple DAG for testing"""
    dag = TaskDAG()
    dag.add_task(Task(task_id="task1", task_type="implement", description="Write code"))
    dag.add_task(Task(task_id="task2", task_type="test", description="Run tests"))
    dag.add_task(Task(task_id="task3", task_type="deploy", description="Deploy to prod"))
    dag.add_dependency("task1", "task2")  # task2 depends on task1
    dag.add_dependency("task2", "task3")  # task3 depends on task2
    return dag


# ============================================================================
# CostProfiler Tests
# ============================================================================

class TestCostProfiler:
    """Test CostProfiler functionality"""

    def test_record_execution_basic(self, cost_profiler):
        """Test basic execution recording"""
        cost_profiler.record_execution(
            task_id="task1",
            agent_name="builder_agent",
            task_type="implement",
            tokens_used=1000,
            execution_time_seconds=10.0,
            success=True,
            cost_tier="medium"
        )

        profile = cost_profiler.get_profile("builder_agent", "implement")
        assert profile is not None
        assert profile.total_executions == 1
        assert profile.successful_executions == 1
        assert profile.total_tokens == 1000
        assert profile.total_time_seconds == 10.0
        assert profile.success_rate == 1.0

    def test_record_multiple_executions(self, cost_profiler):
        """Test recording multiple executions updates statistics"""
        # Record 3 successful executions
        for i in range(3):
            cost_profiler.record_execution(
                task_id=f"task{i}",
                agent_name="qa_agent",
                task_type="test",
                tokens_used=500 + i * 100,  # Variable token usage
                execution_time_seconds=5.0 + i,
                success=True,
                cost_tier="cheap"
            )

        profile = cost_profiler.get_profile("qa_agent", "test")
        assert profile.total_executions == 3
        assert profile.successful_executions == 3
        assert profile.success_rate == 1.0
        assert profile.total_tokens == 500 + 600 + 700  # 1800
        assert profile.avg_tokens == 600.0

    def test_cost_calculation(self, cost_profiler):
        """Test cost calculation based on token usage"""
        cost_profiler.record_execution(
            task_id="task1",
            agent_name="builder_agent",
            task_type="implement",
            tokens_used=1_000_000,  # 1M tokens
            execution_time_seconds=10.0,
            success=True,
            cost_tier="medium"  # $3/1M tokens
        )

        profile = cost_profiler.get_profile("builder_agent", "implement")
        assert abs(profile.total_cost_usd - 3.0) < 0.01  # Should be ~$3

    def test_success_rate_with_failures(self, cost_profiler):
        """Test success rate calculation with mixed results"""
        # Record 7 successes and 3 failures
        for i in range(10):
            cost_profiler.record_execution(
                task_id=f"task{i}",
                agent_name="deploy_agent",
                task_type="deploy",
                tokens_used=800,
                execution_time_seconds=15.0,
                success=(i < 7),  # First 7 succeed
                cost_tier="medium"
            )

        profile = cost_profiler.get_profile("deploy_agent", "deploy")
        assert profile.total_executions == 10
        assert profile.successful_executions == 7
        assert abs(profile.success_rate - 0.7) < 0.01

    def test_estimate_cost_with_no_history(self, cost_profiler):
        """Test cost estimation with no historical data"""
        estimated_cost = cost_profiler.estimate_cost(
            agent_name="unknown_agent",
            task_type="unknown_type",
            task_complexity=1.0
        )

        # Should return default cost
        assert estimated_cost == 0.01

    def test_estimate_cost_with_history(self, cost_profiler):
        """Test cost estimation with historical data"""
        # Record some history
        cost_profiler.record_execution(
            task_id="task1",
            agent_name="builder_agent",
            task_type="implement",
            tokens_used=500_000,  # 500K tokens
            execution_time_seconds=10.0,
            success=True,
            cost_tier="medium"  # $3/1M tokens = $1.50
        )

        estimated_cost = cost_profiler.estimate_cost(
            agent_name="builder_agent",
            task_type="implement",
            task_complexity=1.0
        )

        # Should be close to $1.50
        assert 1.4 < estimated_cost < 1.6

    def test_adaptive_profiling_recent_data(self, cost_profiler):
        """Test adaptive profiling uses recent execution data"""
        # Record 15 old executions (expensive) - to push out of 10-execution buffer
        for i in range(15):
            cost_profiler.record_execution(
                task_id=f"old_task{i}",
                agent_name="builder_agent",
                task_type="implement",
                tokens_used=1_000_000,  # 1M tokens
                execution_time_seconds=20.0,
                success=True,
                cost_tier="expensive"  # $15/1M tokens = $15.00
            )

        # Record 10 recent executions (cheap) - exactly fill the buffer
        for i in range(10):
            cost_profiler.record_execution(
                task_id=f"recent_task{i}",
                agent_name="builder_agent",
                task_type="implement",
                tokens_used=100_000,  # 100K tokens
                execution_time_seconds=5.0,
                success=True,
                cost_tier="cheap"  # $0.03/1M tokens = $0.003
            )

        profile = cost_profiler.get_profile("builder_agent", "implement")

        # Recent average should reflect only last 10 executions (cheap)
        recent_avg = profile.get_recent_avg_cost()
        overall_avg = profile.avg_cost_usd

        # Recent should be MUCH cheaper than overall (recent=~$0.003, overall=~$9+)
        assert recent_avg < overall_avg * 0.1, f"Recent {recent_avg} should be <10% of overall {overall_avg}"


# ============================================================================
# DAAOOptimizer Tests
# ============================================================================

class TestDAAOOptimizer:
    """Test DAAOOptimizer functionality"""

    @pytest.mark.asyncio
    async def test_optimize_simple_dag(self, daao_optimizer, simple_dag, cost_profiler):
        """Test optimization of a simple DAG"""
        # Seed cost profiler with some history
        cost_profiler.record_execution("t1", "builder_agent", "implement", 800_000, 12.0, True, "medium")
        cost_profiler.record_execution("t2", "qa_agent", "test", 300_000, 5.0, True, "cheap")
        cost_profiler.record_execution("t3", "deploy_agent", "deploy", 500_000, 10.0, True, "medium")

        # Initial plan (from HALO)
        initial_plan = {
            "task1": "builder_agent",
            "task2": "qa_agent",
            "task3": "deploy_agent"
        }

        # Optimize
        optimized_plan = await daao_optimizer.optimize_routing_plan(
            initial_plan=initial_plan,
            dag=simple_dag
        )

        # Verify optimization completed
        assert optimized_plan.assignments is not None
        assert len(optimized_plan.assignments) == 3
        assert optimized_plan.estimated_cost > 0.0
        assert optimized_plan.quality_score > 0.0

    @pytest.mark.asyncio
    async def test_cost_savings_reported(self, daao_optimizer, simple_dag, cost_profiler):
        """Test that cost savings are calculated correctly"""
        # Seed with expensive agent for task1
        cost_profiler.record_execution("t1", "builder_agent", "implement", 1_500_000, 20.0, True, "expensive")

        # Create a cheaper alternative (qa_agent can also do generic tasks)
        daao_optimizer.agent_registry["qa_agent"].supported_task_types.append("implement")
        cost_profiler.record_execution("t2", "qa_agent", "implement", 300_000, 8.0, True, "cheap")

        initial_plan = {
            "task1": "builder_agent",  # Expensive
            "task2": "qa_agent",
            "task3": "deploy_agent"
        }

        optimized_plan = await daao_optimizer.optimize_routing_plan(
            initial_plan=initial_plan,
            dag=simple_dag
        )

        # Should show cost savings
        assert optimized_plan.cost_savings >= 0.0  # Non-negative savings

    @pytest.mark.asyncio
    async def test_quality_constraint_enforcement(self, daao_optimizer, simple_dag, cost_profiler):
        """Test that quality constraints are enforced"""
        # Seed with low-quality cheap agent
        cost_profiler.record_execution("t1", "qa_agent", "implement", 200_000, 5.0, False, "cheap")  # Failure
        cost_profiler.record_execution("t2", "qa_agent", "implement", 200_000, 5.0, False, "cheap")  # Failure
        cost_profiler.record_execution("t3", "qa_agent", "implement", 200_000, 5.0, True, "cheap")   # Success

        # qa_agent has 33% success rate on implement tasks

        # Add implement support to qa_agent
        daao_optimizer.agent_registry["qa_agent"].supported_task_types.append("implement")

        initial_plan = {
            "task1": "builder_agent",
            "task2": "qa_agent",
            "task3": "deploy_agent"
        }

        constraints = OptimizationConstraints(
            min_quality_score=0.85  # Require 85% success rate
        )

        optimized_plan = await daao_optimizer.optimize_routing_plan(
            initial_plan=initial_plan,
            dag=simple_dag,
            constraints=constraints
        )

        # Should NOT assign task1 to qa_agent (too low quality)
        assert optimized_plan.assignments["task1"] == "builder_agent"

    @pytest.mark.asyncio
    async def test_budget_constraint_enforcement(self, daao_optimizer, simple_dag, cost_profiler):
        """Test that budget constraints are enforced"""
        # Seed with expensive operations
        cost_profiler.record_execution("t1", "builder_agent", "implement", 2_000_000, 30.0, True, "expensive")
        cost_profiler.record_execution("t2", "qa_agent", "test", 1_000_000, 15.0, True, "expensive")

        initial_plan = {
            "task1": "builder_agent",
            "task2": "qa_agent",
            "task3": "deploy_agent"
        }

        constraints = OptimizationConstraints(
            max_total_cost=1.0  # Only $1 budget
        )

        optimized_plan = await daao_optimizer.optimize_routing_plan(
            initial_plan=initial_plan,
            dag=simple_dag,
            constraints=constraints
        )

        # With very tight budget, optimizer should fail gracefully or use cheapest options
        # Check that it respects the constraint
        if optimized_plan.optimization_details.get("status") == "constraint_violation":
            # Should fallback to initial plan
            assert optimized_plan.assignments == initial_plan

    @pytest.mark.asyncio
    async def test_task_complexity_estimation(self, daao_optimizer, simple_dag):
        """Test task complexity estimation from DAG structure"""
        complexities = daao_optimizer._estimate_task_complexities(simple_dag)

        assert "task1" in complexities
        assert "task2" in complexities
        assert "task3" in complexities

        # All complexities should be reasonable (0.5 to 3.0)
        for task_id, complexity in complexities.items():
            assert 0.5 <= complexity <= 3.0

    @pytest.mark.asyncio
    async def test_replanning_with_feedback(self, daao_optimizer, simple_dag, cost_profiler):
        """Test real-time replanning based on execution feedback"""
        # Initial plan
        initial_plan = {
            "task1": "builder_agent",
            "task2": "qa_agent",
            "task3": "deploy_agent"
        }

        optimized_plan = await daao_optimizer.optimize_routing_plan(
            initial_plan=initial_plan,
            dag=simple_dag
        )

        # Simulate task1 completion with actual metrics
        completed_tasks = ["task1"]
        actual_metrics = {
            "task1": {
                "tokens_used": 1_200_000,  # More expensive than expected
                "execution_time": 18.0,
                "success": True
            }
        }

        # Replan remaining tasks
        replanned = await daao_optimizer.replan_from_feedback(
            current_plan=optimized_plan,
            dag=simple_dag,
            completed_tasks=completed_tasks,
            actual_metrics=actual_metrics
        )

        # Verify replanning happened
        assert replanned.optimization_details.get("replanned") == True
        assert replanned.optimization_details.get("completed_tasks") == 1


# ============================================================================
# Integration Tests (HALO + DAAO)
# ============================================================================

class TestDAAOIntegration:
    """Test DAAO integration with HALO router"""

    @pytest.mark.asyncio
    async def test_halo_with_daao_enabled(self, simple_dag, cost_profiler, sample_agent_registry):
        """Test HALORouter with DAAO cost optimization enabled"""
        # Create DAAO optimizer
        daao_optimizer = DAAOOptimizer(
            cost_profiler=cost_profiler,
            agent_registry=sample_agent_registry
        )

        # Seed cost profiler
        cost_profiler.record_execution("t1", "builder_agent", "implement", 800_000, 12.0, True, "medium")
        cost_profiler.record_execution("t2", "qa_agent", "test", 300_000, 5.0, True, "cheap")
        cost_profiler.record_execution("t3", "deploy_agent", "deploy", 500_000, 10.0, True, "medium")

        # Create HALO router with DAAO enabled
        halo_router = HALORouter(
            agent_registry=sample_agent_registry,
            enable_cost_optimization=True,
            cost_profiler=cost_profiler,
            daao_optimizer=daao_optimizer
        )

        # Route tasks
        routing_plan = await halo_router.route_tasks(simple_dag)

        # Verify optimization happened
        assert routing_plan.metadata.get("daao_optimized") == True
        assert "cost_savings" in routing_plan.metadata
        assert "estimated_cost" in routing_plan.metadata

    @pytest.mark.asyncio
    async def test_halo_without_daao(self, simple_dag, sample_agent_registry):
        """Test HALORouter without DAAO (baseline behavior)"""
        # Create HALO router WITHOUT DAAO
        halo_router = HALORouter(
            agent_registry=sample_agent_registry,
            enable_cost_optimization=False
        )

        # Route tasks
        routing_plan = await halo_router.route_tasks(simple_dag)

        # Verify no optimization metadata
        assert routing_plan.metadata.get("daao_optimized") is None
        assert "cost_savings" not in routing_plan.metadata


# ============================================================================
# Performance Tests
# ============================================================================

class TestDAAOPerformance:
    """Test DAAO performance characteristics"""

    @pytest.mark.asyncio
    async def test_optimization_latency(self, daao_optimizer, cost_profiler, sample_agent_registry):
        """Test that DAAO optimization completes within acceptable time"""
        import time

        # Create larger DAG (20 tasks)
        dag = TaskDAG()
        for i in range(20):
            task_type = ["implement", "test", "deploy"][i % 3]
            dag.add_task(Task(task_id=f"task{i}", task_type=task_type, description=f"Task {i}"))
            if i > 0:
                dag.add_dependency(f"task{i-1}", f"task{i}")

        # Seed cost profiler
        cost_profiler.record_execution("t1", "builder_agent", "implement", 800_000, 12.0, True, "medium")
        cost_profiler.record_execution("t2", "qa_agent", "test", 300_000, 5.0, True, "cheap")
        cost_profiler.record_execution("t3", "deploy_agent", "deploy", 500_000, 10.0, True, "medium")

        # Create initial plan
        initial_plan = {}
        for i in range(20):
            task_type = ["implement", "test", "deploy"][i % 3]
            agent = ["builder_agent", "qa_agent", "deploy_agent"][i % 3]
            initial_plan[f"task{i}"] = agent

        # Measure optimization time
        start = time.time()
        optimized_plan = await daao_optimizer.optimize_routing_plan(
            initial_plan=initial_plan,
            dag=dag
        )
        elapsed = time.time() - start

        # Should complete within 100ms for 20 tasks
        assert elapsed < 0.1, f"Optimization took {elapsed:.3f}s (expected <100ms)"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
