from __future__ import annotations

import os
from typing import Any

import httpx


class AgentMarketSDK:
    """
    Very small async wrapper around the AgentMarket REST API.
    """

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self._base_url = base_url or os.getenv("AGENT_MARKET_API_URL", "http://localhost:4000")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AgentMarketSDK":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:  # noqa: ANN401
        await self.close()

    async def register_user(self, *, email: str, display_name: str, password: str) -> dict[str, Any]:
        response = await self._client.post(
            "/auth/register",
            json={
                "email": email,
                "displayName": display_name,
                "password": password,
            },
        )
        response.raise_for_status()
        return response.json()

    async def login(self, *, email: str, password: str) -> dict[str, Any]:
        response = await self._client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
            },
        )
        response.raise_for_status()
        return response.json()

    async def create_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post("/agents", json=payload)
        if not response.is_success:
            error_text = ""
            try:
                error_text = response.text
                try:
                    error_json = response.json()
                    if isinstance(error_json, dict) and "message" in error_json:
                        error_text = f"{error_text}\nMessage: {error_json['message']}"
                    if isinstance(error_json, list):
                        error_text = f"{error_text}\nValidation errors: {error_json}"
                except:
                    pass
            except:
                error_text = "Could not read error response"
            raise httpx.HTTPStatusError(
                f"Client error '{response.status_code} {response.reason_phrase}' for url '{response.url}'\n{error_text}",
                request=response.request,
                response=response,
            )
        return response.json()

    async def update_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.put(f"/agents/{agent_id}", json=payload)
        response.raise_for_status()
        return response.json()

    async def submit_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(f"/agents/{agent_id}/submit", json=payload)
        response.raise_for_status()
        return response.json()

    async def review_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(f"/agents/{agent_id}/review", json=payload)
        response.raise_for_status()
        return response.json()

    async def execute_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(f"/agents/{agent_id}/execute", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_agent(self, agent_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/agents/{agent_id}")
        response.raise_for_status()
        return response.json()

    async def list_agents(
        self,
        *,
        status: str | None = None,
        visibility: str | None = None,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if status:
            params["status"] = status
        if visibility:
            params["visibility"] = visibility
        if category:
            params["category"] = category
        if tag:
            params["tag"] = tag

        response = await self._client.get("/agents", params=params or None)
        response.raise_for_status()
        return response.json()

    async def ensure_user_wallet(self, user_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/wallets/user/{user_id}")
        response.raise_for_status()
        return response.json()

    async def ensure_agent_wallet(self, agent_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/wallets/agent/{agent_id}")
        response.raise_for_status()
        return response.json()

    async def fund_wallet(self, wallet_id: str, *, amount: float, reference: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"amount": amount}
        if reference:
            payload["reference"] = reference
        response = await self._client.post(f"/wallets/{wallet_id}/fund", json=payload)
        response.raise_for_status()
        return response.json()

    async def get_wallet(self, wallet_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/wallets/{wallet_id}")
        response.raise_for_status()
        return response.json()

    async def list_reviews(self, agent_id: str) -> list[dict[str, Any]]:
        response = await self._client.get(f"/agents/{agent_id}/reviews")
        response.raise_for_status()
        return response.json()

    async def list_executions(self, agent_id: str) -> list[dict[str, Any]]:
        response = await self._client.get(f"/agents/{agent_id}/executions")
        response.raise_for_status()
        return response.json()

    async def create_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post("/workflows", json=payload)
        response.raise_for_status()
        return response.json()

    async def list_workflows(self) -> list[dict[str, Any]]:
        response = await self._client.get("/workflows")
        response.raise_for_status()
        return response.json()

    async def run_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(f"/workflows/{workflow_id}/run", json=payload)
        response.raise_for_status()
        return response.json()

    async def list_workflow_runs(self, workflow_id: str) -> list[dict[str, Any]]:
        response = await self._client.get(f"/workflows/{workflow_id}/runs")
        response.raise_for_status()
        return response.json()

    async def list_billing_plans(self) -> list[dict[str, Any]]:
        response = await self._client.get("/billing/plans")
        response.raise_for_status()
        return response.json()

    async def get_billing_subscription(self) -> dict[str, Any] | None:
        response = await self._client.get("/billing/subscription")
        if response.status_code == 204:
            return None
        response.raise_for_status()
        return response.json()

    async def apply_billing_plan(self, plan_slug: str) -> dict[str, Any]:
        response = await self._client.post("/billing/subscription/apply", json={"planSlug": plan_slug})
        response.raise_for_status()
        return response.json()

    async def create_checkout_session(
        self,
        plan_slug: str,
        *,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"planSlug": plan_slug}
        if success_url:
            payload["successUrl"] = success_url
        if cancel_url:
            payload["cancelUrl"] = cancel_url
        response = await self._client.post("/billing/subscription/checkout", json=payload)
        response.raise_for_status()
        return response.json()
