"""
LangMem TTL and Deduplication Test Suite

Purpose: Validate memory expiration (TTL) and deduplication functionality
for Genesis Memory Store integration.

Test Coverage:
1. TTL expiration (short/medium/long/permanent memory types)
2. Background cleanup task
3. Exact deduplication (MD5 hash)
4. Semantic deduplication (cosine similarity)
5. Cache management (LRU eviction)
6. Performance benchmarks (<50ms P95 dedup latency)
7. Integration with memory backend

Success Criteria:
- TTL cleanup removes expired entries correctly
- Deduplication achieves 30%+ rate on realistic data
- P95 dedup latency <50ms
- Zero memory leaks (cache bounded)
- 18/20+ tests passing (90%+)
"""

import pytest
import asyncio
import hashlib
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from unittest.mock import MagicMock, AsyncMock, patch

# Import LangMem modules
from infrastructure.memory.langmem_ttl import LangMemTTL
from infrastructure.memory.langmem_dedup import LangMemDedup


# Mock backend for testing
class MockMemoryBackend:
    """Mock memory backend for testing"""

    def __init__(self):
        self._storage = {}  # {namespace: {key: entry}}

    async def get(self, namespace, key):
        """Get entry from storage"""
        return self._storage.get(namespace, {}).get(key)

    async def put(self, namespace, key, entry):
        """Put entry in storage"""
        if namespace not in self._storage:
            self._storage[namespace] = {}
        self._storage[namespace][key] = entry

    async def delete(self, namespace, key):
        """Delete entry from storage"""
        if namespace in self._storage and key in self._storage[namespace]:
            del self._storage[namespace][key]

    async def list_keys(self, namespace):
        """List all keys in namespace"""
        return list(self._storage.get(namespace, {}).keys())


class MockEntry:
    """Mock memory entry"""

    def __init__(self, content: str, created_at: str):
        self.content = content
        self.metadata = MockMetadata(created_at)


class MockMetadata:
    """Mock entry metadata"""

    def __init__(self, created_at: str):
        self.created_at = created_at


# Mock observability for tests
@pytest.fixture(autouse=True)
def mock_observability(monkeypatch):
    """Mock observability manager for all tests"""
    from unittest.mock import MagicMock

    mock_obs = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_span.set_attribute = MagicMock()

    mock_obs.span = MagicMock(return_value=mock_span)
    mock_obs.SpanType = type('SpanType', (), {'MEMORY': 'memory'})

    # Patch both imports
    monkeypatch.setattr("infrastructure.memory.langmem_ttl.obs_manager", mock_obs)
    monkeypatch.setattr("infrastructure.memory.langmem_dedup.obs_manager", mock_obs)

    return mock_obs


# Fixtures
@pytest.fixture
def mock_backend():
    """Fixture for mock memory backend"""
    return MockMemoryBackend()


@pytest.fixture
def ttl_manager(mock_backend):
    """Fixture for TTL manager"""
    return LangMemTTL(mock_backend, default_ttl_hours=168)


@pytest.fixture
def dedup_manager():
    """Fixture for deduplication manager"""
    return LangMemDedup(similarity_threshold=0.85, max_cache_size=100)


# TTL Tests
@pytest.mark.asyncio
class TestLangMemTTL:
    """Test suite for TTL expiration"""

    async def test_ttl_initialization(self, ttl_manager):
        """Test TTL manager initializes with correct config"""
        assert ttl_manager.default_ttl_hours == 168
        assert ttl_manager.ttl_config["short_term"] == 24
        assert ttl_manager.ttl_config["medium_term"] == 168
        assert ttl_manager.ttl_config["long_term"] == 8760
        assert ttl_manager.ttl_config["permanent"] is None

    async def test_ttl_get_ttl_for_namespace(self, ttl_manager):
        """Test getting TTL for different namespace types"""
        assert ttl_manager.get_ttl_for_namespace(("short_term", "test")) == 24
        assert ttl_manager.get_ttl_for_namespace(("medium_term", "test")) == 168
        assert ttl_manager.get_ttl_for_namespace(("long_term", "test")) == 8760
        assert ttl_manager.get_ttl_for_namespace(("permanent", "test")) is None
        assert ttl_manager.get_ttl_for_namespace(("custom", "test")) == 168  # default

    async def test_ttl_is_expired_old_memory(self, ttl_manager):
        """Test expired memory detection"""
        now = datetime.now(timezone.utc)
        old_timestamp = (now - timedelta(days=2)).isoformat()

        # Short-term memory (24h TTL) - should be expired
        assert ttl_manager.is_expired(
            old_timestamp,
            ("short_term", "test"),
            now
        ) is True

    async def test_ttl_is_not_expired_recent_memory(self, ttl_manager):
        """Test recent memory not detected as expired"""
        now = datetime.now(timezone.utc)
        recent_timestamp = (now - timedelta(hours=1)).isoformat()

        # Short-term memory (24h TTL) - should NOT be expired
        assert ttl_manager.is_expired(
            recent_timestamp,
            ("short_term", "test"),
            now
        ) is False

    async def test_ttl_permanent_never_expires(self, ttl_manager):
        """Test permanent memories never expire"""
        now = datetime.now(timezone.utc)
        ancient_timestamp = (now - timedelta(days=365)).isoformat()

        # Permanent memory - should NEVER expire
        assert ttl_manager.is_expired(
            ancient_timestamp,
            ("permanent", "test"),
            now
        ) is False

    async def test_ttl_cleanup_expired(self, mock_backend, ttl_manager):
        """Test cleanup removes expired entries"""
        now = datetime.now(timezone.utc)
        namespace = ("short_term", "test")

        # Add expired entry (2 days old)
        old_timestamp = (now - timedelta(days=2)).isoformat()
        await mock_backend.put(
            namespace,
            "old_key",
            MockEntry("Old content", old_timestamp)
        )

        # Add recent entry (1 hour old)
        recent_timestamp = (now - timedelta(hours=1)).isoformat()
        await mock_backend.put(
            namespace,
            "recent_key",
            MockEntry("Recent content", recent_timestamp)
        )

        # Run cleanup
        stats = await ttl_manager.cleanup_expired(namespace_filter=namespace)

        # Verify old entry was deleted
        old_entry = await mock_backend.get(namespace, "old_key")
        assert old_entry is None

        # Verify recent entry was kept
        recent_entry = await mock_backend.get(namespace, "recent_key")
        assert recent_entry is not None

        # Verify stats
        assert stats["deleted_count"] == 1
        assert stats["namespaces_scanned"] == 1

    async def test_ttl_cleanup_multiple_namespaces(self, mock_backend, ttl_manager):
        """Test cleanup across multiple namespaces"""
        now = datetime.now(timezone.utc)

        # Add expired entries in different namespaces
        for ns_type in ["short_term", "medium_term"]:
            namespace = (ns_type, "test")
            old_timestamp = (now - timedelta(days=30)).isoformat()
            await mock_backend.put(
                namespace,
                "old_key",
                MockEntry("Old content", old_timestamp)
            )

        # Run cleanup without namespace filter (all namespaces)
        stats = await ttl_manager.cleanup_expired()

        # Verify both expired entries were deleted
        assert stats["deleted_count"] == 2
        assert stats["namespaces_scanned"] >= 2

    async def test_ttl_background_cleanup_starts_stops(self, ttl_manager):
        """Test background cleanup task lifecycle"""
        # Start background cleanup
        await ttl_manager.start_background_cleanup(interval_seconds=1)

        assert ttl_manager._running is True
        assert ttl_manager._cleanup_task is not None

        # Stop background cleanup
        await ttl_manager.stop_background_cleanup()

        assert ttl_manager._running is False

    async def test_ttl_stats_tracking(self, mock_backend, ttl_manager):
        """Test statistics tracking"""
        now = datetime.now(timezone.utc)
        namespace = ("short_term", "test")

        # Add expired entry
        old_timestamp = (now - timedelta(days=2)).isoformat()
        await mock_backend.put(
            namespace,
            "old_key",
            MockEntry("Old content", old_timestamp)
        )

        # Run cleanup
        await ttl_manager.cleanup_expired(namespace_filter=namespace)

        # Get stats
        stats = ttl_manager.get_stats()

        assert stats["total_cleanups"] == 1
        assert stats["total_deleted"] == 1
        assert stats["last_cleanup"] is not None
        assert stats["last_cleanup_duration"] > 0.0


# Deduplication Tests
@pytest.mark.asyncio
class TestLangMemDedup:
    """Test suite for memory deduplication"""

    async def test_dedup_initialization(self, dedup_manager):
        """Test dedup manager initializes correctly"""
        assert dedup_manager.similarity_threshold == 0.85
        assert dedup_manager.max_cache_size == 100
        assert dedup_manager.enable_semantic is True

    async def test_dedup_exact_duplicates(self, dedup_manager):
        """Test exact duplicate detection via MD5 hash"""
        memories = [
            {"content": "Duplicate message", "entry_id": "1"},
            {"content": "Duplicate message", "entry_id": "2"},  # Exact duplicate
            {"content": "Unique message", "entry_id": "3"}
        ]

        result = await dedup_manager.deduplicate(memories)

        # Should remove 1 exact duplicate
        assert len(result) == 2
        assert result[0]["content"] == "Duplicate message"
        assert result[1]["content"] == "Unique message"

        # Check stats
        stats = dedup_manager.get_stats()
        assert stats["exact_duplicates"] == 1
        assert stats["unique_entries"] == 2

    async def test_dedup_semantic_duplicates(self, dedup_manager):
        """Test semantic duplicate detection via embeddings"""
        # Create similar embeddings (90% similarity)
        embedding1 = np.array([1.0, 0.0, 0.0, 0.0])
        embedding2 = np.array([0.95, 0.31, 0.0, 0.0])  # ~90% cosine similarity

        memories = [
            {
                "content": "First message",
                "entry_id": "1",
                "embedding": embedding1.tolist()
            },
            {
                "content": "Similar message",
                "entry_id": "2",
                "embedding": embedding2.tolist()
            }
        ]

        result = await dedup_manager.deduplicate(memories)

        # Should detect semantic duplicate (90% > 85% threshold)
        assert len(result) == 1
        assert result[0]["entry_id"] == "1"

        # Check stats
        stats = dedup_manager.get_stats()
        assert stats["semantic_duplicates"] == 1

    async def test_dedup_semantic_not_duplicate(self, dedup_manager):
        """Test semantic similarity below threshold not detected"""
        # Create dissimilar embeddings (70% similarity)
        embedding1 = np.array([1.0, 0.0, 0.0, 0.0])
        embedding2 = np.array([0.7, 0.714, 0.0, 0.0])  # ~70% cosine similarity

        memories = [
            {
                "content": "First message",
                "entry_id": "1",
                "embedding": embedding1.tolist()
            },
            {
                "content": "Different message",
                "entry_id": "2",
                "embedding": embedding2.tolist()
            }
        ]

        result = await dedup_manager.deduplicate(memories)

        # Should NOT detect as duplicate (70% < 85% threshold)
        assert len(result) == 2

        # Check stats
        stats = dedup_manager.get_stats()
        assert stats["semantic_duplicates"] == 0

    async def test_dedup_compute_hash(self, dedup_manager):
        """Test MD5 hash computation"""
        content = "Test content"
        hash1 = dedup_manager.compute_hash(content)
        hash2 = dedup_manager.compute_hash(content)

        # Same content should produce same hash
        assert hash1 == hash2

        # Different content should produce different hash
        hash3 = dedup_manager.compute_hash("Different content")
        assert hash1 != hash3

    async def test_dedup_cosine_similarity(self, dedup_manager):
        """Test cosine similarity computation"""
        # Identical vectors (100% similarity)
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 0.0, 0.0])
        assert dedup_manager.compute_cosine_similarity(v1, v2) == 1.0

        # Orthogonal vectors (0% similarity)
        v3 = np.array([1.0, 0.0, 0.0])
        v4 = np.array([0.0, 1.0, 0.0])
        assert dedup_manager.compute_cosine_similarity(v3, v4) == 0.0

        # Opposite vectors (0% similarity, clamped)
        v5 = np.array([1.0, 0.0, 0.0])
        v6 = np.array([-1.0, 0.0, 0.0])
        similarity = dedup_manager.compute_cosine_similarity(v5, v6)
        assert 0.0 <= similarity <= 1.0  # Should be clamped

    async def test_dedup_cache_lru_eviction(self, dedup_manager):
        """Test LRU cache eviction when at capacity"""
        # Set small cache size for testing
        dedup_manager.max_cache_size = 3

        # Add 4 entries (should trigger eviction)
        memories = []
        for i in range(4):
            embedding = np.random.rand(10).astype(np.float32)
            memories.append({
                "content": f"Message {i}",
                "entry_id": str(i),
                "embedding": embedding.tolist()
            })

        await dedup_manager.deduplicate(memories)

        # Cache should have 3 entries (evicted oldest)
        stats = dedup_manager.get_stats()
        assert stats["cache_size"] == 3
        assert stats["cache_evictions"] >= 1

    async def test_dedup_reset_cache(self, dedup_manager):
        """Test cache reset"""
        # Add some data
        memories = [
            {"content": "Test message", "entry_id": "1"}
        ]
        await dedup_manager.deduplicate(memories)

        # Reset cache
        dedup_manager.reset_cache()

        # Verify caches are empty
        assert len(dedup_manager.seen_hashes) == 0
        assert len(dedup_manager.seen_embeddings) == 0

    async def test_dedup_performance_target(self, dedup_manager):
        """Test deduplication meets <50ms P95 latency target"""
        import time

        # Generate 100 memories for realistic workload
        memories = []
        for i in range(100):
            embedding = np.random.rand(384).astype(np.float32)  # Realistic embedding size
            memories.append({
                "content": f"Message {i}",
                "entry_id": str(i),
                "embedding": embedding.tolist()
            })

        # Measure latency
        latencies = []
        for _ in range(10):  # Run 10 times
            start = time.time()
            await dedup_manager.deduplicate(memories)
            latency = (time.time() - start) * 1000  # Convert to ms
            latencies.append(latency)

        # Calculate P95
        latencies.sort()
        p95_latency = latencies[int(len(latencies) * 0.95)]

        print(f"\nDeduplication Performance:")
        print(f"  P95 Latency: {p95_latency:.2f}ms")
        print(f"  Target: <50ms")

        # Verify meets performance target
        assert p95_latency < 50, (
            f"P95 latency {p95_latency:.2f}ms exceeds 50ms target"
        )

    async def test_dedup_rate_target(self, dedup_manager):
        """Test deduplication achieves 30%+ rate on realistic data"""
        # Generate realistic duplicated data
        base_messages = [
            "User requested password reset",
            "API call to /users endpoint",
            "Database query executed successfully",
            "Error: Connection timeout",
            "User logged in from IP 192.168.1.1"
        ]

        memories = []
        entry_id = 0

        # Create dataset with ~40% duplicates
        for _ in range(5):  # Repeat messages 5 times
            for msg in base_messages:
                memories.append({
                    "content": msg,
                    "entry_id": str(entry_id)
                })
                entry_id += 1

        # Add unique messages
        for i in range(10):
            memories.append({
                "content": f"Unique message {i}",
                "entry_id": str(entry_id)
            })
            entry_id += 1

        # Deduplicate
        result = await dedup_manager.deduplicate(memories)

        # Calculate deduplication rate
        dedup_rate = 1 - (len(result) / len(memories))

        print(f"\nDeduplication Rate Test:")
        print(f"  Input: {len(memories)} memories")
        print(f"  Output: {len(result)} unique")
        print(f"  Dedup Rate: {dedup_rate:.1%}")
        print(f"  Target: ≥30%")

        # Verify meets deduplication rate target
        assert dedup_rate >= 0.30, (
            f"Deduplication rate {dedup_rate:.1%} below 30% target"
        )


# Integration Tests
@pytest.mark.asyncio
class TestLangMemIntegration:
    """Integration tests for TTL + Dedup"""

    async def test_ttl_dedup_integration(self, mock_backend):
        """Test TTL and dedup working together"""
        ttl = LangMemTTL(mock_backend, default_ttl_hours=24)
        dedup = LangMemDedup(similarity_threshold=0.85)

        # Add memories with duplicates and old timestamps
        now = datetime.now(timezone.utc)
        namespace = ("short_term", "test")

        # Recent duplicates
        recent_time = (now - timedelta(hours=1)).isoformat()
        for i in range(3):
            await mock_backend.put(
                namespace,
                f"recent_{i}",
                MockEntry("Recent duplicate", recent_time)
            )

        # Old unique
        old_time = (now - timedelta(days=2)).isoformat()
        await mock_backend.put(
            namespace,
            "old_unique",
            MockEntry("Old unique message", old_time)
        )

        # Run TTL cleanup first
        ttl_stats = await ttl.cleanup_expired(namespace_filter=namespace)

        # Get remaining memories
        keys = await mock_backend.list_keys(namespace)
        memories = []
        for key in keys:
            entry = await mock_backend.get(namespace, key)
            if entry:
                memories.append({
                    "content": entry.content,
                    "entry_id": key
                })

        # Run deduplication
        unique_memories = await dedup.deduplicate(memories)

        # Should have 1 unique memory (old one deleted by TTL, duplicates merged)
        assert len(unique_memories) == 1
        assert unique_memories[0]["content"] == "Recent duplicate"

        print(f"\nIntegration Test:")
        print(f"  TTL deleted: {ttl_stats['deleted_count']} entries")
        print(f"  Dedup reduced: {len(memories)} → {len(unique_memories)}")

    async def test_stats_comprehensive(self, mock_backend, ttl_manager, dedup_manager):
        """Test comprehensive statistics tracking"""
        # Generate some activity
        now = datetime.now(timezone.utc)
        namespace = ("short_term", "test")

        # Add expired entry
        old_time = (now - timedelta(days=2)).isoformat()
        await mock_backend.put(
            namespace,
            "old_key",
            MockEntry("Old content", old_time)
        )

        # Run TTL cleanup
        await ttl_manager.cleanup_expired(namespace_filter=namespace)

        # Run deduplication
        memories = [
            {"content": "Test 1", "entry_id": "1"},
            {"content": "Test 1", "entry_id": "2"},  # Duplicate
            {"content": "Test 2", "entry_id": "3"}
        ]
        await dedup_manager.deduplicate(memories)

        # Get comprehensive stats
        ttl_stats = ttl_manager.get_stats()
        dedup_stats = dedup_manager.get_stats()

        # Verify TTL stats
        assert ttl_stats["total_cleanups"] == 1
        assert ttl_stats["total_deleted"] == 1

        # Verify dedup stats
        assert dedup_stats["total_processed"] == 3
        assert dedup_stats["exact_duplicates"] == 1
        assert dedup_stats["dedup_rate"] > 0

        print(f"\nComprehensive Stats:")
        print(f"  TTL: {ttl_stats}")
        print(f"  Dedup: {dedup_stats}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
