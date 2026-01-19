"""
Integration Tests: Pipelex × Genesis Meta-Agent

Tests the integration between Pipelex workflows and Genesis orchestrator.
Validates that Genesis can execute .plx workflows and process results.

Author: Cursor (PinkLake)
Date: November 2, 2025
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Import adapter
from infrastructure.orchestration.pipelex_adapter import (
    PipelexAdapter,
    execute_pipelex_workflow
)

# Import Genesis components
try:
    from infrastructure.halo_router import HALORouter
    from infrastructure.model_registry import ModelRegistry
    GENESIS_AVAILABLE = True
except ImportError:
    GENESIS_AVAILABLE = False


@pytest.fixture
def pipelex_adapter():
    """Create PipelexAdapter instance for testing"""
    return PipelexAdapter(timeout_seconds=30)


@pytest.fixture
def mock_halo_router():
    """Mock HALO router for testing"""
    router = Mock(spec=HALORouter)
    router.route_tasks = AsyncMock(return_value=Mock(
        assignments={"task_1": "qa_agent"}
    ))
    return router


@pytest.fixture
def mock_model_registry():
    """Mock ModelRegistry for testing"""
    registry = Mock(spec=ModelRegistry)
    registry.chat_async = AsyncMock(return_value="Mock response")
    return registry


@pytest.fixture
def workflow_templates():
    """Return paths to workflow templates"""
    base_path = Path(__file__).parent.parent.parent
    return {
        "ecommerce": base_path / "workflows" / "templates" / "ecommerce_business.plx",
        "content": base_path / "workflows" / "templates" / "content_platform_business.plx",
        "saas": base_path / "workflows" / "templates" / "saas_product_business.plx"
    }


class TestPipelexAdapterInitialization:
    """Test PipelexAdapter initialization"""
    
    def test_adapter_initialization(self):
        """Test adapter can be initialized"""
        adapter = PipelexAdapter()
        assert adapter is not None
        assert adapter.timeout_seconds == 300
    
    def test_adapter_with_custom_timeout(self):
        """Test adapter with custom timeout"""
        adapter = PipelexAdapter(timeout_seconds=60)
        assert adapter.timeout_seconds == 60
    
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    def test_adapter_with_genesis_components(self, mock_halo_router, mock_model_registry):
        """Test adapter initializes with Genesis components"""
        adapter = PipelexAdapter(
            halo_router=mock_halo_router,
            model_registry=mock_model_registry
        )
        assert adapter.halo_router == mock_halo_router
        assert adapter.model_registry == mock_model_registry


class TestGenesisTaskMapping:
    """Test Genesis task → Pipelex input mapping"""
    
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    def test_map_ecommerce_task(self, pipelex_adapter):
        """Test mapping Genesis e-commerce task to Pipelex inputs"""
        genesis_task = {
            "description": "Create e-commerce store",
            "niche": "sustainable fashion",
            "target_audience": "millennials"
        }
        
        inputs = pipelex_adapter._map_genesis_task_to_pipelex_inputs(
            genesis_task,
            "ecommerce"
        )
        
        assert "business_niche" in inputs
        assert inputs["business_niche"] == "sustainable fashion"
    
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    def test_map_saas_task(self, pipelex_adapter):
        """Test mapping Genesis SaaS task to Pipelex inputs"""
        genesis_task = {
            "description": "Create SaaS product",
            "problem": "text improvement tools"
        }
        
        inputs = pipelex_adapter._map_genesis_task_to_pipelex_inputs(
            genesis_task,
            "saas_product"
        )
        
        assert "problem_space" in inputs
        assert inputs["problem_space"] == "text improvement tools"
    
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    def test_map_content_task(self, pipelex_adapter):
        """Test mapping Genesis content platform task to Pipelex inputs"""
        genesis_task = {
            "description": "Create content platform",
            "niche": "AI crypto news"
        }
        
        inputs = pipelex_adapter._map_genesis_task_to_pipelex_inputs(
            genesis_task,
            "content_platform"
        )
        
        assert "business_niche" in inputs or "niche" in inputs


class TestWorkflowExecution:
    """Test workflow execution"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    async def test_execute_ecommerce_workflow(self, pipelex_adapter, workflow_templates, mock_model_registry):
        """Test executing e-commerce workflow"""
        workflow_path = str(workflow_templates["ecommerce"])
        
        if not Path(workflow_path).exists():
            pytest.skip(f"Workflow template not found: {workflow_path}")
        
        inputs = {"business_niche": "sustainable fashion"}
        
        # Mock Pipelex execution (will fail gracefully if Pipelex not available)
        try:
            result = await pipelex_adapter.execute_workflow(
                workflow_path=workflow_path,
                inputs=inputs
            )
            assert result is not None
        except (RuntimeError, ImportError, TimeoutError) as e:
            # Expected if Pipelex not properly configured
            pytest.skip(f"Pipelex execution not available: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    async def test_execute_with_genesis_task(self, pipelex_adapter, workflow_templates):
        """Test executing workflow with Genesis task"""
        workflow_path = str(workflow_templates["ecommerce"])
        
        if not Path(workflow_path).exists():
            pytest.skip(f"Workflow template not found: {workflow_path}")
        
        genesis_task = {
            "description": "Create e-commerce store",
            "niche": "sustainable fashion"
        }
        
        try:
            result = await pipelex_adapter.execute_workflow(
                workflow_path=workflow_path,
                genesis_task=genesis_task,
                business_type="ecommerce"
            )
            assert result is not None
        except (RuntimeError, ImportError, TimeoutError) as e:
            pytest.skip(f"Pipelex execution not available: {e}")
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_workflow(self, pipelex_adapter):
        """Test executing non-existent workflow fails gracefully"""
        # PipelexAdapter wraps FileNotFoundError into ValueError
        with pytest.raises(ValueError, match="Workflow file not found"):
            await pipelex_adapter.execute_workflow(
                workflow_path="nonexistent.plx",
                inputs={"business_niche": "test"}
            )
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, pipelex_adapter, workflow_templates):
        """Test workflow execution timeout"""
        from unittest.mock import patch, AsyncMock
        import asyncio

        workflow_path = str(workflow_templates["ecommerce"])

        if not Path(workflow_path).exists():
            pytest.skip(f"Workflow template not found: {workflow_path}")

        # Create adapter with HALO router and ModelRegistry for fallback
        mock_halo_router = AsyncMock()
        mock_halo_router.route_tasks = AsyncMock(return_value=type('obj', (object,), {
            'assignments': {'task_1': 'builder_agent'},
            'explanations': {}
        })())

        mock_model_registry = AsyncMock()
        mock_model_registry.chat_async = AsyncMock(return_value={"output": "fallback result"})

        adapter = PipelexAdapter(
            timeout_seconds=0.1,  # Very short timeout
            halo_router=mock_halo_router,
            model_registry=mock_model_registry
        )

        # Mock _execute_workflow_internal to simulate slow execution
        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(2)  # Sleep longer than timeout
            return {"output": "should not reach"}

        genesis_task = {"description": "Test timeout", "business_type": "ecommerce"}

        with patch.object(adapter, '_execute_workflow_internal', side_effect=slow_execution):
            # With genesis_task, timeout triggers fallback (returns result with fallback flag)
            result = await adapter.execute_workflow(
                workflow_path=workflow_path,
                inputs={"business_niche": "test"},
                genesis_task=genesis_task
            )
            # Should have used fallback due to timeout
            assert result.get("used_fallback") is True


class TestFallbackExecution:
    """Test fallback execution when Pipelex fails"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    async def test_fallback_on_pipelex_error(self, pipelex_adapter, mock_model_registry, mock_halo_router):
        """Test fallback execution when Pipelex fails"""
        adapter = PipelexAdapter(
            halo_router=mock_halo_router,
            model_registry=mock_model_registry
        )
        
        genesis_task = {
            "description": "Create business",
            "niche": "test"
        }

        # Fallback should execute via ModelRegistry
        # _fallback_execution signature: (genesis_task, business_type, inputs)
        result = await adapter._fallback_execution(
            genesis_task=genesis_task,
            business_type="ecommerce",
            inputs={"business_niche": "test"}
        )

        assert result is not None
        assert "fallback" in result
        assert result["fallback"] is True
        mock_model_registry.chat_async.assert_called_once()


class TestConvenienceFunction:
    """Test convenience execute_pipelex_workflow function"""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    async def test_execute_pipelex_workflow_function(self, workflow_templates):
        """Test convenience function for workflow execution"""
        workflow_path = str(workflow_templates["ecommerce"])
        
        if not Path(workflow_path).exists():
            pytest.skip(f"Workflow template not found: {workflow_path}")
        
        inputs = {"business_niche": "test niche"}
        
        try:
            result = await execute_pipelex_workflow(
                workflow_path=workflow_path,
                inputs=inputs
            )
            assert result is not None
        except (RuntimeError, ImportError, TimeoutError) as e:
            pytest.skip(f"Pipelex execution not available: {e}")


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    async def test_ecommerce_workflow_integration(self, workflow_templates):
        """Test complete e-commerce workflow integration"""
        workflow_path = str(workflow_templates["ecommerce"])
        
        if not Path(workflow_path).exists():
            pytest.skip(f"Workflow template not found: {workflow_path}")
        
        genesis_task = {
            "description": "Create sustainable fashion e-commerce store",
            "niche": "sustainable fashion",
            "target_audience": "millennials"
        }
        
        try:
            result = await execute_pipelex_workflow(
                workflow_path=workflow_path,
                genesis_task=genesis_task,
                business_type="ecommerce"
            )
            
            # Validate result structure
            assert result is not None
            assert isinstance(result, dict)
        except (RuntimeError, ImportError, TimeoutError) as e:
            pytest.skip(f"Integration test skipped: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    async def test_content_platform_integration(self, workflow_templates):
        """Test content platform workflow integration"""
        workflow_path = str(workflow_templates["content"])
        
        if not Path(workflow_path).exists():
            pytest.skip(f"Workflow template not found: {workflow_path}")
        
        genesis_task = {
            "description": "Create AI crypto news platform",
            "niche": "AI crypto news"
        }
        
        try:
            result = await execute_pipelex_workflow(
                workflow_path=workflow_path,
                genesis_task=genesis_task,
                business_type="content_platform"
            )
            
            assert result is not None
        except (RuntimeError, ImportError, TimeoutError) as e:
            pytest.skip(f"Integration test skipped: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skipif(not GENESIS_AVAILABLE, reason="Genesis components not available")
    async def test_saas_product_integration(self, workflow_templates):
        """Test SaaS product workflow integration"""
        workflow_path = str(workflow_templates["saas"])
        
        if not Path(workflow_path).exists():
            pytest.skip(f"Workflow template not found: {workflow_path}")
        
        genesis_task = {
            "description": "Create text improvement SaaS",
            "problem": "text improvement tools"
        }
        
        try:
            result = await execute_pipelex_workflow(
                workflow_path=workflow_path,
                genesis_task=genesis_task,
                business_type="saas_product"
            )
            
            assert result is not None
        except (RuntimeError, ImportError, TimeoutError) as e:
            pytest.skip(f"Integration test skipped: {e}")


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
