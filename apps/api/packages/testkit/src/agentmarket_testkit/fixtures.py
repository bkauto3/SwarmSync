from __future__ import annotations

import os
from typing import AsyncIterator, Awaitable, Callable, Dict

import asyncpg
import pytest
import pytest_asyncio

from .sdk import AgentMarketSDK
from .utils import new_uuid, unique_agent_name, unique_email

DEFAULT_PASSWORD = "Testing123!"


def _require_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for integration tests")
    return database_url


async def _ensure_organization_record(slug: str, name: str) -> Dict[str, str]:
    conn = await asyncpg.connect(dsn=_require_database_url())
    try:
        record = await conn.fetchrow(
            'INSERT INTO "Organization"(name, slug) VALUES($1, $2) '
            'ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id, name, slug',
            name,
            slug,
        )
    finally:
        await conn.close()

    if not record:
        raise RuntimeError("Failed to ensure organization record")

    return {
        "id": record["id"],
        "name": record["name"],
        "slug": record["slug"],
    }


async def _persist_user_in_db(
    user_id: str,
    email: str,
    display_name: str,
    organization_id: str,
    role: str = "MEMBER",
) -> None:
    conn = await asyncpg.connect(dsn=_require_database_url())
    try:
        await conn.execute(
            'INSERT INTO "User"(id, email, "displayName", password, "updatedAt") VALUES($1, $2, $3, $4, NOW()) '
            'ON CONFLICT (id) DO NOTHING',
            user_id,
            email,
            display_name,
            "placeholder-hash",
        )
        await conn.execute(
            'INSERT INTO "OrganizationMembership"("userId", "organizationId", role) VALUES($1, $2, $3) '
            'ON CONFLICT ("userId", "organizationId") DO UPDATE SET role = EXCLUDED.role',
            user_id,
            organization_id,
            role,
        )
    finally:
        await conn.close()


async def _assign_agent_to_organization(agent_id: str, organization_id: str) -> None:
    conn = await asyncpg.connect(dsn=_require_database_url())
    try:
        await conn.execute(
            'UPDATE "Agent" SET "organizationId" = $1 WHERE id = $2',
            organization_id,
            agent_id,
        )
    finally:
        await conn.close()


async def _assign_wallet_to_organization(wallet_id: str, organization_id: str) -> None:
    conn = await asyncpg.connect(dsn=_require_database_url())
    try:
        await conn.execute(
            'UPDATE "Wallet" SET "organizationId" = $1 WHERE id = $2',
            organization_id,
            wallet_id,
        )
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def agentmarket_sdk() -> AsyncIterator[AgentMarketSDK]:
    sdk = AgentMarketSDK()
    try:
        yield sdk
    finally:
        await sdk.close()


@pytest_asyncio.fixture
async def organization() -> Dict[str, str]:
    slug = os.getenv("DEFAULT_ORG_SLUG", "genesis")
    name = os.getenv("DEFAULT_ORG_NAME", "Genesis QA Org")
    return await _ensure_organization_record(slug, name)


@pytest_asyncio.fixture
async def registered_user(agentmarket_sdk: AgentMarketSDK, organization: Dict[str, str]) -> Dict[str, str]:
    email = unique_email()
    display_name = f"QA Creator {email.split('@')[0][-4:]}"
    response = await agentmarket_sdk.register_user(
        email=email,
        display_name=display_name,
        password=DEFAULT_PASSWORD,
    )
    user = response["user"]
    await _persist_user_in_db(user["id"], user["email"], user["displayName"], organization["id"], "OWNER")
    return {
        "id": user["id"],
        "email": user["email"],
        "displayName": user["displayName"],
        "password": DEFAULT_PASSWORD,
        "organizationId": organization["id"],
    }


@pytest_asyncio.fixture
async def reviewer_user(agentmarket_sdk: AgentMarketSDK, organization: Dict[str, str]) -> Dict[str, str]:
    email = unique_email("reviewers.test")
    display_name = f"QA Reviewer {email.split('@')[0][-4:]}"
    response = await agentmarket_sdk.register_user(
        email=email,
        display_name=display_name,
        password=DEFAULT_PASSWORD,
    )
    user = response["user"]
    await _persist_user_in_db(user["id"], user["email"], user["displayName"], organization["id"], "ADMIN")
    return {
        "id": user["id"],
        "email": user["email"],
        "displayName": user["displayName"],
        "password": DEFAULT_PASSWORD,
        "organizationId": organization["id"],
    }


@pytest.fixture
def agent_payload_factory() -> Callable[..., Dict[str, object]]:
    def _factory(
        *,
        creator_id: str,
        name_prefix: str = "QA Agent",
        categories: list[str] | None = None,
        tags: list[str] | None = None,
        pricing_model: str = "subscription",
        visibility: str = "PUBLIC",
    ) -> Dict[str, object]:
        return {
            "name": unique_agent_name(name_prefix),
            "description": "Autogenerated agent for lifecycle tests validating CRUD and execution paths.",
            "categories": categories or ["qa", "integration"],
            "tags": tags or ["python", "autogen"],
            "pricingModel": pricing_model,
            "visibility": visibility,
            "creatorId": creator_id,
        }

    return _factory


@pytest_asyncio.fixture
def approved_agent_factory(
    agentmarket_sdk: AgentMarketSDK,
    submission_payload: Dict[str, object],
    review_payload: Dict[str, object],
    organization: Dict[str, str],
    agent_payload_factory: Callable[..., Dict[str, object]],
) -> Callable[..., Awaitable[Dict[str, object]]]:
    async def _factory(
        *,
        creator_id: str,
        name_prefix: str = "QA Agent",
        categories: list[str] | None = None,
        tags: list[str] | None = None,
        pricing_model: str = "subscription",
    ) -> Dict[str, object]:
        payload = agent_payload_factory(
            creator_id=creator_id,
            name_prefix=name_prefix,
            categories=categories,
            tags=tags,
            pricing_model=pricing_model,
        )
        agent = await agentmarket_sdk.create_agent(payload)
        await _assign_agent_to_organization(agent["id"], organization["id"])
        await agentmarket_sdk.submit_agent(agent["id"], submission_payload)
        await agentmarket_sdk.review_agent(agent["id"], review_payload)
        return await agentmarket_sdk.get_agent(agent["id"])

    return _factory


@pytest.fixture
def wallet_linker(organization: Dict[str, str]) -> Callable[[str], Awaitable[None]]:
    async def _link(wallet_id: str) -> None:
        await _assign_wallet_to_organization(wallet_id, organization["id"])

    return _link


@pytest.fixture
def sample_agent_payload(registered_user: Dict[str, str]) -> Dict[str, object]:
    return {
        "name": unique_agent_name(),
        "description": "Autogenerated agent for lifecycle tests validating CRUD and execution paths.",
        "categories": ["qa", "integration"],
        "tags": ["python", "autogen"],
        "pricingModel": "subscription",
        "visibility": "PUBLIC",
        "creatorId": registered_user["id"],
    }


@pytest.fixture
def execution_payload(reviewer_user: Dict[str, str]) -> Dict[str, object]:
    return {
        "initiatorId": reviewer_user["id"],
        "input": '{"task": "demo run"}',
        "jobReference": f"job-{new_uuid()}",
        "budget": 12.34,
    }


@pytest.fixture
def review_payload(reviewer_user: Dict[str, str]) -> Dict[str, object]:
    return {
        "reviewerId": reviewer_user["id"],
        "reviewStatus": "APPROVED",
        "targetStatus": "APPROVED",
        "notes": "Looks ready for production.",
    }


@pytest.fixture
def submission_payload(reviewer_user: Dict[str, str]) -> Dict[str, object]:
    return {
        "reviewerId": reviewer_user["id"],
        "notes": "Please validate business logic.",
    }
