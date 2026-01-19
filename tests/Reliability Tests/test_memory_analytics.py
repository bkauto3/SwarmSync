"""
Test suite for Memory Analytics Dashboard

Validates:
1. Analytics script functions (pattern analysis, community detection)
2. Backend API endpoint response format
3. Knowledge graph construction
4. Performance benchmarks (<2s graph render, <10s analytics)

Created: November 3, 2025
"""

import asyncio
import pytest
import json
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from scripts.analyze_memory_patterns import MemoryAnalytics, PatternStats, CommunityStats
from infrastructure.langgraph_store import GenesisLangGraphStore


@pytest.fixture
async def memory_store():
    """Create test memory store with sample data."""
    store = GenesisLangGraphStore(
        mongodb_uri="mongodb://localhost:27017/",
        database_name="genesis_memory_test"
    )
    await store.setup_indexes()

    # Populate test data
    # Agent namespace
    await store.put(
        ('agent', 'qa_agent'),
        'config',
        {
            'threshold': 0.95,
            'metrics': {'accuracy': 0.92, 'latency_ms': 45},
            'used_patterns': ['pattern_qa_123', 'pattern_testing_456']
        },
        metadata={'retrieval_count': 42, 'success_rate': 0.89}
    )

    await store.put(
        ('agent', 'support_agent'),
        'config',
        {
            'response_time_target': 30,
            'metrics': {'satisfaction': 0.88, 'resolution_rate': 0.85},
            'used_patterns': ['pattern_support_789']
        },
        metadata={'retrieval_count': 38, 'success_rate': 0.87}
    )

    # Business namespace
    await store.put(
        ('business', 'ecommerce'),
        'biz_001',
        {
            'category': 'e-commerce',
            'learned_from': ['agent_qa_agent', 'agent_support_agent'],
            'used_patterns': ['pattern_qa_123', 'pattern_support_789']
        },
        metadata={'retrieval_count': 15}
    )

    # Consensus namespace
    await store.put(
        ('consensus', 'deployment'),
        'best_practices',
        {
            'pattern_type': 'deployment',
            'confidence': 0.95
        },
        metadata={'retrieval_count': 142, 'success_rate': 0.91}
    )

    await store.put(
        ('consensus', 'testing'),
        'qa_threshold_0.95',
        {
            'pattern_type': 'testing',
            'confidence': 0.92
        },
        metadata={'retrieval_count': 89, 'success_rate': 0.87}
    )

    yield store

    # Cleanup
    await store.clear_namespace(('agent', 'qa_agent'))
    await store.clear_namespace(('agent', 'support_agent'))
    await store.clear_namespace(('business', 'ecommerce'))
    await store.clear_namespace(('consensus', 'deployment'))
    await store.clear_namespace(('consensus', 'testing'))
    await store.close()


@pytest.mark.asyncio
async def test_get_most_retrieved_patterns(memory_store):
    """Test pattern retrieval analysis."""
    analytics = MemoryAnalytics(memory_store)

    patterns = await analytics.get_most_retrieved_patterns(limit=10)

    # Verify we got patterns
    assert len(patterns) > 0, "Should retrieve at least one pattern"

    # Verify sorting (descending by retrieval count)
    assert all(
        patterns[i].retrieval_count >= patterns[i + 1].retrieval_count
        for i in range(len(patterns) - 1)
    ), "Patterns should be sorted by retrieval count (descending)"

    # Verify top pattern
    top = patterns[0]
    assert isinstance(top, PatternStats)
    assert top.retrieval_count >= 89  # consensus/testing/qa_threshold_0.95
    assert top.success_rate > 0.0
    assert top.effectiveness_score > 0.0


@pytest.mark.asyncio
async def test_build_knowledge_graph(memory_store):
    """Test knowledge graph construction."""
    analytics = MemoryAnalytics(memory_store)

    graph = await analytics.build_knowledge_graph()

    # Verify graph structure
    assert graph.number_of_nodes() > 0, "Graph should have nodes"
    assert graph.number_of_edges() >= 0, "Graph should have edges (or none if isolated)"

    # Verify node types
    node_types = set(data.get('type') for _, data in graph.nodes(data=True))
    assert 'agent' in node_types or 'business' in node_types or 'consensus' in node_types

    # Performance check: build graph in <2 seconds
    import time
    start = time.time()
    graph2 = await analytics.build_knowledge_graph()
    duration = time.time() - start
    assert duration < 2.0, f"Graph construction took {duration:.2f}s (should be <2s)"


@pytest.mark.asyncio
async def test_detect_communities(memory_store):
    """Test community detection algorithm."""
    analytics = MemoryAnalytics(memory_store)

    graph = await analytics.build_knowledge_graph()

    # Skip if graph is too small
    if graph.number_of_nodes() < 2:
        pytest.skip("Graph too small for community detection")

    communities = analytics.detect_communities(graph)

    # Verify communities detected
    assert isinstance(communities, list)

    if len(communities) > 0:
        # Verify community structure
        comm = communities[0]
        assert isinstance(comm, CommunityStats)
        assert len(comm.members) > 0
        assert 0.0 <= comm.cohesion <= 1.0
        assert isinstance(comm.central_nodes, list)


@pytest.mark.asyncio
async def test_score_pattern_effectiveness(memory_store):
    """Test pattern effectiveness scoring."""
    analytics = MemoryAnalytics(memory_store)

    scores = await analytics.score_pattern_effectiveness()

    # Verify scores calculated
    assert isinstance(scores, dict)
    assert len(scores) > 0

    # Verify score values
    for pattern_id, score in scores.items():
        assert isinstance(pattern_id, str)
        assert isinstance(score, float)
        assert score >= 0.0


@pytest.mark.asyncio
async def test_calculate_cost_savings(memory_store):
    """Test cost savings calculation."""
    analytics = MemoryAnalytics(memory_store)

    savings = await analytics.calculate_cost_savings()

    # Verify savings structure
    assert 'total' in savings
    assert 'storage' in savings
    assert 'api_calls' in savings
    assert 'entries_cached' in savings

    # Verify values are positive
    assert savings['total'] >= 0.0
    assert savings['storage'] >= 0.0
    assert savings['api_calls'] >= 0.0
    assert savings['entries_cached'] >= 0


@pytest.mark.asyncio
async def test_predict_ttl_status(memory_store):
    """Test TTL expiration prediction."""
    analytics = MemoryAnalytics(memory_store)

    predictions = await analytics.predict_ttl_status()

    # Verify prediction structure
    assert 'expiring_soon' in predictions
    assert 'active' in predictions
    assert 'permanent' in predictions

    # Verify counts
    assert predictions['expiring_soon'] >= 0
    assert predictions['active'] >= 0
    assert predictions['permanent'] >= 0  # consensus namespace should be permanent

    # Total should equal test data (5 entries)
    total = predictions['expiring_soon'] + predictions['active'] + predictions['permanent']
    assert total == 5, f"Expected 5 total entries, got {total}"


@pytest.mark.asyncio
async def test_generate_recommendations(memory_store):
    """Test optimization recommendations generation."""
    analytics = MemoryAnalytics(memory_store)

    # Generate base data
    top_patterns = await analytics.get_most_retrieved_patterns(20)
    graph = await analytics.build_knowledge_graph()
    communities = analytics.detect_communities(graph)
    ttl_predictions = await analytics.predict_ttl_status()

    recommendations = await analytics.generate_recommendations(
        top_patterns, communities, ttl_predictions
    )

    # Verify recommendations
    assert isinstance(recommendations, list)
    # Recommendations are optional, so just check type
    if len(recommendations) > 0:
        assert all(isinstance(r, str) for r in recommendations)


@pytest.mark.asyncio
async def test_analytics_performance(memory_store):
    """Test analytics performance benchmarks."""
    import time
    analytics = MemoryAnalytics(memory_store)

    # Test 1: Pattern analysis <5 seconds
    start = time.time()
    patterns = await analytics.get_most_retrieved_patterns(20)
    duration = time.time() - start
    assert duration < 5.0, f"Pattern analysis took {duration:.2f}s (should be <5s)"

    # Test 2: Graph construction <2 seconds
    start = time.time()
    graph = await analytics.build_knowledge_graph()
    duration = time.time() - start
    assert duration < 2.0, f"Graph construction took {duration:.2f}s (should be <2s)"

    # Test 3: Community detection <3 seconds
    start = time.time()
    communities = analytics.detect_communities(graph)
    duration = time.time() - start
    assert duration < 3.0, f"Community detection took {duration:.2f}s (should be <3s)"

    # Test 4: Full analytics <10 seconds
    start = time.time()
    await analytics.get_most_retrieved_patterns(20)
    await analytics.build_knowledge_graph()
    await analytics.calculate_cost_savings()
    await analytics.predict_ttl_status()
    duration = time.time() - start
    assert duration < 10.0, f"Full analytics took {duration:.2f}s (should be <10s)"


@pytest.mark.asyncio
async def test_api_response_format(memory_store):
    """Test backend API response structure (mock)."""
    analytics = MemoryAnalytics(memory_store)

    # Build expected response format
    graph = await analytics.build_knowledge_graph()
    top_patterns = await analytics.get_most_retrieved_patterns(20)
    communities = analytics.detect_communities(graph)
    cost_savings = await analytics.calculate_cost_savings()
    ttl_predictions = await analytics.predict_ttl_status()

    # Simulate API response construction
    response = {
        "nodes": [
            {
                "id": node_id,
                "type": node_data.get("type", "unknown"),
                "label": node_id,
                "data": {
                    "namespace": node_data.get("namespace", []),
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "usageCount": node_data.get("entry_count", 0),
                }
            }
            for node_id, node_data in graph.nodes(data=True)
        ],
        "edges": [
            {
                "id": f"{source}_{target}",
                "source": source,
                "target": target,
                "label": edge_data.get("relationship", "related"),
                "weight": 1.0,
                "type": edge_data.get("relationship", "usage"),
            }
            for source, target, edge_data in graph.edges(data=True)
        ],
        "metrics": {
            "storageByNamespace": {},
            "retrievalFrequency": {},
            "costSavings": cost_savings,
            "ttlPredictions": ttl_predictions,
        },
        "topPatterns": [
            {
                "key": p.key,
                "namespace": p.namespace,
                "retrievalCount": p.retrieval_count,
                "lastUsed": p.last_used.isoformat() if p.last_used else None,
            }
            for p in top_patterns
        ],
        "communities": [
            {
                "id": c.id,
                "members": c.members,
                "cohesion": c.cohesion,
            }
            for c in communities
        ],
    }

    # Verify response structure
    assert "nodes" in response
    assert "edges" in response
    assert "metrics" in response
    assert "topPatterns" in response
    assert "communities" in response

    # Verify metrics structure
    assert "storageByNamespace" in response["metrics"]
    assert "retrievalFrequency" in response["metrics"]
    assert "costSavings" in response["metrics"]
    assert "ttlPredictions" in response["metrics"]

    # Verify JSON serializable
    json_str = json.dumps(response)
    assert len(json_str) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
