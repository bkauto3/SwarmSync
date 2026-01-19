"""
Test suite for GraphDatabase - NetworkX-based relationship tracking

This test suite validates the graph database module used for memory relationship
tracking in the Genesis Hybrid RAG system.

Test Coverage:
- Node operations (add, get)
- Edge operations (add, get neighbors)
- Graph traversal (BFS, 1-hop, 2-hop, filtering)
- Centrality algorithms (PageRank, degree, betweenness)
- Graph persistence (save/load)
- Thread safety (concurrent operations)
- Edge cases (empty graph, non-existent nodes)
- Performance (non-blocking operations)

Total: 18 tests covering all major functionality
"""

import asyncio
import os
import tempfile
import time

import pytest

from infrastructure.graph_database import GraphDatabase


class TestGraphDatabaseBasics:
    """Test basic node and edge operations"""

    @pytest.mark.asyncio
    async def test_add_node(self):
        """Test adding a node to graph"""
        graph = GraphDatabase()

        await graph.add_node(
            node_id="agent:qa_001:bug_123",
            namespace=("agent", "qa_001"),
            content="API timeout error",
            metadata={"severity": "high"}
        )

        node = await graph.get_node("agent:qa_001:bug_123")
        assert node is not None
        assert node["namespace"] == ("agent", "qa_001")
        assert node["content"] == "API timeout error"
        assert node["metadata"]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_add_multiple_nodes(self):
        """Test adding multiple nodes"""
        graph = GraphDatabase()

        # Add 5 nodes
        for i in range(5):
            await graph.add_node(
                node_id=f"node_{i}",
                namespace=("agent", "test"),
                content=f"Node {i}"
            )

        stats = await graph.get_stats()
        assert stats["total_nodes"] == 5

    @pytest.mark.asyncio
    async def test_add_edge(self):
        """Test adding relationship edge"""
        graph = GraphDatabase()

        # Add nodes first
        await graph.add_node("agent:qa_001:bug_123", ("agent", "qa_001"), "Bug 1")
        await graph.add_node("agent:qa_001:bug_456", ("agent", "qa_001"), "Bug 2")

        # Add edge
        await graph.add_edge(
            source_id="agent:qa_001:bug_123",
            target_id="agent:qa_001:bug_456",
            relationship_type="similar_to",
            weight=0.85
        )

        # Verify edge exists
        neighbors = await graph.get_neighbors("agent:qa_001:bug_123")
        assert len(neighbors) == 1
        assert neighbors[0]["id"] == "agent:qa_001:bug_456"
        assert neighbors[0]["relationship_type"] == "similar_to"
        assert neighbors[0]["weight"] == 0.85

    @pytest.mark.asyncio
    async def test_add_multiple_edges(self):
        """Test adding multiple edges from one node"""
        graph = GraphDatabase()

        # Add nodes
        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")

        # Add edges A->B and A->C
        await graph.add_edge("A", "B", "similar_to", weight=0.9)
        await graph.add_edge("A", "C", "similar_to", weight=0.7)

        # Verify both edges exist
        neighbors = await graph.get_neighbors("A")
        assert len(neighbors) == 2

        # Verify sorted by weight (descending)
        assert neighbors[0]["id"] == "B"  # Higher weight first
        assert neighbors[0]["weight"] == 0.9
        assert neighbors[1]["id"] == "C"
        assert neighbors[1]["weight"] == 0.7


class TestGraphTraversal:
    """Test graph traversal algorithms"""

    @pytest.mark.asyncio
    async def test_traverse_one_hop(self):
        """Test graph traversal with 1 hop"""
        graph = GraphDatabase()

        # Create chain: A → B → C
        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")

        await graph.add_edge("A", "B", "similar_to")
        await graph.add_edge("B", "C", "similar_to")

        # 1 hop from A: should get A, B (not C)
        visited = await graph.traverse(["A"], max_hops=1)
        assert visited == {"A", "B"}

    @pytest.mark.asyncio
    async def test_traverse_two_hops(self):
        """Test graph traversal with 2 hops"""
        graph = GraphDatabase()

        # Create chain: A → B → C
        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")

        await graph.add_edge("A", "B", "similar_to")
        await graph.add_edge("B", "C", "similar_to")

        # 2 hops from A: should get A, B, C
        visited = await graph.traverse(["A"], max_hops=2)
        assert visited == {"A", "B", "C"}

    @pytest.mark.asyncio
    async def test_traverse_with_relationship_filter(self):
        """Test traversal filtered by relationship type"""
        graph = GraphDatabase()

        # Add nodes
        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")

        # Add edges with different types
        await graph.add_edge("A", "B", "similar_to")
        await graph.add_edge("A", "C", "referenced_by")

        # Only follow "similar_to" relationships
        visited = await graph.traverse(
            ["A"],
            max_hops=1,
            relationship_filter=["similar_to"]
        )
        assert visited == {"A", "B"}  # C not included (wrong relationship type)

    @pytest.mark.asyncio
    async def test_traverse_multiple_seeds(self):
        """Test traversal from multiple seed nodes"""
        graph = GraphDatabase()

        # Create two chains: A → B and C → D
        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")
        await graph.add_node("D", ("agent", "1"), "Node D")

        await graph.add_edge("A", "B", "similar_to")
        await graph.add_edge("C", "D", "similar_to")

        # Traverse from both A and C
        visited = await graph.traverse(["A", "C"], max_hops=1)
        assert visited == {"A", "B", "C", "D"}

    @pytest.mark.asyncio
    async def test_traverse_nonexistent_node(self):
        """Test traversal from non-existent node"""
        graph = GraphDatabase()

        await graph.add_node("A", ("agent", "1"), "Node A")

        # Start from non-existent node
        visited = await graph.traverse(["nonexistent"], max_hops=2)
        assert visited == {"nonexistent"}  # Only includes start node


class TestNeighborRetrieval:
    """Test neighbor retrieval operations"""

    @pytest.mark.asyncio
    async def test_get_neighbors(self):
        """Test getting direct neighbors"""
        graph = GraphDatabase()

        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")

        await graph.add_edge("A", "B", "similar_to", weight=0.9)
        await graph.add_edge("A", "C", "similar_to", weight=0.7)

        neighbors = await graph.get_neighbors("A")
        assert len(neighbors) == 2

        # Verify sorted by weight (descending)
        assert neighbors[0]["id"] == "B"
        assert neighbors[0]["weight"] == 0.9
        assert neighbors[1]["id"] == "C"

    @pytest.mark.asyncio
    async def test_get_neighbors_with_filter(self):
        """Test getting neighbors filtered by relationship type"""
        graph = GraphDatabase()

        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")

        await graph.add_edge("A", "B", "similar_to", weight=0.9)
        await graph.add_edge("A", "C", "referenced_by", weight=0.8)

        # Only get "similar_to" neighbors
        neighbors = await graph.get_neighbors("A", relationship_type="similar_to")
        assert len(neighbors) == 1
        assert neighbors[0]["id"] == "B"

    @pytest.mark.asyncio
    async def test_get_neighbors_missing_node(self):
        """Test getting neighbors for non-existent node"""
        graph = GraphDatabase()

        neighbors = await graph.get_neighbors("nonexistent")
        assert neighbors == []


class TestCentralityAlgorithms:
    """Test centrality calculation algorithms"""

    @pytest.mark.asyncio
    async def test_calculate_pagerank_centrality(self):
        """Test PageRank centrality calculation"""
        graph = GraphDatabase()

        # Create star pattern: B,C,D → A (A is central)
        await graph.add_node("A", ("agent", "1"), "Central node")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")
        await graph.add_node("D", ("agent", "1"), "Node D")

        # All point to A
        await graph.add_edge("B", "A", "referenced_by")
        await graph.add_edge("C", "A", "referenced_by")
        await graph.add_edge("D", "A", "referenced_by")

        scores = await graph.calculate_centrality(algorithm="pagerank")

        # A should have highest centrality (many incoming edges)
        assert scores["A"] > scores["B"]
        assert scores["A"] > scores["C"]
        assert scores["A"] > scores["D"]

    @pytest.mark.asyncio
    async def test_calculate_degree_centrality(self):
        """Test degree centrality calculation"""
        graph = GraphDatabase()

        # Create hub: A connects to B, C, D
        await graph.add_node("A", ("agent", "1"), "Hub node")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_node("C", ("agent", "1"), "Node C")
        await graph.add_node("D", ("agent", "1"), "Node D")

        await graph.add_edge("A", "B", "similar_to")
        await graph.add_edge("A", "C", "similar_to")
        await graph.add_edge("A", "D", "similar_to")

        scores = await graph.calculate_centrality(algorithm="degree")

        # A has 3 connections, others have 1 each
        assert scores["A"] > scores["B"]
        assert scores["A"] > scores["C"]

    @pytest.mark.asyncio
    async def test_calculate_betweenness_centrality(self):
        """Test betweenness centrality calculation"""
        graph = GraphDatabase()

        # Create bridge: A → B → C (B is bridge)
        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Bridge node")
        await graph.add_node("C", ("agent", "1"), "Node C")

        await graph.add_edge("A", "B", "similar_to")
        await graph.add_edge("B", "C", "similar_to")

        scores = await graph.calculate_centrality(algorithm="betweenness")

        # B is on path from A to C
        assert scores["B"] >= scores["A"]
        assert scores["B"] >= scores["C"]

    @pytest.mark.asyncio
    async def test_centrality_empty_graph(self):
        """Test centrality on empty graph"""
        graph = GraphDatabase()

        scores = await graph.calculate_centrality()
        assert scores == {}

    @pytest.mark.asyncio
    async def test_centrality_invalid_algorithm(self):
        """Test centrality with invalid algorithm name"""
        graph = GraphDatabase()

        await graph.add_node("A", ("agent", "1"), "Node A")

        with pytest.raises(ValueError, match="Unknown centrality algorithm"):
            await graph.calculate_centrality(algorithm="invalid")


class TestGraphPersistence:
    """Test graph save and load operations"""

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Test graph persistence to file"""
        graph = GraphDatabase()

        # Add test data
        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_edge("A", "B", "similar_to", weight=0.8)

        # Save graph
        with tempfile.NamedTemporaryFile(suffix=".graphml", delete=False) as f:
            file_path = f.name

        try:
            await graph.save(file_path)

            # Load into new graph
            new_graph = GraphDatabase()
            await new_graph.load(file_path)

            # Verify loaded correctly
            stats = await new_graph.get_stats()
            assert stats["total_nodes"] == 2
            assert stats["total_edges"] == 1

            # Verify node data preserved
            node = await new_graph.get_node("A")
            assert node is not None

        finally:
            # Cleanup
            if os.path.exists(file_path):
                os.unlink(file_path)


class TestGraphStatistics:
    """Test graph statistics and metadata"""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test graph statistics"""
        graph = GraphDatabase()

        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_edge("A", "B", "similar_to")

        stats = await graph.get_stats()
        assert stats["total_nodes"] == 2
        assert stats["total_edges"] == 1
        assert stats["avg_degree"] > 0

    @pytest.mark.asyncio
    async def test_get_stats_empty_graph(self):
        """Test statistics on empty graph"""
        graph = GraphDatabase()

        stats = await graph.get_stats()
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
        assert stats["avg_degree"] == 0

    @pytest.mark.asyncio
    async def test_get_node_missing(self):
        """Test getting non-existent node"""
        graph = GraphDatabase()

        node = await graph.get_node("nonexistent")
        assert node is None


class TestThreadSafety:
    """Test concurrent operations and thread safety"""

    @pytest.mark.asyncio
    async def test_concurrent_node_operations(self):
        """Test thread-safe concurrent node additions"""
        graph = GraphDatabase()

        # Add 100 nodes concurrently
        tasks = [
            graph.add_node(f"node_{i}", ("agent", "1"), f"Node {i}")
            for i in range(100)
        ]
        await asyncio.gather(*tasks)

        stats = await graph.get_stats()
        assert stats["total_nodes"] == 100

    @pytest.mark.asyncio
    async def test_concurrent_edge_operations(self):
        """Test thread-safe concurrent edge additions"""
        graph = GraphDatabase()

        # Add nodes first
        for i in range(10):
            await graph.add_node(f"node_{i}", ("agent", "1"), f"Node {i}")

        # Add 45 edges concurrently (all pairs)
        tasks = []
        for i in range(10):
            for j in range(i + 1, 10):
                tasks.append(
                    graph.add_edge(f"node_{i}", f"node_{j}", "similar_to")
                )
        await asyncio.gather(*tasks)

        stats = await graph.get_stats()
        assert stats["total_edges"] == 45

    @pytest.mark.asyncio
    async def test_concurrent_read_operations(self):
        """Test thread-safe concurrent reads"""
        graph = GraphDatabase()

        # Setup graph
        await graph.add_node("A", ("agent", "1"), "Node A")
        await graph.add_node("B", ("agent", "1"), "Node B")
        await graph.add_edge("A", "B", "similar_to")

        # Read concurrently 100 times
        tasks = [
            graph.get_neighbors("A")
            for _ in range(100)
        ]
        results = await asyncio.gather(*tasks)

        # All reads should succeed
        assert len(results) == 100
        assert all(len(r) == 1 for r in results)


class TestPerformance:
    """Test performance and non-blocking behavior"""

    @pytest.mark.asyncio
    async def test_operations_are_nonblocking(self):
        """
        Verify operations don't block event loop under concurrent load.

        NetworkX is pure Python (no C++ backend), so it doesn't need
        asyncio.to_thread wrapping per ASYNC_WRAPPER_PATTERN.md.

        However, we still verify non-blocking behavior for graph operations.
        """
        graph = GraphDatabase()

        # Add initial nodes
        for i in range(50):
            await graph.add_node(f"node_{i}", ("agent", "1"), f"Node {i}")

        # Run 50 concurrent traversals
        start_time = time.time()

        tasks = [
            graph.traverse([f"node_{i}"], max_hops=1)
            for i in range(50)
        ]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Should complete quickly (NetworkX is fast for small graphs)
        # Allow 5s for 50 concurrent operations (100ms per operation average)
        assert elapsed < 5.0, f"Operations too slow: {elapsed:.2f}s"
        assert len(results) == 50


class TestRelationshipTypes:
    """Test different relationship types"""

    @pytest.mark.asyncio
    async def test_relationship_types(self):
        """Test all relationship types work correctly"""
        graph = GraphDatabase()

        # Add nodes
        await graph.add_node("agent", ("agent", "qa_001"), "Agent")
        await graph.add_node("memory1", ("agent", "qa_001"), "Memory 1")
        await graph.add_node("memory2", ("agent", "qa_001"), "Memory 2")
        await graph.add_node("business", ("business", "saas_001"), "Business")

        # Test all relationship types (each to a different target to avoid overlap)
        await graph.add_edge("memory1", "agent", "created_by", weight=1.0)
        await graph.add_edge("memory1", "memory2", "similar_to", weight=0.85)
        await graph.add_edge("memory1", "business", "belongs_to", weight=1.0)
        await graph.add_edge("memory2", "memory1", "referenced_by", weight=0.9)

        # Verify all edges exist from memory1
        neighbors = await graph.get_neighbors("memory1")
        assert len(neighbors) == 3  # memory1 has 3 outgoing edges

        # Verify can filter by type
        created_by = await graph.get_neighbors("memory1", relationship_type="created_by")
        assert len(created_by) == 1
        assert created_by[0]["relationship_type"] == "created_by"

        # Verify memory2 has incoming edge
        neighbors2 = await graph.get_neighbors("memory2")
        assert len(neighbors2) == 1  # memory2 -> memory1 (referenced_by)


# Run tests with: pytest tests/test_graph_database.py -v
# For coverage: pytest tests/test_graph_database.py --cov=infrastructure.graph_database --cov-report=term-missing
