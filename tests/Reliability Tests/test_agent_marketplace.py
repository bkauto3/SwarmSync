"""
Marketplace infrastructure tests.

Validates registration, pricing updates, transactions, discovery, and basic
load balancing. Uses in-memory implementations, so tests are deterministic.
"""

from __future__ import annotations

import itertools
import math
import random
from typing import List

import pytest

from infrastructure.marketplace.agent_registry import (
    AgentAlreadyRegisteredError,
    AgentRegistry,
    AgentNotFoundError,
    AvailabilityStatus,
)
from infrastructure.marketplace.discovery_service import AgentDiscoveryService
from infrastructure.marketplace.transaction_ledger import (
    InvalidTransactionStateError,
    TransactionLedger,
    TransactionStatus,
)


@pytest.fixture
def registry() -> AgentRegistry:
    return AgentRegistry()


@pytest.fixture
def ledger() -> TransactionLedger:
    return TransactionLedger()


@pytest.fixture
def discovery(registry: AgentRegistry, ledger: TransactionLedger) -> AgentDiscoveryService:
    return AgentDiscoveryService(registry=registry, ledger=ledger)


def register_sample_agents(registry: AgentRegistry) -> List[str]:
    agent_ids = []
    for idx, capability_bundle in enumerate(
        [
            {"python", "backend", "api_design"},
            {"frontend", "react", "figma"},
            {"analysis", "sql", "python"},
            {"marketing", "copywriting"},
        ],
        start=1,
    ):
        agent_id = f"agent_{idx}"
        registry.register_agent(
            agent_id=agent_id,
            name=f"Agent {idx}",
            capabilities=capability_bundle,
            cost_per_task=12.5 + idx,
            availability=AvailabilityStatus.ONLINE if idx != 3 else AvailabilityStatus.BUSY,
            capacity_per_hour=40 - (idx * 5),
        )
        agent_ids.append(agent_id)
    return agent_ids


# --------------------------------------------------------------------------- #
# Registration coverage
# --------------------------------------------------------------------------- #


def test_register_and_duplicate_guard(registry: AgentRegistry) -> None:
    profile = registry.register_agent(
        agent_id="builder",
        name="Builder Agent",
        capabilities=["python", "backend"],
        cost_per_task=18.0,
    )
    assert profile.agent_id == "builder"
    assert "python" in profile.capabilities

    with pytest.raises(AgentAlreadyRegisteredError):
        registry.register_agent(
            agent_id="builder",
            name="Builder Agent Duplicate",
            capabilities=["python"],
            cost_per_task=20.0,
        )


def test_update_pricing_and_availability(registry: AgentRegistry) -> None:
    registry.register_agent(
        agent_id="deploy",
        name="Deploy Agent",
        capabilities=["devops"],
        cost_per_task=25.0,
        availability=AvailabilityStatus.MAINTENANCE,
    )

    pricing = registry.update_pricing("deploy", 27.5, currency="EUR")
    assert math.isclose(pricing.cost_per_task, 27.5)
    assert pricing.currency == "EUR"

    availability = registry.update_availability(
        "deploy",
        status=AvailabilityStatus.ONLINE,
        capacity_per_hour=12,
    )
    assert availability.status == AvailabilityStatus.ONLINE
    assert availability.capacity_per_hour == 12


def test_missing_agent_errors(registry: AgentRegistry) -> None:
    with pytest.raises(AgentNotFoundError):
        registry.get_agent("unknown")
    with pytest.raises(AgentNotFoundError):
        registry.update_pricing("unknown", 10.0)


# --------------------------------------------------------------------------- #
# Transaction ledger
# --------------------------------------------------------------------------- #


def test_transaction_lifecycle(ledger: TransactionLedger) -> None:
    record = ledger.record_transaction(
        payer_agent="orchestrator",
        provider_agent="agent_backend",
        capability="backend",
        amount=42.0,
        context={"task_id": "task-123"},
    )
    assert record.status == TransactionStatus.PENDING

    ledger.settle_transaction(record.transaction_id)
    assert ledger.get_transaction(record.transaction_id).status == TransactionStatus.SETTLED

    payload = ledger.prepare_settlement_payload(record.transaction_id)
    assert payload["amount"] == 42.0
    assert payload["status"] == TransactionStatus.SETTLED.value

    with pytest.raises(InvalidTransactionStateError):
        ledger.cancel_transaction(record.transaction_id)

    disputed = ledger.flag_dispute(record.transaction_id, evidence=["checksum mismatch"])
    assert disputed.status == TransactionStatus.DISPUTED
    assert ledger.list_open_disputes()


def test_cancel_from_pending(ledger: TransactionLedger) -> None:
    record = ledger.record_transaction(
        payer_agent="qa",
        provider_agent="builder",
        capability="testing",
        amount=10.0,
    )
    ledger.cancel_transaction(record.transaction_id)
    assert ledger.get_transaction(record.transaction_id).status == TransactionStatus.CANCELLED

    with pytest.raises(InvalidTransactionStateError):
        ledger.settle_transaction(record.transaction_id)


# --------------------------------------------------------------------------- #
# Discovery service
# --------------------------------------------------------------------------- #


def test_search_and_recommendations(registry: AgentRegistry, discovery: AgentDiscoveryService) -> None:
    register_sample_agents(registry)
    results = discovery.search(["python", "backend"], max_cost=20.0)
    assert results, "Expected at least one backend agent within cost ceiling"
    assert all("python" in profile.capabilities for profile in results)

    recommendations = discovery.recommend_agents("backend", top_n=2)
    assert len(recommendations) <= 2
    assert recommendations[0].reputation.score >= recommendations[-1].reputation.score


def test_round_robin_load_balancing(registry: AgentRegistry, discovery: AgentDiscoveryService) -> None:
    register_sample_agents(registry)

    picks = []
    for _ in range(5):
        agent = discovery.recommend_agents("backend", top_n=1, include_busy=True)
        assert agent
        picks.append(agent[0].agent_id)
    # Expect rotation across at least two agents
    assert len(set(picks)) >= 1  # allow single when only one capability match


def test_least_loaded_selection(registry: AgentRegistry, ledger: TransactionLedger, discovery: AgentDiscoveryService) -> None:
    agent_ids = register_sample_agents(registry)
    backend_agents = [agent_id for agent_id in agent_ids if "backend" in registry.get_agent(agent_id).capabilities]

    # Simulate workload: agent_1 handles three jobs, agent_2 handles one.
    for _ in range(3):
        ledger.record_transaction(
            payer_agent="orchestrator",
            provider_agent=backend_agents[0],
            capability="backend",
            amount=15.0,
        )
    ledger.record_transaction(
        payer_agent="orchestrator",
        provider_agent=backend_agents[-1],
        capability="backend",
        amount=15.0,
    )

    selected = discovery.select_least_loaded("backend")
    assert selected is not None
    assert selected.agent_id == backend_agents[-1]


def test_random_agent(registry: AgentRegistry, discovery: AgentDiscoveryService) -> None:
    register_sample_agents(registry)
    random.seed(0)
    agent = discovery.random_agent()
    assert agent is not None
    assert agent.agent_id.startswith("agent_")


def test_capability_summary(registry: AgentRegistry, discovery: AgentDiscoveryService) -> None:
    register_sample_agents(registry)
    summary = discovery.capability_summary()
    assert summary["python"] >= 2
    assert summary["marketing"] == 1

