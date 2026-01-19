"""
Tests for Darwin agent routing integration

Validates that HALO correctly routes evolution tasks to darwin_agent
"""
import pytest
from infrastructure.halo_router import HALORouter
from infrastructure.task_dag import Task, TaskDAG


class TestDarwinRouting:
    """Test Darwin agent routing rules"""

    def test_darwin_agent_registered(self):
        """Test darwin_agent is registered in HALO"""
        router = HALORouter()

        assert "darwin_agent" in router.agent_registry

        darwin_cap = router.agent_registry["darwin_agent"]
        assert "evolution" in darwin_cap.supported_task_types
        assert "improve_agent" in darwin_cap.supported_task_types
        assert "fix_bug" in darwin_cap.supported_task_types
        assert "optimize" in darwin_cap.supported_task_types

        assert "self_improvement" in darwin_cap.skills
        assert "code_generation" in darwin_cap.skills
        assert "benchmark_validation" in darwin_cap.skills

        assert darwin_cap.cost_tier == "expensive"  # Uses GPT-4o/Claude
        assert darwin_cap.max_concurrent_tasks == 3  # Resource-intensive

    @pytest.mark.asyncio
    async def test_route_evolution_task(self):
        """Test evolution task routes to darwin_agent"""
        router = HALORouter()

        task = Task(
            task_id="evolution_task",
            task_type="evolution",
            description="Evolve agent code"
        )

        dag = TaskDAG()
        dag.add_task(task)

        routing_plan = await router.route_tasks(dag)

        assert routing_plan.assignments["evolution_task"] == "darwin_agent"
        assert "darwin" in routing_plan.explanations["evolution_task"].lower()

    @pytest.mark.asyncio
    async def test_route_improve_agent_task(self):
        """Test improve_agent task routes to darwin_agent"""
        router = HALORouter()

        task = Task(
            task_id="improve_marketing",
            task_type="improve_agent",
            description="Improve marketing agent performance"
        )

        dag = TaskDAG()
        dag.add_task(task)

        routing_plan = await router.route_tasks(dag)

        assert routing_plan.assignments["improve_marketing"] == "darwin_agent"
        assert "Agent improvement" in routing_plan.explanations["improve_marketing"]

    @pytest.mark.asyncio
    async def test_route_bug_fix_task(self):
        """Test fix_bug task with agent_code target routes to darwin_agent"""
        router = HALORouter()

        task = Task(
            task_id="fix_builder_bug",
            task_type="fix_bug",
            description="Fix bug in builder agent",
            metadata={"target": "agent_code"}
        )

        dag = TaskDAG()
        dag.add_task(task)

        routing_plan = await router.route_tasks(dag)

        assert routing_plan.assignments["fix_builder_bug"] == "darwin_agent"
        assert "bug fix" in routing_plan.explanations["fix_builder_bug"].lower()

    @pytest.mark.asyncio
    async def test_route_performance_optimization_task(self):
        """Test optimize task with agent_performance target routes to darwin_agent"""
        router = HALORouter()

        task = Task(
            task_id="optimize_backend",
            task_type="optimize",
            description="Optimize backend agent performance",
            metadata={"target": "agent_performance"}
        )

        dag = TaskDAG()
        dag.add_task(task)

        routing_plan = await router.route_tasks(dag)

        assert routing_plan.assignments["optimize_backend"] == "darwin_agent"
        assert "performance optimization" in routing_plan.explanations["optimize_backend"].lower()

    @pytest.mark.asyncio
    async def test_darwin_routing_priority(self):
        """Test Darwin routing rules have correct priority"""
        router = HALORouter()

        # Find Darwin routing rules
        darwin_rules = [
            rule for rule in router.routing_rules
            if rule.target_agent == "darwin_agent"
        ]

        assert len(darwin_rules) == 4  # 4 Darwin rules added

        # Check priorities
        evolution_rules = [r for r in darwin_rules if r.condition.get("task_type") in ["evolution", "improve_agent"]]
        for rule in evolution_rules:
            assert rule.priority == 20  # High priority

        optimization_rules = [r for r in darwin_rules if r.condition.get("task_type") in ["fix_bug", "optimize"]]
        for rule in optimization_rules:
            assert rule.priority == 15  # Medium-high priority

    @pytest.mark.asyncio
    async def test_darwin_routing_with_multiple_tasks(self):
        """Test routing DAG with mixed Darwin and non-Darwin tasks"""
        router = HALORouter()

        tasks = [
            Task(task_id="design", task_type="design", description="Design system"),
            Task(task_id="evolve", task_type="evolution", description="Evolve agent"),
            Task(task_id="build", task_type="implement", description="Build feature"),
            Task(task_id="improve", task_type="improve_agent", description="Improve agent"),
        ]

        dag = TaskDAG()
        for task in tasks:
            dag.add_task(task)

        routing_plan = await router.route_tasks(dag)

        # Darwin tasks go to darwin_agent
        assert routing_plan.assignments["evolve"] == "darwin_agent"
        assert routing_plan.assignments["improve"] == "darwin_agent"

        # Non-Darwin tasks go to appropriate agents
        assert routing_plan.assignments["design"] == "spec_agent"
        assert routing_plan.assignments["build"] == "builder_agent"

    @pytest.mark.asyncio
    async def test_darwin_load_balancing(self):
        """Test Darwin agent respects max_concurrent_tasks limit"""
        router = HALORouter()

        # Create 5 evolution tasks (exceeds darwin's limit of 3)
        tasks = [
            Task(task_id=f"evolve_{i}", task_type="evolution", description=f"Evolution {i}")
            for i in range(5)
        ]

        dag = TaskDAG()
        for task in tasks:
            dag.add_task(task)

        routing_plan = await router.route_tasks(dag)

        # Darwin agent has max_concurrent_tasks=3, so only 3 should be assigned
        darwin_tasks = [
            task_id for task_id, agent in routing_plan.assignments.items()
            if agent == "darwin_agent"
        ]

        assert len(darwin_tasks) == 3  # Darwin limit is 3 concurrent tasks
        assert len(routing_plan.unassigned_tasks) == 2  # 2 tasks rejected due to load

    @pytest.mark.asyncio
    async def test_darwin_explainability(self):
        """Test Darwin routing decisions are explainable"""
        router = HALORouter()

        task = Task(
            task_id="improve_test",
            task_type="improve_agent",
            description="Improve test agent"
        )

        dag = TaskDAG()
        dag.add_task(task)

        routing_plan = await router.route_tasks(dag)

        # Check explanation is provided
        explanation = router.get_routing_explanation("improve_test", routing_plan)

        assert "darwin_agent" in explanation
        assert "improve" in explanation.lower()
        assert "routed to" in explanation.lower()
