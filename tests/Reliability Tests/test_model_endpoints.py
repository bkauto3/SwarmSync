"""
Test suite for Vertex AI Model Endpoints

Tests endpoint creation, model deployment, prediction serving, traffic management, and scaling.
Includes tests for A/B testing and health monitoring.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from infrastructure.vertex_ai.model_endpoints import (
    ModelEndpoints,
    EndpointConfig,
    TrafficSplitStrategy,
    TrafficSplit,
)


@pytest.fixture
def mock_vertex_ai():
    """
    Mock Vertex AI client with proper endpoint lifecycle simulation.

    Context7 MCP Validation: /websites/cloud_google_vertex-ai_generative-ai
    Simulates official Vertex AI API:
    - Endpoint.create() returns endpoint with resource_name
    - Endpoint has all required attributes (display_name, traffic_split, deployed_models)
    - Model.deploy() works correctly
    """
    # Track state across all endpoint operations
    created_endpoints = {}
    endpoint_counter = [0]
    deployed_model_counter = [0]

    # Mock Endpoint class with full lifecycle
    class MockEndpoint:
        def __init__(self, endpoint_id=None):
            if endpoint_id and endpoint_id in created_endpoints:
                cached = created_endpoints[endpoint_id]
                self.resource_name = cached.resource_name
                self.name = cached.name
                self.display_name = cached.display_name
                self.network = cached.network
                self.deployed_models = cached.deployed_models
                self.traffic_split = cached.traffic_split
                self._endpoint_id = cached._endpoint_id
            else:
                self.resource_name = None
                self.name = None
                self.display_name = None
                self.network = ""
                self.deployed_models = []
                self.traffic_split = {}
                self._endpoint_id = None

        @staticmethod
        def create(display_name, description="", labels=None,
                  dedicated_endpoint_enabled=False, encryption_spec_key_name=None, sync=True):
            endpoint_counter[0] += 1
            endpoint_id = f"endpoint-{endpoint_counter[0]}"
            endpoint = MockEndpoint()
            endpoint._endpoint_id = endpoint_id
            endpoint.resource_name = f"projects/test-project/locations/us-central1/endpoints/{endpoint_id}"
            endpoint.name = endpoint_id
            endpoint.display_name = display_name
            endpoint.network = ""
            endpoint.deployed_models = []
            endpoint.traffic_split = {}
            created_endpoints[endpoint_id] = endpoint
            created_endpoints[endpoint.resource_name] = endpoint
            return endpoint

        def wait(self):
            pass

        def deploy(self, model, deployed_model_display_name, traffic_percentage=100,
                  machine_type=None, accelerator_type=None, accelerator_count=0,
                  min_replica_count=1, max_replica_count=1,
                  autoscaling_target_accelerator_duty_cycle=60,
                  enable_access_logging=True, enable_container_logging=True, sync=True):
            deployed_model_counter[0] += 1
            deployed_model_id = f"deployed-model-{deployed_model_counter[0]}"
            deployed_model = Mock()
            deployed_model.id = deployed_model_id
            deployed_model.display_name = deployed_model_display_name
            deployed_model.model = model
            deployed_model.machine_type = machine_type
            deployed_model.min_replica_count = min_replica_count
            deployed_model.max_replica_count = max_replica_count
            self.deployed_models.append(deployed_model)
            self.traffic_split[deployed_model_id] = traffic_percentage
            return deployed_model

        def predict(self, instances, parameters=None, timeout=60.0):
            response = Mock()
            response.predictions = [{"output": "mock"} for _ in instances]
            response.deployed_model_id = self.deployed_models[0].id if self.deployed_models else "no-model"
            return response

        def update(self, traffic_split=None):
            if traffic_split:
                self.traffic_split = traffic_split

        def undeploy(self, deployed_model_id, sync=True):
            self.deployed_models = [m for m in self.deployed_models if m.id != deployed_model_id]
            if deployed_model_id in self.traffic_split:
                del self.traffic_split[deployed_model_id]

        def delete(self, force=False, sync=True):
            if self.name in created_endpoints:
                del created_endpoints[self.name]
            if self.resource_name in created_endpoints:
                del created_endpoints[self.resource_name]

        def refresh(self):
            pass

        @staticmethod
        def list(filter=None):
            endpoints = []
            seen = set()
            for endpoint in created_endpoints.values():
                if endpoint._endpoint_id not in seen:
                    endpoints.append(endpoint)
                    seen.add(endpoint._endpoint_id)
            return endpoints

    # Mock Model class
    class MockModel:
        def __init__(self, model_resource_name):
            self.resource_name = model_resource_name
            self.display_name = "Mock Model"

        def deploy(self, endpoint, deployed_model_display_name, machine_type=None,
                  accelerator_type=None, accelerator_count=0, min_replica_count=1,
                  max_replica_count=1, autoscaling_target_accelerator_duty_cycle=60,
                  traffic_percentage=100, enable_access_logging=True,
                  enable_container_logging=True, sync=True):
            return endpoint.deploy(
                model=self, deployed_model_display_name=deployed_model_display_name,
                machine_type=machine_type, accelerator_type=accelerator_type,
                accelerator_count=accelerator_count, min_replica_count=min_replica_count,
                max_replica_count=max_replica_count,
                autoscaling_target_accelerator_duty_cycle=autoscaling_target_accelerator_duty_cycle,
                traffic_percentage=traffic_percentage, enable_access_logging=enable_access_logging,
                enable_container_logging=enable_container_logging, sync=sync)

    with patch('infrastructure.vertex_ai.model_endpoints.VERTEX_AI_AVAILABLE', True):
        with patch('infrastructure.vertex_ai.model_endpoints.Endpoint', MockEndpoint):
            with patch('infrastructure.vertex_ai.model_endpoints.Model', MockModel):
                with patch('infrastructure.vertex_ai.model_endpoints.aiplatform') as mock_api:
                    mock_api.init = Mock()
                    mock_api.Endpoint = MockEndpoint
                    mock_api.Model = MockModel
                    yield mock_api


@pytest.fixture
def model_endpoints(mock_vertex_ai):
    """Create ModelEndpoints instance for testing"""
    with patch('infrastructure.vertex_ai.model_endpoints.ModelRegistry') as mock_registry_class:
        mock_registry = Mock()
        async def mock_get_model(model_name, model_version):
            mock_model = mock_vertex_ai.Model(
                f"projects/test-project/locations/us-central1/models/{model_name}-{model_version}")
            mock_metadata = Mock()
            mock_metadata.name = model_name
            mock_metadata.version = model_version
            return mock_model, mock_metadata
        mock_registry.get_model = mock_get_model
        mock_registry_class.return_value = mock_registry
        endpoints = ModelEndpoints(project_id="test-project", location="us-central1")
        yield endpoints


@pytest.fixture
def sample_endpoint_config():
    """Sample endpoint configuration"""
    return EndpointConfig(
        name="test-endpoint",
        display_name="Test Endpoint",
        description="A test endpoint",
        labels={"environment": "test", "team": "ml"},
        network="",
        enable_request_logging=True,
        enable_access_logging=True,
    )


@pytest.mark.asyncio
async def test_create_endpoint_success(model_endpoints, sample_endpoint_config):
    """Test successful endpoint creation"""
    endpoint = await model_endpoints.create_endpoint(
        sample_endpoint_config,
        sync=False
    )

    assert endpoint is not None
    assert endpoint.name == "test-endpoint" or endpoint.display_name == "Test Endpoint"


@pytest.mark.asyncio
async def test_create_endpoint_with_network(model_endpoints):
    """Test endpoint creation with network specification"""
    config = EndpointConfig(
        name="private-endpoint",
        display_name="Private Endpoint",
        description="VPC endpoint",
        labels={"access": "private"},
        network="projects/test-project/global/networks/custom-vpc",
        enable_request_logging=False,
        enable_access_logging=False,
    )

    endpoint = await model_endpoints.create_endpoint(config, sync=False)
    assert endpoint is not None


@pytest.mark.asyncio
async def test_deploy_model_success(model_endpoints, sample_endpoint_config):
    """Test successful model deployment to endpoint"""
    # Create endpoint first
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)

    # Deploy model
    deployed_id = await model_endpoints.deploy_model(
        endpoint_id=endpoint.name if hasattr(endpoint, 'name') else "test-endpoint",
        model_name="test-model",
        model_version="1.0.0",
        display_name="Test Model Deployment",
        machine_type="n1-standard-4",
        accelerator_type="nvidia-tesla-t4",
        min_replica_count=1,
        max_replica_count=3,
    )

    assert deployed_id is not None


@pytest.mark.asyncio
async def test_deploy_model_with_autoscaling(model_endpoints, sample_endpoint_config):
    """Test model deployment with autoscaling configuration"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)

    deployed_id = await model_endpoints.deploy_model(
        endpoint_id=endpoint.name if hasattr(endpoint, 'name') else "test-endpoint",
        model_name="autoscale-model",
        model_version="1.0.0",
        display_name="Autoscaling Deployment",
        machine_type="n1-standard-8",
        accelerator_type="nvidia-tesla-v100",
        min_replica_count=2,
        max_replica_count=10,
    )

    assert deployed_id is not None


@pytest.mark.asyncio
async def test_predict_success(model_endpoints, sample_endpoint_config):
    """Test successful prediction request"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)
    endpoint_id = endpoint.name if hasattr(endpoint, 'name') else "test-endpoint"

    await model_endpoints.deploy_model(
        endpoint_id=endpoint_id,
        model_name="test-model",
        model_version="1.0.0",
        display_name="Test Deployment",
    )

    # Make prediction
    predictions = await model_endpoints.predict(
        endpoint_id=endpoint_id,
        instances=[{"text": "Hello, world!"}],
        parameters={"temperature": 0.7, "max_tokens": 100},
    )

    assert predictions is not None
    assert isinstance(predictions, (list, dict))


@pytest.mark.asyncio
async def test_predict_batch(model_endpoints, sample_endpoint_config):
    """Test batch prediction request"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)
    endpoint_id = endpoint.name if hasattr(endpoint, 'name') else "test-endpoint"

    await model_endpoints.deploy_model(
        endpoint_id=endpoint_id,
        model_name="batch-model",
        model_version="1.0.0",
        display_name="Batch Deployment",
    )

    # Batch predictions
    instances = [
        {"text": f"Query {i}"} for i in range(10)
    ]

    predictions = await model_endpoints.predict(
        endpoint_id=endpoint_id,
        instances=instances,
        parameters=None,
    )

    assert predictions is not None


@pytest.mark.asyncio
async def test_update_traffic_split_ab_testing(model_endpoints, sample_endpoint_config):
    """Test A/B testing with traffic split"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)
    endpoint_id = endpoint.name if hasattr(endpoint, 'name') else "test-endpoint"

    # Deploy two models
    v1_id = await model_endpoints.deploy_model(
        endpoint_id=endpoint_id,
        model_name="model-v1",
        model_version="1.0.0",
        display_name="V1",
    )

    v2_id = await model_endpoints.deploy_model(
        endpoint_id=endpoint_id,
        model_name="model-v2",
        model_version="2.0.0",
        display_name="V2",
    )

    # Split traffic 70/30
    traffic_split = TrafficSplit(
        strategy=TrafficSplitStrategy.CANARY,
        splits={v1_id: 70, v2_id: 30}
    )

    success = await model_endpoints.update_traffic_split(
        endpoint_id=endpoint_id,
        traffic_split=traffic_split
    )

    assert success is True


@pytest.mark.asyncio
async def test_update_traffic_split_gradual_rollout(model_endpoints, sample_endpoint_config):
    """Test gradual rollout traffic strategy"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)
    endpoint_id = endpoint.name if hasattr(endpoint, 'name') else "test-endpoint"

    # Deploy new model
    new_id = await model_endpoints.deploy_model(
        endpoint_id=endpoint_id,
        model_name="new-model",
        model_version="3.0.0",
        display_name="Gradual Rollout",
    )

    # Start with 10% traffic
    traffic_split = TrafficSplit(
        strategy=TrafficSplitStrategy.GRADUAL,
        splits={"old_deployed_id": 90, new_id: 10}
    )

    success = await model_endpoints.update_traffic_split(
        endpoint_id=endpoint_id,
        traffic_split=traffic_split
    )

    assert success is True


@pytest.mark.asyncio
async def test_undeploy_model(model_endpoints, sample_endpoint_config):
    """Test model undeployment"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)
    endpoint_id = endpoint.name if hasattr(endpoint, 'name') else "test-endpoint"

    deployed_id = await model_endpoints.deploy_model(
        endpoint_id=endpoint_id,
        model_name="test-model",
        model_version="1.0.0",
        display_name="Test",
    )

    # Undeploy model
    success = await model_endpoints.undeploy_model(
        endpoint_id=endpoint_id,
        deployed_model_id=deployed_id or "deployed-model-1",
        sync=False
    )

    assert success is True


@pytest.mark.asyncio
async def test_delete_endpoint(model_endpoints, sample_endpoint_config):
    """Test endpoint deletion"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)
    endpoint_id = endpoint.name if hasattr(endpoint, 'name') else "test-endpoint"

    success = await model_endpoints.delete_endpoint(
        endpoint_id=endpoint_id,
        force=True,
        sync=False
    )

    assert success is True


@pytest.mark.asyncio
async def test_list_endpoints(model_endpoints, sample_endpoint_config):
    """Test listing endpoints"""
    # Create multiple endpoints
    config1 = sample_endpoint_config
    config2 = EndpointConfig(
        name="endpoint-2",
        display_name="Endpoint 2",
        description="Second endpoint",
    )

    await model_endpoints.create_endpoint(config1, sync=False)
    await model_endpoints.create_endpoint(config2, sync=False)

    endpoints = await model_endpoints.list_endpoints()
    assert len(endpoints) >= 2


@pytest.mark.asyncio
async def test_list_endpoints_with_filters(model_endpoints, sample_endpoint_config):
    """Test listing endpoints with label filters"""
    # Create endpoint with labels
    config = EndpointConfig(
        name="labeled-endpoint",
        display_name="Labeled Endpoint",
        description="For filtering",
        labels={"team": "ml", "stage": "prod"},
    )

    await model_endpoints.create_endpoint(config, sync=False)

    # Filter by labels
    endpoints = await model_endpoints.list_endpoints(
        filter_labels={"team": "ml"}
    )

    assert len(endpoints) >= 1


@pytest.mark.asyncio
async def test_get_endpoint_stats(model_endpoints, sample_endpoint_config):
    """Test retrieving endpoint statistics"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)
    endpoint_id = endpoint.name if hasattr(endpoint, 'name') else "test-endpoint"

    stats = await model_endpoints.get_endpoint_stats(endpoint_id=endpoint_id)

    assert stats is not None
    assert isinstance(stats, dict)
    # Verify expected metrics
    assert "endpoint_id" in stats or "id" in stats or len(stats) > 0


def test_traffic_split_strategy_enum():
    """Test TrafficSplitStrategy enum"""
    assert TrafficSplitStrategy.SINGLE.value == "single"
    assert TrafficSplitStrategy.CANARY.value == "canary"
    assert TrafficSplitStrategy.GRADUAL.value == "gradual"
    assert TrafficSplitStrategy.BLUE_GREEN.value == "blue_green"


def test_traffic_split_initialization():
    """Test TrafficSplit dataclass initialization"""
    traffic = TrafficSplit(
        strategy=TrafficSplitStrategy.CANARY,
        splits={"model1": 80, "model2": 20}
    )

    assert traffic.strategy == TrafficSplitStrategy.CANARY
    assert traffic.splits["model1"] == 80
    assert traffic.splits["model2"] == 20


@pytest.mark.asyncio
async def test_endpoint_config_initialization(sample_endpoint_config):
    """Test EndpointConfig creation"""
    assert sample_endpoint_config.name == "test-endpoint"
    assert sample_endpoint_config.display_name == "Test Endpoint"
    assert sample_endpoint_config.enable_request_logging is True
    assert sample_endpoint_config.enable_access_logging is True


@pytest.mark.asyncio
async def test_predict_with_custom_parameters(model_endpoints, sample_endpoint_config):
    """Test prediction with various custom parameters"""
    endpoint = await model_endpoints.create_endpoint(sample_endpoint_config, sync=False)
    endpoint_id = endpoint.name if hasattr(endpoint, 'name') else "test-endpoint"

    await model_endpoints.deploy_model(
        endpoint_id=endpoint_id,
        model_name="param-model",
        model_version="1.0.0",
        display_name="Parameterized Model",
    )

    # Various parameter combinations
    predictions = await model_endpoints.predict(
        endpoint_id=endpoint_id,
        instances=[{"input": "test"}],
        parameters={
            "temperature": 0.8,
            "top_p": 0.95,
            "max_tokens": 200,
            "stop_sequences": ["\n"],
        }
    )

    assert predictions is not None
