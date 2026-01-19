"""
Test Suite for HierarchicalPlanner

Coverage:
- Goal decomposition (5 tests)
- Ownership assignment (5 tests)
- Status tracking (3 tests)
- Dependency resolution (3 tests)
- Progress reporting (2 tests)
- PROJECT_STATUS.md generation (2 tests)

Total: 20 tests
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from orchestration.hierarchical_planner import (
    HierarchicalPlanner,
    HierarchicalTask,
    TaskStatus,
    TaskLevel
)
from orchestration.project_status_updater import ProjectStatusUpdater
from infrastructure.task_dag import TaskDAG, Task, TaskStatus as DAGTaskStatus
from infrastructure.halo_router import RoutingPlan


class TestHierarchicalPlanner:
    """Test HierarchicalPlanner core functionality"""

    @pytest.fixture
    def mock_htdag(self):
        """Mock HTDAG decomposer"""
        htdag = Mock()

        async def mock_decompose(user_request, context=None):
            dag = TaskDAG()

            # Create 3 tasks: 1 subgoal, 2 steps
            # Don't set dependencies in constructor - let add_dependency do it
            subgoal = Task(
                task_id="task_0001",
                task_type="implement",
                description="Implement feature flags for progressive rollout"
            )

            step1 = Task(
                task_id="task_0002",
                task_type="code",
                description="Create flags JSON"
            )

            step2 = Task(
                task_id="task_0003",
                task_type="test",
                description="Test flags"
            )

            dag.add_task(subgoal)
            dag.add_task(step1)
            dag.add_task(step2)
            dag.add_dependency("task_0001", "task_0002")
            dag.add_dependency("task_0002", "task_0003")

            return dag

        htdag.decompose_task = AsyncMock(side_effect=mock_decompose)
        return htdag

    @pytest.fixture
    def mock_halo(self):
        """Mock HALO router"""
        halo = Mock()

        async def mock_route(dag, context=None):
            # Assign different agents based on task type
            plan = RoutingPlan()
            for task_id, task in dag.tasks.items():
                if task.task_type == "implement":
                    plan.assignments[task_id] = "builder_agent"
                    plan.explanations[task_id] = "Implementation task"
                elif task.task_type == "code":
                    plan.assignments[task_id] = "coder_agent"
                    plan.explanations[task_id] = "Coding task"
                elif task.task_type == "test":
                    plan.assignments[task_id] = "qa_agent"
                    plan.explanations[task_id] = "Testing task"
                else:
                    plan.assignments[task_id] = "orchestrator"
            return plan

        halo.route_dag = AsyncMock(side_effect=mock_route)
        return halo

    @pytest.fixture
    def planner(self, mock_htdag, mock_halo):
        """Create planner instance"""
        return HierarchicalPlanner(mock_htdag, mock_halo)

    # ===== Goal Decomposition Tests (5 tests) =====

    @pytest.mark.asyncio
    async def test_goal_decomposition_creates_root(self, planner):
        """Test goal decomposition creates root goal task"""
        result = await planner.decompose_with_ownership(
            goal="Launch Phase 4",
            context={"priority": "high"}
        )

        # Should have root goal
        assert result["root_goal_id"] is not None
        root = result["tasks"][result["root_goal_id"]]
        assert root.level == TaskLevel.GOAL
        assert root.description == "Launch Phase 4"
        assert root.metadata["is_root"] is True

    @pytest.mark.asyncio
    async def test_goal_decomposition_creates_hierarchy(self, planner):
        """Test goal → subgoals → steps hierarchy"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        # Should have 1 goal + DAG tasks (but task_0001 becomes subgoal, not separate)
        # Root goal + task_0002 + task_0003 = 3 tasks
        # task_0001 is not included because it has <10 words and becomes a step
        assert len(result["tasks"]) >= 3

        # Count by level
        levels = [t.level for t in result["tasks"].values()]
        assert levels.count(TaskLevel.GOAL) == 1  # The root goal
        # At least some subgoals or steps exist
        assert levels.count(TaskLevel.SUBGOAL) + levels.count(TaskLevel.STEP) >= 2

    @pytest.mark.asyncio
    async def test_goal_decomposition_links_children(self, planner):
        """Test parent-child relationships are tracked"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        root_id = result["root_goal_id"]
        root = result["tasks"][root_id]

        # Root should have children
        assert len(root.children_ids) > 0

        # Children should reference root as parent
        for child_id in root.children_ids:
            child = result["tasks"][child_id]
            assert child.parent_id == root_id

    @pytest.mark.asyncio
    async def test_goal_decomposition_empty_goal_fails(self, planner):
        """Test empty goal raises ValueError"""
        with pytest.raises(ValueError, match="Goal cannot be empty"):
            await planner.decompose_with_ownership("")

    @pytest.mark.asyncio
    async def test_goal_decomposition_preserves_context(self, planner):
        """Test context is preserved in root task metadata"""
        context = {"priority": "high", "deadline": "2025-10-30"}
        result = await planner.decompose_with_ownership("Launch Phase 4", context)

        root = result["tasks"][result["root_goal_id"]]
        assert root.metadata["context"] == context

    # ===== Ownership Assignment Tests (5 tests) =====

    @pytest.mark.asyncio
    async def test_ownership_all_tasks_assigned(self, planner):
        """Test HALO assigns owners to all tasks"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        # All tasks should have owners
        for task_id, task in result["tasks"].items():
            assert task.owner is not None
            assert isinstance(task.owner, str)

    @pytest.mark.asyncio
    async def test_ownership_correct_agents(self, planner):
        """Test correct agents assigned based on task type"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        # Find tasks by description
        tasks = list(result["tasks"].values())

        # Check agent assignments (excluding root goal)
        for task in tasks:
            if task.level != TaskLevel.GOAL:
                task_type = task.metadata.get("task_type")
                if task_type == "implement":
                    assert task.owner == "builder_agent"
                elif task_type == "code":
                    assert task.owner == "coder_agent"
                elif task_type == "test":
                    assert task.owner == "qa_agent"

    @pytest.mark.asyncio
    async def test_ownership_map_generated(self, planner):
        """Test ownership map is generated correctly"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        ownership_map = result["ownership_map"]
        assert len(ownership_map) == len(result["tasks"])

        # All tasks in map
        for task_id in result["tasks"].keys():
            assert task_id in ownership_map

    @pytest.mark.asyncio
    async def test_ownership_fallback_on_halo_failure(self, planner, mock_halo):
        """Test fallback to orchestrator if HALO fails"""
        # Make HALO fail
        mock_halo.route_dag = AsyncMock(side_effect=Exception("HALO down"))

        result = await planner.decompose_with_ownership("Launch Phase 4")

        # Should still assign orchestrator as fallback
        for task in result["tasks"].values():
            if task.level != TaskLevel.GOAL:  # Root may not have owner assigned
                assert task.owner == "orchestrator"

    @pytest.mark.asyncio
    async def test_ownership_workload_distribution(self, planner):
        """Test agent workload is tracked correctly"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        workload = planner.get_agent_workload()

        # Should have entries for assigned agents
        assert len(workload) > 0

        # Each agent should have stats
        for agent_name, stats in workload.items():
            assert "total" in stats
            assert "completed" in stats
            assert "in_progress" in stats
            assert "pending" in stats
            assert stats["total"] > 0

    # ===== Status Tracking Tests (3 tests) =====

    @pytest.mark.asyncio
    async def test_status_tracking_updates_status(self, planner):
        """Test status updates work correctly"""
        result = await planner.decompose_with_ownership("Launch Phase 4")
        task_ids = list(result["tasks"].keys())

        # Update status
        planner.update_task_status(task_ids[1], TaskStatus.IN_PROGRESS)
        assert result["tasks"][task_ids[1]].status == TaskStatus.IN_PROGRESS

        planner.update_task_status(task_ids[1], TaskStatus.COMPLETED)
        assert result["tasks"][task_ids[1]].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_status_tracking_timestamps(self, planner):
        """Test timestamps are tracked correctly"""
        result = await planner.decompose_with_ownership("Launch Phase 4")
        task_id = list(result["tasks"].keys())[1]
        task = result["tasks"][task_id]

        # Initially no timestamps
        assert task.started_at is None
        assert task.completed_at is None

        # Start task
        planner.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        assert task.started_at is not None

        # Complete task
        planner.update_task_status(task_id, TaskStatus.COMPLETED)
        assert task.completed_at is not None

        # Duration should be calculable
        assert task.duration() is not None
        assert task.duration() >= 0

    @pytest.mark.asyncio
    async def test_status_tracking_invalid_task_fails(self, planner):
        """Test updating non-existent task raises ValueError"""
        await planner.decompose_with_ownership("Launch Phase 4")

        with pytest.raises(ValueError, match="Task .* not found"):
            planner.update_task_status("invalid_id", TaskStatus.COMPLETED)

    # ===== Dependency Resolution Tests (3 tests) =====

    @pytest.mark.asyncio
    async def test_dependency_execution_order(self, planner):
        """Test execution order respects dependencies"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        order = result["execution_order"]
        assert len(order) == len(result["tasks"])

        # Check dependencies: no task executes before its dependencies
        executed = set()
        for task_id in order:
            task = result["tasks"][task_id]
            for dep_id in task.blocked_by:
                assert dep_id in executed, f"Dependency {dep_id} not executed before {task_id}"
            executed.add(task_id)

    @pytest.mark.asyncio
    async def test_dependency_is_ready_check(self, planner):
        """Test is_ready() checks dependencies correctly"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        # Find a task with dependencies
        task_with_deps = None
        for task in result["tasks"].values():
            if task.blocked_by:
                task_with_deps = task
                break

        assert task_with_deps is not None

        # Not ready initially (dependencies not completed)
        assert not task_with_deps.is_ready(set())

        # Ready when all dependencies completed
        completed = set(task_with_deps.blocked_by)
        assert task_with_deps.is_ready(completed)

    @pytest.mark.asyncio
    async def test_dependency_blocked_by_tracking(self, planner):
        """Test blocked_by list is populated from DAG dependencies"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        # task_0002 depends on task_0001
        task_0002 = result["tasks"]["task_0002"]
        assert "task_0001" in task_0002.blocked_by

        # task_0003 depends on task_0002
        task_0003 = result["tasks"]["task_0003"]
        assert "task_0002" in task_0003.blocked_by

    # ===== Progress Reporting Tests (2 tests) =====

    @pytest.mark.asyncio
    async def test_progress_summary_metrics(self, planner):
        """Test progress summary calculates metrics correctly"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        summary = planner.get_progress_summary()

        # Check structure
        assert "total_tasks" in summary
        assert "completed" in summary
        assert "in_progress" in summary
        assert "pending" in summary
        assert "blocked" in summary
        assert "failed" in summary
        assert "completion_pct" in summary

        # Check values
        assert summary["total_tasks"] == len(result["tasks"])
        assert summary["completion_pct"] == 0.0  # Nothing completed yet

        # Complete a task
        task_id = list(result["tasks"].keys())[1]
        planner.update_task_status(task_id, TaskStatus.COMPLETED)

        summary = planner.get_progress_summary()
        assert summary["completed"] == 1
        assert summary["completion_pct"] > 0.0

    @pytest.mark.asyncio
    async def test_progress_workload_by_agent(self, planner):
        """Test agent workload distribution is calculated"""
        result = await planner.decompose_with_ownership("Launch Phase 4")

        workload = planner.get_agent_workload()

        # Should have multiple agents
        assert len(workload) > 0

        # Complete a task and check workload updates
        task_id = list(result["tasks"].keys())[1]
        task = result["tasks"][task_id]
        agent = task.owner

        planner.update_task_status(task_id, TaskStatus.COMPLETED)

        updated_workload = planner.get_agent_workload()
        assert updated_workload[agent]["completed"] == 1


class TestProjectStatusUpdater:
    """Test ProjectStatusUpdater functionality"""

    @pytest.fixture
    def mock_planner(self):
        """Mock planner with sample tasks"""
        planner = Mock(spec=HierarchicalPlanner)

        # Create sample tasks
        planner.tasks = {
            "task_0001": HierarchicalTask(
                id="task_0001",
                level=TaskLevel.GOAL,
                description="Launch Phase 4",
                owner="orchestrator",
                status=TaskStatus.IN_PROGRESS
            ),
            "task_0002": HierarchicalTask(
                id="task_0002",
                level=TaskLevel.SUBGOAL,
                description="Implement feature flags",
                owner="builder_agent",
                status=TaskStatus.COMPLETED,
                parent_id="task_0001",
                started_at=datetime.now(),
                completed_at=datetime.now()
            ),
            "task_0003": HierarchicalTask(
                id="task_0003",
                level=TaskLevel.STEP,
                description="Create flags JSON",
                owner="coder_agent",
                status=TaskStatus.PENDING,
                parent_id="task_0002",
                blocked_by=["task_0002"]
            )
        }

        planner.get_progress_summary.return_value = {
            "total_tasks": 3,
            "completed": 1,
            "in_progress": 1,
            "pending": 1,
            "blocked": 0,
            "failed": 0,
            "completion_pct": 0.33
        }

        planner.get_agent_workload.return_value = {
            "orchestrator": {"total": 1, "completed": 0, "in_progress": 1, "pending": 0},
            "builder_agent": {"total": 1, "completed": 1, "in_progress": 0, "pending": 0},
            "coder_agent": {"total": 1, "completed": 0, "in_progress": 0, "pending": 1}
        }

        return planner

    @pytest.fixture
    def updater(self, mock_planner, tmp_path):
        """Create updater instance with temp file"""
        status_file = tmp_path / "PROJECT_STATUS.md"
        return ProjectStatusUpdater(mock_planner, str(status_file))

    def test_status_report_generation(self, updater):
        """Test status report is generated correctly"""
        report = updater.generate_status_report()

        # Check key sections exist
        assert "# Project Status (Auto-Generated)" in report
        assert "## 📊 Overall Progress" in report
        assert "## 👥 Agent Workload Distribution" in report
        assert "## 📋 Task Breakdown by Owner" in report

        # Check metrics
        assert "33.3%" in report  # Completion percentage
        assert "✅ Completed" in report
        assert "⏳ In Progress" in report
        assert "📋 Pending" in report

        # Check agents mentioned
        assert "orchestrator" in report
        assert "builder_agent" in report
        assert "coder_agent" in report

    def test_status_file_update(self, updater, tmp_path):
        """Test status file is written correctly"""
        updater.update_file()

        # Check file exists
        status_file = tmp_path / "PROJECT_STATUS.md"
        assert status_file.exists()

        # Check content
        content = status_file.read_text()
        assert "# Project Status (Auto-Generated)" in content
        assert "Launch Phase 4" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
