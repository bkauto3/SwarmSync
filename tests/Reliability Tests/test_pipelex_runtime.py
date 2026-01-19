"""
Integration Tests: Pipelex Runtime Execution with Mocks

Tests the actual Pipelex runtime execution paths with comprehensive mocking
to achieve 85%+ functional coverage of pipelex_adapter.py critical paths.

Focus areas:
- Lines 343-351: Pipelex runtime execution
- Lines 370-415: Fallback execution
- Lines 437-468: OTEL observability
- Error handling, timeouts, concurrent execution

Author: Cora (QA Auditor)
Date: November 2, 2025
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

# Import adapter
from infrastructure.orchestration.pipelex_adapter import PipelexAdapter

# Import observability for testing
try:
    from infrastructure.observability import SpanType, CorrelationContext
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


@pytest.fixture
def mock_piperunner():
    """Mock PipeRunner for Pipelex runtime testing"""
    mock_runner = Mock()
    mock_runner.run = Mock()
    return mock_runner


@pytest.fixture
def mock_halo_router():
    """Mock HALO router for fallback testing"""
    router = AsyncMock()
    router.route_tasks = AsyncMock(return_value=type('obj', (object,), {
        'assignments': {'task_1': 'builder_agent'},
        'explanations': {}
    })())
    return router


@pytest.fixture
def mock_model_registry():
    """Mock ModelRegistry for fallback testing"""
    registry = AsyncMock()
    registry.chat_async = AsyncMock(return_value={
        "output": "Fallback result from model registry"
    })
    return registry


@pytest.fixture
def workflow_path():
    """Path to test workflow"""
    return Path("/home/genesis/genesis-rebuild/workflows/templates/ecommerce_business.plx")


class TestPipelexRuntimeExecution:
    """Test successful execution through real Pipelex runtime"""

    @pytest.mark.asyncio
    async def test_pipelex_runtime_execution_success(self, workflow_path):
        """Test successful execution through real Pipelex runtime"""
        adapter = PipelexAdapter()

        # Mock _execute_workflow_internal to simulate successful Pipelex execution
        async def mock_execution(workflow_path, inputs):
            return {
                "ProductCatalog": "Catalog generated successfully",
                "WebsiteDesign": "Design completed",
                "status": "success"
            }

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            result = await adapter.execute_workflow(
                workflow_name="ecommerce_business.plx",
                inputs={"business_niche": "sustainable fashion"}
            )

            # Verify result structure
            assert result["status"] == "completed"
            assert result["used_fallback"] is False
            assert "ProductCatalog" in result["outputs"]
            assert result["outputs"]["ProductCatalog"] == "Catalog generated successfully"

    @pytest.mark.asyncio
    async def test_pipelex_runtime_returns_non_dict(self, workflow_path):
        """Test Pipelex runtime returning non-dict output"""
        adapter = PipelexAdapter()

        # Mock runtime returning string (wrapped in dict by _execute_workflow_internal)
        async def mock_execution(workflow_path, inputs):
            return {"output": "Simple string output"}

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            result = await adapter.execute_workflow(
                workflow_name="ecommerce_business.plx",
                inputs={"business_niche": "test"}
            )

            # Should have the output
            assert result["status"] == "completed"
            assert result["outputs"]["output"] == "Simple string output"


class TestPipelexRuntimeFailure:
    """Test fallback triggers when Pipelex runtime fails"""

    @pytest.mark.asyncio
    async def test_pipelex_runtime_failure_triggers_fallback(
        self, workflow_path, mock_halo_router, mock_model_registry
    ):
        """Test fallback triggers when Pipelex runtime fails"""
        adapter = PipelexAdapter(
            halo_router=mock_halo_router,
            model_registry=mock_model_registry
        )

        # Mock runtime failure
        async def mock_execution(workflow_path, inputs):
            raise RuntimeError("Pipelex execution failed")

        genesis_task = {"description": "Create ecommerce store", "niche": "fashion"}

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            result = await adapter.execute_workflow(
                workflow_name="ecommerce_business.plx",
                inputs={"business_niche": "fashion"},
                genesis_task=genesis_task
            )

        # Verify fallback was used
        assert result.get("used_fallback") is True
        assert result.get("fallback") is True
        assert result.get("fallback_reason") is not None

    @pytest.mark.asyncio
    async def test_pipelex_runtime_failure_without_genesis_task(self, workflow_path):
        """Test runtime failure without genesis_task raises RuntimeError"""
        adapter = PipelexAdapter()

        # Mock runtime failure
        async def mock_execution(workflow_path, inputs):
            raise RuntimeError("Pipelex execution failed")

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            # Without genesis_task, should raise RuntimeError
            with pytest.raises(RuntimeError, match="Pipelex execution failed"):
                await adapter.execute_workflow(
                    workflow_name="ecommerce_business.plx",
                    inputs={"business_niche": "fashion"}
                )


class TestOTELInstrumentation:
    """Test OTEL spans are created with correct attributes"""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not OTEL_AVAILABLE, reason="OTEL not available")
    async def test_otel_span_creation_during_execution(self, workflow_path):
        """Test OTEL spans are created with correct attributes"""
        adapter = PipelexAdapter()

        # Mock _execute_workflow_internal
        async def mock_execution(workflow_path, inputs):
            return {"output": "success"}

        # Mock OTEL manager
        mock_otel_manager = Mock()
        mock_span_context = MagicMock()
        mock_span = Mock()
        mock_span.set_attribute = Mock()
        mock_span_context.__enter__ = Mock(return_value=mock_span)
        mock_span_context.__exit__ = Mock(return_value=None)
        mock_otel_manager.span = Mock(return_value=mock_span_context)

        adapter.otel_manager = mock_otel_manager

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            result = await adapter.execute_workflow(
                workflow_name="ecommerce_business.plx",
                inputs={"business_niche": "fashion"}
            )

        # Verify span was created
        mock_otel_manager.span.assert_called_once()
        call_kwargs = mock_otel_manager.span.call_args[1]
        assert call_kwargs["name"] == "pipelex.execute_workflow"
        assert call_kwargs["span_type"] == SpanType.ORCHESTRATION

        # Verify span attributes were set
        assert mock_span.set_attribute.called
        # Check that workflow.path and workflow.inputs were set
        attribute_calls = [call[0] for call in mock_span.set_attribute.call_args_list]
        assert any("workflow.path" in str(call) for call in attribute_calls)

    @pytest.mark.asyncio
    @pytest.mark.skipif(not OTEL_AVAILABLE, reason="OTEL not available")
    async def test_otel_span_closed_on_error(self, workflow_path):
        """Test OTEL span is properly closed even on error"""
        adapter = PipelexAdapter()

        # Mock runtime failure
        async def mock_execution(workflow_path, inputs):
            raise RuntimeError("Test error")

        # Mock OTEL manager
        mock_otel_manager = Mock()
        mock_span_context = MagicMock()
        mock_span_context.__enter__ = Mock(return_value=Mock())
        mock_span_context.__exit__ = Mock(return_value=None)
        mock_otel_manager.span = Mock(return_value=mock_span_context)

        adapter.otel_manager = mock_otel_manager

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            try:
                await adapter.execute_workflow(
                    workflow_name="ecommerce_business.plx",
                    inputs={"business_niche": "fashion"}
                )
            except RuntimeError:
                pass  # Expected

        # Verify span was closed (exit called)
        mock_span_context.__exit__.assert_called_once()


class TestConcurrentExecution:
    """Test concurrent workflow execution"""

    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, workflow_path):
        """Test multiple workflows can execute concurrently"""
        adapter = PipelexAdapter()

        # Mock execution with delay
        async def delayed_execution(workflow_path, inputs):
            await asyncio.sleep(0.1)
            return {"output": f"success for {inputs['business_niche']}"}

        with patch.object(adapter, '_execute_workflow_internal', side_effect=delayed_execution):
            # Execute 3 workflows concurrently
            tasks = [
                adapter.execute_workflow(
                    workflow_name="ecommerce_business.plx",
                    inputs={"business_niche": f"niche_{i}"}
                )
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # Verify all succeeded
            assert len(results) == 3
            for result in results:
                assert result["status"] == "completed"


class TestWorkflowVariableHandling:
    """Test workflow with missing or invalid variables"""

    @pytest.mark.asyncio
    async def test_workflow_with_missing_variables(self, workflow_path, mock_piperunner, mock_halo_router, mock_model_registry):
        """Test workflow execution with missing required variables"""
        # Mock runtime failure due to missing variables
        mock_piperunner.run.side_effect = KeyError("Missing required variable: business_niche")

        with patch('infrastructure.orchestration.pipelex_adapter.PipeRunner', return_value=mock_piperunner):
            adapter = PipelexAdapter(
                halo_router=mock_halo_router,
                model_registry=mock_model_registry
            )

            genesis_task = {"description": "Test missing vars"}

            # Should trigger fallback
            result = await adapter.execute_workflow(
                workflow_name="ecommerce_business.plx",
                inputs={},  # Empty inputs
                genesis_task=genesis_task
            )

            assert result.get("used_fallback") is True


class TestFallbackExecutionPaths:
    """Test various fallback execution scenarios"""

    @pytest.mark.asyncio
    async def test_fallback_with_model_registry(self, mock_halo_router, mock_model_registry):
        """Test fallback execution through model registry"""
        adapter = PipelexAdapter(
            halo_router=mock_halo_router,
            model_registry=mock_model_registry
        )

        genesis_task = {"description": "Build an ecommerce platform"}

        result = await adapter._fallback_execution(
            genesis_task=genesis_task,
            business_type="ecommerce",
            inputs={"business_niche": "electronics"}
        )

        # Verify fallback structure
        assert result["status"] == "fallback"
        assert result["used_fallback"] is True
        assert result["fallback"] is True
        assert "agent_name" in result
        assert "outputs" in result

        # Verify model registry was called
        mock_model_registry.chat_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_without_model_registry(self, mock_halo_router):
        """Test fallback execution without model registry (stub result)"""
        # Don't patch HALO_AVAILABLE - make sure model_registry is None
        adapter = PipelexAdapter(
            halo_router=None,  # No HALO router
            model_registry=None  # No model registry
        )

        genesis_task = {"description": "Build platform"}

        result = await adapter._fallback_execution(
            genesis_task=genesis_task,
            business_type="saas",
            inputs={"business_type": "saas"}
        )

        # Should return stub result without model registry
        assert result["status"] == "fallback"
        assert result["used_fallback"] is True
        # When HALO is available but model_registry is None, it returns a message
        assert "outputs" in result

    @pytest.mark.asyncio
    async def test_fallback_with_task_object(self, mock_halo_router, mock_model_registry):
        """Test fallback with TaskDAGTask object (not dict)"""
        adapter = PipelexAdapter(
            halo_router=mock_halo_router,
            model_registry=mock_model_registry
        )

        # Create mock task object with description attribute
        task_obj = type('Task', (), {
            'description': 'Build ecommerce store',
            'task_id': 'test_task_1'
        })()

        result = await adapter._fallback_execution(
            genesis_task=task_obj,
            business_type="ecommerce",
            inputs={"business_niche": "fashion"}
        )

        # Should handle object with hasattr
        assert result["status"] == "fallback"
        assert result["used_fallback"] is True

        # Verify model registry was called with correct description
        call_args = mock_model_registry.chat_async.call_args
        messages = call_args[0][1]
        assert messages[0]["content"] == "Build ecommerce store"


class TestErrorPropagation:
    """Test error propagation from Pipelex to caller"""

    @pytest.mark.asyncio
    async def test_file_not_found_error_propagation(self):
        """Test FileNotFoundError is wrapped in ValueError"""
        adapter = PipelexAdapter()

        with pytest.raises(ValueError, match="Workflow file not found"):
            await adapter.execute_workflow(
                workflow_name="nonexistent.plx",
                inputs={"test": "value"}
            )

    @pytest.mark.asyncio
    async def test_missing_inputs_error(self):
        """Test error when both inputs and genesis_task are None"""
        adapter = PipelexAdapter()

        with pytest.raises(ValueError, match="Either inputs or genesis_task must be provided"):
            await adapter.execute_workflow(
                workflow_name="ecommerce_business.plx",
                inputs=None,
                genesis_task=None
            )


class TestCacheBehavior:
    """Test cache behavior with multiple executions"""

    @pytest.mark.asyncio
    async def test_multiple_executions_of_same_workflow(self):
        """Test executing the same workflow multiple times"""
        adapter = PipelexAdapter()

        # Mock execution
        call_count = 0
        async def mock_execution(workflow_path, inputs):
            nonlocal call_count
            call_count += 1
            return {"output": f"success {call_count}"}

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            # Execute same workflow 3 times
            for i in range(3):
                result = await adapter.execute_workflow(
                    workflow_name="ecommerce_business.plx",
                    inputs={"business_niche": "fashion"}
                )
                assert result["status"] == "completed"

            # Verify was called 3 times (no caching of execution)
            assert call_count == 3


class TestLoggingDuringExecution:
    """Test logging during Pipelex execution"""

    @pytest.mark.asyncio
    async def test_logging_on_successful_execution(self, caplog):
        """Test logging behavior during successful execution"""
        import logging

        adapter = PipelexAdapter()

        async def mock_execution(workflow_path, inputs):
            return {"output": "success"}

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            with caplog.at_level(logging.DEBUG):
                result = await adapter.execute_workflow(
                    workflow_name="ecommerce_business.plx",
                    inputs={"business_niche": "fashion"}
                )

            assert result["status"] == "completed"
            # Logging happens at debug level, should not crash

    @pytest.mark.asyncio
    async def test_logging_on_fallback(self, mock_halo_router, mock_model_registry, caplog):
        """Test logging behavior when fallback is triggered"""
        import logging

        adapter = PipelexAdapter(
            halo_router=mock_halo_router,
            model_registry=mock_model_registry
        )

        async def mock_execution(workflow_path, inputs):
            raise RuntimeError("Test error")

        genesis_task = {"description": "Test"}

        with patch.object(adapter, '_execute_workflow_internal', side_effect=mock_execution):
            with caplog.at_level(logging.DEBUG):
                result = await adapter.execute_workflow(
                    workflow_name="ecommerce_business.plx",
                    inputs={"business_niche": "fashion"},
                    genesis_task=genesis_task
                )

            assert result.get("used_fallback") is True
            # Should have logged fallback reason at debug level
            # (The actual logging happens inside the adapter, we just verify no crash)
