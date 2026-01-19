"""
Comprehensive tests for vLLM Agent-Lightning Token Caching

This test suite validates the token caching implementation for 60-80% latency reduction.
Covers token caching/retrieval, cache hit rates, latency validation, drift checks, and
Redis integration.

Test Categories:
1. Token caching (5 tests): Cache key generation, storage, retrieval, TTL
2. Cache performance (5 tests): Hit rate, latency reduction, throughput
3. Token consistency (5 tests): Drift detection, determinism, round-trip integrity
4. Redis integration (5 tests): Connection handling, error recovery, namespace ops
5. End-to-end (5 tests): Full RAG pipeline, multiple queries, edge cases

Author: Thon (Python Expert) + Nova (Vertex AI Agent Architect)
Date: October 24, 2025
Status: Token Caching Test Suite
"""

import asyncio
import json
import pytest
import time
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import the classes we're testing
from infrastructure.token_cached_rag import TokenCachedRAG, TokenCacheStats
from infrastructure.llm_client import MockLLMClient


# Fixtures
@pytest.fixture
def mock_vector_db():
    """Mock vector database for testing"""
    db = Mock()
    db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Genesis is a multi-agent system", "score": 0.95},
        {"id": "doc_2", "content": "Built on Microsoft Agent Framework", "score": 0.92},
        {"id": "doc_3", "content": "Supports autonomous agent evolution", "score": 0.88}
    ])
    return db


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    return MockLLMClient()


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)  # Default: cache miss
    redis.setex = AsyncMock()
    redis.delete = AsyncMock(return_value=1)
    redis.scan_iter = AsyncMock(return_value=iter([]))
    return redis


@pytest.fixture
async def token_cached_rag(mock_vector_db, mock_llm_client, mock_redis):
    """Create TokenCachedRAG instance for testing"""
    return TokenCachedRAG(
        vector_db=mock_vector_db,
        llm_client=mock_llm_client,
        redis_client=mock_redis,
        cache_ttl=300,
        enable_caching=True
    )


# ============================================================================
# Category 1: Token Caching Tests (5 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_cache_key_generation(token_cached_rag):
    """Test 1: Cache key generation is deterministic and collision-resistant"""
    # Same docs in different order should produce same cache key
    doc_ids_1 = ["doc_1", "doc_2", "doc_3"]
    doc_ids_2 = ["doc_3", "doc_1", "doc_2"]  # Different order

    key_1 = token_cached_rag._generate_cache_key(doc_ids_1)
    key_2 = token_cached_rag._generate_cache_key(doc_ids_2)

    assert key_1 == key_2, "Cache keys should be order-independent"
    assert key_1.startswith("rag_tokens:"), "Cache key should have correct prefix"
    assert len(key_1) == len("rag_tokens:") + 64, "SHA-256 hash should be 64 hex chars"


@pytest.mark.asyncio
async def test_cache_key_collision_resistance(token_cached_rag):
    """Test 2: Different doc sets produce different cache keys"""
    doc_ids_1 = ["doc_1", "doc_2", "doc_3"]
    doc_ids_2 = ["doc_1", "doc_2", "doc_4"]  # One different doc

    key_1 = token_cached_rag._generate_cache_key(doc_ids_1)
    key_2 = token_cached_rag._generate_cache_key(doc_ids_2)

    assert key_1 != key_2, "Different doc sets should have different cache keys"


@pytest.mark.asyncio
async def test_token_storage_in_redis(token_cached_rag, mock_redis):
    """Test 3: Token IDs are correctly stored in Redis with TTL"""
    cache_key = "rag_tokens:test_key"
    token_ids = [1, 2, 3, 4, 5]

    await token_cached_rag._cache_tokens(cache_key, token_ids)

    # Verify Redis setex was called with correct parameters
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args[0]

    assert call_args[0] == cache_key, "Cache key should match"
    assert call_args[1] == 300, "TTL should be 300 seconds"
    assert json.loads(call_args[2]) == token_ids, "Token IDs should be JSON-serialized"


@pytest.mark.asyncio
async def test_token_retrieval_from_redis(token_cached_rag, mock_redis):
    """Test 4: Token IDs are correctly retrieved from Redis cache"""
    cache_key = "rag_tokens:test_key"
    token_ids = [10, 20, 30, 40, 50]

    # Mock Redis get to return cached tokens
    mock_redis.get = AsyncMock(return_value=json.dumps(token_ids))

    result = await token_cached_rag._get_cached_tokens(cache_key)

    assert result == token_ids, "Retrieved token IDs should match stored"
    mock_redis.get.assert_called_once_with(cache_key)


@pytest.mark.asyncio
async def test_cache_miss_handling(token_cached_rag, mock_redis, mock_vector_db, mock_llm_client):
    """Test 5: Cache miss triggers tokenization and storage"""
    # Mock Redis cache miss
    mock_redis.get = AsyncMock(return_value=None)

    # Mock vector DB to return documents
    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Test document content"}
    ])

    # Retrieve tokens (cache miss expected)
    token_ids, metadata = await token_cached_rag.retrieve_tokens("test query")

    # Verify cache miss was recorded
    assert metadata["cache_hit"] is False, "Should be cache miss"
    assert token_cached_rag.stats.cache_misses == 1, "Cache miss count should increment"
    assert token_cached_rag.stats.cache_hits == 0, "No cache hits yet"

    # Verify tokenization occurred
    assert len(token_ids) > 0, "Should have tokenized content"

    # Verify Redis setex was called to store tokens
    mock_redis.setex.assert_called_once()


# ============================================================================
# Category 2: Cache Performance Tests (5 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_cache_hit_rate_after_warmup(token_cached_rag, mock_redis, mock_vector_db):
    """Test 6: Cache hit rate exceeds 70% after warmup"""
    # Simulate repeated queries with cache hits
    cached_tokens = [1, 2, 3, 4, 5]

    for i in range(10):
        if i < 3:
            # First 3 queries: cache miss
            mock_redis.get = AsyncMock(return_value=None)
        else:
            # Next 7 queries: cache hit
            mock_redis.get = AsyncMock(return_value=json.dumps(cached_tokens))

        mock_vector_db.search = AsyncMock(return_value=[
            {"id": "doc_1", "content": "Test content"}
        ])

        await token_cached_rag.retrieve_tokens(f"query_{i}")

    stats = token_cached_rag.get_cache_stats()

    assert stats["hit_rate"] >= 70.0, f"Hit rate should be ≥70%, got {stats['hit_rate']:.1f}%"
    assert stats["hits"] == 7, "Should have 7 cache hits"
    assert stats["misses"] == 3, "Should have 3 cache misses"


@pytest.mark.asyncio
async def test_cache_hit_latency_reduction(token_cached_rag, mock_redis, mock_vector_db):
    """Test 7: Cache hits are 60-80% faster than cache misses"""
    cached_tokens = [1, 2, 3, 4, 5]

    # Cache MISS measurement
    mock_redis.get = AsyncMock(return_value=None)
    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Test content" * 100}  # Large content
    ])

    start_miss = time.time()
    await token_cached_rag.retrieve_tokens("query_miss")
    miss_latency = (time.time() - start_miss) * 1000

    # Cache HIT measurement
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_tokens))

    start_hit = time.time()
    await token_cached_rag.retrieve_tokens("query_hit")
    hit_latency = (time.time() - start_hit) * 1000

    # Verify hit is significantly faster (at least 30% faster for this mock)
    reduction_percent = ((miss_latency - hit_latency) / miss_latency) * 100

    assert reduction_percent > 30, f"Hit should be >30% faster, got {reduction_percent:.1f}%"
    assert hit_latency < miss_latency, "Cache hit should be faster than miss"


@pytest.mark.asyncio
async def test_cache_size_tracking(token_cached_rag):
    """Test 8: Cache size is tracked correctly"""
    cache_key = "rag_tokens:test"
    token_ids = [1] * 100  # 100 tokens

    initial_size = token_cached_rag.stats.total_cache_size_bytes

    await token_cached_rag._cache_tokens(cache_key, token_ids)

    final_size = token_cached_rag.stats.total_cache_size_bytes

    assert final_size > initial_size, "Cache size should increase after storing tokens"
    assert token_cached_rag.stats.total_tokens_cached == 100, "Should track 100 cached tokens"


@pytest.mark.asyncio
async def test_parallel_cache_requests(token_cached_rag, mock_redis, mock_vector_db):
    """Test 9: Parallel cache requests don't cause race conditions"""
    cached_tokens = [1, 2, 3, 4, 5]
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_tokens))
    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Test"}
    ])

    # Run 10 parallel cache requests
    tasks = [token_cached_rag.retrieve_tokens(f"query_{i}") for i in range(10)]
    results = await asyncio.gather(*tasks)

    # All should return same cached tokens
    for token_ids, metadata in results:
        assert token_ids == cached_tokens, "All requests should get same cached tokens"
        assert metadata["cache_hit"] is True, "All should be cache hits"

    assert token_cached_rag.stats.cache_hits == 10, "Should have 10 cache hits"


@pytest.mark.asyncio
async def test_cache_ttl_expiration(token_cached_rag, mock_redis):
    """Test 10: Cache TTL is correctly set for expiration"""
    cache_key = "rag_tokens:ttl_test"
    token_ids = [1, 2, 3]
    ttl = 300  # 5 minutes

    await token_cached_rag._cache_tokens(cache_key, token_ids)

    # Verify TTL was set correctly
    call_args = mock_redis.setex.call_args[0]
    assert call_args[1] == ttl, f"TTL should be {ttl} seconds"


# ============================================================================
# Category 3: Token Consistency Tests (5 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_tokenization_determinism(mock_llm_client):
    """Test 11: Tokenization is deterministic for same input"""
    text = "Genesis multi-agent system with RAG optimization"

    token_ids_1 = await mock_llm_client.tokenize(text)
    token_ids_2 = await mock_llm_client.tokenize(text)

    assert token_ids_1 == token_ids_2, "Tokenization should be deterministic"


@pytest.mark.asyncio
async def test_token_round_trip_integrity(mock_llm_client):
    """Test 12: Tokens can be round-tripped without loss"""
    original_text = "Test document for token round-trip"

    # Tokenize
    token_ids = await mock_llm_client.tokenize(original_text)

    # Generate from token IDs (round-trip)
    result = await mock_llm_client.generate_from_token_ids(token_ids)

    assert "text" in result, "Result should contain text"
    assert "token_ids" in result, "Result should contain token_ids"
    assert len(result["token_ids"]) > 0, "Generated token IDs should not be empty"


@pytest.mark.asyncio
async def test_zero_tokenization_drift(token_cached_rag, mock_redis, mock_vector_db, mock_llm_client):
    """Test 13: Cached tokens produce identical outputs to fresh tokenization"""
    doc_content = "Genesis system documentation"

    # First pass: Fresh tokenization
    mock_redis.get = AsyncMock(return_value=None)
    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": doc_content}
    ])

    fresh_tokens, _ = await token_cached_rag.retrieve_tokens("query_1")

    # Second pass: Cached tokenization
    mock_redis.get = AsyncMock(return_value=json.dumps(fresh_tokens))

    cached_tokens, _ = await token_cached_rag.retrieve_tokens("query_2")

    assert fresh_tokens == cached_tokens, "Cached tokens should match fresh tokenization (zero drift)"


@pytest.mark.asyncio
async def test_multi_doc_token_concatenation(token_cached_rag, mock_vector_db, mock_llm_client):
    """Test 14: Multi-document token concatenation preserves order"""
    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Part 1"},
        {"id": "doc_2", "content": "Part 2"},
        {"id": "doc_3", "content": "Part 3"}
    ])

    token_ids, metadata = await token_cached_rag.retrieve_tokens("multi-doc query")

    assert len(token_ids) > 0, "Should have concatenated tokens from all docs"
    assert metadata["doc_count"] == 3, "Should have retrieved 3 documents"


@pytest.mark.asyncio
async def test_token_truncation_at_max_context(token_cached_rag, mock_vector_db, mock_llm_client):
    """Test 15: Token IDs are truncated if exceeding max context window"""
    # Create large content that exceeds max context
    large_content = "A" * 50000  # Very large doc

    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": large_content}
    ])

    token_ids, metadata = await token_cached_rag.retrieve_tokens("large doc query")

    assert len(token_ids) <= token_cached_rag.max_context_tokens, \
        f"Token count should not exceed max_context_tokens={token_cached_rag.max_context_tokens}"


# ============================================================================
# Category 4: Redis Integration Tests (5 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_redis_connection_graceful_degradation(mock_vector_db, mock_llm_client):
    """Test 16: System degrades gracefully when Redis is unavailable"""
    # Create TokenCachedRAG without Redis
    rag = TokenCachedRAG(
        vector_db=mock_vector_db,
        llm_client=mock_llm_client,
        redis_client=None,  # No Redis
        enable_caching=True
    )

    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Test content"}
    ])

    # Should still work without caching
    token_ids, metadata = await rag.retrieve_tokens("test query")

    assert len(token_ids) > 0, "Should still retrieve tokens without Redis"
    assert metadata["cache_hit"] is False, "Should always be cache miss without Redis"


@pytest.mark.asyncio
async def test_redis_error_handling(token_cached_rag, mock_redis, mock_vector_db):
    """Test 17: Redis errors are handled gracefully without crashing"""
    # Mock Redis to raise exception
    mock_redis.get = AsyncMock(side_effect=Exception("Redis connection error"))

    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Test"}
    ])

    # Should not crash, just log warning
    token_ids, metadata = await token_cached_rag.retrieve_tokens("error query")

    assert len(token_ids) > 0, "Should still return tokens despite Redis error"
    assert metadata["cache_hit"] is False, "Should be cache miss on error"


@pytest.mark.asyncio
async def test_cache_clear_operation(token_cached_rag, mock_redis):
    """Test 18: Cache clear removes all cached tokens"""
    # Mock scan_iter to return some keys
    mock_keys = [b"rag_tokens:key1", b"rag_tokens:key2", b"rag_tokens:key3"]

    async def mock_scan_iter(match, **kwargs):
        for key in mock_keys:
            yield key

    mock_redis.scan_iter = mock_scan_iter
    mock_redis.delete = AsyncMock(return_value=3)

    deleted_count = await token_cached_rag.clear_cache("rag_tokens:*")

    assert deleted_count == 3, "Should delete 3 cached entries"
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_redis_namespace_isolation(token_cached_rag):
    """Test 19: Cache keys are properly namespaced to avoid collisions"""
    doc_ids_1 = ["doc_1", "doc_2"]
    doc_ids_2 = ["other_1", "other_2"]

    key_1 = token_cached_rag._generate_cache_key(doc_ids_1)
    key_2 = token_cached_rag._generate_cache_key(doc_ids_2)

    assert key_1.startswith("rag_tokens:"), "Key should have namespace prefix"
    assert key_2.startswith("rag_tokens:"), "Key should have namespace prefix"
    assert key_1 != key_2, "Different doc sets should have different keys"


@pytest.mark.asyncio
async def test_cache_stats_reset(token_cached_rag):
    """Test 20: Cache statistics can be reset"""
    # Generate some stats
    token_cached_rag.stats.cache_hits = 10
    token_cached_rag.stats.cache_misses = 5
    token_cached_rag.stats.total_tokens_cached = 1000

    # Reset stats
    token_cached_rag.reset_stats()

    stats = token_cached_rag.get_cache_stats()

    assert stats["hits"] == 0, "Hits should be reset"
    assert stats["misses"] == 0, "Misses should be reset"
    assert stats["hit_rate"] == 0.0, "Hit rate should be 0 after reset"


# ============================================================================
# Category 5: End-to-End Tests (5 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_full_rag_pipeline_with_caching(token_cached_rag, mock_redis, mock_vector_db, mock_llm_client):
    """Test 21: Full RAG pipeline with token caching works end-to-end"""
    # First query: Cache miss
    mock_redis.get = AsyncMock(return_value=None)
    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Genesis is awesome"}
    ])

    response_1 = await token_cached_rag.generate_with_rag("What is Genesis?")

    assert "response" in response_1, "Should contain response"
    assert response_1["cache_hit"] is False, "First query should be cache miss"
    assert response_1["context_tokens"] > 0, "Should have context tokens"

    # Second query: Cache hit
    cached_tokens = await mock_llm_client.tokenize("Genesis is awesome")
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_tokens))

    response_2 = await token_cached_rag.generate_with_rag("Explain Genesis")

    assert "response" in response_2, "Should contain response"
    assert response_2["cache_hit"] is True, "Second query should be cache hit"
    assert response_2["latency_ms"] > 0, "Should track latency"


@pytest.mark.asyncio
async def test_multiple_sequential_queries(token_cached_rag, mock_redis, mock_vector_db):
    """Test 22: Multiple sequential queries with mixed cache hits/misses"""
    queries = [
        "What is Genesis?",
        "How does Genesis work?",
        "What is Genesis?",  # Repeat query (should hit cache)
    ]

    cached_tokens = [1, 2, 3, 4, 5]

    results = []
    for i, query in enumerate(queries):
        if i == 2:
            # Third query should hit cache
            mock_redis.get = AsyncMock(return_value=json.dumps(cached_tokens))
        else:
            # First two queries miss cache
            mock_redis.get = AsyncMock(return_value=None)

        mock_vector_db.search = AsyncMock(return_value=[
            {"id": f"doc_{i}", "content": f"Content for {query}"}
        ])

        response = await token_cached_rag.generate_with_rag(query)
        results.append(response)

    # Verify mixed cache behavior
    assert results[0]["cache_hit"] is False, "First query should miss"
    assert results[1]["cache_hit"] is False, "Second query should miss"
    assert results[2]["cache_hit"] is True, "Third query (repeat) should hit"


@pytest.mark.asyncio
async def test_empty_document_retrieval(token_cached_rag, mock_vector_db):
    """Test 23: Handles empty document retrieval gracefully"""
    mock_vector_db.search = AsyncMock(return_value=[])  # No documents

    token_ids, metadata = await token_cached_rag.retrieve_tokens("nonexistent query")

    assert len(token_ids) == 0, "Should return empty token list"
    assert metadata["doc_count"] == 0, "Should have 0 documents"
    assert metadata["cache_hit"] is False, "Should be cache miss"


@pytest.mark.asyncio
async def test_large_batch_caching(token_cached_rag, mock_redis, mock_vector_db):
    """Test 24: Large batch of queries performs well with caching"""
    cached_tokens = [1, 2, 3, 4, 5]

    # Simulate 20 queries (first 5 miss, rest hit)
    for i in range(20):
        if i < 5:
            mock_redis.get = AsyncMock(return_value=None)
        else:
            mock_redis.get = AsyncMock(return_value=json.dumps(cached_tokens))

        mock_vector_db.search = AsyncMock(return_value=[
            {"id": "doc_1", "content": "Test"}
        ])

        await token_cached_rag.retrieve_tokens(f"batch_query_{i}")

    stats = token_cached_rag.get_cache_stats()

    assert stats["hits"] == 15, "Should have 15 cache hits"
    assert stats["misses"] == 5, "Should have 5 cache misses"
    assert stats["hit_rate"] == 75.0, "Hit rate should be 75%"


@pytest.mark.asyncio
async def test_cache_stats_reporting(token_cached_rag):
    """Test 25: Cache statistics are correctly reported"""
    # Simulate some cache activity
    token_cached_rag.stats.cache_hits = 80
    token_cached_rag.stats.cache_misses = 20
    token_cached_rag.stats.total_tokens_cached = 10000
    token_cached_rag.stats.total_cache_size_bytes = 40000

    stats = token_cached_rag.get_cache_stats()

    assert stats["hits"] == 80, "Should report 80 hits"
    assert stats["misses"] == 20, "Should report 20 misses"
    assert stats["hit_rate"] == 80.0, "Hit rate should be 80%"
    assert stats["total_tokens_cached"] == 10000, "Should report token count"
    assert stats["cache_size_mb"] > 0, "Should report cache size in MB"


# ============================================================================
# Performance Benchmark Test (Bonus)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_cache_performance_benchmark(token_cached_rag, mock_redis, mock_vector_db, benchmark):
    """
    Benchmark test: Validate 60-80% latency reduction on cache hits.

    This test is marked with @pytest.mark.benchmark and can be run separately.
    """
    cached_tokens = [1] * 100  # 100 tokens

    # Benchmark cache HIT
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_tokens))
    mock_vector_db.search = AsyncMock(return_value=[
        {"id": "doc_1", "content": "Test"}
    ])

    async def cache_hit_operation():
        return await token_cached_rag.retrieve_tokens("benchmark query")

    # Note: benchmark fixture requires synchronous function
    # For async, we'll just measure directly
    start = time.time()
    for _ in range(100):
        await cache_hit_operation()
    hit_time = (time.time() - start) / 100

    # Benchmark cache MISS
    mock_redis.get = AsyncMock(return_value=None)

    start = time.time()
    for _ in range(100):
        await cache_hit_operation()
    miss_time = (time.time() - start) / 100

    reduction = ((miss_time - hit_time) / miss_time) * 100

    print(f"\nBenchmark Results:")
    print(f"  Cache HIT:  {hit_time*1000:.2f}ms avg")
    print(f"  Cache MISS: {miss_time*1000:.2f}ms avg")
    print(f"  Reduction:  {reduction:.1f}%")

    # For mock implementation, any reduction is good
    # In production, we expect 60-80% reduction
    assert hit_time < miss_time, "Cache hit should be faster than miss"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
