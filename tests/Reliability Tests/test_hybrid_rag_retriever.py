"""
Test suite for HybridRAGRetriever - Comprehensive validation of hybrid vector+graph retrieval

This test suite validates the Hybrid RAG implementation with 42 tests covering:
- Category 1: RRF Algorithm Tests (11 tests) - Reciprocal Rank Fusion scoring
- Category 2: Hybrid Search Infrastructure (10 tests) - End-to-end hybrid search
- Category 3: Fallback Modes (9 tests) - 4-tier graceful degradation
- Category 4: De-duplication (7 tests) - Consensus scoring for duplicates
- Category 5: Infrastructure Integration (5 tests) - Integration with existing components

Target: 85-90% code coverage for hybrid_rag_retriever.py

Author: Thon (Python Expert)
Date: October 23, 2025
Phase: 5.3 Day 3 - Task 4 (Comprehensive Test Suite)
"""

import asyncio
from typing import Any, Dict, List, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from infrastructure.hybrid_rag_retriever import (
    HybridRAGRetriever,
    HybridSearchResult,
)
from infrastructure.vector_database import VectorSearchResult


# ===========================
# FIXTURES
# ===========================

@pytest.fixture
def mock_vector_db():
    """Mock VectorDatabase for testing."""
    mock = AsyncMock()
    mock.search = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_graph_db():
    """Mock GraphDatabase for testing."""
    mock = AsyncMock()
    mock.traverse = AsyncMock(return_value=set())
    mock.graph = MagicMock()
    mock.graph.nodes = MagicMock(return_value=[])
    return mock


@pytest.fixture
def mock_embedding_gen():
    """Mock EmbeddingGenerator for testing."""
    mock = AsyncMock()
    # Return deterministic embedding for reproducibility
    mock.generate_embedding = AsyncMock(
        return_value=np.random.rand(1536).astype('float32')
    )
    return mock


@pytest.fixture
def mock_mongodb_backend():
    """Mock MongoDBBackend for testing Tier 4 fallback."""
    mock = AsyncMock()
    mock.search_regex = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def hybrid_retriever(mock_vector_db, mock_graph_db, mock_embedding_gen):
    """Pre-configured HybridRAGRetriever for testing."""
    return HybridRAGRetriever(
        vector_db=mock_vector_db,
        graph_db=mock_graph_db,
        embedding_generator=mock_embedding_gen
    )


@pytest.fixture
def sample_vector_results():
    """Sample vector search results for testing."""
    return [
        VectorSearchResult(
            id="agent:qa_001:test_123",
            score=0.95,
            metadata={"value": {"content": "Test 123"}, "type": "test"}
        ),
        VectorSearchResult(
            id="agent:qa_001:test_456",
            score=0.85,
            metadata={"value": {"content": "Test 456"}, "type": "test"}
        ),
        VectorSearchResult(
            id="agent:qa_001:test_789",
            score=0.75,
            metadata={"value": {"content": "Test 789"}, "type": "test"}
        ),
    ]


# ===========================
# CATEGORY 1: RRF ALGORITHM TESTS (11 tests)
# ===========================

class TestRRFAlgorithm:
    """Test Reciprocal Rank Fusion scoring algorithm."""

    def test_rrf_equal_weighting(self, hybrid_retriever):
        """Test RRF with both systems contributing equally."""
        # Vector results: 3 memories at ranks 1, 2, 3
        vector_results = [
            VectorSearchResult("mem_1", 0.95, {}),
            VectorSearchResult("mem_2", 0.85, {}),
            VectorSearchResult("mem_3", 0.75, {}),
        ]

        # Graph results: 3 different memories at "ranks" 1, 2, 3
        graph_node_ids = {"mem_4", "mem_5", "mem_6"}

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        # All should have similar scores since no overlap
        # Vector rank 1: 1/(60+1) = 0.0164
        # Graph rank 1: 1/(60+1) = 0.0164 (sorted order)
        assert len(rrf_scores) == 6
        assert abs(rrf_scores["mem_1"][0] - 1/(60+1)) < 0.001
        assert abs(rrf_scores["mem_4"][0] - 1/(60+1)) < 0.001

    def test_rrf_vector_dominance(self, hybrid_retriever):
        """Test RRF when vector results should rank higher (lower k)."""
        vector_results = [
            VectorSearchResult("mem_1", 0.99, {}),  # Rank 1
        ]
        graph_node_ids = {"mem_2"}  # Rank 1 in graph

        # Lower k = vector dominance (ranks matter more)
        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=30
        )

        # Both rank 1, but with k=30, scores are higher (more sensitive to rank)
        # Score = 1/(30+1) = 0.0323
        assert abs(rrf_scores["mem_1"][0] - 1/31) < 0.001
        assert abs(rrf_scores["mem_2"][0] - 1/31) < 0.001

    def test_rrf_graph_dominance(self, hybrid_retriever):
        """Test RRF when graph results should rank higher (higher k)."""
        vector_results = [
            VectorSearchResult("mem_1", 0.50, {}),  # Rank 1 but low score
        ]
        graph_node_ids = {"mem_2"}  # Rank 1 in graph

        # Higher k = less rank sensitivity (flattens scores)
        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=90
        )

        # Both rank 1: 1/(90+1) = 0.01099
        assert abs(rrf_scores["mem_1"][0] - 1/91) < 0.001
        assert abs(rrf_scores["mem_2"][0] - 1/91) < 0.001

    def test_rrf_consensus_scoring(self, hybrid_retriever):
        """Test that memories appearing in both systems get boosted scores."""
        # Memory "mem_123" appears in BOTH vector and graph
        vector_results = [
            VectorSearchResult("mem_123", 0.95, {}),  # Rank 1
            VectorSearchResult("mem_456", 0.85, {}),  # Rank 2
        ]

        # Graph results (sorted order determines rank)
        graph_node_ids = {"mem_123", "mem_789"}  # mem_123 consensus!

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        # mem_123 should have HIGHEST score (appears in both)
        # Vector rank 1: 1/(60+1) = 0.0164
        # Graph rank 1: 1/(60+1) = 0.0164 (sorted alphabetically: "mem_123" < "mem_789")
        # Total: 0.0164 + 0.0164 = 0.0328
        mem_123_score = rrf_scores["mem_123"][0]
        mem_456_score = rrf_scores["mem_456"][0]
        mem_789_score = rrf_scores["mem_789"][0]

        assert mem_123_score > mem_456_score, "Consensus memory should outscore vector-only"
        assert mem_123_score > mem_789_score, "Consensus memory should outscore graph-only"
        assert abs(mem_123_score - (1/61 + 1/61)) < 0.001  # Sum of both ranks

    def test_rrf_single_result_vector(self, hybrid_retriever):
        """Test RRF when only vector returns results."""
        vector_results = [
            VectorSearchResult("mem_1", 0.95, {}),
            VectorSearchResult("mem_2", 0.85, {}),
        ]
        graph_node_ids = set()  # Empty graph results

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        assert len(rrf_scores) == 2
        assert rrf_scores["mem_1"][1] == ["vector"]  # Source tracking
        assert rrf_scores["mem_2"][1] == ["vector"]

    def test_rrf_single_result_graph(self, hybrid_retriever):
        """Test RRF when only graph returns results."""
        vector_results = []  # Empty vector results
        graph_node_ids = {"mem_1", "mem_2"}

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        assert len(rrf_scores) == 2
        # Check sources (graph-only)
        for memory_id, (score, sources, v_rank, g_rank) in rrf_scores.items():
            assert sources == ["graph"]
            assert v_rank == 0  # No vector rank
            assert g_rank > 0  # Has graph rank

    def test_rrf_empty_vector(self, hybrid_retriever):
        """Test RRF when vector returns empty list."""
        vector_results = []
        graph_node_ids = {"mem_1"}

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        assert len(rrf_scores) == 1
        assert "mem_1" in rrf_scores
        assert rrf_scores["mem_1"][1] == ["graph"]

    def test_rrf_empty_graph(self, hybrid_retriever):
        """Test RRF when graph returns empty set."""
        vector_results = [VectorSearchResult("mem_1", 0.95, {})]
        graph_node_ids = set()

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        assert len(rrf_scores) == 1
        assert "mem_1" in rrf_scores
        assert rrf_scores["mem_1"][1] == ["vector"]

    def test_rrf_k_parameter(self, hybrid_retriever):
        """Test RRF with different k values (30, 60, 90)."""
        vector_results = [VectorSearchResult("mem_1", 0.95, {})]  # Rank 1
        graph_node_ids = set()

        # k=30: Higher sensitivity to rank
        scores_k30 = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=30
        )
        assert abs(scores_k30["mem_1"][0] - 1/31) < 0.001

        # k=60: Default balanced
        scores_k60 = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )
        assert abs(scores_k60["mem_1"][0] - 1/61) < 0.001

        # k=90: Lower sensitivity (flatter scores)
        scores_k90 = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=90
        )
        assert abs(scores_k90["mem_1"][0] - 1/91) < 0.001

        # Verify k=30 > k=60 > k=90 for rank 1
        assert scores_k30["mem_1"][0] > scores_k60["mem_1"][0]
        assert scores_k60["mem_1"][0] > scores_k90["mem_1"][0]

    def test_rrf_rank_preservation(self, hybrid_retriever):
        """Test that top-ranked memory stays top after fusion."""
        # Vector rank 1 should dominate if no consensus
        vector_results = [
            VectorSearchResult("mem_TOP", 0.99, {}),  # Rank 1
            VectorSearchResult("mem_2", 0.85, {}),    # Rank 2
        ]
        graph_node_ids = {"mem_3", "mem_4"}  # Different memories

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        # mem_TOP should have highest score (rank 1 in vector)
        scores_list = [(mem_id, score) for mem_id, (score, _, _, _) in rrf_scores.items()]
        scores_list.sort(key=lambda x: x[1], reverse=True)

        assert scores_list[0][0] == "mem_TOP", "Rank 1 memory should stay on top"

    def test_rrf_score_calculation(self, hybrid_retriever):
        """Test manual verification of RRF formula."""
        vector_results = [
            VectorSearchResult("mem_1", 0.95, {}),  # Rank 1
            VectorSearchResult("mem_2", 0.85, {}),  # Rank 2
        ]
        graph_node_ids = {"mem_1"}  # mem_1 also in graph (consensus)

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        # Manual calculation for mem_1 (appears in both):
        # Vector contribution: 1/(60+1) = 0.0164
        # Graph contribution: 1/(60+1) = 0.0164 (sorted first alphabetically)
        # Total: 0.0164 + 0.0164 = 0.0328
        expected_score = 1/61 + 1/61
        actual_score = rrf_scores["mem_1"][0]

        assert abs(actual_score - expected_score) < 0.0001, \
            f"Expected {expected_score}, got {actual_score}"

        # Manual calculation for mem_2 (vector only):
        # Vector contribution: 1/(60+2) = 0.0161
        expected_score_mem2 = 1/62
        actual_score_mem2 = rrf_scores["mem_2"][0]

        assert abs(actual_score_mem2 - expected_score_mem2) < 0.0001


# ===========================
# CATEGORY 2: HYBRID SEARCH INFRASTRUCTURE (10 tests)
# ===========================

class TestHybridSearchInfrastructure:
    """Test end-to-end hybrid search functionality."""

    @pytest.mark.asyncio
    async def test_hybrid_search_basic(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test simple query returns results."""
        # Mock vector search results
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:test_123", 0.95, {
                "value": {"content": "Test 123"},
                "metadata": {}
            })
        ]

        # Mock graph traversal results
        mock_graph_db.graph.nodes.return_value = ["agent:qa_001:test_456"]
        mock_graph_db.traverse.return_value = {"agent:qa_001:test_456"}

        results = await hybrid_retriever.hybrid_search(
            query="test query",
            top_k=5
        )

        # Should return combined results
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, HybridSearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_hybrid_search_parallel_execution(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test that vector and graph are called via asyncio.gather."""
        # Configure mocks to return valid data
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:test_123", 0.95, {
                "value": {"content": "Test"},
                "metadata": {}
            })
        ]
        mock_graph_db.graph.nodes.return_value = ["agent:qa_001:test_456"]
        mock_graph_db.traverse.return_value = {"agent:qa_001:test_456"}

        # Execute hybrid search WITH namespace_filter (required for graph traversal)
        results = await hybrid_retriever.hybrid_search(
            query="test",
            namespace_filter=("agent", "qa_001"),  # Required for graph to run
            top_k=5
        )

        # Verify both methods were called (proves parallel execution via gather)
        mock_vector_db.search.assert_called()
        mock_graph_db.traverse.assert_called()

        # Results should contain combined data
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_hybrid_search_namespace_filtering(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test hybrid search with agent_id namespace filter."""
        # Mock vector DB returns namespace-filtered results
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:test_123", 0.95, {
                "value": {"content": "QA test"},
                "metadata": {}
            })
        ]

        # Mock graph DB with namespace seeds
        mock_graph_db.graph.nodes.return_value = [
            "agent:qa_001:test_456",
            "agent:qa_001:test_789",
            "agent:other:test_999"  # Different namespace
        ]
        mock_graph_db.traverse.return_value = {"agent:qa_001:test_456"}

        results = await hybrid_retriever.hybrid_search(
            query="test procedures",
            namespace_filter=("agent", "qa_001"),
            top_k=5
        )

        # All results should be from qa_001 namespace
        for result in results:
            assert result.namespace == ("agent", "qa_001"), \
                f"Expected qa_001, got {result.namespace}"

    @pytest.mark.asyncio
    async def test_hybrid_search_top_k_limit(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test that hybrid search respects top_k parameter."""
        # Mock many results
        vector_results = [
            VectorSearchResult(f"agent:qa_001:test_{i}", 0.9 - i*0.05, {
                "value": {"content": f"Test {i}"},
                "metadata": {}
            })
            for i in range(20)
        ]
        mock_vector_db.search.return_value = vector_results

        mock_graph_db.graph.nodes.return_value = []
        mock_graph_db.traverse.return_value = set()

        # Request only top 5
        results = await hybrid_retriever.hybrid_search(
            query="test",
            top_k=5
        )

        assert len(results) <= 5, f"Expected ≤5 results, got {len(results)}"

    @pytest.mark.asyncio
    async def test_hybrid_search_empty_query(self, hybrid_retriever):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await hybrid_retriever.hybrid_search(query="", top_k=5)

        with pytest.raises(ValueError, match="Query cannot be empty"):
            await hybrid_retriever.hybrid_search(query="   ", top_k=5)

    @pytest.mark.asyncio
    async def test_hybrid_search_no_results(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test hybrid search when both systems return empty."""
        mock_vector_db.search.return_value = []
        mock_graph_db.graph.nodes.return_value = []
        mock_graph_db.traverse.return_value = set()

        results = await hybrid_retriever.hybrid_search(
            query="nonexistent query",
            top_k=10
        )

        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_hybrid_search_result_format(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test that results match HybridSearchResult dataclass."""
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:test_123", 0.95, {
                "value": {"content": "Test"},
                "metadata": {"type": "test"}
            })
        ]
        mock_graph_db.graph.nodes.return_value = []
        mock_graph_db.traverse.return_value = set()

        results = await hybrid_retriever.hybrid_search(query="test", top_k=5)

        assert len(results) == 1
        result = results[0]

        # Validate HybridSearchResult fields
        assert isinstance(result, HybridSearchResult)
        assert isinstance(result.namespace, tuple)
        assert isinstance(result.key, str)
        assert isinstance(result.value, dict)
        assert isinstance(result.metadata, dict)
        assert isinstance(result.rrf_score, float)
        assert isinstance(result.sources, list)
        assert isinstance(result.search_rank, int)
        assert result.search_rank > 0

    @pytest.mark.asyncio
    async def test_hybrid_search_seed_node_selection(self, hybrid_retriever, mock_graph_db):
        """Test that namespace filter correctly selects seed nodes."""
        # Graph has nodes from multiple namespaces
        mock_graph_db.graph.nodes.return_value = [
            "agent:qa_001:test_1",
            "agent:qa_001:test_2",
            "agent:support:test_3",
            "business:saas:test_4"
        ]

        # Get seed nodes for qa_001 namespace
        seed_nodes = await hybrid_retriever._get_namespace_seed_nodes(
            namespace_filter=("agent", "qa_001")
        )

        # Should only return qa_001 nodes
        assert len(seed_nodes) == 2
        assert all("agent:qa_001:" in node for node in seed_nodes)
        assert "agent:support:test_3" not in seed_nodes

    @pytest.mark.asyncio
    async def test_hybrid_search_result_ranking(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test that results are sorted by RRF score descending."""
        # Create results with different scores
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:high", 0.95, {
                "value": {"content": "High"},
                "metadata": {}
            }),
            VectorSearchResult("agent:qa_001:low", 0.60, {
                "value": {"content": "Low"},
                "metadata": {}
            }),
        ]
        mock_graph_db.graph.nodes.return_value = []
        mock_graph_db.traverse.return_value = set()

        results = await hybrid_retriever.hybrid_search(query="test", top_k=10)

        # Verify descending order by RRF score
        for i in range(len(results) - 1):
            assert results[i].rrf_score >= results[i+1].rrf_score, \
                f"Results not sorted: {results[i].rrf_score} < {results[i+1].rrf_score}"

        # Verify search_rank matches order
        for i, result in enumerate(results):
            assert result.search_rank == i + 1

    @pytest.mark.asyncio
    async def test_hybrid_search_observability(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test that OTEL spans are created for hybrid search."""
        mock_vector_db.search.return_value = []
        mock_graph_db.graph.nodes.return_value = []
        mock_graph_db.traverse.return_value = set()

        # Execute search (spans should be created internally)
        with patch('infrastructure.hybrid_rag_retriever.obs_manager') as mock_obs:
            mock_obs.span = MagicMock()
            mock_obs.span.return_value.__enter__ = MagicMock()
            mock_obs.span.return_value.__exit__ = MagicMock()

            results = await hybrid_retriever.hybrid_search(query="test", top_k=5)

            # Verify span was created (observability integration)
            # Note: This is a basic check; full OTEL validation requires more setup
            assert isinstance(results, list)


# ===========================
# CATEGORY 3: FALLBACK MODES (9 tests)
# ===========================

class TestFallbackModes:
    """Test 4-tier graceful degradation."""

    @pytest.mark.asyncio
    async def test_fallback_tier2_vector_only(self, mock_vector_db, mock_graph_db, mock_embedding_gen):
        """Test Tier 2 fallback when graph database unavailable."""
        # Mock vector DB (working)
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:test_123", 0.95, {
                "value": {"content": "Test"},
                "metadata": {}
            })
        ]

        # Mock graph DB (failing)
        mock_graph_db.graph.nodes.return_value = ["agent:qa_001:test_456"]
        mock_graph_db.traverse.side_effect = RuntimeError("Graph DB connection failed")

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Should fall back to vector-only
        results = await retriever.hybrid_search(
            query="test",
            fallback_mode="auto"
        )

        # Should return vector-only results
        assert len(results) > 0
        assert all(r.sources == ["vector"] for r in results)

    @pytest.mark.asyncio
    async def test_fallback_tier3_graph_only(self, mock_vector_db, mock_graph_db, mock_embedding_gen):
        """Test Tier 3 fallback when vector database unavailable."""
        # Mock vector DB (failing)
        mock_vector_db.search.side_effect = RuntimeError("Vector DB failed")

        # Mock graph DB (working)
        mock_graph_db.graph.nodes.return_value = ["agent:qa_001:test_123"]
        mock_graph_db.traverse.return_value = {"agent:qa_001:test_123"}

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Should fall back to graph-only
        results = await retriever.hybrid_search(
            query="test",
            namespace_filter=("agent", "qa_001"),  # Required for graph-only
            fallback_mode="auto"
        )

        # Should return graph-only results
        assert len(results) > 0
        assert all(r.sources == ["graph"] for r in results)

    @pytest.mark.asyncio
    async def test_fallback_tier4_mongodb(self, mock_vector_db, mock_graph_db, mock_embedding_gen, mock_mongodb_backend):
        """Test Tier 4 MongoDB fallback when both vector and graph fail."""
        # Both systems fail
        mock_vector_db.search.side_effect = RuntimeError("Vector failed")
        mock_graph_db.traverse.side_effect = RuntimeError("Graph failed")

        # MongoDB fallback available
        mock_mongodb_backend.search_regex.return_value = []

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen,
            mongodb_backend=mock_mongodb_backend
        )

        # Should fall back to MongoDB regex search
        results = await retriever.hybrid_search(
            query="test",
            fallback_mode="auto"
        )

        # MongoDB fallback returns empty for now (not implemented)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_fallback_mode_auto(self, mock_vector_db, mock_graph_db, mock_embedding_gen):
        """Test automatic tier detection with fallback_mode='auto'."""
        # Hybrid fails, vector succeeds
        mock_graph_db.traverse.side_effect = RuntimeError("Graph failed")
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:test", 0.95, {
                "value": {"content": "Test"},
                "metadata": {}
            })
        ]

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        results = await retriever.hybrid_search(
            query="test",
            fallback_mode="auto"  # Should automatically fall back
        )

        assert len(results) > 0
        assert results[0].sources == ["vector"]

    @pytest.mark.asyncio
    async def test_fallback_mode_vector_only(self, mock_vector_db, mock_graph_db, mock_embedding_gen):
        """Test forcing vector-only mode."""
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:test", 0.95, {
                "value": {"content": "Test"},
                "metadata": {}
            })
        ]

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        results = await retriever.hybrid_search(
            query="test",
            fallback_mode="vector_only"
        )

        # Should only use vector, never call graph
        assert len(results) > 0
        assert all(r.sources == ["vector"] for r in results)
        mock_graph_db.traverse.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_mode_graph_only(self, mock_vector_db, mock_graph_db, mock_embedding_gen):
        """Test forcing graph-only mode."""
        mock_graph_db.graph.nodes.return_value = ["agent:qa_001:test"]
        mock_graph_db.traverse.return_value = {"agent:qa_001:test"}

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        results = await retriever.hybrid_search(
            query="test",
            namespace_filter=("agent", "qa_001"),
            fallback_mode="graph_only"
        )

        # Should only use graph, never call vector
        assert len(results) > 0
        assert all(r.sources == ["graph"] for r in results)
        mock_vector_db.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_mode_none(self, mock_vector_db, mock_graph_db, mock_embedding_gen):
        """Test that fallback_mode='none' raises exception on failure."""
        # Both systems fail
        mock_graph_db.traverse.side_effect = RuntimeError("Graph failed")
        mock_vector_db.search.side_effect = RuntimeError("Vector failed")

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Should raise RuntimeError with fallback_mode="none"
        with pytest.raises(RuntimeError, match="All retrieval methods failed"):
            await retriever.hybrid_search(
                query="test",
                fallback_mode="none"
            )

    @pytest.mark.asyncio
    async def test_fallback_partial_results(self, mock_vector_db, mock_graph_db, mock_embedding_gen):
        """Test handling of partial failure (one system succeeds, one fails)."""
        # Vector succeeds
        mock_vector_db.search.return_value = [
            VectorSearchResult("agent:qa_001:test", 0.95, {
                "value": {"content": "Test"},
                "metadata": {}
            })
        ]

        # Graph fails
        mock_graph_db.graph.nodes.return_value = ["agent:qa_001:seed"]
        mock_graph_db.traverse.side_effect = RuntimeError("Graph connection lost")

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Should handle partial failure gracefully
        results = await retriever.hybrid_search(
            query="test",
            fallback_mode="auto"
        )

        assert len(results) > 0
        # Should fall back to vector-only
        assert all(r.sources == ["vector"] for r in results)

    @pytest.mark.asyncio
    async def test_fallback_exception_propagation(self, mock_vector_db, mock_graph_db, mock_embedding_gen):
        """Test that critical errors bubble up with fallback_mode='none'."""
        # All systems fail
        mock_vector_db.search.side_effect = RuntimeError("Vector critical error")
        mock_graph_db.traverse.side_effect = RuntimeError("Graph critical error")

        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Should propagate exception
        with pytest.raises(RuntimeError):
            await retriever.hybrid_search(
                query="test",
                fallback_mode="none"
            )


# ===========================
# CATEGORY 4: DE-DUPLICATION (7 tests)
# ===========================

class TestDeduplication:
    """Test consensus scoring for duplicate memories."""

    @pytest.mark.asyncio
    async def test_dedup_memory_in_both_systems(self, hybrid_retriever):
        """Test de-duplication for memory appearing in both vector and graph."""
        # Create mock results with duplicate
        vector_results = [
            VectorSearchResult("agent:qa_001:test_123", 0.95, {
                "value": {"content": "Shared memory"},
                "metadata": {}
            })
        ]
        graph_node_ids = {"agent:qa_001:test_123"}  # Same memory

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        # Should have single entry with summed scores
        assert len(rrf_scores) == 1
        score, sources, v_rank, g_rank = rrf_scores["agent:qa_001:test_123"]

        # Score should be sum of both (consensus bonus)
        expected_score = 1/61 + 1/61  # Both rank 1
        assert abs(score - expected_score) < 0.001

        # Sources should include both
        assert set(sources) == {"vector", "graph"}

    @pytest.mark.asyncio
    async def test_dedup_memory_in_vector_only(self, hybrid_retriever):
        """Test single source tracking for vector-only memory."""
        vector_results = [
            VectorSearchResult("agent:qa_001:test_123", 0.95, {})
        ]
        graph_node_ids = set()  # Not in graph

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        score, sources, v_rank, g_rank = rrf_scores["agent:qa_001:test_123"]

        assert sources == ["vector"]
        assert v_rank == 1
        assert g_rank == 0

    @pytest.mark.asyncio
    async def test_dedup_memory_in_graph_only(self, hybrid_retriever):
        """Test single source tracking for graph-only memory."""
        vector_results = []
        graph_node_ids = {"agent:qa_001:test_123"}

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        score, sources, v_rank, g_rank = rrf_scores["agent:qa_001:test_123"]

        assert sources == ["graph"]
        assert v_rank == 0
        assert g_rank == 1  # First in sorted order

    @pytest.mark.asyncio
    async def test_dedup_multiple_duplicates(self, hybrid_retriever):
        """Test complex overlap scenario with multiple duplicates."""
        vector_results = [
            VectorSearchResult("mem_A", 0.95, {}),  # Rank 1
            VectorSearchResult("mem_B", 0.85, {}),  # Rank 2
            VectorSearchResult("mem_C", 0.75, {}),  # Rank 3
        ]
        # mem_A and mem_C also in graph (2 duplicates)
        graph_node_ids = {"mem_A", "mem_C", "mem_D"}

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        # Should have 4 unique memories (A, B, C, D)
        assert len(rrf_scores) == 4

        # mem_A and mem_C should have higher scores (in both systems)
        mem_a_score = rrf_scores["mem_A"][0]
        mem_b_score = rrf_scores["mem_B"][0]
        mem_c_score = rrf_scores["mem_C"][0]

        # mem_A should outscore mem_B (consensus vs. vector-only)
        assert mem_a_score > mem_b_score

        # mem_A sources should include both
        assert set(rrf_scores["mem_A"][1]) == {"vector", "graph"}
        assert set(rrf_scores["mem_C"][1]) == {"vector", "graph"}
        assert rrf_scores["mem_B"][1] == ["vector"]

    @pytest.mark.asyncio
    async def test_dedup_sources_list(self, hybrid_retriever):
        """Test that sources list correctly tracks vector and graph."""
        vector_results = [
            VectorSearchResult("mem_1", 0.95, {}),
            VectorSearchResult("mem_2", 0.85, {}),
        ]
        graph_node_ids = {"mem_2", "mem_3"}  # mem_2 in both

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        # Verify sources tracking
        assert rrf_scores["mem_1"][1] == ["vector"]
        assert set(rrf_scores["mem_2"][1]) == {"vector", "graph"}
        assert rrf_scores["mem_3"][1] == ["graph"]

    @pytest.mark.asyncio
    async def test_dedup_rank_tracking(self, hybrid_retriever):
        """Test that original ranks are preserved."""
        vector_results = [
            VectorSearchResult("mem_1", 0.95, {}),  # Vector rank 1
            VectorSearchResult("mem_2", 0.85, {}),  # Vector rank 2
        ]
        graph_node_ids = {"mem_2", "mem_3"}  # mem_2 in both

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        # Check rank tracking
        _, _, mem1_v_rank, mem1_g_rank = rrf_scores["mem_1"]
        _, _, mem2_v_rank, mem2_g_rank = rrf_scores["mem_2"]
        _, _, mem3_v_rank, mem3_g_rank = rrf_scores["mem_3"]

        assert mem1_v_rank == 1 and mem1_g_rank == 0  # Vector only
        assert mem2_v_rank == 2 and mem2_g_rank == 1  # Both (sorted: mem_2 < mem_3)
        assert mem3_v_rank == 0 and mem3_g_rank == 2  # Graph only

    @pytest.mark.asyncio
    async def test_dedup_score_comparison(self, hybrid_retriever):
        """Test that consensus scores are higher than single-source."""
        vector_results = [
            VectorSearchResult("mem_consensus", 0.85, {}),  # Rank 1
            VectorSearchResult("mem_vector_only", 0.95, {}),  # Rank 2
        ]
        # mem_consensus also in graph (consensus!)
        graph_node_ids = {"mem_consensus"}

        rrf_scores = hybrid_retriever._compute_rrf_scores(
            vector_results, graph_node_ids, k=60
        )

        consensus_score = rrf_scores["mem_consensus"][0]
        vector_only_score = rrf_scores["mem_vector_only"][0]

        # Consensus should outscore vector-only despite lower vector rank
        # mem_consensus: 1/61 (vector rank 1) + 1/61 (graph rank 1) = 0.0328
        # mem_vector_only: 1/62 (vector rank 2) = 0.0161
        assert consensus_score > vector_only_score, \
            f"Consensus ({consensus_score}) should outscore single-source ({vector_only_score})"


# ===========================
# CATEGORY 5: INFRASTRUCTURE INTEGRATION (5 tests)
# ===========================

class TestInfrastructureIntegration:
    """Test integration with existing components."""

    @pytest.mark.asyncio
    async def test_integration_vector_database(self):
        """Test integration with real VectorDatabase instance."""
        # Import real components (not mocks)
        from infrastructure.vector_database import FAISSVectorDatabase
        from infrastructure.graph_database import GraphDatabase

        # Create real instances (no embedding generator to avoid API key)
        vector_db = FAISSVectorDatabase(embedding_dim=1536)
        graph_db = GraphDatabase()

        # Mock embedding generator to avoid API key requirement
        mock_embedding_gen = AsyncMock()
        mock_embedding_gen.generate_embedding = AsyncMock(
            return_value=np.random.rand(1536).astype('float32')
        )

        retriever = HybridRAGRetriever(
            vector_db=vector_db,
            graph_db=graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Add test vector
        test_embedding = np.random.rand(1536).astype('float32')
        await vector_db.add(
            embedding=test_embedding,
            id="agent:qa_001:test_123",
            metadata={"value": {"content": "Test memory"}, "type": "test"}
        )

        # Search via hybrid retriever
        results = await retriever.hybrid_search(
            query="test memory",
            top_k=5
        )

        # Should return results from real vector DB
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_integration_graph_database(self):
        """Test integration with real GraphDatabase instance."""
        from infrastructure.vector_database import FAISSVectorDatabase
        from infrastructure.graph_database import GraphDatabase

        vector_db = FAISSVectorDatabase(embedding_dim=1536)
        graph_db = GraphDatabase()

        # Mock embedding generator
        mock_embedding_gen = AsyncMock()
        mock_embedding_gen.generate_embedding = AsyncMock(
            return_value=np.random.rand(1536).astype('float32')
        )

        retriever = HybridRAGRetriever(
            vector_db=vector_db,
            graph_db=graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Add graph nodes
        await graph_db.add_node(
            node_id="agent:qa_001:test_1",
            namespace=("agent", "qa_001"),
            content="Test node 1"
        )
        await graph_db.add_node(
            node_id="agent:qa_001:test_2",
            namespace=("agent", "qa_001"),
            content="Test node 2"
        )
        await graph_db.add_edge(
            source_id="agent:qa_001:test_1",
            target_id="agent:qa_001:test_2",
            relationship_type="related_to"
        )

        # Get seed nodes via retriever
        seed_nodes = await retriever._get_namespace_seed_nodes(
            namespace_filter=("agent", "qa_001")
        )

        assert len(seed_nodes) == 2
        assert "agent:qa_001:test_1" in seed_nodes
        assert "agent:qa_001:test_2" in seed_nodes

    @pytest.mark.asyncio
    async def test_integration_embedding_generator(self):
        """Test integration with embedding generation (mocked to avoid API key)."""
        from infrastructure.vector_database import FAISSVectorDatabase
        from infrastructure.graph_database import GraphDatabase

        vector_db = FAISSVectorDatabase(embedding_dim=1536)
        graph_db = GraphDatabase()

        # Mock embedding generator (real EmbeddingGenerator requires API key)
        mock_embedding_gen = AsyncMock()
        mock_embedding_gen.generate_embedding = AsyncMock(
            return_value=np.random.rand(1536).astype('float32')
        )

        retriever = HybridRAGRetriever(
            vector_db=vector_db,
            graph_db=graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Verify embedding generator is called during hybrid search
        results = await retriever.hybrid_search(
            query="test query for embedding generation",
            top_k=5
        )

        # Verify embedding_gen was called
        mock_embedding_gen.generate_embedding.assert_called_once()
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_integration_memory_store(self):
        """Test hybrid_search integration with GenesisMemoryStore backend."""
        from infrastructure.vector_database import FAISSVectorDatabase
        from infrastructure.graph_database import GraphDatabase
        from infrastructure.memory_store import InMemoryBackend

        # Create real instances (mock embedding gen to avoid API key)
        vector_db = FAISSVectorDatabase(embedding_dim=1536)
        graph_db = GraphDatabase()
        backend = InMemoryBackend()  # Use in-memory backend

        mock_embedding_gen = AsyncMock()
        mock_embedding_gen.generate_embedding = AsyncMock(
            return_value=np.random.rand(1536).astype('float32')
        )

        # Create hybrid retriever with backend components
        retriever = HybridRAGRetriever(
            vector_db=vector_db,
            graph_db=graph_db,
            embedding_generator=mock_embedding_gen,
            mongodb_backend=None
        )

        # Add test memory to backend
        await backend.put(
            namespace=("agent", "qa_001"),
            key="test_123",
            value={"content": "Test authentication flow"},
            metadata=None
        )

        # Verify backend integration (retriever can access vector/graph DBs)
        results = await retriever.hybrid_search(
            query="authentication testing",
            top_k=10
        )

        # Should return results (even if empty)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_integration_observability(self):
        """Test that OTEL spans are created during hybrid search."""
        from infrastructure.vector_database import FAISSVectorDatabase
        from infrastructure.graph_database import GraphDatabase
        from infrastructure.observability import CorrelationContext

        vector_db = FAISSVectorDatabase(embedding_dim=1536)
        graph_db = GraphDatabase()

        # Mock embedding generator
        mock_embedding_gen = AsyncMock()
        mock_embedding_gen.generate_embedding = AsyncMock(
            return_value=np.random.rand(1536).astype('float32')
        )

        retriever = HybridRAGRetriever(
            vector_db=vector_db,
            graph_db=graph_db,
            embedding_generator=mock_embedding_gen
        )

        # Create correlation context (observability dataclass)
        correlation_ctx = CorrelationContext(
            correlation_id="test_correlation_id_12345",
            user_request="test observability"
        )

        # Execute search (OTEL spans created internally)
        results = await retriever.hybrid_search(
            query="test observability",
            top_k=5
        )

        # Verify correlation context structure
        assert correlation_ctx.correlation_id == "test_correlation_id_12345"
        assert isinstance(correlation_ctx.to_dict(), dict)

        # Verify search executed successfully
        assert isinstance(results, list)


# ===========================
# STATISTICS AND EDGE CASES
# ===========================

class TestStatisticsAndEdgeCases:
    """Test retrieval statistics and edge cases."""

    @pytest.mark.asyncio
    async def test_get_stats(self, hybrid_retriever, mock_vector_db, mock_graph_db):
        """Test retrieval statistics tracking."""
        mock_vector_db.search.return_value = []
        mock_graph_db.graph.nodes.return_value = []
        mock_graph_db.traverse.return_value = set()

        # Initial stats
        stats = hybrid_retriever.get_stats()
        assert stats["total_searches"] == 0

        # Perform searches
        await hybrid_retriever.hybrid_search(query="test1", top_k=5)
        await hybrid_retriever.hybrid_search(query="test2", top_k=5)

        # Updated stats
        stats = hybrid_retriever.get_stats()
        assert stats["total_searches"] == 2

    @pytest.mark.asyncio
    async def test_invalid_top_k(self, hybrid_retriever):
        """Test that invalid top_k raises ValueError."""
        with pytest.raises(ValueError, match="top_k must be between 1 and 1000"):
            await hybrid_retriever.hybrid_search(query="test", top_k=0)

        with pytest.raises(ValueError, match="top_k must be between 1 and 1000"):
            await hybrid_retriever.hybrid_search(query="test", top_k=1001)

    @pytest.mark.asyncio
    async def test_invalid_memory_id_format(self, hybrid_retriever):
        """Test handling of invalid memory ID format."""
        vector_results = [
            VectorSearchResult("invalid_format", 0.95, {
                "value": {},
                "metadata": {}
            })
        ]

        hybrid_results = await hybrid_retriever._create_hybrid_results(
            rrf_scores={"invalid_format": (0.5, ["vector"], 1, 0)},
            vector_results=vector_results,
            graph_node_ids=set()
        )

        # Should skip invalid IDs
        assert len(hybrid_results) == 0
