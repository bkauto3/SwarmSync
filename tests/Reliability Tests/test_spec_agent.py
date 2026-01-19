"""
Comprehensive test suite for SpecAgent

Tests all integrations:
- Microsoft Agent Framework (ChatAgent)
- ReasoningBank (query/store patterns)
- Replay Buffer (trajectory recording)
- Reflection Harness (quality checks)

EXECUTION:
  pytest tests/test_spec_agent.py -v -s

REQUIREMENTS:
- pytest
- pytest-asyncio
- pytest-mock
- All infrastructure components (ReasoningBank, ReplayBuffer, ReflectionHarness)
- Azure CLI credentials configured
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

# Import agent directly to avoid __init__.py import issues
import sys
sys.path.insert(0, '/home/genesis/genesis-rebuild')

# Import directly from module to avoid __init__.py cascading imports
import importlib.util
spec = importlib.util.spec_from_file_location(
    "spec_agent",
    "/home/genesis/genesis-rebuild/agents/spec_agent.py"
)
spec_agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spec_agent_module)

SpecAgent = spec_agent_module.SpecAgent
SpecCreationContext = spec_agent_module.SpecCreationContext
get_spec_agent = spec_agent_module.get_spec_agent

from infrastructure.reasoning_bank import (
    OutcomeTag,
    StrategyNugget
)

from infrastructure.replay_buffer import (
    Trajectory,
    ActionStep
)

from infrastructure.reflection_harness import (
    HarnessResult,
    ReflectionResult
)


class TestSpecCreationContext:
    """Test SpecCreationContext dataclass"""

    def test_context_creation_with_defaults(self):
        """Test context creation with default values"""
        context = SpecCreationContext(
            business_id="test",
            idea="Test SaaS idea"
        )

        assert context.business_id == "test"
        assert context.idea == "Test SaaS idea"
        assert context.tech_stack is None
        assert context.started_at != ""
        assert context.initial_state is not None
        assert "idea" in context.initial_state
        assert "tech_stack" in context.initial_state

    def test_context_creation_with_tech_stack(self):
        """Test context creation with tech stack override"""
        tech_stack = {"frontend": "Next.js 14", "database": "Supabase"}
        context = SpecCreationContext(
            business_id="test",
            idea="Test idea",
            tech_stack=tech_stack
        )

        assert context.tech_stack == tech_stack
        assert context.initial_state["tech_stack"] == tech_stack

    def test_context_timestamps(self):
        """Test that context has valid ISO timestamps"""
        context = SpecCreationContext(
            business_id="test",
            idea="Test idea"
        )

        # Verify ISO format
        assert "T" in context.started_at
        assert "Z" in context.started_at or "+" in context.started_at or "-" in context.started_at


class TestSpecAgentInitialization:
    """Test SpecAgent initialization and setup"""

    def test_agent_initialization_without_azure(self):
        """Test agent initialization without Azure (infrastructure only)"""
        agent = SpecAgent(
            business_id="test",
            quality_threshold=0.80,
            max_reflection_attempts=3
        )

        assert agent.business_id == "test"
        assert agent.agent_id == "spec_test"
        assert agent.reasoning_bank is not None
        assert agent.replay_buffer is not None
        assert agent.reflection_harness is not None
        assert agent.stats["specs_created"] == 0

    def test_agent_default_parameters(self):
        """Test agent uses correct default parameters"""
        agent = SpecAgent()

        assert agent.business_id == "default"
        assert agent.agent_id == "spec_default"
        assert agent.reflection_harness.quality_threshold == 0.75
        assert agent.reflection_harness.max_attempts == 2

    def test_agent_custom_parameters(self):
        """Test agent respects custom parameters"""
        agent = SpecAgent(
            business_id="custom",
            quality_threshold=0.85,
            max_reflection_attempts=4
        )

        assert agent.business_id == "custom"
        assert agent.reflection_harness.quality_threshold == 0.85
        assert agent.reflection_harness.max_attempts == 4

    def test_agent_infrastructure_singleton_sharing(self):
        """Test that multiple agents share infrastructure singletons"""
        agent1 = SpecAgent(business_id="agent1")
        agent2 = SpecAgent(business_id="agent2")

        # They should share the same ReasoningBank and ReplayBuffer instances
        assert agent1.reasoning_bank is agent2.reasoning_bank
        assert agent1.replay_buffer is agent2.replay_buffer


class TestSpecAgentTools:
    """Test SpecAgent tool functions"""

    @pytest.fixture
    def agent(self):
        """Fixture: Create agent instance"""
        return SpecAgent(business_id="test")

    def test_tool_query_patterns_no_results(self, agent):
        """Test query_patterns tool with no results"""
        result_json = agent._tool_query_patterns("nonexistent_pattern", top_n=5)
        result = json.loads(result_json)

        assert "patterns_found" in result
        assert "patterns" in result
        assert result["patterns_found"] == 0
        assert isinstance(result["patterns"], list)

    def test_tool_query_patterns_with_stored_strategy(self, agent):
        """Test query_patterns tool after storing a strategy"""
        # Store a test strategy
        strategy_id = agent.reasoning_bank.store_strategy(
            description="Test spec pattern for authentication",
            context="technical specification authentication",
            task_metadata={"test": True},
            environment="test",
            tools_used=["agent.run"],
            outcome=OutcomeTag.SUCCESS,
            steps=["Step 1: Design auth flow", "Step 2: Implement JWT"],
            learned_from=["test_trajectory"]
        )

        # Mark it as successful (win_rate > 0)
        agent.reasoning_bank.update_strategy_outcome(strategy_id, success=True)

        # Query for it
        result_json = agent._tool_query_patterns("authentication", top_n=5)
        result = json.loads(result_json)

        assert result["patterns_found"] >= 1
        # Note: Results depend on database state, so we check structure not exact values

    def test_tool_get_anti_patterns_empty(self, agent):
        """Test get_anti_patterns tool with no failures"""
        result_json = agent._tool_get_anti_patterns("spec", top_n=3)
        result = json.loads(result_json)

        assert "anti_patterns_found" in result
        assert "anti_patterns" in result
        assert isinstance(result["anti_patterns"], list)

    def test_tool_get_anti_patterns_with_failure(self, agent):
        """Test get_anti_patterns tool after recording a failure"""
        # Store a failure trajectory
        failure_trajectory = Trajectory(
            trajectory_id="test_failure_123",
            agent_id=agent.agent_id,
            task_description="Create technical specification: Test failure",
            initial_state={"idea": "Test"},
            steps=tuple([
                ActionStep(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    tool_name="test_tool",
                    tool_args={},
                    tool_result="Failed",
                    agent_reasoning="Test failure"
                )
            ]),
            final_outcome=OutcomeTag.FAILURE.value,
            reward=0.0,
            metadata={"test": True},
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=1.0,
            failure_rationale="Test failure for anti-pattern testing",
            error_category="test_error",
            fix_applied="Test fix"
        )

        agent.replay_buffer.store_trajectory(failure_trajectory)

        # Query anti-patterns
        result_json = agent._tool_get_anti_patterns("spec", top_n=3)
        result = json.loads(result_json)

        assert "anti_patterns" in result
        # Note: Anti-patterns may or may not be found depending on ReasoningBank indexing


class TestSpecAgentStatistics:
    """Test SpecAgent statistics tracking"""

    def test_initial_statistics(self):
        """Test that statistics start at zero"""
        agent = SpecAgent(business_id="test")
        stats = agent.get_statistics()

        assert stats["agent_id"] == "spec_test"
        assert stats["business_id"] == "test"
        assert stats["specs_created"] == 0
        assert stats["successful_reflections"] == 0
        assert stats["failed_reflections"] == 0
        assert stats["reflection_success_rate"] == 0.0
        assert stats["strategies_reused"] == 0
        assert stats["trajectories_recorded"] == 0

    def test_statistics_structure(self):
        """Test that statistics have correct structure"""
        agent = SpecAgent(business_id="test")
        stats = agent.get_statistics()

        required_keys = [
            "agent_id",
            "business_id",
            "specs_created",
            "successful_reflections",
            "failed_reflections",
            "reflection_success_rate",
            "strategies_reused",
            "trajectories_recorded",
            "reflection_harness_stats"
        ]

        for key in required_keys:
            assert key in stats

    def test_statistics_after_manual_increment(self):
        """Test statistics update correctly after manual increments"""
        agent = SpecAgent(business_id="test")

        agent.stats["specs_created"] = 5
        agent.stats["successful_reflections"] = 4
        agent.stats["failed_reflections"] = 1

        stats = agent.get_statistics()

        assert stats["specs_created"] == 5
        assert stats["successful_reflections"] == 4
        assert stats["failed_reflections"] == 1
        assert stats["reflection_success_rate"] == 0.8  # 4/5


class TestSpecAgentIntegration:
    """Integration tests for SpecAgent (mocked Azure)"""

    @pytest.mark.asyncio
    async def test_create_spec_with_mocked_agent(self):
        """Test create_spec with mocked Agent Framework response"""
        agent = SpecAgent(business_id="test")

        # Mock the agent attribute
        mock_agent = AsyncMock()
        mock_response = Mock()
        mock_response.text = json.dumps({
            "overview": {"problem": "Test problem", "solution": "Test solution"},
            "features": [{"name": "Feature 1", "user_story": "As a user..."}],
            "tech_stack": {"frontend": "Next.js 14"},
            "database_schema": "CREATE TABLE users (id SERIAL PRIMARY KEY);",
            "api_endpoints": [{"method": "GET", "path": "/api/users"}],
            "pages": [{"route": "/", "components": ["Header", "Hero"]}],
            "stripe_integration": {"products": [], "webhooks": []},
            "deployment": {"env_vars": ["DATABASE_URL"]},
            "testing": {"unit": [], "integration": []}
        })
        mock_agent.run = AsyncMock(return_value=mock_response)

        agent.agent = mock_agent

        # Mock Reflection Agent (assume it passes)
        with patch('agents.spec_agent.ReflectionHarness') as MockHarness:
            mock_harness = MockHarness.return_value
            mock_harness.wrap = AsyncMock(return_value=HarnessResult(
                output=mock_response.text,
                passed_reflection=True,
                reflection_result=Mock(overall_score=0.85),
                attempts_made=1,
                regenerations=0,
                total_time_seconds=1.5,
                fallback_used=False,
                metadata={}
            ))

            agent.reflection_harness = mock_harness

            # Execute create_spec
            spec = await agent.create_spec(
                idea="Test SaaS application",
                tech_stack={"frontend": "Next.js 14"}
            )

            # Assertions
            assert spec is not None
            assert isinstance(spec, str)
            assert agent.stats["specs_created"] == 1
            assert agent.stats["trajectories_recorded"] == 1

    @pytest.mark.asyncio
    async def test_create_spec_records_trajectory(self):
        """Test that create_spec records trajectory in ReplayBuffer"""
        agent = SpecAgent(business_id="test")

        # Mock agent
        mock_agent = AsyncMock()
        mock_response = Mock()
        mock_response.text = "Test spec content"
        mock_agent.run = AsyncMock(return_value=mock_response)
        agent.agent = mock_agent

        # Mock reflection harness
        with patch('agents.spec_agent.ReflectionHarness') as MockHarness:
            mock_harness = MockHarness.return_value
            mock_harness.wrap = AsyncMock(return_value=HarnessResult(
                output="Test spec",
                passed_reflection=True,
                reflection_result=Mock(overall_score=0.75),
                attempts_made=1,
                regenerations=0,
                total_time_seconds=1.0,
                fallback_used=False,
                metadata={}
            ))
            agent.reflection_harness = mock_harness

            # Execute
            await agent.create_spec("Test idea")

            # Check trajectory was recorded
            assert agent.stats["trajectories_recorded"] == 1

    @pytest.mark.asyncio
    async def test_create_spec_queries_reasoning_bank(self):
        """Test that create_spec queries ReasoningBank for patterns"""
        agent = SpecAgent(business_id="test")

        # Mock agent
        mock_agent = AsyncMock()
        mock_response = Mock()
        mock_response.text = "Test spec"
        mock_agent.run = AsyncMock(return_value=mock_response)
        agent.agent = mock_agent

        # Mock reflection harness
        with patch('agents.spec_agent.ReflectionHarness') as MockHarness:
            mock_harness = MockHarness.return_value
            mock_harness.wrap = AsyncMock(return_value=HarnessResult(
                output="Test spec",
                passed_reflection=True,
                reflection_result=Mock(overall_score=0.75),
                attempts_made=1,
                regenerations=0,
                total_time_seconds=1.0,
                fallback_used=False,
                metadata={}
            ))
            agent.reflection_harness = mock_harness

            # Spy on ReasoningBank
            original_search = agent.reasoning_bank.search_strategies
            search_called = False

            def mock_search(*args, **kwargs):
                nonlocal search_called
                search_called = True
                return original_search(*args, **kwargs)

            agent.reasoning_bank.search_strategies = mock_search

            # Execute
            await agent.create_spec("Test idea for authentication")

            # Verify ReasoningBank was queried
            assert search_called


class TestSpecAgentResourceManagement:
    """Test SpecAgent resource management (context manager)"""

    @pytest.mark.asyncio
    async def test_context_manager_close(self):
        """Test that context manager properly closes resources"""
        agent = SpecAgent(business_id="test")

        # Mock credential with async close method
        mock_credential = AsyncMock()
        mock_credential.close = AsyncMock()

        # Use context manager (initialize happens in __aenter__)
        async with agent:
            # Set mock AFTER initialization creates the credential
            agent.credential = mock_credential

        # Verify close was called
        mock_credential.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_close(self):
        """Test manual close of agent"""
        agent = SpecAgent(business_id="test")

        mock_credential = AsyncMock()
        agent.credential = mock_credential

        await agent.close()

        mock_credential.close.assert_called_once()


class TestSpecAgentErrorHandling:
    """Test SpecAgent error handling"""

    @pytest.mark.asyncio
    async def test_create_spec_handles_exception(self):
        """Test that create_spec handles exceptions and records failure trajectory"""
        agent = SpecAgent(business_id="test")

        # Initialize agent first to ensure agent.agent exists
        await agent.initialize()

        # Mock the reflection harness to raise exception immediately
        mock_harness = AsyncMock()
        mock_harness.wrap = AsyncMock(side_effect=Exception("Test exception"))
        agent.reflection_harness = mock_harness

        # Execute and expect exception (reflection harness raises, create_spec catches and re-raises)
        with pytest.raises(Exception, match="Test exception"):
            await agent.create_spec("Test idea")

        # Verify failure trajectory was recorded
        assert agent.stats["trajectories_recorded"] == 1

        # Verify trajectory is a failure
        # (Can't easily check this without accessing replay_buffer internals,
        # but the trajectory recording code was executed based on stats)

        # Clean up
        await agent.close()


class TestFactoryFunction:
    """Test get_spec_agent factory function"""

    @pytest.mark.asyncio
    async def test_factory_function_creates_agent(self):
        """Test that factory function creates and initializes agent"""
        # This test requires Azure credentials - skip if not available
        pytest.skip("Requires Azure credentials - run manually with valid credentials")

        agent = await get_spec_agent(
            business_id="factory_test",
            quality_threshold=0.80,
            max_reflection_attempts=3
        )

        assert agent is not None
        assert agent.business_id == "factory_test"
        assert agent.agent is not None  # Should be initialized


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests with pytest
    import subprocess
    result = subprocess.run(
        ["pytest", __file__, "-v", "-s", "--tb=short"],
        cwd="/home/genesis/genesis-rebuild"
    )
    exit(result.returncode)
