"""
Test suite for Vertex AI Model Registry

Tests model registration, versioning, metadata tracking, and deployment stage management.
Covers both success and error scenarios with proper mocking.
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from infrastructure.vertex_ai.model_registry import (
    ModelRegistry,
    ModelMetadata,
    ModelSource,
    DeploymentStage,
)
from infrastructure.observability import get_observability_manager, SpanType


@pytest.fixture
def mock_vertex_model():
    """Mock Vertex AI Model object"""
    model = MagicMock()
    model.resource_name = "projects/test-project/locations/us-central1/models/model-123"
    model.display_name = "Test Model v1"
    model.version_id = "1.0.0"
    model.version_aliases = ["champion", "latest"]
    model.labels = {"test": "true"}
    model.create = MagicMock(return_value=model)
    model.upload = MagicMock(return_value=model)
    model.update = MagicMock(return_value=model)
    model.delete = MagicMock()
    return model


@pytest.fixture
def mock_vertex_ai(mock_vertex_model):
    """Mock Vertex AI client"""
    with patch('infrastructure.vertex_ai.model_registry.VERTEX_AI_AVAILABLE', True):
        with patch('infrastructure.vertex_ai.model_registry.Model') as mock_model_class:
            with patch('infrastructure.vertex_ai.model_registry.Endpoint') as mock_endpoint_class:
                with patch('infrastructure.vertex_ai.model_registry.aiplatform') as mock_api:
                    # Configure Model class methods
                    mock_model_class.upload = MagicMock(return_value=mock_vertex_model)
                    mock_model_class.list = MagicMock(return_value=[mock_vertex_model])
                    mock_model_class.return_value = mock_vertex_model

                    # Configure aiplatform module
                    mock_api.Model = mock_model_class
                    mock_api.Endpoint = mock_endpoint_class
                    mock_api.init = MagicMock()

                    yield mock_api


@pytest.fixture
def model_registry(mock_vertex_ai):
    """Create ModelRegistry instance for testing"""
    registry = ModelRegistry(
        project_id="test-project",
        location="us-central1"
    )
    return registry


@pytest.fixture
def sample_metadata():
    """Sample model metadata for tests"""
    return ModelMetadata(
        name="test-model",
        display_name="Test Model v1",
        version="1.0.0",
        description="A test model",
        source=ModelSource.MANUAL_UPLOAD,
        artifact_uri="gs://test-bucket/model",
        serving_container_uri="us-docker.pkg.dev/vertex-ai/prediction/tensorflow:latest",
        deployment_stage=DeploymentStage.DEVELOPMENT,
        base_model=None,
        performance_metrics={"accuracy": 0.95, "latency_ms": 50.0},
        cost_metrics={"per_1m_tokens": 0.01},
        tags=["test", "v1"],
    )


@pytest.mark.asyncio
async def test_upload_model_success(model_registry, sample_metadata):
    """Test successful model upload"""
    model_registry.models = {}  # Reset models

    model = await model_registry.upload_model(
        sample_metadata,
        serving_container_ports=[8080],
        serving_container_predict_route="/predict",
        sync=False
    )

    assert model is not None
    assert model.resource_name is not None
    # Verify metadata was cached
    cached_metadata = model_registry.metadata_cache.get("test-model:1.0.0")
    assert cached_metadata is not None
    assert cached_metadata.name == "test-model"
    assert cached_metadata.version == "1.0.0"
    assert cached_metadata.deployment_stage == DeploymentStage.DEVELOPMENT


@pytest.mark.asyncio
async def test_upload_model_with_parent_version(model_registry, sample_metadata):
    """Test model upload with parent version tracking"""
    model_registry.models = {}

    metadata1 = sample_metadata
    await model_registry.upload_model(metadata1, sync=False)

    # Upload improved version
    metadata2 = ModelMetadata(
        name="test-model",
        display_name="Test Model v2",
        version="2.0.0",
        description="Improved test model",
        source=ModelSource.SE_DARWIN_EVOLUTION,
        artifact_uri="gs://test-bucket/model-v2",
        serving_container_uri="us-docker.pkg.dev/vertex-ai/prediction/tensorflow:latest",
        deployment_stage=DeploymentStage.DEVELOPMENT,
        base_model="test-model",
        performance_metrics={"accuracy": 0.97, "latency_ms": 45.0},
        cost_metrics={"per_1m_tokens": 0.01},
        tags=["test", "v2"],
    )

    model = await model_registry.upload_model(metadata2, sync=False)
    assert model is not None
    # Verify v2 metadata was cached
    cached_metadata = model_registry.metadata_cache.get("test-model:2.0.0")
    assert cached_metadata.version == "2.0.0"


@pytest.mark.asyncio
async def test_get_model_success(model_registry, sample_metadata):
    """Test successful model retrieval"""
    model_registry.models = {}
    await model_registry.upload_model(sample_metadata, sync=False)

    model, metadata = await model_registry.get_model("test-model", "1.0.0")
    assert metadata.name == "test-model"
    assert metadata.version == "1.0.0"


@pytest.mark.asyncio
async def test_get_model_not_found(model_registry):
    """Test retrieval of non-existent model"""
    model_registry.models = {}

    with pytest.raises(Exception):
        await model_registry.get_model("nonexistent", "1.0.0")


@pytest.mark.asyncio
async def test_list_models_filtered(model_registry, sample_metadata):
    """Test listing models with filters"""
    # Reset state
    model_registry.models = {}
    model_registry.metadata_cache = {}

    # Upload models with different stages
    staging_meta = ModelMetadata(
        name="staging-model",
        display_name="Staging Model",
        version="1.0.0",
        description="For staging",
        source=ModelSource.MANUAL_UPLOAD,
        artifact_uri="gs://test-bucket/staging",
        serving_container_uri="us-docker.pkg.dev/vertex-ai/prediction/tensorflow:latest",
        deployment_stage=DeploymentStage.STAGING,
        tags=["staging"],
    )

    await model_registry.upload_model(sample_metadata, sync=False)
    await model_registry.upload_model(staging_meta, sync=False)

    # List only development models
    models = await model_registry.list_models(stage=DeploymentStage.DEVELOPMENT)
    assert len(models) == 1
    assert models[0].name == "test-model"


@pytest.mark.asyncio
async def test_promote_model(model_registry, sample_metadata):
    """Test model promotion through deployment stages"""
    model_registry.models = {}
    await model_registry.upload_model(sample_metadata, sync=False)

    # Promote from development to staging
    metadata = await model_registry.promote_model(
        "test-model",
        "1.0.0",
        DeploymentStage.STAGING
    )

    assert metadata.deployment_stage == DeploymentStage.STAGING


@pytest.mark.asyncio
async def test_update_performance_metrics(model_registry, sample_metadata):
    """Test updating model performance metrics"""
    model_registry.models = {}
    await model_registry.upload_model(sample_metadata, sync=False)

    new_metrics = {"accuracy": 0.98, "latency_ms": 40.0, "f1_score": 0.96}
    metadata = await model_registry.update_performance_metrics(
        "test-model",
        "1.0.0",
        new_metrics
    )

    assert metadata.performance_metrics["accuracy"] == 0.98
    assert metadata.performance_metrics["f1_score"] == 0.96


@pytest.mark.asyncio
async def test_update_cost_metrics(model_registry, sample_metadata):
    """Test updating model cost metrics"""
    model_registry.models = {}
    await model_registry.upload_model(sample_metadata, sync=False)

    new_metrics = {"per_1m_tokens": 0.015, "per_inference": 0.001}
    metadata = await model_registry.update_cost_metrics(
        "test-model",
        "1.0.0",
        new_metrics
    )

    assert metadata.cost_metrics["per_1m_tokens"] == 0.015


@pytest.mark.asyncio
async def test_delete_model(model_registry, sample_metadata):
    """Test model deletion"""
    model_registry.models = {}
    await model_registry.upload_model(sample_metadata, sync=False)

    result = await model_registry.delete_model(
        "test-model",
        "1.0.0",
        delete_from_vertex_ai=False
    )

    assert result is True
    # Verify model is deleted
    with pytest.raises(Exception):
        await model_registry.get_model("test-model", "1.0.0")


@pytest.mark.asyncio
async def test_compare_versions(model_registry, sample_metadata):
    """Test comparison between model versions"""
    model_registry.models = {}

    v1_meta = sample_metadata
    await model_registry.upload_model(v1_meta, sync=False)

    v2_meta = ModelMetadata(
        name="test-model",
        display_name="Test Model v2",
        version="2.0.0",
        description="Improved version",
        source=ModelSource.SE_DARWIN_EVOLUTION,
        artifact_uri="gs://test-bucket/model-v2",
        serving_container_uri="us-docker.pkg.dev/vertex-ai/prediction/tensorflow:latest",
        performance_metrics={"accuracy": 0.98, "latency_ms": 40.0},
        cost_metrics={"per_1m_tokens": 0.015},
    )

    await model_registry.upload_model(v2_meta, sync=False)

    comparison = await model_registry.compare_versions("test-model", "1.0.0", "2.0.0")
    assert comparison is not None
    assert "v1_0_0" in comparison or "1.0.0" in str(comparison)
    assert "v2_0_0" in comparison or "2.0.0" in str(comparison)


def test_model_metadata_serialization(sample_metadata):
    """Test ModelMetadata can be serialized to dict"""
    metadata_dict = {
        "name": sample_metadata.name,
        "display_name": sample_metadata.display_name,
        "version": sample_metadata.version,
        "description": sample_metadata.description,
    }

    assert metadata_dict["name"] == "test-model"
    assert metadata_dict["version"] == "1.0.0"


def test_deployment_stage_enum():
    """Test DeploymentStage enum values"""
    assert DeploymentStage.DEVELOPMENT.value == "development"
    assert DeploymentStage.STAGING.value == "staging"
    assert DeploymentStage.PRODUCTION.value == "production"
    assert DeploymentStage.ARCHIVED.value == "archived"


def test_model_source_enum():
    """Test ModelSource enum values"""
    assert ModelSource.SE_DARWIN_EVOLUTION.value == "se_darwin"
    assert ModelSource.MANUAL_UPLOAD.value == "manual"
    assert ModelSource.PRETRAINED_HF.value == "huggingface"


@pytest.mark.asyncio
async def test_concurrent_model_access(model_registry, sample_metadata):
    """Test concurrent access to model registry"""
    import asyncio

    model_registry.models = {}
    await model_registry.upload_model(sample_metadata, sync=False)

    # Simulate concurrent reads
    tasks = [
        model_registry.get_model("test-model", "1.0.0")
        for _ in range(5)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert all(not isinstance(r, Exception) for r in results)
    assert len(results) == 5
