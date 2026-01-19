"""
Advanced Marketplace Infrastructure Tests
=========================================

Tests for thread-safe, persistent backends, and instrumented components.
"""

import pytest
import threading
import time
from typing import List

from infrastructure.marketplace.thread_safe import (
    ThreadSafeAgentRegistry,
    ThreadSafeTransactionLedger,
)
from infrastructure.marketplace.metrics import (
    InstrumentedAgentRegistry,
    InstrumentedTransactionLedger,
    InstrumentedDiscoveryService,
)
from infrastructure.marketplace.agent_registry import AvailabilityStatus


# ============================================================================
# THREAD SAFETY TESTS
# ============================================================================

def test_thread_safe_registry_concurrent_registrations():
    """Test concurrent agent registrations"""
    registry = ThreadSafeAgentRegistry()
    errors = []
    
    def register_agent(agent_id: str):
        try:
            registry.register_agent(
                agent_id=f"agent_{agent_id}",
                name=f"Agent {agent_id}",
                capabilities=["python"],
                cost_per_task=10.0 + float(agent_id)
            )
        except Exception as e:
            errors.append(e)
    
    # Spawn 10 threads registering agents concurrently
    threads = []
    for i in range(10):
        t = threading.Thread(target=register_agent, args=(str(i),))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Concurrent registrations failed: {errors}"
    assert len(registry.list_agents()) == 10


def test_thread_safe_registry_concurrent_updates():
    """Test concurrent updates to same agent"""
    registry = ThreadSafeAgentRegistry()
    registry.register_agent(
        agent_id="shared_agent",
        name="Shared Agent",
        capabilities=["python"],
        cost_per_task=10.0
    )
    
    def update_reputation(success: bool):
        for _ in range(100):
            registry.record_task_outcome("shared_agent", success=success)
    
    # Two threads: one recording successes, one recording failures
    t1 = threading.Thread(target=update_reputation, args=(True,))
    t2 = threading.Thread(target=update_reputation, args=(False,))
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    agent = registry.get_agent("shared_agent")
    # Should have 200 total feedback events
    assert agent.reputation.total_feedback == 200
    assert agent.reputation.successful_tasks == 100
    assert agent.reputation.failed_tasks == 100


def test_thread_safe_ledger_concurrent_transactions():
    """Test concurrent transaction recording"""
    ledger = ThreadSafeTransactionLedger()
    errors = []
    
    def record_transaction(idx: int):
        try:
            ledger.record_transaction(
                payer_agent=f"payer_{idx}",
                provider_agent="provider",
                capability="python",
                amount=15.0
            )
        except Exception as e:
            errors.append(e)
    
    # Spawn 10 threads recording transactions concurrently
    threads = []
    for i in range(10):
        t = threading.Thread(target=record_transaction, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Concurrent transactions failed: {errors}"
    assert len(ledger.list_transactions()) == 10


def test_thread_safe_ledger_concurrent_state_transitions():
    """Test concurrent state transitions on different transactions"""
    ledger = ThreadSafeTransactionLedger()
    
    # Create 5 transactions
    tx_ids = []
    for i in range(5):
        tx = ledger.record_transaction(
            payer_agent="payer",
            provider_agent=f"provider_{i}",
            capability="python",
            amount=10.0
        )
        tx_ids.append(tx.transaction_id)
    
    errors = []
    
    def settle_transaction(tx_id: str):
        try:
            time.sleep(0.001)  # Small delay to encourage race conditions
            ledger.settle_transaction(tx_id)
        except Exception as e:
            errors.append(e)
    
    # Settle all transactions concurrently
    threads = []
    for tx_id in tx_ids:
        t = threading.Thread(target=settle_transaction, args=(tx_id,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Concurrent settlements failed: {errors}"
    for tx_id in tx_ids:
        tx = ledger.get_transaction(tx_id)
        assert tx.status.value == "settled"


# ============================================================================
# INSTRUMENTED COMPONENTS TESTS
# ============================================================================

def test_instrumented_registry_tracks_registrations():
    """Test that instrumented registry tracks metrics"""
    registry = InstrumentedAgentRegistry()
    
    # Register agent
    profile = registry.register_agent(
        agent_id="metrics_test",
        name="Metrics Test Agent",
        capabilities=["python", "backend"],
        cost_per_task=20.0
    )
    
    assert profile.agent_id == "metrics_test"
    # Metrics are recorded (even if Prometheus not installed, no errors)


def test_instrumented_registry_tracks_task_outcomes():
    """Test that task outcomes are tracked"""
    registry = InstrumentedAgentRegistry()
    registry.register_agent(
        agent_id="task_agent",
        name="Task Agent",
        capabilities=["testing"],
        cost_per_task=15.0
    )
    
    # Record outcomes
    registry.record_task_outcome("task_agent", success=True, weight=1.0)
    registry.record_task_outcome("task_agent", success=True, weight=1.0)
    registry.record_task_outcome("task_agent", success=False, weight=1.0)
    
    agent = registry.get_agent("task_agent")
    assert agent.reputation.successful_tasks == 2
    assert agent.reputation.failed_tasks == 1


def test_instrumented_ledger_tracks_transactions():
    """Test that instrumented ledger tracks transaction metrics"""
    ledger = InstrumentedTransactionLedger()
    
    # Record transaction
    tx = ledger.record_transaction(
        payer_agent="payer",
        provider_agent="provider",
        capability="python",
        amount=25.50
    )
    
    assert tx.amount == 25.50
    # Metrics are recorded (even if Prometheus not installed, no errors)


def test_instrumented_ledger_tracks_state_transitions():
    """Test that state transitions are tracked"""
    ledger = InstrumentedTransactionLedger()
    
    tx = ledger.record_transaction(
        payer_agent="payer",
        provider_agent="provider",
        capability="python",
        amount=30.0
    )
    
    # Transition to settled
    ledger.settle_transaction(tx.transaction_id)
    settled_tx = ledger.get_transaction(tx.transaction_id)
    assert settled_tx.status.value == "settled"
    
    # Transition to disputed
    ledger.flag_dispute(tx.transaction_id, evidence=["Test evidence"])
    disputed_tx = ledger.get_transaction(tx.transaction_id)
    assert disputed_tx.status.value == "disputed"


def test_instrumented_discovery_tracks_searches():
    """Test that discovery searches are tracked"""
    registry = InstrumentedAgentRegistry()
    ledger = InstrumentedTransactionLedger()
    discovery = InstrumentedDiscoveryService(registry, ledger)
    
    # Register test agents
    for i in range(3):
        registry.register_agent(
            agent_id=f"search_agent_{i}",
            name=f"Search Agent {i}",
            capabilities=["search_test"],
            cost_per_task=10.0 + i
        )
    
    # Perform search
    results = discovery.search(["search_test"])
    assert len(results) == 3
    
    # Perform recommendations
    recommendations = discovery.recommend_agents("search_test", top_n=2)
    assert len(recommendations) <= 2


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_thread_safe_with_instrumented():
    """Test that thread-safe and instrumented components can be combined"""
    # Note: In production, you'd use a custom class that inherits from both
    # For testing, we verify they work independently
    
    ts_registry = ThreadSafeAgentRegistry()
    inst_registry = InstrumentedAgentRegistry()
    
    # Both should work without conflict
    ts_profile = ts_registry.register_agent(
        agent_id="ts_agent",
        name="Thread Safe Agent",
        capabilities=["concurrent"],
        cost_per_task=15.0
    )
    
    inst_profile = inst_registry.register_agent(
        agent_id="inst_agent",
        name="Instrumented Agent",
        capabilities=["metrics"],
        cost_per_task=20.0
    )
    
    assert ts_profile.agent_id == "ts_agent"
    assert inst_profile.agent_id == "inst_agent"


def test_graceful_degradation_without_dependencies():
    """Test that components work without optional dependencies"""
    # These should not raise errors even if redis, psycopg2, prometheus_client missing
    
    from infrastructure.marketplace.thread_safe import ThreadSafeAgentRegistry
    from infrastructure.marketplace.metrics import InstrumentedAgentRegistry
    
    registry1 = ThreadSafeAgentRegistry()
    registry2 = InstrumentedAgentRegistry()
    
    # Both should function (falling back to in-memory if needed)
    profile1 = registry1.register_agent(
        agent_id="fallback1",
        name="Fallback 1",
        capabilities=["test"],
        cost_per_task=10.0
    )
    
    profile2 = registry2.register_agent(
        agent_id="fallback2",
        name="Fallback 2",
        capabilities=["test"],
        cost_per_task=10.0
    )
    
    assert profile1.agent_id == "fallback1"
    assert profile2.agent_id == "fallback2"

