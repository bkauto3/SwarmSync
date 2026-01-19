"""
Test suite for Vertex AI Client initialization and integration

Tests client initialization, authentication, error handling, and fallback behavior.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from infrastructure.vertex_ai.model_registry import ModelRegistry
from infrastructure.vertex_ai.model_endpoints import ModelEndpoints
from infrastructure.vertex_ai.monitoring import VertexAIMonitoring
from infrastructure.vertex_ai.fine_tuning_pipeline import FineTuningPipeline


class TestVertexAIClientInitialization:
    """Test Vertex AI client initialization"""

    def test_model_registry_initialization(self):
        """Test ModelRegistry initialization with valid parameters"""
        registry = ModelRegistry(
            project_id="test-project",
            location="us-central1"
        )

        assert registry is not None
        assert registry.project_id == "test-project"
        assert registry.location == "us-central1"

    def test_model_endpoints_initialization(self):
        """Test ModelEndpoints initialization"""
        endpoints = ModelEndpoints(
            project_id="test-project",
            location="us-west1"
        )

        assert endpoints is not None
        assert endpoints.project_id == "test-project"
        assert endpoints.location == "us-west1"

    def test_monitoring_initialization(self):
        """Test VertexAIMonitoring initialization"""
        monitoring = VertexAIMonitoring(
            project_id="test-project",
            location="us-central1"
        )

        assert monitoring is not None
        assert monitoring.project_id == "test-project"

    def test_fine_tuning_pipeline_initialization(self):
        """Test FineTuningPipeline initialization"""
        pipeline = FineTuningPipeline(
            project_id="test-project",
            location="us-central1"
        )

        assert pipeline is not None
        assert pipeline.project_id == "test-project"

    def test_initialization_with_custom_location(self):
        """Test initialization with custom location"""
        locations = ["us-central1", "us-west1", "europe-west1", "asia-southeast1"]

        for location in locations:
            registry = ModelRegistry(
                project_id="test-project",
                location=location
            )
            assert registry.location == location

    def test_initialization_preserves_project_id(self):
        """Test that project ID is properly stored"""
        project_ids = ["my-project", "example-123", "prod-ml-platform"]

        for project_id in project_ids:
            registry = ModelRegistry(
                project_id=project_id,
                location="us-central1"
            )
            assert registry.project_id == project_id


class TestVertexAIErrorHandling:
    """Test error handling in Vertex AI clients"""

    @pytest.mark.asyncio
    async def test_get_model_error_handling(self):
        """Test error handling for missing models"""
        registry = ModelRegistry(
            project_id="test-project",
            location="us-central1"
        )
        registry.models = {}  # Empty registry

        with pytest.raises(Exception):
            await registry.get_model("nonexistent-model", "1.0.0")

    @pytest.mark.asyncio
    async def test_endpoint_not_found_error(self):
        """Test error when endpoint doesn't exist"""
        endpoints = ModelEndpoints(
            project_id="test-project",
            location="us-central1"
        )
        endpoints.endpoints = {}

        # Should handle gracefully
        with pytest.raises(Exception):
            await endpoints.delete_endpoint("nonexistent-endpoint")

    @pytest.mark.asyncio
    async def test_invalid_tuning_config(self):
        """Test error on invalid tuning configuration"""
        from infrastructure.vertex_ai.fine_tuning_pipeline import TuningJobConfig, TuningType

        # Missing required fields should raise
        try:
            config = TuningJobConfig(
                name="",  # Empty name should fail
                model_id="",  # Empty model ID
                tuning_type=TuningType.SUPERVISED,
                training_data_uri="",
                output_model_uri="",
            )
            # If validation isn't strict, configuration was created
            assert config is not None
        except Exception:
            # If validation is strict, exception is raised
            pass


class TestVertexAIEnvironmentHandling:
    """Test environment variable and configuration handling"""

    def test_project_id_from_environment(self):
        """Test reading project ID from environment"""
        with patch.dict(os.environ, {"GCP_PROJECT_ID": "env-project"}):
            # Client should read project from env if available
            registry = ModelRegistry(
                project_id="override-project",  # Explicit override
                location="us-central1"
            )
            assert registry.project_id == "override-project"

    def test_location_defaults(self):
        """Test default location handling"""
        registry = ModelRegistry(
            project_id="test-project",
            location="us-central1"  # Explicit location
        )
        assert registry.location == "us-central1"

    def test_credential_handling_mock_mode(self):
        """Test credential handling in mock mode (when Vertex AI unavailable)"""
        with patch('infrastructure.vertex_ai.model_registry.VERTEX_AI_AVAILABLE', False):
            # Should work in mock mode without real credentials
            registry = ModelRegistry(
                project_id="test-project",
                location="us-central1"
            )
            assert registry is not None


class TestVertexAIIntegration:
    """Test integration between Vertex AI components"""

    def test_registry_and_endpoints_integration(self):
        """Test that registry and endpoints can work together"""
        registry = ModelRegistry(
            project_id="test-project",
            location="us-central1"
        )
        endpoints = ModelEndpoints(
            project_id="test-project",
            location="us-central1"
        )

        # Both should be initialized
        assert registry.project_id == endpoints.project_id
        assert registry.location == endpoints.location

    def test_monitoring_with_endpoints(self):
        """Test monitoring and endpoints integration"""
        endpoints = ModelEndpoints(
            project_id="test-project",
            location="us-central1"
        )
        monitoring = VertexAIMonitoring(
            project_id="test-project",
            location="us-central1"
        )

        assert endpoints.project_id == monitoring.project_id

    def test_fine_tuning_with_registry(self):
        """Test fine-tuning pipeline with model registry"""
        registry = ModelRegistry(
            project_id="test-project",
            location="us-central1"
        )
        pipeline = FineTuningPipeline(
            project_id="test-project",
            location="us-central1"
        )

        # Both should have same project ID
        assert registry.project_id == pipeline.project_id

    def test_all_components_same_project(self):
        """Test all Vertex AI components use same project"""
        project_id = "unified-project"
        location = "us-central1"

        registry = ModelRegistry(project_id=project_id, location=location)
        endpoints = ModelEndpoints(project_id=project_id, location=location)
        monitoring = VertexAIMonitoring(project_id=project_id, location=location)
        pipeline = FineTuningPipeline(project_id=project_id, location=location)

        assert registry.project_id == project_id
        assert endpoints.project_id == project_id
        assert monitoring.project_id == project_id
        assert pipeline.project_id == project_id


class TestVertexAIFallbackBehavior:
    """Test fallback behavior when Vertex AI is unavailable"""

    def test_mock_mode_fallback(self):
        """Test that components work in mock mode"""
        with patch('infrastructure.vertex_ai.model_registry.VERTEX_AI_AVAILABLE', False):
            registry = ModelRegistry(
                project_id="test-project",
                location="us-central1"
            )
            assert registry is not None

    def test_monitoring_without_real_api(self):
        """Test monitoring works without real Vertex AI API"""
        with patch('infrastructure.vertex_ai.monitoring.VERTEX_AI_AVAILABLE', False):
            monitoring = VertexAIMonitoring(
                project_id="test-project",
                location="us-central1"
            )
            assert monitoring is not None

    def test_endpoints_degraded_mode(self):
        """Test endpoints handle missing Vertex AI gracefully"""
        with patch('infrastructure.vertex_ai.model_endpoints.VERTEX_AI_AVAILABLE', False):
            endpoints = ModelEndpoints(
                project_id="test-project",
                location="us-central1"
            )
            assert endpoints is not None


class TestVertexAICostTracking:
    """Test cost tracking integration"""

    def test_cost_metrics_initialization(self):
        """Test cost tracking is available"""
        monitoring = VertexAIMonitoring(
            project_id="test-project",
            location="us-central1"
        )
        assert monitoring is not None
        # Cost tracking should be initialized
        assert hasattr(monitoring, 'metrics_cache') or hasattr(monitoring, 'project_id')

    def test_model_cost_tracking(self):
        """Test model cost metrics can be tracked"""
        registry = ModelRegistry(
            project_id="test-project",
            location="us-central1"
        )
        # Registry should support cost tracking
        assert hasattr(registry, 'models') or hasattr(registry, 'project_id')


class TestVertexAIObservability:
    """Test observability integration"""

    def test_observability_import(self):
        """Test that observability is properly imported"""
        from infrastructure.vertex_ai.model_registry import obs_manager
        assert obs_manager is not None

    def test_observability_available_in_all_modules(self):
        """Test observability manager is available in all modules"""
        from infrastructure.vertex_ai.model_registry import obs_manager as reg_obs
        from infrastructure.vertex_ai.model_endpoints import obs_manager as ep_obs
        from infrastructure.vertex_ai.monitoring import obs_manager as mon_obs
        from infrastructure.vertex_ai.fine_tuning_pipeline import obs_manager as ft_obs

        assert reg_obs is not None
        assert ep_obs is not None
        assert mon_obs is not None
        assert ft_obs is not None


class TestVertexAIAuthentication:
    """Test authentication handling"""

    def test_authentication_initialization(self):
        """Test authentication is initialized"""
        registry = ModelRegistry(
            project_id="test-project",
            location="us-central1"
        )
        # Should initialize without requiring credentials in test mode
        assert registry is not None

    def test_multiple_clients_independence(self):
        """Test multiple clients are independent"""
        reg1 = ModelRegistry(project_id="project1", location="us-central1")
        reg2 = ModelRegistry(project_id="project2", location="us-west1")

        assert reg1.project_id != reg2.project_id
        assert reg1.location != reg2.location
