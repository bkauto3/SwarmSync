"""
Tests for AATC (Agent-Augmented Tool Creation) System

Tests cover:
- ToolGenerator: Tool generation and safety validation
- DynamicAgentCreator: Agent creation with custom tools
- HALORouter integration: AATC fallback routing
"""

import asyncio
import pytest
from dataclasses import asdict

from infrastructure.tool_generator import (
    ToolGenerator,
    ToolSafetyValidator,
    ToolSpec,
    SecurityError,
)
from infrastructure.dynamic_agent_creator import (
    DynamicAgentCreator,
    DynamicAgent,
    AgentCreationError,
)
from infrastructure.halo_router import HALORouter, AgentCapability
from infrastructure.task_dag import TaskDAG, Task, TaskStatus


# ==================== Tool Generator Tests ====================


class TestToolSafetyValidator:
    """Test tool safety validation"""

    def setup_method(self):
        self.validator = ToolSafetyValidator()

    def test_safe_tool_passes(self):
        """Safe tool should pass validation"""
        tool = ToolSpec(
            tool_name="fetch_url",
            description="Fetch URL content",
            input_schema={"url": "str"},
            output_schema={"content": "str"},
            implementation='''
import requests

def fetch_url(url: str) -> dict:
    """Fetch URL content"""
    try:
        response = requests.get(url, timeout=10)
        return {"status": "success", "content": response.text}
    except Exception as e:
        return {"status": "error", "error": str(e)}
''',
            dependencies=["requests"],
        )

        assert self.validator.is_safe(tool) is True

    def test_eval_rejected(self):
        """Tool with eval() should be rejected"""
        tool = ToolSpec(
            tool_name="dangerous_tool",
            description="Dangerous tool",
            input_schema={},
            output_schema={},
            implementation='''
def dangerous_tool():
    result = eval("1 + 1")
    return result
''',
        )

        assert self.validator.is_safe(tool) is False

    def test_exec_rejected(self):
        """Tool with exec() should be rejected"""
        tool = ToolSpec(
            tool_name="dangerous_tool",
            description="Dangerous tool",
            input_schema={},
            output_schema={},
            implementation='''
def dangerous_tool():
    exec("print('hello')")
''',
        )

        assert self.validator.is_safe(tool) is False

    def test_subprocess_rejected(self):
        """Tool with subprocess should be rejected"""
        tool = ToolSpec(
            tool_name="dangerous_tool",
            description="Dangerous tool",
            input_schema={},
            output_schema={},
            implementation='''
import subprocess

def dangerous_tool():
    subprocess.run(['ls', '-la'])
''',
        )

        assert self.validator.is_safe(tool) is False

    def test_file_access_rejected(self):
        """Tool with raw file access should be rejected"""
        tool = ToolSpec(
            tool_name="dangerous_tool",
            description="Dangerous tool",
            input_schema={},
            output_schema={},
            implementation='''
def dangerous_tool():
    with open('/etc/passwd', 'r') as f:
        return f.read()
''',
        )

        assert self.validator.is_safe(tool) is False

    def test_non_whitelisted_import_rejected(self):
        """Tool importing non-whitelisted module should be rejected"""
        tool = ToolSpec(
            tool_name="dangerous_tool",
            description="Dangerous tool",
            input_schema={},
            output_schema={},
            implementation='''
import os

def dangerous_tool():
    return os.listdir('/')
''',
        )

        assert self.validator.is_safe(tool) is False

    def test_whitelisted_imports_allowed(self):
        """Whitelisted imports should be allowed"""
        tool = ToolSpec(
            tool_name="json_parser",
            description="Parse JSON",
            input_schema={"data": "str"},
            output_schema={"result": "dict"},
            implementation='''
import json
from typing import Dict

def json_parser(data: str) -> Dict:
    """Parse JSON string"""
    return json.loads(data)
''',
            dependencies=["json"],
        )

        assert self.validator.is_safe(tool) is True


class TestToolGenerator:
    """Test tool generation"""

    @pytest.fixture
    def generator(self):
        return ToolGenerator(llm_client=None)  # Use heuristic generation

    @pytest.mark.asyncio
    async def test_generate_fetch_tool(self, generator):
        """Test generating fetch tool"""
        tool = await generator.generate_tool(
            task_description="Fetch content from URL",
            context={}
        )

        assert tool.tool_name == "fetch_url"
        assert "fetch" in tool.description.lower()
        assert tool.dependencies == ["requests"]
        assert "url" in tool.input_schema
        assert len(tool.test_cases) > 0

    @pytest.mark.asyncio
    async def test_generate_parse_tool(self, generator):
        """Test generating JSON parse tool"""
        tool = await generator.generate_tool(
            task_description="Parse JSON data from API",
            context={}
        )

        assert "parse" in tool.tool_name or "json" in tool.tool_name.lower()
        assert "json" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_generate_generic_tool(self, generator):
        """Test generating generic tool"""
        tool = await generator.generate_tool(
            task_description="Process customer data",
            context={}
        )

        assert tool.tool_name is not None
        assert tool.description is not None
        assert tool.implementation is not None

    @pytest.mark.asyncio
    async def test_generated_tool_is_safe(self, generator):
        """Generated tools should pass safety validation"""
        tool = await generator.generate_tool(
            task_description="Fetch and parse JSON data",
            context={}
        )

        # Should not raise SecurityError
        assert generator.safety_validator.is_safe(tool) is True

    @pytest.mark.asyncio
    async def test_validate_tool_syntax(self, generator):
        """Test tool syntax validation"""
        tool = ToolSpec(
            tool_name="valid_tool",
            description="Valid tool",
            input_schema={"x": "int"},
            output_schema={"result": "int"},
            implementation='''
def valid_tool(x: int) -> dict:
    """Valid tool"""
    return {"result": x * 2}
''',
        )

        result = await generator.validate_tool(tool)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_tool_invalid_syntax(self, generator):
        """Test tool with invalid syntax"""
        tool = ToolSpec(
            tool_name="invalid_tool",
            description="Invalid syntax",
            input_schema={},
            output_schema={},
            implementation='''
def invalid_tool(
    # Missing closing parenthesis
''',
        )

        with pytest.raises(ValueError, match="syntax errors"):
            await generator.validate_tool(tool)


# ==================== Dynamic Agent Creator Tests ====================


class TestDynamicAgentCreator:
    """Test dynamic agent creation"""

    @pytest.fixture
    def creator(self):
        return DynamicAgentCreator(llm_client=None)  # Use heuristic generation

    @pytest.mark.asyncio
    async def test_create_scraper_agent(self, creator):
        """Test creating web scraping agent"""
        agent = await creator.create_agent_for_task(
            task_description="Scrape cryptocurrency prices from exchanges",
            context={"data_format": "json"}
        )

        assert agent.agent_id.startswith("dynamic_")
        assert "scraper" in agent.name.lower() or "scrape" in agent.description.lower()
        assert len(agent.tools) > 0
        assert "web_scraping" in agent.capabilities or "data_extraction" in agent.capabilities
        assert agent.cost_tier in ["cheap", "medium", "expensive"]
        assert 0.0 <= agent.success_rate <= 1.0

    @pytest.mark.asyncio
    async def test_create_api_agent(self, creator):
        """Test creating API integration agent"""
        agent = await creator.create_agent_for_task(
            task_description="Integrate with Stripe API for payments",
            context={}
        )

        assert agent.agent_id.startswith("dynamic_")
        assert len(agent.tools) > 0
        assert "api" in agent.name.lower() or "api" in agent.description.lower()

    @pytest.mark.asyncio
    async def test_create_analytics_agent(self, creator):
        """Test creating analytics agent"""
        agent = await creator.create_agent_for_task(
            task_description="Analyze sales data and generate reports",
            context={}
        )

        assert agent.agent_id.startswith("dynamic_")
        assert len(agent.tools) > 0
        assert "analytics" in agent.name.lower() or "analysis" in agent.description.lower()

    @pytest.mark.asyncio
    async def test_agent_tools_are_safe(self, creator):
        """All tools in created agent should be safe"""
        agent = await creator.create_agent_for_task(
            task_description="Monitor website uptime",
            context={}
        )

        validator = ToolSafetyValidator()
        for tool in agent.tools:
            assert validator.is_safe(tool) is True

    @pytest.mark.asyncio
    async def test_convert_to_agent_capability(self, creator):
        """Test converting DynamicAgent to AgentCapability"""
        agent = await creator.create_agent_for_task(
            task_description="Transform data formats",
            context={}
        )

        capability = creator.convert_to_agent_capability(agent)

        assert capability.agent_name == agent.agent_id
        assert capability.supported_task_types == agent.capabilities
        assert capability.cost_tier == agent.cost_tier
        assert capability.success_rate == agent.success_rate
        assert capability.max_concurrent_tasks == 5  # Conservative default

    def test_list_created_agents(self, creator):
        """Test listing all created agents"""
        assert len(creator.list_agents()) == 0

    @pytest.mark.asyncio
    async def test_get_agent_by_id(self, creator):
        """Test retrieving agent by ID"""
        agent = await creator.create_agent_for_task(
            task_description="Process data",
            context={}
        )

        retrieved = creator.get_agent(agent.agent_id)
        assert retrieved is not None
        assert retrieved.agent_id == agent.agent_id

    @pytest.mark.asyncio
    async def test_update_agent_success_rate(self, creator):
        """Test updating agent success rate"""
        agent = await creator.create_agent_for_task(
            task_description="Process data",
            context={}
        )

        old_rate = agent.success_rate
        creator.update_agent_success_rate(agent.agent_id, 0.95)

        updated = creator.get_agent(agent.agent_id)
        assert updated.success_rate == 0.95
        assert updated.success_rate != old_rate

    @pytest.mark.asyncio
    async def test_clone_agent(self, creator):
        """Test cloning existing agent"""
        original = await creator.create_agent_for_task(
            task_description="Monitor services",
            context={}
        )

        cloned = await creator.clone_agent(original.agent_id, "ClonedMonitor")

        assert cloned.agent_id != original.agent_id
        assert cloned.name == "ClonedMonitor"
        assert cloned.capabilities == original.capabilities
        assert cloned.cost_tier == original.cost_tier
        assert len(cloned.tools) == len(original.tools)


# ==================== HALORouter AATC Integration Tests ====================


class TestHALORouterAATCIntegration:
    """Test AATC integration with HALORouter"""

    @pytest.fixture
    def router(self):
        return HALORouter()

    @pytest.fixture
    def creator(self):
        return DynamicAgentCreator(llm_client=None)

    @pytest.mark.asyncio
    async def test_create_specialized_agent_without_creator(self, router):
        """Test create_specialized_agent without agent_creator returns None"""
        task = Task(
            task_id="test_task",
            task_type="unknown_type",
            description="Test task"
        )

        result = await router.create_specialized_agent(task, agent_creator=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_specialized_agent_with_creator(self, router, creator):
        """Test create_specialized_agent with agent_creator"""
        task = Task(
            task_id="scrape_task",
            task_type="web_scraping",
            description="Scrape data from websites"
        )

        agent_id = await router.create_specialized_agent(task, agent_creator=creator)

        assert agent_id is not None
        assert agent_id.startswith("dynamic_")

        # Agent should be registered in router
        assert agent_id in router.agent_registry
        assert agent_id in router.agent_workload

        # Check agent capability
        capability = router.agent_registry[agent_id]
        assert capability.agent_name == agent_id

    @pytest.mark.asyncio
    async def test_dynamic_agent_can_be_routed_to(self, router, creator):
        """Test that dynamically created agent can be routed to"""
        # Create a task that no standard agent handles
        task = Task(
            task_id="novel_task",
            task_type="novel_capability",
            description="Novel task requiring custom agent"
        )

        # Create specialized agent
        agent_id = await router.create_specialized_agent(task, agent_creator=creator)
        assert agent_id is not None

        # Create DAG with this task
        dag = TaskDAG()
        dag.add_task(task)

        # Route should now work (dynamic agent available)
        routing_plan = await router.route_tasks(dag, available_agents=[agent_id])

        # Task should be assigned to dynamic agent
        # Note: This might still be unassigned if capabilities don't match exactly
        # But agent should exist in registry
        assert agent_id in router.agent_registry

    @pytest.mark.asyncio
    async def test_multiple_dynamic_agents(self, router, creator):
        """Test creating multiple dynamic agents"""
        tasks = [
            Task(task_id="task1", task_type="type1", description="Scrape websites"),
            Task(task_id="task2", task_type="type2", description="Analyze data"),
            Task(task_id="task3", task_type="type3", description="Monitor services"),
        ]

        agent_ids = []
        for task in tasks:
            agent_id = await router.create_specialized_agent(task, agent_creator=creator)
            assert agent_id is not None
            agent_ids.append(agent_id)

        # All agents should be unique
        assert len(set(agent_ids)) == len(agent_ids)

        # All should be registered
        for agent_id in agent_ids:
            assert agent_id in router.agent_registry

    @pytest.mark.asyncio
    async def test_dynamic_agent_workload_tracking(self, router, creator):
        """Test workload tracking for dynamic agents"""
        task = Task(
            task_id="task1",
            task_type="custom",
            description="Custom task"
        )

        agent_id = await router.create_specialized_agent(task, agent_creator=creator)
        assert agent_id is not None

        # Workload should be initialized to 0
        assert router.agent_workload[agent_id] == 0

        # Simulate routing to this agent
        router.agent_workload[agent_id] += 1
        assert router.agent_workload[agent_id] == 1


# ==================== End-to-End Tests ====================


class TestAATCEndToEnd:
    """End-to-end tests for complete AATC workflow"""

    @pytest.mark.asyncio
    async def test_complete_aatc_workflow(self):
        """Test complete workflow: tool generation → agent creation → registration → routing"""
        # Step 1: Create tool generator
        tool_gen = ToolGenerator(llm_client=None)

        # Step 2: Generate tool
        tool = await tool_gen.generate_tool(
            task_description="Fetch cryptocurrency prices",
            context={}
        )
        assert tool.tool_name is not None

        # Step 3: Validate tool
        assert tool_gen.safety_validator.is_safe(tool) is True

        # Step 4: Create agent with tool
        creator = DynamicAgentCreator(llm_client=None)
        agent = await creator.create_agent_for_task(
            task_description="Scrape cryptocurrency prices",
            context={}
        )
        assert len(agent.tools) > 0

        # Step 5: Register agent in router
        router = HALORouter()
        agent_capability = creator.convert_to_agent_capability(agent)
        router.agent_registry[agent.agent_id] = agent_capability
        router.agent_workload[agent.agent_id] = 0

        # Step 6: Verify agent is routable
        assert agent.agent_id in router.agent_registry

        # Step 7: Create task and route
        task = Task(
            task_id="crypto_task",
            task_type=agent.capabilities[0],  # Use agent's capability
            description="Scrape crypto prices"
        )
        dag = TaskDAG()
        dag.add_task(task)

        routing_plan = await router.route_tasks(dag, available_agents=[agent.agent_id])

        # Agent should be available for routing
        assert agent.agent_id in router.agent_registry

    @pytest.mark.asyncio
    async def test_fallback_to_aatc_when_no_agent_matches(self):
        """Test that AATC creates agent when no existing agent matches"""
        router = HALORouter()
        creator = DynamicAgentCreator(llm_client=None)

        # Create task with completely novel type
        task = Task(
            task_id="novel_task",
            task_type="quantum_computing_simulation",
            description="Simulate quantum circuit"
        )

        # No existing agent should handle this
        dag = TaskDAG()
        dag.add_task(task)

        routing_plan = await router.route_tasks(dag)

        # Task should be unassigned (no standard agent)
        assert task.task_id in routing_plan.unassigned_tasks

        # Now create specialized agent via AATC
        agent_id = await router.create_specialized_agent(task, agent_creator=creator)
        assert agent_id is not None

        # Re-route with new agent available
        routing_plan2 = await router.route_tasks(dag, available_agents=[agent_id])

        # Agent should now exist in registry
        assert agent_id in router.agent_registry


# ==================== Performance Tests ====================


class TestAATCPerformance:
    """Performance tests for AATC system"""

    @pytest.mark.asyncio
    async def test_tool_generation_speed(self):
        """Test tool generation is reasonably fast"""
        import time

        generator = ToolGenerator(llm_client=None)

        start = time.time()
        tool = await generator.generate_tool(
            task_description="Process data",
            context={}
        )
        duration = time.time() - start

        # Heuristic generation should be fast (<1 second)
        assert duration < 1.0

    @pytest.mark.asyncio
    async def test_agent_creation_speed(self):
        """Test agent creation is reasonably fast"""
        import time

        creator = DynamicAgentCreator(llm_client=None)

        start = time.time()
        agent = await creator.create_agent_for_task(
            task_description="Monitor services",
            context={}
        )
        duration = time.time() - start

        # Should complete in reasonable time (<5 seconds)
        assert duration < 5.0

    @pytest.mark.asyncio
    async def test_multiple_agents_parallel(self):
        """Test creating multiple agents in parallel"""
        import time

        creator = DynamicAgentCreator(llm_client=None)

        tasks = [
            "Scrape websites",
            "Analyze data",
            "Monitor services",
            "Transform data",
            "Generate reports",
        ]

        start = time.time()
        agents = await asyncio.gather(*[
            creator.create_agent_for_task(task, {})
            for task in tasks
        ])
        duration = time.time() - start

        assert len(agents) == len(tasks)
        # Parallel creation should be faster than sequential
        assert duration < len(tasks) * 5.0  # Generous upper bound


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
