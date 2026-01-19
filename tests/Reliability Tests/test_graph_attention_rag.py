"""
Test Suite for Graph Attention RAG Optimization

Tests for Phase 6 Day 7 graph attention mechanism:
- GraphAttentionMechanism class
- AttentionGuidedGraphTraversal class
- HybridRAGRetriever integration

Target: 25% faster retrieval, >93% accuracy maintained

Author: Vanguard (MLOps Agent)
Date: October 24, 2025
"""

import asyncio
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from infrastructure.hybrid_rag_retriever import (
    GraphAttentionMechanism,
    AttentionGuidedGraphTraversal,
    HybridRAGRetriever,
    HybridSearchResult
)


# ========== UNIT TESTS (6 tests) ==========

class TestGraphAttentionMechanism:
    """Unit tests for GraphAttentionMechanism"""

    @pytest.mark.asyncio
    async def test_attention_score_computation(self):
        """
        Test 1: Verify attention score computation with softmax normalization.

        Success criteria:
        - Scores sum to 1.0 (softmax property)
        - All scores between 0 and 1
        - Higher similarity → higher attention
        """
        # Setup
        mock_embedding_gen = AsyncMock()
        attention = GraphAttentionMechanism(
            embedding_generator=mock_embedding_gen,
            redis_cache=None,  # No cache for unit test
            obs_manager=None
        )

        # Create query and candidate embeddings
        query_embedding = np.random.randn(768)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)  # Normalize

        # Candidate 1: High similarity (same direction)
        candidate1_emb = query_embedding * 0.9 + np.random.randn(768) * 0.1
        candidate1_emb = candidate1_emb / np.linalg.norm(candidate1_emb)

        # Candidate 2: Low similarity (orthogonal)
        candidate2_emb = np.random.randn(768)
        candidate2_emb = candidate2_emb / np.linalg.norm(candidate2_emb)

        candidate_nodes = [
            {"id": "node1", "embedding": candidate1_emb.tolist()},
            {"id": "node2", "embedding": candidate2_emb.tolist()},
        ]

        # Execute
        scores = await attention.compute_attention_scores(
            query_embedding,
            candidate_nodes
        )

        # Verify
        assert len(scores) == 2, "Should have scores for both nodes"
        assert abs(sum(scores.values()) - 1.0) < 0.001, "Scores should sum to 1.0 (softmax)"
        assert all(0 <= score <= 1 for score in scores.values()), "All scores should be in [0, 1]"

        # High similarity should have higher attention
        assert scores["node1"] > scores["node2"], "More similar node should have higher attention"

        print(f"✓ Test 1 PASSED: Attention scores = {scores}")

    @pytest.mark.asyncio
    async def test_attention_cache_functionality(self):
        """
        Test 2: Verify Redis cache hit/miss behavior.

        Success criteria:
        - Cache miss on first call
        - Cache hit on second call (same inputs)
        - Identical scores returned
        """
        # Setup mock Redis cache
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Cache miss first
        mock_redis.set = AsyncMock()

        mock_embedding_gen = AsyncMock()
        attention = GraphAttentionMechanism(
            embedding_generator=mock_embedding_gen,
            redis_cache=mock_redis,
            obs_manager=None
        )

        query_embedding = np.random.randn(768)
        candidate_nodes = [
            {"id": "node1", "embedding": np.random.randn(768).tolist()}
        ]

        # First call (cache miss)
        scores1 = await attention.compute_attention_scores(query_embedding, candidate_nodes)

        assert mock_redis.set.called, "Should write to cache on miss"
        assert attention._stats["cache_misses"] == 1, "Should record cache miss"
        assert attention._stats["cache_hits"] == 0, "No cache hits yet"

        # Second call (cache hit simulation)
        mock_redis.get = AsyncMock(return_value=f'{{"node1": {scores1["node1"]}}}'.encode())
        scores2 = await attention.compute_attention_scores(query_embedding, candidate_nodes)

        assert scores1 == scores2, "Cached scores should match original"
        assert attention._stats["cache_hits"] == 1, "Should record cache hit"

        print(f"✓ Test 2 PASSED: Cache hit rate = {attention.get_stats()['cache_hit_rate_pct']:.1f}%")

    def test_softmax_normalization(self):
        """
        Test 3: Verify softmax normalization correctness.

        Success criteria:
        - Scores sum to 1.0
        - Relative ordering preserved
        - Numerical stability (no overflow)
        """
        # Setup
        mock_embedding_gen = Mock()
        attention = GraphAttentionMechanism(
            embedding_generator=mock_embedding_gen,
            redis_cache=None,
            obs_manager=None
        )

        # Test case 1: Normal scores
        scores = {"node1": 2.0, "node2": 1.0, "node3": 0.5}
        normalized = attention._softmax(scores)

        assert abs(sum(normalized.values()) - 1.0) < 0.001, "Should sum to 1.0"
        assert normalized["node1"] > normalized["node2"] > normalized["node3"], "Ordering preserved"

        # Test case 2: Large scores (numerical stability)
        large_scores = {"node1": 1000.0, "node2": 999.0}
        normalized_large = attention._softmax(large_scores)

        assert abs(sum(normalized_large.values()) - 1.0) < 0.001, "Should handle large scores"
        assert not any(np.isnan(v) or np.isinf(v) for v in normalized_large.values()), "No overflow"

        # Test case 3: Empty scores
        empty_normalized = attention._softmax({})
        assert empty_normalized == {}, "Should handle empty input"

        print("✓ Test 3 PASSED: Softmax normalization correct")


class TestAttentionGuidedGraphTraversal:
    """Unit tests for AttentionGuidedGraphTraversal"""

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(self):
        """
        Test 4: Verify priority queue explores highest-attention nodes first.

        Success criteria:
        - Highest attention nodes visited first
        - Priority queue ordering maintained
        - Results sorted by attention score
        """
        # Setup mock graph database
        mock_graph_db = MagicMock()
        mock_graph_db.graph = MagicMock()
        mock_graph_db.graph.nodes = {
            "node1": {"content": "test1"},
            "node2": {"content": "test2"},
            "node3": {"content": "test3"}
        }
        mock_graph_db.graph.successors = MagicMock(side_effect=lambda n: [])  # No neighbors

        # Setup mock attention mechanism (higher scores for lower node IDs)
        mock_attention = AsyncMock()
        mock_attention.compute_attention_scores = AsyncMock(return_value={
            "node1": 0.6,  # Highest
            "node2": 0.3,
            "node3": 0.1   # Lowest
        })

        traversal = AttentionGuidedGraphTraversal(
            graph_db=mock_graph_db,
            attention_mechanism=mock_attention,
            obs_manager=None,
            max_depth=2,
            top_k=10
        )

        # Execute
        query_embedding = np.random.randn(768)
        results = await traversal.traverse(
            query_embedding=query_embedding,
            start_nodes=["node1", "node2", "node3"]
        )

        # Verify ordering (should be sorted by attention score descending)
        assert len(results) >= 2, "Should return multiple results"
        for i in range(len(results) - 1):
            assert results[i]["attention_score"] >= results[i+1]["attention_score"], \
                "Results should be sorted by attention score (descending)"

        print(f"✓ Test 4 PASSED: Results ordered correctly, top score = {results[0]['attention_score']:.2f}")

    @pytest.mark.asyncio
    async def test_attention_threshold_pruning(self):
        """
        Test 5: Verify low-attention nodes are pruned.

        Success criteria:
        - Nodes below threshold not explored
        - Pruning count tracked correctly
        - Efficiency improved
        """
        # Setup mock graph with neighbors
        mock_graph_db = MagicMock()
        mock_graph_db.graph = MagicMock()
        mock_graph_db.graph.nodes = {
            "start": {"content": "start"},
            "high_attn": {"content": "high"},
            "low_attn": {"content": "low"}
        }
        mock_graph_db.graph.successors = MagicMock(side_effect=lambda n: {
            "start": ["high_attn", "low_attn"]
        }.get(n, []))

        # Mock attention: high_attn above threshold, low_attn below
        mock_attention = AsyncMock()
        async def attention_side_effect(query_embedding, candidate_nodes):
            scores = {}
            for node in candidate_nodes:
                if node["id"] == "high_attn":
                    scores[node["id"]] = 0.8  # Above threshold (0.05)
                elif node["id"] == "low_attn":
                    scores[node["id"]] = 0.02  # Below threshold
            return scores

        mock_attention.compute_attention_scores = AsyncMock(side_effect=attention_side_effect)

        traversal = AttentionGuidedGraphTraversal(
            graph_db=mock_graph_db,
            attention_mechanism=mock_attention,
            obs_manager=None,
            max_depth=2,
            top_k=10,
            attention_threshold=0.05  # Explicit threshold
        )

        # Execute
        query_embedding = np.random.randn(768)
        results = await traversal.traverse(
            query_embedding=query_embedding,
            start_nodes=["start"]
        )

        # Verify pruning
        result_ids = {r["id"] for r in results}
        assert "start" in result_ids, "Start node should be in results"
        assert "high_attn" in result_ids, "High attention node should be explored"
        assert "low_attn" not in result_ids, "Low attention node should be pruned"

        stats = traversal.get_stats()
        assert stats["avg_nodes_pruned"] > 0, "Should track pruned nodes"

        print(f"✓ Test 5 PASSED: Pruned {stats['avg_nodes_pruned']:.1f} low-attention nodes")

    @pytest.mark.asyncio
    async def test_max_depth_limit(self):
        """
        Test 6: Verify max_depth constraint is respected.

        Success criteria:
        - Traversal stops at max_depth
        - No nodes beyond max_depth explored
        - Depth tracked correctly
        """
        # Setup mock graph with deep chain: start → level1 → level2 → level3
        mock_graph_db = MagicMock()
        mock_graph_db.graph = MagicMock()
        mock_graph_db.graph.nodes = {
            "start": {"content": "start"},
            "level1": {"content": "level1"},
            "level2": {"content": "level2"},
            "level3": {"content": "level3"}
        }
        mock_graph_db.graph.successors = MagicMock(side_effect=lambda n: {
            "start": ["level1"],
            "level1": ["level2"],
            "level2": ["level3"]
        }.get(n, []))

        # Mock attention (all nodes high attention)
        mock_attention = AsyncMock()
        mock_attention.compute_attention_scores = AsyncMock(return_value={
            "level1": 0.9, "level2": 0.9, "level3": 0.9
        })

        traversal = AttentionGuidedGraphTraversal(
            graph_db=mock_graph_db,
            attention_mechanism=mock_attention,
            obs_manager=None,
            max_depth=2,  # Should reach level2 but not level3
            top_k=10
        )

        # Execute
        query_embedding = np.random.randn(768)
        results = await traversal.traverse(
            query_embedding=query_embedding,
            start_nodes=["start"]
        )

        # Verify depth constraint
        result_ids = {r["id"] for r in results}
        max_result_depth = max(r["depth"] for r in results)

        assert "start" in result_ids, "Start node (depth 0) should be in results"
        assert "level1" in result_ids, "Level 1 node (depth 1) should be in results"
        assert "level2" in result_ids, "Level 2 node (depth 2) should be in results"
        assert "level3" not in result_ids, "Level 3 node (depth 3) should NOT be in results"
        assert max_result_depth <= 2, f"Max depth should be 2, got {max_result_depth}"

        print(f"✓ Test 6 PASSED: Max depth {traversal.max_depth} respected")


# ========== INTEGRATION TESTS (3 tests) ==========

class TestHybridRAGIntegration:
    """Integration tests for graph attention with HybridRAGRetriever"""

    @pytest.mark.asyncio
    async def test_hybrid_rag_with_attention_enabled(self):
        """
        Test 7: End-to-end hybrid search with graph attention enabled.

        Success criteria:
        - Both vector and attention-guided graph retrieval execute
        - RRF fusion works correctly
        - Results have proper metadata
        """
        # Setup mocks
        mock_vector_db = AsyncMock()
        mock_vector_db.search = AsyncMock(return_value=[
            MagicMock(id="vec:1:key1", metadata={"value": "result1"}),
            MagicMock(id="vec:1:key2", metadata={"value": "result2"})
        ])

        mock_graph_db = MagicMock()
        mock_graph_db.graph = MagicMock()
        mock_graph_db.graph.nodes = {
            "vec:1:key1": {"content": "overlap"},
            "graph:1:key3": {"content": "graph_only"}
        }
        mock_graph_db.graph.successors = MagicMock(return_value=[])

        mock_embedding_gen = AsyncMock()
        mock_embedding_gen.generate_embedding = AsyncMock(return_value=np.random.randn(768))

        # Create retriever with attention enabled
        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen,
            use_graph_attention=True
        )

        # Execute
        results = await retriever.hybrid_search(
            query="test query",
            namespace_filter=("vec", "1"),
            top_k=5
        )

        # Verify
        assert isinstance(results, list), "Should return list of results"
        assert retriever._stats["hybrid_attention_searches"] > 0, "Should track attention searches"

        print(f"✓ Test 7 PASSED: Hybrid search with attention completed, {len(results)} results")

    @pytest.mark.asyncio
    async def test_feature_flag_switching(self):
        """
        Test 8: Verify feature flag enables/disables attention correctly.

        Success criteria:
        - use_graph_attention=True enables attention
        - use_graph_attention=False uses baseline
        - Both modes work without errors
        """
        # Setup mocks
        mock_vector_db = AsyncMock()
        mock_vector_db.search = AsyncMock(return_value=[])

        mock_graph_db = MagicMock()
        mock_graph_db.graph = MagicMock()
        mock_graph_db.graph.nodes = {}
        mock_graph_db.traverse = AsyncMock(return_value=set())

        mock_embedding_gen = AsyncMock()
        mock_embedding_gen.generate_embedding = AsyncMock(return_value=np.random.randn(768))

        # Test with attention ENABLED
        retriever_with_attention = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen,
            use_graph_attention=True
        )

        assert retriever_with_attention.graph_attention is not None, "Should have attention mechanism"
        assert retriever_with_attention.attention_guided_traversal is not None, "Should have attention traversal"

        # Test with attention DISABLED
        retriever_without_attention = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen,
            use_graph_attention=False
        )

        assert retriever_without_attention.graph_attention is None, "Should NOT have attention mechanism"
        assert retriever_without_attention.attention_guided_traversal is None, "Should NOT have attention traversal"

        # Execute both (should not error)
        await retriever_with_attention.hybrid_search(query="test", namespace_filter=("ns", "1"), top_k=5)
        await retriever_without_attention.hybrid_search(query="test", namespace_filter=("ns", "1"), top_k=5)

        print("✓ Test 8 PASSED: Feature flag switching works correctly")

    @pytest.mark.asyncio
    async def test_cache_persistence(self):
        """
        Test 9: Verify Redis cache TTL behavior for attention scores.

        Success criteria:
        - Cache keys generated deterministically
        - TTL set correctly (5 minutes = 300 seconds)
        - Cache reused for identical queries
        """
        # Setup mock Redis
        mock_redis = AsyncMock()
        cache_data = {}

        async def mock_get(key):
            return cache_data.get(key)

        async def mock_set(key, value, ex=None):
            cache_data[key] = value
            return True

        mock_redis.get = AsyncMock(side_effect=mock_get)
        mock_redis.set = AsyncMock(side_effect=mock_set)

        mock_embedding_gen = AsyncMock()
        attention = GraphAttentionMechanism(
            embedding_generator=mock_embedding_gen,
            redis_cache=mock_redis,
            obs_manager=None
        )

        query_embedding = np.random.randn(768)
        candidate_nodes = [
            {"id": "node1", "embedding": np.random.randn(768).tolist()}
        ]

        # First call (cache miss)
        await attention.compute_attention_scores(query_embedding, candidate_nodes)

        # Verify cache was written with TTL=300
        assert mock_redis.set.called, "Should write to cache"
        call_args = mock_redis.set.call_args
        assert call_args.kwargs.get("ex") == 300, "TTL should be 300 seconds (5 minutes)"

        # Verify cache key is deterministic
        cache_key1 = attention._compute_cache_key(query_embedding, candidate_nodes)
        cache_key2 = attention._compute_cache_key(query_embedding, candidate_nodes)
        assert cache_key1 == cache_key2, "Cache key should be deterministic"

        print(f"✓ Test 9 PASSED: Cache TTL = 300s, key = {cache_key1[:32]}...")


# ========== BENCHMARK TESTS (3 tests) ==========

@pytest.mark.benchmark
class TestGraphAttentionPerformance:
    """Benchmark tests for graph attention optimization"""

    @pytest.mark.asyncio
    async def test_retrieval_speed_improvement(self):
        """
        Test 10 (BENCHMARK): Validate 25% faster retrieval with graph attention.

        Success criteria:
        - Attention-guided ≥20% faster than baseline
        - Target: 25% speedup (200ms → 150ms P95)
        - Measured over 20+ queries
        """
        import time

        # This test requires real graph database and embeddings
        # For now, we'll create a simulation with controlled timing
        pytest.skip("Benchmark requires production graph database")

        # Expected implementation:
        # 1. Load real graph database with 100+ nodes
        # 2. Run 20 queries with baseline traversal
        # 3. Run same 20 queries with attention-guided traversal
        # 4. Compare P95 latencies
        # 5. Assert: attention_p95 <= baseline_p95 * 0.75 (25% faster)

    @pytest.mark.asyncio
    async def test_accuracy_preservation(self):
        """
        Test 11 (BENCHMARK): Validate accuracy ≥93% maintained.

        Success criteria:
        - Top-3 accuracy ≥93% (baseline: 94.8%)
        - Top-5 accuracy ≥95%
        - Top-10 accuracy ≥97%
        - Measured on 50+ test queries with ground truth
        """
        pytest.skip("Benchmark requires ground truth dataset")

        # Expected implementation:
        # 1. Load ground truth dataset (50+ query/answer pairs)
        # 2. Run retrieval with attention-guided traversal
        # 3. Compute top-k accuracy (k=3,5,10)
        # 4. Assert: top3_accuracy >= 0.93

    @pytest.mark.asyncio
    async def test_cache_hit_rate_validation(self):
        """
        Test 12 (BENCHMARK): Validate 30-40% cache hit rate.

        Success criteria:
        - Cache hit rate between 30-40%
        - Measured on realistic query patterns
        - Repeated similar queries increase hit rate
        """
        pytest.skip("Benchmark requires production workload simulation")

        # Expected implementation:
        # 1. Generate 100 queries with 30-40% similarity
        # 2. Run through attention mechanism
        # 3. Measure cache hit rate
        # 4. Assert: 0.30 <= hit_rate <= 0.50 (allow 10% margin)


# ========== PYTEST CONFIGURATION ==========

def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers", "benchmark: mark test as a benchmark test (requires production data)"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
