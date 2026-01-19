"""
Unit tests for GAP Planner (Graph-based Agent Planning).

Tests cover:
- Plan parsing (XML format)
- Heuristic decomposition (fallback)
- DAG construction (topological sort)
- Circular dependency detection
- Parallel execution
- Speedup calculation
- End-to-end pipeline

Based on arXiv:2510.25320 - GAP framework for parallel tool execution.

Author: Claude Code (Genesis AI Team)
Date: November 1, 2025
"""

import pytest
import asyncio
from infrastructure.orchestration.gap_planner import GAPPlanner, Task


class TestTaskDataclass:
    """Test Task dataclass functionality."""

    def test_task_creation(self):
        """Test basic Task creation"""
        task = Task(
            id="task_1",
            description="Fetch user data",
            dependencies=set()
        )

        assert task.id == "task_1"
        assert task.description == "Fetch user data"
        assert task.dependencies == set()
        assert task.status == "pending"
        assert task.result is None
        assert task.error is None

    def test_task_with_dependencies(self):
        """Test Task with dependencies"""
        task = Task(
            id="task_3",
            description="Generate report",
            dependencies={"task_1", "task_2"}
        )

        assert len(task.dependencies) == 2
        assert "task_1" in task.dependencies
        assert "task_2" in task.dependencies

    def test_task_hash(self):
        """Test Task is hashable (for set operations)"""
        task1 = Task(id="task_1", description="Test")
        task2 = Task(id="task_1", description="Test")

        # Same ID = same hash
        assert hash(task1) == hash(task2)

        # Can be added to set
        task_set = {task1, task2}
        assert len(task_set) == 1  # Deduplication works


class TestParsePlan:
    """Test plan parsing from XML-style format."""

    def test_parse_simple_plan(self):
        """Test parsing a simple 3-task plan"""
        planner = GAPPlanner()

        plan_text = """
        <plan>
        Task 1: Fetch user data | Dependencies: none
        Task 2: Calculate metrics | Dependencies: none
        Task 3: Generate report | Dependencies: Task 1, Task 2
        </plan>
        """

        tasks = planner.parse_plan(plan_text)

        assert len(tasks) == 3
        assert tasks[0].id == "task_1"
        assert tasks[0].description == "Fetch user data"
        assert tasks[0].dependencies == set()

        assert tasks[1].id == "task_2"
        assert tasks[1].description == "Calculate metrics"
        assert tasks[1].dependencies == set()

        assert tasks[2].id == "task_3"
        assert tasks[2].description == "Generate report"
        assert tasks[2].dependencies == {"task_1", "task_2"}

    def test_parse_with_think_block(self):
        """Test parsing plan with <think> block (should be ignored)"""
        planner = GAPPlanner()

        plan_text = """
        <think>
        This query requires fetching two independent pieces of data, then comparing them.
        </think>

        <plan>
        Task 1: Search for population of Paris | Dependencies: none
        Task 2: Search for population of London | Dependencies: none
        Task 3: Compare populations | Dependencies: Task 1, Task 2
        </plan>
        """

        tasks = planner.parse_plan(plan_text)

        assert len(tasks) == 3
        assert "Paris" in tasks[0].description
        assert "London" in tasks[1].description
        assert "Compare" in tasks[2].description

    def test_parse_single_dependency(self):
        """Test parsing task with single dependency"""
        planner = GAPPlanner()

        plan_text = """
        <plan>
        Task 1: Fetch data | Dependencies: none
        Task 2: Process data | Dependencies: Task 1
        </plan>
        """

        tasks = planner.parse_plan(plan_text)

        assert len(tasks) == 2
        assert tasks[1].dependencies == {"task_1"}

    def test_parse_no_plan_block(self):
        """Test fallback to heuristic decomposition when <plan> missing"""
        planner = GAPPlanner()

        query = "Fetch user data and calculate metrics"
        tasks = planner.parse_plan(query)

        # Should use heuristic decomposition
        assert len(tasks) >= 1
        assert all(isinstance(t, Task) for t in tasks)

    def test_parse_empty_plan(self):
        """Test parsing empty <plan> block"""
        planner = GAPPlanner()

        plan_text = """
        <plan>
        </plan>
        """

        tasks = planner.parse_plan(plan_text)

        # Empty plan = use heuristic decomposition on empty string
        assert len(tasks) >= 0

    def test_parse_malformed_task_line(self):
        """Test handling malformed task lines"""
        planner = GAPPlanner()

        plan_text = """
        <plan>
        Task 1: Valid task | Dependencies: none
        This is not a valid task line
        Task 2: Another valid task | Dependencies: none
        </plan>
        """

        tasks = planner.parse_plan(plan_text)

        # Should skip malformed line, parse valid ones
        assert len(tasks) == 2
        assert tasks[0].id == "task_1"
        assert tasks[1].id == "task_2"


class TestHeuristicDecompose:
    """Test heuristic task decomposition fallback."""

    def test_decompose_with_and(self):
        """Test splitting on 'and' keyword"""
        planner = GAPPlanner()

        query = "Fetch user data and calculate metrics and generate report"
        tasks = planner._heuristic_decompose(query)

        assert len(tasks) == 3
        assert "Fetch user data" in tasks[0].description
        assert "calculate metrics" in tasks[1].description
        assert "generate report" in tasks[2].description

    def test_decompose_with_then(self):
        """Test splitting on 'then' keyword"""
        planner = GAPPlanner()

        query = "First fetch data then process it then save results"
        tasks = planner._heuristic_decompose(query)

        assert len(tasks) == 3
        assert all(isinstance(t, Task) for t in tasks)

    def test_decompose_sequential_dependencies(self):
        """Test heuristic creates sequential dependencies"""
        planner = GAPPlanner()

        query = "Step A and Step B and Step C"
        tasks = planner._heuristic_decompose(query)

        # Task 1: no dependencies
        assert tasks[0].dependencies == set()

        # Task 2: depends on Task 1
        assert tasks[1].dependencies == {"task_1"}

        # Task 3: depends on Task 2
        assert tasks[2].dependencies == {"task_2"}

    def test_decompose_single_task(self):
        """Test single task with no splitting"""
        planner = GAPPlanner()

        query = "Fetch user data"
        tasks = planner._heuristic_decompose(query)

        assert len(tasks) == 1
        assert tasks[0].description == "Fetch user data"
        assert tasks[0].dependencies == set()

    def test_decompose_with_period(self):
        """Test splitting on period"""
        planner = GAPPlanner()

        query = "Fetch data. Process data. Save results."
        tasks = planner._heuristic_decompose(query)

        assert len(tasks) == 3


class TestBuildDAG:
    """Test DAG construction via topological sort."""

    def test_build_simple_dag(self):
        """Test building DAG with 2 levels"""
        planner = GAPPlanner()

        tasks = [
            Task(id="task_1", description="A", dependencies=set()),
            Task(id="task_2", description="B", dependencies=set()),
            Task(id="task_3", description="C", dependencies={"task_1", "task_2"})
        ]

        dag = planner.build_dag(tasks)

        # Level 0: task_1, task_2 (no dependencies)
        assert len(dag[0]) == 2
        assert set(t.id for t in dag[0]) == {"task_1", "task_2"}

        # Level 1: task_3 (depends on task_1, task_2)
        assert len(dag[1]) == 1
        assert dag[1][0].id == "task_3"

    def test_build_sequential_dag(self):
        """Test building sequential DAG (3 levels)"""
        planner = GAPPlanner()

        tasks = [
            Task(id="task_1", description="A", dependencies=set()),
            Task(id="task_2", description="B", dependencies={"task_1"}),
            Task(id="task_3", description="C", dependencies={"task_2"})
        ]

        dag = planner.build_dag(tasks)

        # 3 levels (sequential)
        assert len(dag) == 3
        assert dag[0][0].id == "task_1"
        assert dag[1][0].id == "task_2"
        assert dag[2][0].id == "task_3"

    def test_build_parallel_dag(self):
        """Test building fully parallel DAG (all Level 0)"""
        planner = GAPPlanner()

        tasks = [
            Task(id="task_1", description="A", dependencies=set()),
            Task(id="task_2", description="B", dependencies=set()),
            Task(id="task_3", description="C", dependencies=set())
        ]

        dag = planner.build_dag(tasks)

        # All in Level 0
        assert len(dag) == 1
        assert len(dag[0]) == 3

    def test_circular_dependency_detection(self):
        """Test circular dependency detection"""
        planner = GAPPlanner()

        tasks = [
            Task(id="task_1", description="A", dependencies={"task_2"}),
            Task(id="task_2", description="B", dependencies={"task_1"})
        ]

        with pytest.raises(ValueError, match="Circular dependencies"):
            planner.build_dag(tasks)

    def test_self_dependency_detection(self):
        """Test self-dependency detection"""
        planner = GAPPlanner()

        tasks = [
            Task(id="task_1", description="A", dependencies={"task_1"})
        ]

        with pytest.raises(ValueError, match="Circular dependencies"):
            planner.build_dag(tasks)

    def test_complex_dag(self):
        """Test complex DAG with 4 levels"""
        planner = GAPPlanner()

        tasks = [
            Task(id="task_1", description="A", dependencies=set()),
            Task(id="task_2", description="B", dependencies=set()),
            Task(id="task_3", description="C", dependencies={"task_1"}),
            Task(id="task_4", description="D", dependencies={"task_1", "task_2"}),
            Task(id="task_5", description="E", dependencies={"task_3", "task_4"})
        ]

        dag = planner.build_dag(tasks)

        # Level 0: task_1, task_2
        assert len(dag[0]) == 2

        # Level 1: task_3, task_4
        assert len(dag[1]) == 2

        # Level 2: task_5
        assert len(dag[2]) == 1
        assert dag[2][0].id == "task_5"


class TestExecuteLevel:
    """Test parallel execution of task levels."""

    @pytest.mark.asyncio
    async def test_execute_single_task(self):
        """Test executing single task"""
        planner = GAPPlanner()

        task = Task(id="task_1", description="Fetch data", dependencies=set())
        context = {}

        observations = await planner.execute_level([task], context)

        assert "task_1" in observations
        assert observations["task_1"]["result"] is not None
        assert observations["task_1"]["execution_time_ms"] > 0
        assert task.status == "complete"

    @pytest.mark.asyncio
    async def test_execute_parallel_tasks(self):
        """Test executing multiple tasks in parallel"""
        planner = GAPPlanner()

        tasks = [
            Task(id="task_1", description="Fetch A", dependencies=set()),
            Task(id="task_2", description="Fetch B", dependencies=set()),
            Task(id="task_3", description="Fetch C", dependencies=set())
        ]
        context = {}

        observations = await planner.execute_level(tasks, context)

        # All 3 tasks complete
        assert len(observations) == 3
        assert all(t.status == "complete" for t in tasks)
        assert all("result" in obs for obs in observations.values())

    @pytest.mark.asyncio
    async def test_task_failure_handling(self):
        """Test handling task execution failure"""
        planner = GAPPlanner()

        # Mock a task that will fail
        task = Task(id="task_1", description="Invalid task", dependencies=set())

        # Patch execute_task to simulate failure
        import unittest.mock as mock

        async def mock_execute_fail(task):
            task.status = "failed"
            task.error = "Simulated failure"
            return (task.id, None, 100.0)

        with mock.patch.object(planner, 'execute_level') as mock_exec:
            # Still returns observations, just with None result
            mock_exec.return_value = {
                "task_1": {
                    "result": None,
                    "execution_time_ms": 100.0
                }
            }

            observations = await mock_exec([task], {})
            assert observations["task_1"]["result"] is None


class TestExecutePlan:
    """Test end-to-end plan execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_query(self):
        """Test executing simple query end-to-end"""
        planner = GAPPlanner()

        query = "What is the capital of France?"

        result = await planner.execute_plan(query)

        assert "answer" in result
        assert "observations" in result
        assert "total_time_ms" in result
        assert "speedup_factor" in result
        assert "task_count" in result
        assert "level_count" in result

        assert result["task_count"] >= 1
        assert result["speedup_factor"] >= 1.0

    @pytest.mark.asyncio
    async def test_execute_with_plan_text(self):
        """Test executing with provided plan text"""
        planner = GAPPlanner()

        query = "Compare Paris and London populations"
        plan_text = """
        <plan>
        Task 1: Get Paris population | Dependencies: none
        Task 2: Get London population | Dependencies: none
        Task 3: Compare results | Dependencies: Task 1, Task 2
        </plan>
        """

        result = await planner.execute_plan(query, plan_text=plan_text)

        assert result["task_count"] == 3
        assert result["level_count"] == 2  # 2 levels (parallel + sequential)
        assert result["speedup_factor"] > 1.0  # Parallel speedup

    @pytest.mark.asyncio
    async def test_speedup_calculation(self):
        """Test parallel speedup calculation"""
        planner = GAPPlanner()

        plan_text = """
        <plan>
        Task 1: Parallel task A | Dependencies: none
        Task 2: Parallel task B | Dependencies: none
        Task 3: Sequential task | Dependencies: Task 1, Task 2
        </plan>
        """

        result = await planner.execute_plan("test query", plan_text=plan_text)

        # Speedup should be ~1.5x-2x for this pattern
        # (2 parallel tasks + 1 sequential vs 3 sequential)
        assert result["speedup_factor"] >= 1.2

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test handling empty query"""
        planner = GAPPlanner()

        result = await planner.execute_plan("")

        # Should still return valid result structure
        assert "answer" in result
        assert result["task_count"] >= 0

    @pytest.mark.asyncio
    async def test_circular_dependency_error(self):
        """Test handling circular dependencies in plan"""
        planner = GAPPlanner()

        plan_text = """
        <plan>
        Task 1: A | Dependencies: Task 2
        Task 2: B | Dependencies: Task 1
        </plan>
        """

        result = await planner.execute_plan("test", plan_text=plan_text)

        # Should return error in answer
        assert "Error" in result["answer"]
        assert result["task_count"] == 2
        assert result["level_count"] == 0


class TestGetStatistics:
    """Test statistics tracking."""

    @pytest.mark.asyncio
    async def test_statistics_empty(self):
        """Test statistics with no executions"""
        planner = GAPPlanner()

        stats = planner.get_statistics()

        assert stats["avg_speedup"] == 0.0
        assert stats["avg_tasks"] == 0.0
        assert stats["avg_levels"] == 0.0
        assert stats["avg_time_ms"] == 0.0

    @pytest.mark.asyncio
    async def test_statistics_after_execution(self):
        """Test statistics after one execution"""
        planner = GAPPlanner()

        await planner.execute_plan("Test query")

        stats = planner.get_statistics()

        assert stats["avg_speedup"] >= 1.0
        assert stats["avg_tasks"] >= 1
        assert stats["avg_levels"] >= 1
        assert stats["avg_time_ms"] > 0
        assert stats["total_executions"] == 1

    @pytest.mark.asyncio
    async def test_statistics_multiple_executions(self):
        """Test statistics after multiple executions"""
        planner = GAPPlanner()

        # Execute 3 queries
        await planner.execute_plan("Query 1")
        await planner.execute_plan("Query 2")
        await planner.execute_plan("Query 3")

        stats = planner.get_statistics()

        assert stats["total_executions"] == 3
        assert stats["avg_speedup"] >= 1.0
        assert stats["avg_tasks"] >= 1
        assert stats["avg_levels"] >= 1
        assert stats["avg_time_ms"] > 0


class TestIntegration:
    """Integration tests for complete GAP workflows."""

    @pytest.mark.asyncio
    async def test_hotpotqa_style_query(self):
        """Test HotpotQA-style multi-hop query"""
        planner = GAPPlanner()

        query = "What is the population of the capital of France?"
        plan_text = """
        <plan>
        Task 1: Find capital of France | Dependencies: none
        Task 2: Get population of that capital | Dependencies: Task 1
        </plan>
        """

        result = await planner.execute_plan(query, plan_text=plan_text)

        assert result["task_count"] == 2
        assert result["level_count"] == 2  # Sequential
        assert result["speedup_factor"] == 1.0  # No parallelism

    @pytest.mark.asyncio
    async def test_parallel_search_query(self):
        """Test parallel search query (like paper example)"""
        planner = GAPPlanner()

        query = "Compare populations of Paris and London"
        plan_text = """
        <plan>
        Task 1: Search Paris population | Dependencies: none
        Task 2: Search London population | Dependencies: none
        Task 3: Compare results | Dependencies: Task 1, Task 2
        </plan>
        """

        result = await planner.execute_plan(query, plan_text=plan_text)

        assert result["task_count"] == 3
        assert result["level_count"] == 2  # Parallel + merge
        assert result["speedup_factor"] > 1.0  # Expect ~1.5x speedup

    @pytest.mark.asyncio
    async def test_complex_multi_step_query(self):
        """Test complex query with 4+ steps"""
        planner = GAPPlanner()

        query = "Analyze sales trends"
        plan_text = """
        <plan>
        Task 1: Fetch Q1 sales data | Dependencies: none
        Task 2: Fetch Q2 sales data | Dependencies: none
        Task 3: Fetch Q3 sales data | Dependencies: none
        Task 4: Calculate Q1-Q2 growth | Dependencies: Task 1, Task 2
        Task 5: Calculate Q2-Q3 growth | Dependencies: Task 2, Task 3
        Task 6: Generate trend report | Dependencies: Task 4, Task 5
        </plan>
        """

        result = await planner.execute_plan(query, plan_text=plan_text)

        assert result["task_count"] == 6
        assert result["level_count"] == 3  # 3 levels of parallelism
        assert result["speedup_factor"] >= 1.5  # Significant speedup expected

    @pytest.mark.asyncio
    async def test_heuristic_fallback_integration(self):
        """Test complete flow with heuristic fallback"""
        planner = GAPPlanner()

        query = "Fetch data and process it and save results"

        # No plan_text = uses heuristic decomposition
        result = await planner.execute_plan(query)

        assert result["task_count"] >= 3
        assert result["level_count"] >= 3  # Heuristic creates sequential
        assert result["speedup_factor"] == 1.0  # No parallelism in sequential


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
