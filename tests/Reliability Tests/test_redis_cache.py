"""
Integration Tests for Redis Cache Layer

Tests require Redis running locally or via connection string.
To skip if Redis unavailable: pytest -m "not redis"

Test coverage:
1. Connection and setup
2. Get/set operations
3. TTL management (hot/warm/cold)
4. Cache-aside pattern (get_or_fetch)
5. Cache statistics
6. Performance benchmarks

Setup:
- Install Redis locally OR use Redis cloud
- Set REDIS_URL environment variable if not using localhost
"""

import asyncio
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from infrastructure.redis_cache import RedisCacheLayer
from infrastructure.memory_store import MemoryEntry, MemoryMetadata


# Check if Redis is available
def redis_available() -> bool:
    """Check if Redis is accessible"""
    try:
        import redis
        client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=2
        )
        client.ping()
        client.close()
        return True
    except Exception:
        return False


REDIS_AVAILABLE = redis_available()
pytestmark = pytest.mark.skipif(
    not REDIS_AVAILABLE,
    reason="Redis not available (install locally or set REDIS_URL)"
)


@pytest.fixture
async def redis_cache():
    """Create Redis cache for testing"""
    cache = RedisCacheLayer(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/1")  # Use DB 1 for tests
    )

    await cache.connect()

    yield cache

    # Cleanup: Clear test cache and close
    if cache.redis:
        await cache.redis.flushdb()  # Clear test database
        await cache.close()


class TestRedisConnection:
    """Test Redis connection"""

    @pytest.mark.asyncio
    async def test_connect(self, redis_cache):
        """Test Redis connection succeeds"""
        assert redis_cache._connected is True
        assert redis_cache.redis is not None

    @pytest.mark.asyncio
    async def test_ping(self, redis_cache):
        """Test Redis ping"""
        result = await redis_cache.redis.ping()
        assert result is True


class TestRedisGetSet:
    """Test get/set operations"""

    @pytest.mark.asyncio
    async def test_set_and_get(self, redis_cache):
        """Test basic set and get"""
        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="test_key",
            value={"data": "test_value"}
        )

        # Set entry
        success = await redis_cache.set(
            namespace=("agent", "qa_001"),
            key="test_key",
            entry=entry
        )

        assert success is True

        # Get entry
        retrieved = await redis_cache.get(
            namespace=("agent", "qa_001"),
            key="test_key"
        )

        assert retrieved is not None
        assert retrieved.value["data"] == "test_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, redis_cache):
        """Test get returns None for missing key"""
        result = await redis_cache.get(
            namespace=("agent", "qa_001"),
            key="nonexistent"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_increments_stats(self, redis_cache):
        """Test cache hit increments statistics"""
        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="test",
            value={"data": "test"}
        )

        await redis_cache.set(("agent", "qa_001"), "test", entry)

        # Reset stats
        redis_cache.reset_stats()

        # Get (cache hit)
        await redis_cache.get(("agent", "qa_001"), "test")

        stats = redis_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0

    @pytest.mark.asyncio
    async def test_cache_miss_increments_stats(self, redis_cache):
        """Test cache miss increments statistics"""
        redis_cache.reset_stats()

        # Get nonexistent (cache miss)
        await redis_cache.get(("agent", "qa_001"), "missing")

        stats = redis_cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1


class TestRedisTTL:
    """Test TTL management"""

    @pytest.mark.asyncio
    async def test_hot_memory_ttl(self, redis_cache):
        """Test hot memory gets 1 hour TTL"""
        # Create entry accessed recently (hot)
        metadata = MemoryMetadata()
        metadata.last_accessed = datetime.now(timezone.utc).isoformat()

        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="hot_memory",
            value={"temperature": "hot"},
            metadata=metadata
        )

        await redis_cache.set(("agent", "qa_001"), "hot_memory", entry)

        # Check TTL
        cache_key = redis_cache._make_cache_key(("agent", "qa_001"), "hot_memory")
        ttl = await redis_cache.redis.ttl(cache_key)

        # Should be close to 1 hour (3600 seconds)
        assert 3590 <= ttl <= 3600

    @pytest.mark.asyncio
    async def test_warm_memory_ttl(self, redis_cache):
        """Test warm memory gets 24 hour TTL"""
        # Create entry accessed 2 hours ago (warm)
        metadata = MemoryMetadata()
        accessed_time = datetime.now(timezone.utc) - timedelta(hours=2)
        metadata.last_accessed = accessed_time.isoformat()

        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="warm_memory",
            value={"temperature": "warm"},
            metadata=metadata
        )

        await redis_cache.set(("agent", "qa_001"), "warm_memory", entry)

        # Check TTL
        cache_key = redis_cache._make_cache_key(("agent", "qa_001"), "warm_memory")
        ttl = await redis_cache.redis.ttl(cache_key)

        # Should be close to 24 hours (86400 seconds)
        assert 86390 <= ttl <= 86400

    @pytest.mark.asyncio
    async def test_custom_ttl(self, redis_cache):
        """Test custom TTL override"""
        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="custom_ttl",
            value={"data": "test"}
        )

        # Set with custom 60 second TTL
        await redis_cache.set(
            namespace=("agent", "qa_001"),
            key="custom_ttl",
            entry=entry,
            ttl=60
        )

        cache_key = redis_cache._make_cache_key(("agent", "qa_001"), "custom_ttl")
        ttl = await redis_cache.redis.ttl(cache_key)

        # Should be close to 60 seconds
        assert 55 <= ttl <= 60

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, redis_cache):
        """Test entry expires after TTL"""
        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="expiring",
            value={"data": "test"}
        )

        # Set with 1 second TTL
        await redis_cache.set(
            namespace=("agent", "qa_001"),
            key="expiring",
            entry=entry,
            ttl=1
        )

        # Should exist immediately
        result = await redis_cache.get(("agent", "qa_001"), "expiring")
        assert result is not None

        # Wait for expiration
        await asyncio.sleep(2)

        # Should be expired
        result = await redis_cache.get(("agent", "qa_001"), "expiring")
        assert result is None


class TestCacheAsidePattern:
    """Test cache-aside pattern (get_or_fetch)"""

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_hit(self, redis_cache):
        """Test get_or_fetch returns cached value"""
        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="cached",
            value={"source": "cache"}
        )

        # Populate cache
        await redis_cache.set(("agent", "qa_001"), "cached", entry)

        # Mock fetch function (should not be called)
        fetch_called = False

        async def mock_fetch():
            nonlocal fetch_called
            fetch_called = True
            return MemoryEntry(
                namespace=("agent", "qa_001"),
                key="cached",
                value={"source": "backend"}
            )

        # Get or fetch
        result = await redis_cache.get_or_fetch(
            namespace=("agent", "qa_001"),
            key="cached",
            fetch_fn=mock_fetch
        )

        # Should return cached value without calling fetch
        assert result.value["source"] == "cache"
        assert fetch_called is False

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_miss(self, redis_cache):
        """Test get_or_fetch fetches and populates cache on miss"""
        # Mock fetch function
        async def mock_fetch():
            return MemoryEntry(
                namespace=("agent", "qa_001"),
                key="fetched",
                value={"source": "backend", "data": "fetched_data"}
            )

        # Get or fetch (cache miss)
        result = await redis_cache.get_or_fetch(
            namespace=("agent", "qa_001"),
            key="fetched",
            fetch_fn=mock_fetch
        )

        # Should return fetched value
        assert result.value["source"] == "backend"
        assert result.value["data"] == "fetched_data"

        # Should now be in cache
        cached = await redis_cache.get(("agent", "qa_001"), "fetched")
        assert cached is not None
        assert cached.value["data"] == "fetched_data"

    @pytest.mark.asyncio
    async def test_get_or_fetch_not_found(self, redis_cache):
        """Test get_or_fetch returns None if not in cache or backend"""
        async def mock_fetch():
            return None

        result = await redis_cache.get_or_fetch(
            namespace=("agent", "qa_001"),
            key="not_found",
            fetch_fn=mock_fetch
        )

        assert result is None


class TestCacheOperations:
    """Test cache operations"""

    @pytest.mark.asyncio
    async def test_delete(self, redis_cache):
        """Test delete removes entry from cache"""
        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="to_delete",
            value={"data": "test"}
        )

        # Set entry
        await redis_cache.set(("agent", "qa_001"), "to_delete", entry)

        # Verify exists
        result = await redis_cache.get(("agent", "qa_001"), "to_delete")
        assert result is not None

        # Delete
        deleted = await redis_cache.delete(("agent", "qa_001"), "to_delete")
        assert deleted is True

        # Verify deleted
        result = await redis_cache.get(("agent", "qa_001"), "to_delete")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_namespace(self, redis_cache):
        """Test clear_namespace removes all entries in namespace"""
        # Set multiple entries
        for i in range(5):
            entry = MemoryEntry(
                namespace=("agent", "qa_001"),
                key=f"key_{i}",
                value={"index": i}
            )
            await redis_cache.set(("agent", "qa_001"), f"key_{i}", entry)

        # Clear namespace
        count = await redis_cache.clear_namespace(("agent", "qa_001"))

        assert count == 5

        # Verify all cleared
        for i in range(5):
            result = await redis_cache.get(("agent", "qa_001"), f"key_{i}")
            assert result is None


class TestCacheStatistics:
    """Test cache statistics"""

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self, redis_cache):
        """Test hit rate is calculated correctly"""
        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="test",
            value={"data": "test"}
        )

        await redis_cache.set(("agent", "qa_001"), "test", entry)

        redis_cache.reset_stats()

        # 7 hits, 3 misses = 70% hit rate
        for _ in range(7):
            await redis_cache.get(("agent", "qa_001"), "test")  # Hit

        for i in range(3):
            await redis_cache.get(("agent", "qa_001"), f"missing_{i}")  # Miss

        stats = redis_cache.get_stats()

        assert stats["hits"] == 7
        assert stats["misses"] == 3
        assert stats["total_requests"] == 10
        assert abs(stats["hit_rate"] - 0.7) < 0.01  # 70%


class TestRedisPerformance:
    """Performance benchmarks"""

    @pytest.mark.asyncio
    async def test_get_performance(self, redis_cache):
        """Benchmark cache get operations (target: <10ms P95)"""
        # Setup: Populate cache with 100 entries
        for i in range(100):
            entry = MemoryEntry(
                namespace=("agent", "bench"),
                key=f"bench_key_{i}",
                value={"index": i}
            )
            await redis_cache.set(("agent", "bench"), f"bench_key_{i}", entry)

        # Benchmark gets
        get_times = []

        for i in range(100):
            start = time.perf_counter()

            await redis_cache.get(
                namespace=("agent", "bench"),
                key=f"bench_key_{i}"
            )

            duration = (time.perf_counter() - start) * 1000  # ms
            get_times.append(duration)

        # Calculate P95
        p95 = sorted(get_times)[94]
        avg = sum(get_times) / len(get_times)

        print(f"\nRedis Get Performance:")
        print(f"  Average: {avg:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  Target: <10ms P95")

        # Redis get should be <10ms P95
        assert p95 < 10, f"Get P95 {p95:.2f}ms exceeds 10ms target"

    @pytest.mark.asyncio
    async def test_set_performance(self, redis_cache):
        """Benchmark cache set operations (target: <10ms P95)"""
        set_times = []

        for i in range(100):
            entry = MemoryEntry(
                namespace=("agent", "bench"),
                key=f"set_bench_{i}",
                value={"index": i, "data": "x" * 100}
            )

            start = time.perf_counter()

            await redis_cache.set(
                namespace=("agent", "bench"),
                key=f"set_bench_{i}",
                entry=entry
            )

            duration = (time.perf_counter() - start) * 1000  # ms
            set_times.append(duration)

        # Calculate P95
        p95 = sorted(set_times)[94]
        avg = sum(set_times) / len(set_times)

        print(f"\nRedis Set Performance:")
        print(f"  Average: {avg:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  Target: <10ms P95")

        # Redis set should be <10ms P95
        assert p95 < 10, f"Set P95 {p95:.2f}ms exceeds 10ms target"


if __name__ == "__main__":
    if not REDIS_AVAILABLE:
        print("Redis not available. Skipping tests.")
        print("To run tests:")
        print("  1. Install Redis locally: brew install redis")
        print("  2. Start Redis: brew services start redis")
        print("  3. OR set REDIS_URL environment variable")
    else:
        pytest.main([__file__, "-v", "-s"])
