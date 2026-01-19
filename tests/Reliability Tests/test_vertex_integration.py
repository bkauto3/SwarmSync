"""
Vertex AI integration tests (mock mode).

These tests exercise the orchestration logic provided by the deployment manager
and router without requiring access to Google Cloud.  The underlying modules
fall back to in-memory simulations when ``google-cloud-aiplatform`` is not
installed, which allows us to verify promotion/rollback behaviour and routing
decisions deterministically.
"""

from __future__ import annotations

import pytest

from infrastructure.vertex_deployment import VertexDeploymentManager
from infrastructure.vertex_router import VertexModelRouter

PROJECT_ID = "mock-project"
LOCATION = "us-central1"


@pytest.fixture
def deployment_manager() -> VertexDeploymentManager:
    return VertexDeploymentManager(
        project_id=PROJECT_ID,
        location=LOCATION,
        enable_vertex=False,  # Force mock mode for tests
    )


def test_upload_and_deploy_flow(deployment_manager: VertexDeploymentManager) -> None:
    """Uploading multiple models and deploying them should update traffic splits."""
    model_a = deployment_manager.upload_model(
        display_name="Mistral QA v1",
        artifact_uri="gs://mock-bucket/mistral-qa-v1",
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/tensorflow:latest",
    )
    model_b = deployment_manager.upload_model(
        display_name="Mistral QA v2",
        artifact_uri="gs://mock-bucket/mistral-qa-v2",
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/tensorflow:latest",
    )

    endpoint = deployment_manager.create_endpoint("qa-endpoint")
    deployment_manager.deploy_model(endpoint, model_a, traffic_percentage=80)
    deployment_manager.deploy_model(endpoint, model_b, traffic_percentage=20)

    endpoints = deployment_manager.list_endpoints()
    assert len(endpoints) == 1
    traffic = endpoints[0].traffic_split
    # Percentages should be normalised to 100
    assert traffic[model_a] + traffic[model_b] == 100


def test_promote_and_rollback(deployment_manager: VertexDeploymentManager) -> None:
    """Promoting a model should push it on history stack, rollback should restore previous."""
    model_v1 = deployment_manager.upload_model(
        display_name="Analyst v1",
        artifact_uri="gs://mock/analyst-v1",
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/tensorflow:latest",
    )
    model_v2 = deployment_manager.upload_model(
        display_name="Analyst v2",
        artifact_uri="gs://mock/analyst-v2",
        serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/tensorflow:latest",
    )
    endpoint = deployment_manager.create_endpoint("analyst-endpoint")
    deployment_manager.promote_model(endpoint, model_v1)
    deployment_manager.promote_model(endpoint, model_v2)

    endpoints = deployment_manager.list_endpoints()
    assert endpoints[0].version_history[-1] == model_v2

    active_after_rollback = deployment_manager.rollback(endpoint)
    assert active_after_rollback == model_v1
    endpoints = deployment_manager.list_endpoints()
    assert endpoints[0].traffic_split == {model_v1: 100}


def test_router_round_robin() -> None:
    """Router should rotate through registered endpoints based on weights."""
    router = VertexModelRouter(project_id=PROJECT_ID, location=LOCATION, enable_vertex=False)
    router.register_endpoint("qa", "endpoint-1", weight=1)
    router.register_endpoint("qa", "endpoint-2", weight=2)

    # Access protected helper for deterministic assertions
    selected = [router._select_endpoint("qa") for _ in range(6)]  # type: ignore[attr-defined]
    assert selected.count("endpoint-1") == 2
    assert selected.count("endpoint-2") == 4


def test_router_fallback_to_base_model() -> None:
    """When no endpoints are registered the router returns an empty string (base model call skipped)."""
    router = VertexModelRouter(project_id=PROJECT_ID, location=LOCATION, enable_vertex=False)
    output = router.route(role="qa", prompt="Hello?")
    assert isinstance(output, str)
