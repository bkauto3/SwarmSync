"""
Test Suite for GenesisLangGraphStore

Tests the LangGraph Store API implementation with MongoDB backend,
covering CRUD operations, namespace isolation, cross-session persistence,
and performance requirements.

Test Coverage:
- Basic put/get/delete operations
- Namespace isolation
- Cross-session persistence
- Search functionality
- Error handling
- Performance (<100ms for put/get)
- Health checks

Run with: pytest tests/test_langgraph_store.py -v
"""

import pytest
import asyncio
from datetime import datetime
from infrastructure.langgraph_store import GenesisLangGraphStore, get_store


@pytest.fixture
async def store():
    """Create a test store instance."""
    test_store = GenesisLangGraphStore(
        mongodb_uri="mongodb://localhost:27017/",
        database_name="genesis_memory_test",
        timeout_ms=5000
    )

    yield test_store

    # Cleanup: clear all test data (use client.drop_database, not db.drop_database)
    await test_store.client.drop_database("genesis_memory_test")
    await test_store.close()


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return {
        "preferences": {
            "threshold": 0.95,
            "model": "gpt-4o",
            "temperature": 0.7
        },
        "metrics": {
            "accuracy": 0.89,
            "latency_ms": 245,
            "total_requests": 1523
        },
        "evolution_log": {
            "generation": 42,
            "trajectories": ["traj_1", "traj_2", "traj_3"],
            "best_score": 0.91
        }
    }


class TestBasicOperations:
    """Test basic CRUD operations."""

    @pytest.mark.asyncio
    async def test_put_and_get(self, store, sample_data):
        """Test storing and retrieving data."""
        namespace = ("agent", "qa_agent")
        key = "preferences"

        # Store data
        await store.put(namespace, key, sample_data["preferences"])

        # Retrieve data
        result = await store.get(namespace, key)

        assert result is not None
        assert result["threshold"] == 0.95
        assert result["model"] == "gpt-4o"
        assert result["temperature"] == 0.7

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, store):
        """Test retrieving a key that doesn't exist."""
        namespace = ("agent", "nonexistent_agent")
        key = "missing_key"

        result = await store.get(namespace, key)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, store, sample_data):
        """Test deleting an existing key."""
        namespace = ("agent", "qa_agent")
        key = "temp_config"

        # Store data
        await store.put(namespace, key, sample_data["preferences"])

        # Verify it exists
        result = await store.get(namespace, key)
        assert result is not None

        # Delete it
        deleted = await store.delete(namespace, key)
        assert deleted is True

        # Verify it's gone
        result = await store.get(namespace, key)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, store):
        """Test deleting a key that doesn't exist."""
        namespace = ("agent", "qa_agent")
        key = "never_existed"

        deleted = await store.delete(namespace, key)

        assert deleted is False

    @pytest.mark.asyncio
    async def test_update_existing_key(self, store):
        """Test updating an existing key."""
        namespace = ("agent", "qa_agent")
        key = "counter"

        # Store initial value
        await store.put(namespace, key, {"count": 1})

        # Update value
        await store.put(namespace, key, {"count": 2})

        # Verify updated value
        result = await store.get(namespace, key)
        assert result["count"] == 2


class TestNamespaceIsolation:
    """Test namespace isolation between agents."""

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, store, sample_data):
        """Test that different namespaces are isolated."""
        namespace_1 = ("agent", "qa_agent")
        namespace_2 = ("agent", "support_agent")
        key = "config"

        # Store different data in each namespace
        await store.put(namespace_1, key, {"agent": "qa", "threshold": 0.95})
        await store.put(namespace_2, key, {"agent": "support", "threshold": 0.85})

        # Verify each namespace has its own data
        result_1 = await store.get(namespace_1, key)
        result_2 = await store.get(namespace_2, key)

        assert result_1["agent"] == "qa"
        assert result_1["threshold"] == 0.95
        assert result_2["agent"] == "support"
        assert result_2["threshold"] == 0.85

    @pytest.mark.asyncio
    async def test_different_namespace_types(self, store):
        """Test different namespace types (agent, business, evolution, consensus)."""
        namespaces = [
            ("agent", "qa_agent"),
            ("business", "biz_123"),
            ("evolution", "gen_42"),
            ("consensus", "proc_001")
        ]

        # Store data in each namespace type
        for namespace in namespaces:
            await store.put(namespace, "test_key", {"namespace": namespace})

        # Verify each namespace has correct data
        for namespace in namespaces:
            result = await store.get(namespace, "test_key")
            assert result["namespace"] == list(namespace)


class TestSearchFunctionality:
    """Test search and listing operations."""

    @pytest.mark.asyncio
    async def test_search_all_in_namespace(self, store):
        """Test searching for all entries in a namespace."""
        namespace = ("agent", "qa_agent")

        # Store multiple entries
        await store.put(namespace, "config_1", {"value": 1})
        await store.put(namespace, "config_2", {"value": 2})
        await store.put(namespace, "config_3", {"value": 3})

        # Search all
        results = await store.search(namespace)

        assert len(results) == 3
        keys = [r["key"] for r in results]
        assert "config_1" in keys
        assert "config_2" in keys
        assert "config_3" in keys

    @pytest.mark.asyncio
    async def test_search_with_query(self, store):
        """Test searching with a MongoDB query."""
        namespace = ("agent", "qa_agent")

        # Store entries with different values
        await store.put(namespace, "high_threshold", {"threshold": 0.95})
        await store.put(namespace, "low_threshold", {"threshold": 0.75})

        # Search for high threshold entries
        results = await store.search(
            namespace,
            query={"value.threshold": {"$gt": 0.9}}
        )

        assert len(results) == 1
        assert results[0]["key"] == "high_threshold"

    @pytest.mark.asyncio
    async def test_search_with_limit(self, store):
        """Test search limit parameter."""
        namespace = ("agent", "qa_agent")

        # Store 10 entries
        for i in range(10):
            await store.put(namespace, f"entry_{i}", {"index": i})

        # Search with limit
        results = await store.search(namespace, limit=5)

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_list_namespaces(self, store):
        """Test listing all namespaces."""
        # Create entries in different namespaces
        namespaces = [
            ("agent", "qa_agent"),
            ("agent", "support_agent"),
            ("business", "biz_123"),
        ]

        for namespace in namespaces:
            await store.put(namespace, "key", {"data": "value"})

        # List all namespaces
        all_namespaces = await store.list_namespaces()

        assert len(all_namespaces) >= 3
        for namespace in namespaces:
            assert namespace in all_namespaces

    @pytest.mark.asyncio
    async def test_list_namespaces_with_prefix(self, store):
        """Test listing namespaces filtered by prefix."""
        # Create entries in different namespaces
        await store.put(("agent", "qa_agent"), "key", {"data": "value"})
        await store.put(("agent", "support_agent"), "key", {"data": "value"})
        await store.put(("business", "biz_123"), "key", {"data": "value"})

        # List only agent namespaces
        agent_namespaces = await store.list_namespaces(prefix=("agent",))

        assert len(agent_namespaces) >= 2
        assert all(ns[0] == "agent" for ns in agent_namespaces)

    @pytest.mark.asyncio
    async def test_clear_namespace(self, store):
        """Test clearing all entries in a namespace."""
        namespace = ("agent", "qa_agent")

        # Store multiple entries
        for i in range(5):
            await store.put(namespace, f"key_{i}", {"value": i})

        # Verify entries exist
        results = await store.search(namespace)
        assert len(results) == 5

        # Clear namespace
        deleted_count = await store.clear_namespace(namespace)
        assert deleted_count == 5

        # Verify namespace is empty
        results = await store.search(namespace)
        assert len(results) == 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_empty_namespace_error(self, store):
        """Test that empty namespace raises error."""
        with pytest.raises(ValueError):
            await store.put((), "key", {"data": "value"})

    @pytest.mark.asyncio
    async def test_empty_key_error(self, store):
        """Test that empty key raises error."""
        with pytest.raises(ValueError):
            await store.put(("agent", "qa"), "", {"data": "value"})

    @pytest.mark.asyncio
    async def test_timeout_handling(self, store):
        """Test timeout error handling."""
        # Create store with very short timeout
        short_timeout_store = GenesisLangGraphStore(
            database_name="genesis_memory_test",
            timeout_ms=1  # 1ms - will likely timeout
        )

        try:
            # This may or may not timeout depending on system speed
            # Just verify it doesn't crash
            await short_timeout_store.put(
                ("agent", "test"),
                "key",
                {"large_data": "x" * 10000}
            )
        except TimeoutError:
            # Expected for very short timeout
            pass
        finally:
            await short_timeout_store.close()


class TestPerformance:
    """Test performance requirements."""

    @pytest.mark.asyncio
    async def test_put_performance(self, store):
        """Test that put operation completes in <100ms."""
        namespace = ("agent", "qa_agent")
        key = "perf_test"
        data = {"test": "data"}

        start = datetime.now()
        await store.put(namespace, key, data)
        duration_ms = (datetime.now() - start).total_seconds() * 1000

        assert duration_ms < 100, f"Put took {duration_ms}ms (target: <100ms)"

    @pytest.mark.asyncio
    async def test_get_performance(self, store):
        """Test that get operation completes in <100ms."""
        namespace = ("agent", "qa_agent")
        key = "perf_test"
        data = {"test": "data"}

        # Store data first
        await store.put(namespace, key, data)

        # Measure get performance
        start = datetime.now()
        result = await store.get(namespace, key)
        duration_ms = (datetime.now() - start).total_seconds() * 1000

        assert result is not None
        assert duration_ms < 100, f"Get took {duration_ms}ms (target: <100ms)"

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, store):
        """Test concurrent put operations."""
        namespace = ("agent", "qa_agent")

        # Create 10 concurrent put operations
        tasks = []
        for i in range(10):
            tasks.append(
                store.put(namespace, f"concurrent_{i}", {"index": i})
            )

        # Execute all concurrently
        await asyncio.gather(*tasks)

        # Verify all were stored
        results = await store.search(namespace)
        assert len(results) == 10


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, store):
        """Test health check returns healthy status."""
        health = await store.health_check()

        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert health["database"] == "genesis_memory_test"
        assert isinstance(health["collections"], list)
        assert isinstance(health["size_mb"], (int, float))


class TestSingleton:
    """Test singleton pattern."""

    def test_singleton_instance(self):
        """Test that get_store returns singleton instance."""
        store1 = get_store()
        store2 = get_store()

        assert store1 is store2


class TestCrossSessionPersistence:
    """Test that data persists across store instances."""

    @pytest.mark.asyncio
    async def test_data_persists_across_instances(self):
        """Test that data stored in one instance is available in another."""
        namespace = ("agent", "persistence_test")
        key = "test_key"
        data = {"persisted": True, "value": 42}

        # Create first store instance and store data
        store1 = GenesisLangGraphStore(database_name="genesis_memory_test")
        await store1.put(namespace, key, data)
        await store1.close()

        # Create second store instance and retrieve data
        store2 = GenesisLangGraphStore(database_name="genesis_memory_test")
        result = await store2.get(namespace, key)

        assert result is not None
        assert result["persisted"] is True
        assert result["value"] == 42

        # Cleanup
        await store2.clear_namespace(namespace)
        await store2.close()


# Run tests with: pytest tests/test_langgraph_store.py -v
# Run with coverage: pytest tests/test_langgraph_store.py --cov=infrastructure.langgraph_store --cov-report=html
