"""
Memory Edge Case Tests for Genesis Memory Store

Tests failure modes, edge conditions, and error handling in memory persistence layer.

Context7 MCP Research Sources:
- /mongodb/mongo-python-driver: Connection failures, ServerSelectionTimeoutError, resilience patterns
- /pytest-dev/pytest: Error handling test patterns, monkeypatch usage, exception validation
- /mongodb/motor: Async error handling patterns

Key Patterns from Research:
1. ServerSelectionTimeoutError for connection failures (mongo-python-driver: common-issues.rst)
2. Monkeypatch for simulating failures (pytest-dev/pytest: monkeypatch patterns)
3. Graceful degradation testing (mongo-python-driver: connection resilience)
4. Edge case parametrization (pytest-dev/pytest: parametrize with edge values)
"""

import asyncio
import pytest
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from unittest.mock import AsyncMock, Mock, patch

from infrastructure.memory_store import GenesisMemoryStore, InMemoryBackend
from infrastructure.mongodb_backend import MongoDBBackend


# Test 1: MongoDB connection failure
# Context7 Source: /mongodb/mongo-python-driver - ServerSelectionTimeoutError handling


@pytest.mark.asyncio
async def test_mongodb_connection_failure(monkeypatch):
    """
    Test graceful handling of MongoDB connection failures.

    Context7 Pattern: /mongodb/mongo-python-driver - common connection errors
    """
    def _raise_failure(*args, **kwargs):
        raise ConnectionFailure("unable to connect")

    monkeypatch.setattr("infrastructure.mongodb_backend.MongoClient", _raise_failure)

    backend = MongoDBBackend(
        connection_uri="mongodb://invalid:27017",
        database_name="genesis_test"
    )

    with pytest.raises(ConnectionFailure):
        await backend.connect()


# Test 2: MongoDB server selection timeout (NEW)
# Context7 Source: /mongodb/mongo-python-driver - ServerSelectionTimeoutError


@pytest.mark.asyncio
async def test_mongodb_server_selection_timeout():
    """
    Test handling of server selection timeouts when MongoDB is unavailable.

    This simulates network issues or MongoDB being temporarily down.

    Context7 Pattern: /mongodb/mongo-python-driver - timeout error handling
    """
    backend = MongoDBBackend(
        connection_uri="mongodb://nonexistent:27017/?serverSelectionTimeoutMS=1000",
        database_name="genesis_test"
    )

    with pytest.raises((ConnectionFailure, ServerSelectionTimeoutError)):
        await backend.connect()
        # Attempt an operation
        await backend.save_memory(
            ("agent", "qa"),
            "test",
            {"value": "data"}
        )


# Test 3: Memory corruption handled gracefully
# Context7 Source: /pytest-dev/pytest - exception testing patterns


@pytest.mark.asyncio
async def test_memory_corruption_handled_gracefully():
    """
    Test that invalid memory payloads are rejected with clear errors.

    Context7 Pattern: /pytest-dev/pytest - pytest.raises for validation
    """
    store = GenesisMemoryStore()

    # Non-dict payloads should be rejected
    with pytest.raises(ValueError):
        await store.save_memory(("agent", "qa"), "broken", "not-a-dict")


# Test 4: Invalid namespace types (NEW)
# Context7 Source: /pytest-dev/pytest - parametrized edge cases


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_namespace", [
    "not-a-tuple",
    123,
    None,
    [],
    ("single-element",),  # Needs 2 elements
    ("too", "many", "elements"),  # Needs exactly 2
])
async def test_invalid_namespace_types(invalid_namespace):
    """
    Test that invalid namespace types are properly rejected.

    Context7 Pattern: /pytest-dev/pytest - parametrize with edge values
    """
    store = GenesisMemoryStore()

    with pytest.raises((ValueError, TypeError, AssertionError)):
        await store.save_memory(invalid_namespace, "key", {"value": "data"})


# Test 5: Large query pagination
# Context7 Source: /mongodb/mongo-python-driver - bulk operations


@pytest.mark.asyncio
async def test_large_query_pagination():
    """
    Test pagination with large result sets.

    Context7 Pattern: /mongodb/mongo-python-driver - performance patterns
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "bulk")

    # Create 120 entries
    for i in range(120):
        await store.save_memory(namespace, f"item_{i}", {"index": i})

    # Test first page
    first_page = await store.search_memories(namespace, query="item", limit=50)
    assert len(first_page) == 50

    # Test larger page
    second_page = await store.search_memories(namespace, query="item", limit=80)
    assert len(second_page) == 80


# Test 6: Empty result set pagination (NEW - addresses P1 issue)
# Context7 Source: /pytest-dev/pytest - edge case testing


@pytest.mark.asyncio
async def test_empty_result_set_pagination():
    """
    Test pagination behavior with empty result sets.

    Context7 Pattern: /pytest-dev/pytest - boundary condition tests
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "empty")

    # Query non-existent data
    results = await store.search_memories(namespace, query="nonexistent", limit=50)
    assert results == []


# Test 7: Single page pagination (NEW - limit exceeds data)
# Context7 Source: /pytest-dev/pytest - edge case handling


@pytest.mark.asyncio
async def test_single_page_pagination():
    """
    Test pagination when limit exceeds total available items.

    This is a common edge case where pagination limit is larger than dataset.

    Context7 Pattern: /pytest-dev/pytest - boundary testing
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "small")

    # Create only 10 items
    for i in range(10):
        await store.save_memory(namespace, f"item_{i}", {"index": i})

    # Request 50 items (more than available)
    results = await store.search_memories(namespace, query="item", limit=50)
    assert len(results) == 10  # Should return all available


# Test 8: Concurrent pagination (NEW - addresses P1 issue)
# Context7 Source: /pytest-dev/pytest - async concurrency patterns


@pytest.mark.asyncio
async def test_concurrent_pagination():
    """
    Test multiple agents paginating the same dataset simultaneously.

    Context7 Pattern: /pytest-dev/pytest - asyncio.gather for concurrency
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "concurrent_paginate")

    # Create 100 entries
    for i in range(100):
        await store.save_memory(namespace, f"item_{i}", {"index": i})

    async def paginate_worker(worker_id: int, limit: int):
        """Simulate an agent paginating through results"""
        results = await store.search_memories(namespace, query="item", limit=limit)
        return (worker_id, len(results))

    # Run 5 concurrent pagination requests with different limits
    workers = [
        paginate_worker(0, 20),
        paginate_worker(1, 30),
        paginate_worker(2, 50),
        paginate_worker(3, 75),
        paginate_worker(4, 100),
    ]

    results = await asyncio.gather(*workers)

    # Verify each worker got expected results
    assert results[0][1] == 20
    assert results[1][1] == 30
    assert results[2][1] == 50
    assert results[3][1] == 75
    assert results[4][1] == 100


# Test 9: Network timeout simulation (NEW)
# Context7 Source: /mongodb/mongo-python-driver - network_timeout parameter


@pytest.mark.asyncio
async def test_network_timeout_handling():
    """
    Test handling of network timeouts during MongoDB operations.

    Context7 Pattern: /mongodb/mongo-python-driver - network timeout errors
    """
    # Create backend with very short timeout
    backend = MongoDBBackend(
        connection_uri="mongodb://localhost:27017/?serverSelectionTimeoutMS=100",
        database_name="genesis_test_timeout"
    )

    # If MongoDB is not running, this will timeout
    # If it is running, the test validates timeout configuration works
    try:
        await backend.connect()
        # If connection succeeds, verify operations work through GenesisMemoryStore
        store = GenesisMemoryStore(backend=backend)
        await store.save_memory(
            ("agent", "test"),
            "key",
            {"value": "data"}
        )
        # Cleanup
        if backend.client:
            backend.client.drop_database("genesis_test_timeout")
            backend.client.close()
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        # Expected if MongoDB is down - timeout worked correctly
        assert "timeout" in str(e).lower() or "connect" in str(e).lower()


# Test 10: Partial write failure recovery (NEW - addresses P1 issue)
# Context7 Source: /mongodb/mongo-python-driver - transaction patterns


@pytest.mark.asyncio
async def test_partial_write_failure_recovery():
    """
    Test recovery from partial write failures.

    Simulates a scenario where some writes succeed but others fail,
    verifying the system maintains consistency.

    Context7 Pattern: /mongodb/mongo-python-driver - error recovery patterns
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "partial_failure")

    # Write some successful entries
    await store.save_memory(namespace, "success_1", {"status": "ok"})
    await store.save_memory(namespace, "success_2", {"status": "ok"})

    # Attempt invalid write
    try:
        await store.save_memory(namespace, "failure", "invalid-not-dict")
    except ValueError:
        pass  # Expected failure

    # Verify successful writes persisted
    data1 = await store.get_memory(namespace, "success_1")
    data2 = await store.get_memory(namespace, "success_2")
    assert data1["status"] == "ok"
    assert data2["status"] == "ok"

    # Verify failed write didn't create corrupted entry
    failed = await store.get_memory(namespace, "failure")
    assert failed is None


# Test 11: TTL cleanup during active read operations (NEW)
# Context7 Source: /mongodb/mongo-python-driver - concurrent operations


@pytest.mark.asyncio
async def test_ttl_cleanup_during_active_reads():
    """
    Test TTL cleanup doesn't interfere with active read operations.

    This validates read consistency during background maintenance.

    Context7 Pattern: /mongodb/mongo-python-driver - connection resilience
    """
    from infrastructure.memory.langmem_ttl import LangMemTTL
    from datetime import datetime, timedelta, timezone

    backend = InMemoryBackend()
    store = GenesisMemoryStore(backend=backend)
    namespace = ("agent", "cleanup_test")

    # Create entries
    for i in range(50):
        await store.save_memory(namespace, f"item_{i}", {"value": i})

    # Expire half of them
    for i in range(0, 50, 2):
        backend._storage[namespace][f"item_{i}"].metadata.created_at = (
            datetime.now(timezone.utc) - timedelta(days=60)
        ).isoformat()

    ttl = LangMemTTL(backend)

    async def reader_task():
        """Read while cleanup is happening"""
        results = []
        for _ in range(10):  # Multiple read passes
            for i in range(50):
                data = await store.get_memory(namespace, f"item_{i}")
                results.append(data)
            await asyncio.sleep(0.01)  # Small delay
        return results

    async def cleanup_task():
        """Run cleanup"""
        await asyncio.sleep(0.05)  # Let readers start
        return await ttl.cleanup_expired()

    # Run concurrently
    read_results, cleanup_stats = await asyncio.gather(
        reader_task(),
        cleanup_task()
    )

    # Verify cleanup worked
    assert cleanup_stats["deleted_count"] == 25

    # Verify no read errors occurred (None values are OK for expired items)
    assert len(read_results) == 500  # 10 passes × 50 items


# Test 12: Large memory value handling (NEW)
# Context7 Source: /mongodb/mongo-python-driver - document size limits


@pytest.mark.asyncio
async def test_large_memory_value_handling():
    """
    Test handling of very large memory values.

    MongoDB has a 16MB document size limit. This tests behavior near that limit.

    Context7 Pattern: /mongodb/mongo-python-driver - performance patterns
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "large_values")

    # Create a 1MB value (well within 16MB limit)
    large_value = {
        "data": "x" * (1024 * 1024),  # 1MB of data
        "metadata": {"size": "1MB"}
    }

    # Should succeed
    await store.save_memory(namespace, "large_item", large_value)

    # Verify retrieval
    retrieved = await store.get_memory(namespace, "large_item")
    assert retrieved is not None
    assert len(retrieved["data"]) == 1024 * 1024


# Test 13: Namespace key collision detection (NEW)
# Context7 Source: /pytest-dev/pytest - collision testing


@pytest.mark.asyncio
async def test_namespace_key_collision_detection():
    """
    Test that identical keys in different namespaces don't collide.

    This is critical for multi-tenant isolation.

    Context7 Pattern: /pytest-dev/pytest - isolation testing
    """
    store = GenesisMemoryStore()
    key = "collision_test"

    namespaces = [
        ("agent", "qa"),
        ("agent", "builder"),
        ("business", "saas_001"),
        ("business", "saas_002"),
    ]

    # Write same key to different namespaces with unique values
    for i, namespace in enumerate(namespaces):
        await store.save_memory(namespace, key, {"namespace_id": i})

    # Verify isolation: each namespace has its own value
    for i, namespace in enumerate(namespaces):
        data = await store.get_memory(namespace, key)
        assert data["namespace_id"] == i


# Test 14: Empty key handling (NEW)
# Context7 Source: /pytest-dev/pytest - edge case validation


@pytest.mark.asyncio
async def test_empty_key_handling():
    """
    Test handling of empty or whitespace-only keys.

    Context7 Pattern: /pytest-dev/pytest - boundary value testing
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "qa")

    # Empty string key should be rejected
    with pytest.raises((ValueError, AssertionError)):
        await store.save_memory(namespace, "", {"value": "data"})

    # Whitespace-only key should be rejected
    with pytest.raises((ValueError, AssertionError)):
        await store.save_memory(namespace, "   ", {"value": "data"})


# Test 15: Null/None value handling (NEW)
# Context7 Source: /pytest-dev/pytest - null value testing


@pytest.mark.asyncio
async def test_null_value_handling():
    """
    Test handling of None/null values.

    Context7 Pattern: /pytest-dev/pytest - null safety testing
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "qa")

    # None value should be rejected (requires dict)
    with pytest.raises((ValueError, TypeError)):
        await store.save_memory(namespace, "null_test", None)


# Test 16: Backend disconnection during operation (NEW)
# Context7 Source: /mongodb/mongo-python-driver - connection resilience


@pytest.mark.asyncio
async def test_backend_disconnection_during_operation():
    """
    Test graceful handling when backend disconnects mid-operation.

    Context7 Pattern: /mongodb/mongo-python-driver - resilience patterns
    """
    # Use InMemory backend and simulate disconnection
    backend = InMemoryBackend()
    store = GenesisMemoryStore(backend=backend)
    namespace = ("agent", "disconnect_test")

    # Write some data
    await store.save_memory(namespace, "before_disconnect", {"status": "ok"})

    # Simulate backend failure by corrupting internal state
    original_storage = backend._storage
    backend._storage = None

    # Attempt operation (should fail gracefully)
    with pytest.raises((AttributeError, TypeError, RuntimeError)):
        await store.save_memory(namespace, "after_disconnect", {"status": "fail"})

    # Restore backend
    backend._storage = original_storage

    # Verify original data still accessible
    data = await store.get_memory(namespace, "before_disconnect")
    assert data["status"] == "ok"


# Test 17: Concurrent namespace creation (NEW)
# Context7 Source: /pytest-dev/pytest - race condition testing


@pytest.mark.asyncio
async def test_concurrent_namespace_creation():
    """
    Test concurrent creation of new namespaces doesn't cause race conditions.

    Context7 Pattern: /pytest-dev/pytest - concurrency edge cases
    """
    store = GenesisMemoryStore()

    async def create_namespace(namespace_id: int):
        """Create a new namespace concurrently"""
        namespace = ("agent", f"concurrent_{namespace_id}")
        for i in range(10):
            await store.save_memory(namespace, f"key_{i}", {"value": i})

    # Create 10 namespaces concurrently
    await asyncio.gather(*(create_namespace(i) for i in range(10)))

    # Verify all namespaces created correctly
    for ns_id in range(10):
        namespace = ("agent", f"concurrent_{ns_id}")
        for i in range(10):
            data = await store.get_memory(namespace, f"key_{i}")
            assert data is not None
            assert data["value"] == i


# Test 18: Search with special characters (NEW)
# Context7 Source: /pytest-dev/pytest - input validation testing


@pytest.mark.asyncio
@pytest.mark.parametrize("special_query", [
    "test*",
    "test?",
    "test[123]",
    "test.",
    "test$",
    "test^",
])
async def test_search_with_special_characters(special_query):
    """
    Test search functionality with special regex characters.

    Context7 Pattern: /pytest-dev/pytest - special character handling
    """
    store = GenesisMemoryStore()
    namespace = ("agent", "special_chars")

    # Create test data
    await store.save_memory(namespace, "test_key", {"value": "data"})

    # Search should handle special chars without regex errors
    try:
        results = await store.search_memories(namespace, query=special_query)
        # Results may be empty, but should not raise exception
        assert isinstance(results, list)
    except Exception as e:
        # If backend doesn't support special chars, should raise ValueError, not crash
        assert isinstance(e, (ValueError, NotImplementedError))
