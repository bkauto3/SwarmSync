"""
Integration tests for Darwin Orchestration Bridge
Tests full pipeline: User → HTDAG → HALO → AOP → Darwin → Result

Author: Alex (Testing & Full-Stack Integration Specialist)
Date: October 19, 2025
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from infrastructure.darwin_orchestration_bridge import (
    DarwinOrchestrationBridge,
    EvolutionTaskType,
    EvolutionRequest,
    EvolutionResult,
    get_darwin_bridge,
    evolve_agent_via_orchestration
)
from infrastructure.feature_flags import get_feature_flag_manager
from infrastructure.task_dag import TaskDAG, Task, TaskStatus
from infrastructure.halo_router import RoutingPlan
from infrastructure.aop_validator import ValidationResult
from agents.darwin_agent import EvolutionAttempt, ImprovementType


@pytest.fixture
def mock_openai_patch(monkeypatch):
    """Mock OpenAI API calls"""
    # Set API key environment variable
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    with patch('openai.AsyncOpenAI'):
        yield


@pytest.fixture
def enable_darwin_flag(monkeypatch):
    """Enable Darwin integration feature flag BEFORE bridge creation"""
    # Patch is_feature_enabled to return True BEFORE bridge is created
    monkeypatch.setattr(
        'infrastructure.darwin_orchestration_bridge.is_feature_enabled',
        lambda flag_name: True if flag_name == "darwin_integration_enabled" else False
    )
    yield
    # No cleanup needed - monkeypatch auto-reverts


class TestFullEvolutionPipeline:
    """Test complete evolution pipeline end-to-end"""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocked_components(self, enable_darwin_flag, mock_openai_patch):
        """Test complete evolution pipeline with mocked orchestration"""
        bridge = DarwinOrchestrationBridge()

        # Mock HTDAG decomposition
        mock_dag = TaskDAG()
        mock_dag.add_task(Task(
            task_id="evo_task_1",
            task_type="evolution",
            description="Evolve agent",
            agent_assigned="darwin_agent",
            metadata={"evolution_request_id": "test_req"}
        ))

        # Mock HALO routing
        mock_routing_plan = RoutingPlan(
            assignments={"evo_task_1": "darwin_agent"}
        )

        # Mock AOP validation
        mock_validation = ValidationResult(
            passed=True,
            solvability_passed=True,
            completeness_passed=True,
            redundancy_passed=True,
            issues=[]
        )

        # Mock Darwin evolution attempt
        mock_attempt = EvolutionAttempt(
            attempt_id="test_attempt",
            parent_agent="marketing_agent",
            parent_version="v1",
            improvement_type="optimization",
            problem_diagnosis="Test improvement",
            proposed_changes="# Improved code here",
            validation_results={"passed": True},
            accepted=True,
            metrics_before={"overall_score": 0.65},
            metrics_after={"overall_score": 0.75},
            improvement_delta={"overall_score": 0.10},
            timestamp="2025-10-19T12:00:00Z",
            generation=1
        )

        with patch.object(bridge, '_decompose_evolution_task', return_value=mock_dag):
            with patch.object(bridge, '_route_to_darwin', return_value=mock_routing_plan):
                with patch.object(bridge.aop, 'validate_routing_plan', return_value=mock_validation):
                    with patch.object(bridge, '_execute_single_evolution_attempt', return_value=mock_attempt):
                        result = await bridge.evolve_agent(
                            agent_name="marketing_agent",
                            evolution_type=EvolutionTaskType.IMPROVE_AGENT,
                            context={"current_score": 0.65, "target_score": 0.80}
                        )

        # Validate result
        assert isinstance(result, EvolutionResult)
        assert result.success is True
        assert result.agent_name == "marketing_agent"
        assert result.metrics_before == {"overall_score": 0.65}
        assert result.metrics_after == {"overall_score": 0.75}
        assert result.improvement_delta == {"overall_score": 0.10}
        assert result.new_version == "v2"

    @pytest.mark.asyncio
    async def test_full_pipeline_aop_validation_failure(self, enable_darwin_flag):
        """Test pipeline when AOP validation fails"""
        bridge = DarwinOrchestrationBridge()

        mock_dag = TaskDAG()
        mock_dag.add_task(Task(
            task_id="evo_task_1",
            task_type="evolution",
            description="Evolve agent",
            agent_assigned="darwin_agent"
        ))

        mock_routing_plan = RoutingPlan(
            assignments={"evo_task_1": "darwin_agent"}
        )

        # AOP validation FAILS
        mock_validation = ValidationResult(
            passed=False,
            solvability_passed=False,
            completeness_passed=True,
            redundancy_passed=True,
            issues=["Task not solvable by assigned agent"]
        )

        with patch.object(bridge, '_decompose_evolution_task', return_value=mock_dag):
            with patch.object(bridge, '_route_to_darwin', return_value=mock_routing_plan):
                with patch.object(bridge.aop, 'validate_routing_plan', return_value=mock_validation):
                    result = await bridge.evolve_agent(
                        agent_name="marketing_agent",
                        evolution_type=EvolutionTaskType.IMPROVE_AGENT
                    )

        # Should fail gracefully
        assert result.success is False
        assert "Validation failed" in result.error_message
        assert "not solvable" in result.error_message


class TestFeatureFlagIntegration:
    """Test Darwin integration feature flag behavior"""

    @pytest.mark.asyncio
    async def test_feature_flag_disabled(self):
        """Test evolution fails gracefully when feature flag disabled"""
        manager = get_feature_flag_manager()
        manager.set_flag("darwin_integration_enabled", False)

        bridge = DarwinOrchestrationBridge()

        result = await bridge.evolve_agent(
            agent_name="marketing_agent",
            evolution_type=EvolutionTaskType.IMPROVE_AGENT
        )

        assert result.success is False
        assert result.error_message == "Darwin integration disabled"
        assert result.request_id == "disabled"

    @pytest.mark.asyncio
    async def test_feature_flag_enabled(self, enable_darwin_flag):
        """Test evolution proceeds when feature flag enabled"""
        bridge = DarwinOrchestrationBridge()

        assert bridge.enabled is True

        # Should proceed (may fail later, but should NOT fail at flag check)
        with patch.object(bridge, '_decompose_evolution_task', side_effect=Exception("Expected")):
            result = await bridge.evolve_agent(
                agent_name="marketing_agent",
                evolution_type=EvolutionTaskType.IMPROVE_AGENT
            )

            # Should NOT be "Darwin integration disabled"
            assert result.error_message != "Darwin integration disabled"


class TestEvolutionTypes:
    """Test all evolution type variations"""

    @pytest.mark.asyncio
    async def test_evolution_type_improve_agent(self, enable_darwin_flag, mock_openai_patch):
        """Test IMPROVE_AGENT evolution type"""
        bridge = DarwinOrchestrationBridge()

        mock_attempt = EvolutionAttempt(
            attempt_id="test",
            parent_agent="marketing_agent",
            parent_version="v1",
            improvement_type="optimization",
            problem_diagnosis="test",
            proposed_changes="# code",
            validation_results={},
            accepted=True,
            metrics_before={},
            metrics_after={},
            improvement_delta={},
            timestamp="2025-10-19T12:00:00Z",
            generation=1
        )

        with patch.object(bridge, '_decompose_evolution_task', new_callable=AsyncMock):
            with patch.object(bridge, '_route_to_darwin', new_callable=AsyncMock):
                with patch.object(bridge.aop, 'validate_routing_plan', return_value=ValidationResult(
                    passed=True, solvability_passed=True, completeness_passed=True, redundancy_passed=True, issues=[]
                )):
                    with patch.object(bridge, '_execute_single_evolution_attempt', return_value=mock_attempt):
                        result = await bridge.evolve_agent(
                            agent_name="marketing_agent",
                            evolution_type=EvolutionTaskType.IMPROVE_AGENT
                        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_evolution_type_fix_bug(self, enable_darwin_flag):
        """Test FIX_BUG evolution type"""
        bridge = DarwinOrchestrationBridge()

        with patch.object(bridge, '_execute_darwin_evolution') as mock_execute:
            mock_execute.return_value = EvolutionResult(
                request_id="test",
                agent_name="marketing_agent",
                success=True,
                metrics_before={},
                metrics_after={},
                improvement_delta={}
            )

            with patch.object(bridge, '_decompose_evolution_task', new_callable=AsyncMock):
                with patch.object(bridge, '_route_to_darwin', new_callable=AsyncMock):
                    with patch.object(bridge.aop, 'validate_routing_plan', return_value=ValidationResult(
                        passed=True, solvability_passed=True, completeness_passed=True, redundancy_passed=True, issues=[]
                    )):
                        result = await bridge.evolve_agent(
                            agent_name="marketing_agent",
                            evolution_type=EvolutionTaskType.FIX_BUG
                        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_evolution_type_add_feature(self, enable_darwin_flag):
        """Test ADD_FEATURE evolution type"""
        bridge = DarwinOrchestrationBridge()

        with patch.object(bridge, '_execute_darwin_evolution') as mock_execute:
            mock_execute.return_value = EvolutionResult(
                request_id="test",
                agent_name="marketing_agent",
                success=True,
                metrics_before={},
                metrics_after={},
                improvement_delta={}
            )

            with patch.object(bridge, '_decompose_evolution_task', new_callable=AsyncMock):
                with patch.object(bridge, '_route_to_darwin', new_callable=AsyncMock):
                    with patch.object(bridge.aop, 'validate_routing_plan', return_value=ValidationResult(
                        passed=True, solvability_passed=True, completeness_passed=True, redundancy_passed=True, issues=[]
                    )):
                        result = await bridge.evolve_agent(
                            agent_name="marketing_agent",
                            evolution_type=EvolutionTaskType.ADD_FEATURE
                        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_evolution_type_optimize_performance(self, enable_darwin_flag):
        """Test OPTIMIZE_PERFORMANCE evolution type"""
        bridge = DarwinOrchestrationBridge()

        with patch.object(bridge, '_execute_darwin_evolution') as mock_execute:
            mock_execute.return_value = EvolutionResult(
                request_id="test",
                agent_name="marketing_agent",
                success=True,
                metrics_before={},
                metrics_after={},
                improvement_delta={}
            )

            with patch.object(bridge, '_decompose_evolution_task', new_callable=AsyncMock):
                with patch.object(bridge, '_route_to_darwin', new_callable=AsyncMock):
                    with patch.object(bridge.aop, 'validate_routing_plan', return_value=ValidationResult(
                        passed=True, solvability_passed=True, completeness_passed=True, redundancy_passed=True, issues=[]
                    )):
                        result = await bridge.evolve_agent(
                            agent_name="marketing_agent",
                            evolution_type=EvolutionTaskType.OPTIMIZE_PERFORMANCE
                        )

        assert result.success is True


class TestDarwinAgentCaching:
    """Test Darwin agent per-agent caching"""

    @pytest.mark.asyncio
    async def test_darwin_agent_cached_per_agent(self, enable_darwin_flag, mock_openai_patch):
        """Test Darwin agents are cached per agent_name"""
        bridge = DarwinOrchestrationBridge()

        with patch('infrastructure.darwin_orchestration_bridge.DarwinAgent') as MockDarwin:
            mock_darwin_instance = Mock()
            MockDarwin.return_value = mock_darwin_instance

            # Get Darwin agent twice for same agent
            darwin1 = await bridge._get_darwin_agent("marketing_agent")
            darwin2 = await bridge._get_darwin_agent("marketing_agent")

            # Should be same instance (cached)
            assert darwin1 is darwin2
            # Should only create once
            assert MockDarwin.call_count == 1

    @pytest.mark.asyncio
    async def test_darwin_agent_separate_per_agent(self, enable_darwin_flag, mock_openai_patch):
        """Test different agents get separate Darwin instances"""
        bridge = DarwinOrchestrationBridge()

        with patch('infrastructure.darwin_orchestration_bridge.DarwinAgent') as MockDarwin:
            MockDarwin.side_effect = [Mock(), Mock()]

            darwin_marketing = await bridge._get_darwin_agent("marketing_agent")
            darwin_builder = await bridge._get_darwin_agent("builder_agent")

            # Should be different instances
            assert darwin_marketing is not darwin_builder
            # Should create twice
            assert MockDarwin.call_count == 2


class TestHTDAGIntegration:
    """Test HTDAG decomposition integration"""

    @pytest.mark.asyncio
    async def test_htdag_adds_darwin_metadata(self, enable_darwin_flag):
        """Test HTDAG decomposition adds Darwin metadata to tasks"""
        bridge = DarwinOrchestrationBridge()

        request = EvolutionRequest(
            request_id="test_req_123",
            agent_name="marketing_agent",
            evolution_type=EvolutionTaskType.IMPROVE_AGENT,
            context={"test": "data"}
        )

        # Mock HTDAG to return a simple DAG
        mock_dag = TaskDAG()
        mock_dag.add_task(Task(
            task_id="task_1",
            task_type="test",
            description="Test task",
            agent_assigned="test_agent",
            metadata={}
        ))

        with patch.object(bridge.htdag, 'decompose_task', return_value=mock_dag):
            dag = await bridge._decompose_evolution_task(request)

        # Verify metadata was added
        for task_id in dag.get_all_task_ids():
            task = dag.tasks[task_id]
            assert "evolution_request_id" in task.metadata
            assert task.metadata["evolution_request_id"] == "test_req_123"
            assert task.metadata["target_agent"] == "marketing_agent"
            assert task.metadata["evolution_type"] == "improve_agent"


class TestHALORouting:
    """Test HALO routing integration"""

    @pytest.mark.asyncio
    async def test_halo_routes_to_darwin(self, enable_darwin_flag):
        """Test HALO correctly routes evolution tasks to darwin_agent"""
        bridge = DarwinOrchestrationBridge()

        dag = TaskDAG()
        dag.add_task(Task(
            task_id="evo_task",
            task_type="evolution",
            description="Evolve marketing agent",
            agent_assigned="",
            metadata={"evolution_type": "improve_agent"}
        ))

        # Mock HALO routing
        mock_routing = RoutingPlan(
            assignments={"evo_task": "darwin_agent"}
        )

        with patch.object(bridge.halo, 'route_tasks', return_value=mock_routing):
            routing_plan = await bridge._route_to_darwin(dag)

        # Verify darwin_agent assigned
        assert "darwin_agent" in routing_plan.assignments.values()


class TestErrorHandling:
    """Test error handling throughout pipeline"""

    @pytest.mark.asyncio
    async def test_error_handling_invalid_agent_name(self, enable_darwin_flag):
        """Test error handling for invalid agent name"""
        bridge = DarwinOrchestrationBridge()

        result = await bridge.evolve_agent(
            agent_name="nonexistent_agent",
            evolution_type=EvolutionTaskType.IMPROVE_AGENT
        )

        assert result.success is False
        assert "Invalid agent name" in result.error_message

    @pytest.mark.asyncio
    async def test_error_handling_htdag_failure(self, enable_darwin_flag):
        """Test error handling when HTDAG fails"""
        bridge = DarwinOrchestrationBridge()

        with patch.object(bridge, '_decompose_evolution_task', side_effect=Exception("HTDAG failed")):
            result = await bridge.evolve_agent(
                agent_name="marketing_agent",
                evolution_type=EvolutionTaskType.IMPROVE_AGENT
            )

        assert result.success is False
        assert "HTDAG failed" in result.error_message

    @pytest.mark.asyncio
    async def test_error_handling_darwin_execution_failure(self, enable_darwin_flag):
        """Test error handling when Darwin execution fails"""
        bridge = DarwinOrchestrationBridge()

        mock_dag = TaskDAG()
        mock_routing = RoutingPlan(assignments={})
        mock_validation = ValidationResult(
            passed=True, solvability_passed=True, completeness_passed=True, redundancy_passed=True, issues=[]
        )

        with patch.object(bridge, '_decompose_evolution_task', return_value=mock_dag):
            with patch.object(bridge, '_route_to_darwin', return_value=mock_routing):
                with patch.object(bridge.aop, 'validate_routing_plan', return_value=mock_validation):
                    with patch.object(bridge, '_execute_darwin_evolution', side_effect=Exception("Darwin failed")):
                        result = await bridge.evolve_agent(
                            agent_name="marketing_agent",
                            evolution_type=EvolutionTaskType.IMPROVE_AGENT
                        )

        assert result.success is False
        assert "Darwin failed" in result.error_message


class TestConvenienceFunctions:
    """Test convenience wrapper functions"""

    def test_get_darwin_bridge(self):
        """Test get_darwin_bridge() creates bridge"""
        bridge = get_darwin_bridge()

        assert isinstance(bridge, DarwinOrchestrationBridge)
        assert bridge.htdag is not None
        assert bridge.halo is not None
        assert bridge.aop is not None

    @pytest.mark.asyncio
    async def test_evolve_agent_via_orchestration(self, enable_darwin_flag):
        """Test evolve_agent_via_orchestration() wrapper"""
        with patch('infrastructure.darwin_orchestration_bridge.get_darwin_bridge') as mock_get:
            mock_bridge = Mock()
            mock_bridge.evolve_agent = AsyncMock(return_value=EvolutionResult(
                request_id="test",
                agent_name="marketing_agent",
                success=True,
                metrics_before={},
                metrics_after={},
                improvement_delta={}
            ))
            mock_get.return_value = mock_bridge

            result = await evolve_agent_via_orchestration(
                agent_name="marketing_agent",
                evolution_type="improve_agent",
                context={"test": "data"}
            )

            assert result.success is True
            mock_bridge.evolve_agent.assert_called_once()
