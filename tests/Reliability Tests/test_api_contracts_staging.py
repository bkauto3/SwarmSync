"""Integration tests for the API contracts middleware and validator."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pydantic import BaseModel
except ModuleNotFoundError:  # pragma: no cover - guard for environments without FastAPI
    pytest.skip("FastAPI not installed; skipping API contracts integration tests", allow_module_level=True)

from api.middleware.openapi_middleware import OpenAPIValidationMiddleware


class AskRequest(BaseModel):
    role: str
    prompt: str
    temperature: float | None = None
    max_output_tokens: int | None = None
    top_p: float | None = None
    top_k: int | None = None


def create_app(*, rate_limit: int = 100, rate_window: int = 60) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        OpenAPIValidationMiddleware,
        spec_directory="api/schemas",
        enable_validation=True,
        enable_idempotency=True,
        enable_rate_limiting=True,
        rate_limit=rate_limit,
        rate_window=rate_window,
    )

    @app.post("/agents/ask")
    def ask(body: AskRequest) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        request_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        return {
            "data": {
                "role": body.role,
                "answer": f"Generated answer for {body.role}",
                "model_used": "tuned",
                "confidence": 0.92,
            },
            "metadata": {
                "request_id": request_id,
                "timestamp": now.isoformat(),
                "execution_time_ms": 123,
                "tokens_used": {
                    "input_tokens": 12,
                    "output_tokens": 48,
                    "total_tokens": 60,
                },
                "fallback_used": False,
                "trace_id": trace_id,
            },
        }

    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture()
def limited_client() -> TestClient:
    return TestClient(create_app(rate_limit=2, rate_window=60))


def test_valid_request_returns_200(client: TestClient) -> None:
    payload = {"role": "qa", "prompt": "Write unit tests"}
    response = client.post("/agents/ask", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["role"] == "qa"
    assert data["data"]["model_used"] == "tuned"
    assert response.headers["X-Schema-Version"].startswith("v")


def test_missing_prompt_triggers_validation_error(client: TestClient) -> None:
    response = client.post("/agents/ask", json={"role": "qa"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_role_rejected(client: TestClient) -> None:
    response = client.post("/agents/ask", json={"role": "invalid", "prompt": "hi"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_idempotency_cache_hits(client: TestClient) -> None:
    payload = {"role": "qa", "prompt": "Check caching"}
    key = str(uuid.uuid4())

    first = client.post("/agents/ask", json=payload, headers={"X-Idempotency-Key": key})
    assert first.status_code == 200

    second = client.post("/agents/ask", json=payload, headers={"X-Idempotency-Key": key})
    assert second.status_code == 200
    assert second.headers.get("X-Idempotency-Cached") == "true"
    assert second.json() == first.json()


def test_idempotency_conflict_detected(client: TestClient) -> None:
    key = str(uuid.uuid4())
    client.post(
        "/agents/ask",
        json={"role": "qa", "prompt": "one"},
        headers={"X-Idempotency-Key": key},
    )

    conflict = client.post(
        "/agents/ask",
        json={"role": "qa", "prompt": "two"},
        headers={"X-Idempotency-Key": key},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_rate_limit_exceeded_returns_429(limited_client: TestClient) -> None:
    payload = {"role": "qa", "prompt": "check rate limit"}
    for _ in range(2):
        assert limited_client.post("/agents/ask", json=payload).status_code == 200

    blocked = limited_client.post("/agents/ask", json=payload)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_response_headers_include_rate_limit(client: TestClient) -> None:
    response = client.post("/agents/ask", json={"role": "qa", "prompt": "headers"})
    assert response.status_code == 200
    headers = response.headers
    assert "X-RateLimit-Limit" in headers
    assert "X-RateLimit-Remaining" in headers
    assert "X-RateLimit-Reset" in headers


pytestmark = [pytest.mark.staging]
