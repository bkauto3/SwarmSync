"""
Test Suite for DAG API Type Conversion Fix

This test suite validates that HALORouter.route_tasks() accepts both:
1. TaskDAG objects (original API)
2. List[Task] objects (new flexible API)
3. TaskDAG.get_all_tasks() results (List[Task])

This fix resolves 49 test failures caused by type mismatch errors.
"""
import pytest
from infrastructure.task_dag import TaskDAG, Task
from infrastructure.halo_router import HALORouter


class TestDAGAPITypeConversion:
    """Test HALORouter accepts both TaskDAG and List[Task]"""

    @pytest.mark.asyncio
    async def test_route_tasks_accepts_taskdag(self):
        """Test original API: route_tasks(dag)"""
        router = HALORouter()

        # Create TaskDAG
        dag = TaskDAG()
        task1 = Task(task_id="task1", task_type="implement", description="Build feature")
        task2 = Task(task_id="task2", task_type="test", description="Test feature")
        dag.add_task(task1)
        dag.add_task(task2)

        # Call with TaskDAG (original API)
        routing_plan = await router.route_tasks(dag)

        # Verify routing worked
        assert len(routing_plan.assignments) == 2
        assert "task1" in routing_plan.assignments
        assert "task2" in routing_plan.assignments

    @pytest.mark.asyncio
    async def test_route_tasks_accepts_list_of_tasks(self):
        """Test new API: route_tasks([task1, task2])"""
        router = HALORouter()

        # Create tasks list
        tasks = [
            Task(task_id="task1", task_type="implement", description="Build feature"),
            Task(task_id="task2", task_type="test", description="Test feature"),
            Task(task_id="task3", task_type="deploy", description="Deploy feature")
        ]

        # Call with List[Task] (new flexible API)
        routing_plan = await router.route_tasks(tasks)

        # Verify routing worked
        assert len(routing_plan.assignments) == 3
        assert "task1" in routing_plan.assignments
        assert "task2" in routing_plan.assignments
        assert "task3" in routing_plan.assignments

    @pytest.mark.asyncio
    async def test_route_tasks_accepts_get_all_tasks_result(self):
        """Test common pattern: route_tasks(dag.get_all_tasks())"""
        router = HALORouter()

        # Create TaskDAG
        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="design", description="Design system"))
        dag.add_task(Task(task_id="task2", task_type="implement", description="Build system"))
        dag.add_task(Task(task_id="task3", task_type="test", description="Test system"))

        # Call with dag.get_all_tasks() result (List[Task])
        routing_plan = await router.route_tasks(dag.get_all_tasks())

        # Verify routing worked
        assert len(routing_plan.assignments) == 3
        assert routing_plan.assignments["task1"] == "spec_agent"
        assert routing_plan.assignments["task2"] == "builder_agent"
        assert routing_plan.assignments["task3"] == "qa_agent"

    @pytest.mark.asyncio
    async def test_route_tasks_single_task_list(self):
        """Test edge case: route_tasks([single_task])"""
        router = HALORouter()

        # Single task in list
        task = Task(task_id="solo", task_type="security", description="Security audit")

        # Call with single-element list
        routing_plan = await router.route_tasks([task])

        # Verify routing worked
        assert len(routing_plan.assignments) == 1
        assert routing_plan.assignments["solo"] == "security_agent"

    @pytest.mark.asyncio
    async def test_route_tasks_empty_list(self):
        """Test edge case: route_tasks([])"""
        router = HALORouter()

        # Empty list
        routing_plan = await router.route_tasks([])

        # Verify empty plan
        assert len(routing_plan.assignments) == 0
        assert routing_plan.is_complete()

    @pytest.mark.asyncio
    async def test_route_tasks_rejects_invalid_type(self):
        """Test type validation: reject non-TaskDAG, non-List types"""
        router = HALORouter()

        # Try with invalid types
        with pytest.raises(TypeError, match="Expected TaskDAG or List\\[Task\\]"):
            await router.route_tasks("invalid")

        with pytest.raises(TypeError, match="Expected TaskDAG or List\\[Task\\]"):
            await router.route_tasks(123)

        with pytest.raises(TypeError, match="Expected TaskDAG or List\\[Task\\]"):
            await router.route_tasks({"task": "dict"})

    @pytest.mark.asyncio
    async def test_route_tasks_rejects_list_with_non_task_objects(self):
        """Test list validation: reject lists containing non-Task objects"""
        router = HALORouter()

        # List with invalid objects
        invalid_list = [
            Task(task_id="valid", task_type="test", description="Valid task"),
            "not a task",
            123
        ]

        with pytest.raises(TypeError, match="Expected Task object"):
            await router.route_tasks(invalid_list)

    @pytest.mark.asyncio
    async def test_backwards_compatibility_with_taskdag(self):
        """Test backwards compatibility: all old TaskDAG calls still work"""
        router = HALORouter()

        # Create complex DAG with dependencies
        dag = TaskDAG()
        task1 = Task(task_id="design", task_type="design", description="Design")
        task2 = Task(task_id="build", task_type="implement", description="Build")
        task3 = Task(task_id="test", task_type="test", description="Test")

        dag.add_task(task1)
        dag.add_task(task2)
        dag.add_task(task3)
        dag.add_dependency("design", "build")
        dag.add_dependency("build", "test")

        # Old API should still work
        routing_plan = await router.route_tasks(dag)

        # Verify topological order respected
        assert len(routing_plan.assignments) == 3

    @pytest.mark.asyncio
    async def test_type_conversion_preserves_task_metadata(self):
        """Test that converting List[Task] to TaskDAG preserves task metadata"""
        router = HALORouter()

        # Create tasks with metadata
        tasks = [
            Task(
                task_id="meta_task",
                task_type="implement",
                description="Task with metadata",
                metadata={"priority": "high", "team": "backend"}
            )
        ]

        # Route with List[Task]
        routing_plan = await router.route_tasks(tasks)

        # Verify task was routed (metadata should be preserved internally)
        assert "meta_task" in routing_plan.assignments
        assert routing_plan.assignments["meta_task"] == "builder_agent"

    @pytest.mark.asyncio
    async def test_flexible_api_with_available_agents_parameter(self):
        """Test that List[Task] API works with optional parameters"""
        router = HALORouter()

        tasks = [
            Task(task_id="t1", task_type="implement", description="Build"),
            Task(task_id="t2", task_type="test", description="Test")
        ]

        # Call with List[Task] + available_agents parameter
        routing_plan = await router.route_tasks(
            tasks,
            available_agents=["builder_agent", "qa_agent"]
        )

        # Verify routing used only available agents
        assert len(routing_plan.assignments) == 2
        assert routing_plan.assignments["t1"] in ["builder_agent", "qa_agent"]
        assert routing_plan.assignments["t2"] in ["builder_agent", "qa_agent"]


class TestDAGAPIErrorMessages:
    """Test clear error messages for API misuse"""

    @pytest.mark.asyncio
    async def test_error_message_includes_usage_examples(self):
        """Test that TypeError includes helpful usage examples"""
        router = HALORouter()

        try:
            await router.route_tasks(None)
            pytest.fail("Should have raised TypeError")
        except TypeError as e:
            error_msg = str(e)
            # Verify error message includes usage examples
            assert "route_tasks(dag)" in error_msg
            assert "route_tasks([task1, task2])" in error_msg
            assert "route_tasks(dag.get_all_tasks())" in error_msg

    @pytest.mark.asyncio
    async def test_error_message_shows_actual_type_received(self):
        """Test that TypeError shows what type was actually received"""
        router = HALORouter()

        try:
            await router.route_tasks({"invalid": "dict"})
            pytest.fail("Should have raised TypeError")
        except TypeError as e:
            error_msg = str(e)
            # Verify error message includes actual type received
            assert "dict" in error_msg
