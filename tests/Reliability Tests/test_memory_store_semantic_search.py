"""
Unit Tests for GenesisMemoryStore Semantic Search

Tests cover:
1. Save with semantic indexing
2. Basic semantic search
3. Search with agent_id filter
4. Search with namespace_filter
5. Empty search results
6. Text extraction from various value formats
7. Error handling when vector DB not configured
8. Save without indexing (index_for_search=False)

Target: 8 tests, 100% coverage of semantic search functionality
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from infrastructure.embedding_generator import EmbeddingGenerator
from infrastructure.memory_store import GenesisMemoryStore, InMemoryBackend
from infrastructure.vector_database import FAISSVectorDatabase


@pytest.fixture
def embedding_dim():
    """Standard embedding dimension for tests"""
    return 128  # Smaller for faster tests


@pytest.fixture
def vector_db(embedding_dim):
    """Create in-memory vector database"""
    return FAISSVectorDatabase(embedding_dim=embedding_dim, index_type="flat")


@pytest.fixture
def mock_embedding_gen(embedding_dim):
    """Create mock embedding generator"""
    mock = MagicMock(spec=EmbeddingGenerator)
    mock.generate_embedding = AsyncMock(
        return_value=np.random.randn(embedding_dim).astype('float32')
    )
    return mock


@pytest.fixture
def memory_store_with_search(vector_db, mock_embedding_gen):
    """Create memory store with semantic search enabled"""
    return GenesisMemoryStore(
        backend=InMemoryBackend(),
        vector_db=vector_db,
        embedding_gen=mock_embedding_gen
    )


@pytest.fixture
def memory_store_without_search():
    """Create memory store without semantic search"""
    return GenesisMemoryStore(backend=InMemoryBackend())


# Test 1: Save with semantic indexing
@pytest.mark.asyncio
async def test_save_with_semantic_indexing(memory_store_with_search, vector_db):
    """Test memory is indexed in vector DB when saved"""
    await memory_store_with_search.save_memory(
        namespace=("agent", "qa_001"),
        key="bug_001",
        value={"content": "API timeout error in payment processing"},
        index_for_search=True
    )

    # Verify indexed in vector DB
    stats = vector_db.get_stats()
    assert stats["total_vectors"] == 1

    # Verify memory also saved in backend
    memory = await memory_store_with_search.get_memory(
        namespace=("agent", "qa_001"),
        key="bug_001"
    )
    assert memory is not None
    assert memory["content"] == "API timeout error in payment processing"


# Test 2: Basic semantic search
@pytest.mark.asyncio
async def test_semantic_search_basic(memory_store_with_search):
    """Test basic semantic search"""
    # Save some test memories
    await memory_store_with_search.save_memory(
        namespace=("agent", "qa_001"),
        key="bug_001",
        value={"content": "API timeout error in payment processing"},
        index_for_search=True
    )
    await memory_store_with_search.save_memory(
        namespace=("agent", "qa_001"),
        key="bug_002",
        value={"content": "Database connection failure in user auth"},
        index_for_search=True
    )
    await memory_store_with_search.save_memory(
        namespace=("agent", "qa_001"),
        key="bug_003",
        value={"content": "UI rendering glitch on mobile devices"},
        index_for_search=True
    )

    # Search for payment-related bugs
    results = await memory_store_with_search.semantic_search(
        query="Find bugs related to payments",
        top_k=3
    )

    assert len(results) <= 3
    assert all("_search_score" in r for r in results)
    assert all("_search_rank" in r for r in results)
    assert all("namespace" in r for r in results)
    assert all("key" in r for r in results)
    assert all("value" in r for r in results)

    # Ranks should be sequential
    ranks = [r["_search_rank"] for r in results]
    assert ranks == sorted(ranks)


# Test 3: Search with agent_id filter
@pytest.mark.asyncio
async def test_semantic_search_with_agent_filter(memory_store_with_search):
    """Test search filtered by agent_id"""
    # Save memories for different agents
    await memory_store_with_search.save_memory(
        namespace=("agent", "qa_001"),
        key="qa_memory_1",
        value={"content": "QA agent memory about testing"},
        index_for_search=True
    )
    await memory_store_with_search.save_memory(
        namespace=("agent", "support_001"),
        key="support_memory_1",
        value={"content": "Support agent memory about customer tickets"},
        index_for_search=True
    )
    await memory_store_with_search.save_memory(
        namespace=("agent", "qa_001"),
        key="qa_memory_2",
        value={"content": "Another QA memory about bug tracking"},
        index_for_search=True
    )

    # Search with agent filter
    results = await memory_store_with_search.semantic_search(
        query="Find memories about testing and bugs",
        agent_id="qa_001",
        top_k=5
    )

    # All results should be from qa_001 namespace
    assert all(
        r["namespace"] == ("agent", "qa_001")
        for r in results
    )


# Test 4: Search with namespace_filter
@pytest.mark.asyncio
async def test_semantic_search_with_namespace_filter(memory_store_with_search):
    """Test search filtered by explicit namespace"""
    # Save memories in different namespaces
    await memory_store_with_search.save_memory(
        namespace=("business", "saas_001"),
        key="metric_1",
        value={"content": "Monthly revenue metrics for Q1"},
        index_for_search=True
    )
    await memory_store_with_search.save_memory(
        namespace=("business", "saas_002"),
        key="metric_1",
        value={"content": "User growth metrics for Q1"},
        index_for_search=True
    )
    await memory_store_with_search.save_memory(
        namespace=("business", "saas_001"),
        key="metric_2",
        value={"content": "Customer acquisition cost for Q1"},
        index_for_search=True
    )

    # Search with namespace filter
    results = await memory_store_with_search.semantic_search(
        query="Find business metrics",
        namespace_filter=("business", "saas_001"),
        top_k=5
    )

    # All results should be from saas_001 namespace
    assert all(
        r["namespace"] == ("business", "saas_001")
        for r in results
    )


# Test 5: Empty search results
@pytest.mark.asyncio
async def test_semantic_search_empty_results(memory_store_with_search):
    """Test search with no matches"""
    # Don't save any memories

    results = await memory_store_with_search.semantic_search(
        query="Find something that doesn't exist",
        top_k=5
    )

    # Should return empty list, not error
    assert isinstance(results, list)
    assert len(results) == 0


# Test 6: Extract searchable text
def test_extract_searchable_text(memory_store_with_search):
    """Test text extraction from various value formats"""
    # Test priority: content field
    text = memory_store_with_search._extract_searchable_text({
        "content": "Main content",
        "description": "Secondary"
    })
    assert text == "Main content"

    # Test fallback: description field
    text = memory_store_with_search._extract_searchable_text({
        "description": "Description text"
    })
    assert text == "Description text"

    # Test fallback: concatenate all strings
    text = memory_store_with_search._extract_searchable_text({
        "field1": "value1",
        "field2": "value2",
        "field3": 123  # Non-string should be ignored
    })
    assert "field1: value1" in text
    assert "field2: value2" in text
    assert "123" not in text


# Test 7: Error when vector DB not configured
@pytest.mark.asyncio
async def test_semantic_search_without_vector_db(memory_store_without_search):
    """Test error when vector DB not configured"""
    with pytest.raises(ValueError, match="Semantic search not configured"):
        await memory_store_without_search.semantic_search("test query")


# Test 8: Save without indexing
@pytest.mark.asyncio
async def test_save_without_indexing(memory_store_with_search, vector_db):
    """Test save without semantic indexing"""
    await memory_store_with_search.save_memory(
        namespace=("agent", "test"),
        key="key1",
        value={"content": "test content"},
        index_for_search=False  # Explicitly disable
    )

    # Vector DB should be empty
    stats = vector_db.get_stats()
    assert stats["total_vectors"] == 0

    # But memory should still be saved in backend
    memory = await memory_store_with_search.get_memory(
        namespace=("agent", "test"),
        key="key1"
    )
    assert memory is not None
    assert memory["content"] == "test content"


# Bonus Test: Integration test with real embedding generation
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
async def test_semantic_search_integration_real_embeddings(vector_db):
    """
    Integration test with real OpenAI embeddings.

    Skipped if OPENAI_API_KEY not set.
    """
    from infrastructure.embedding_generator import EmbeddingGenerator

    # Create real embedding generator
    embedding_gen = EmbeddingGenerator(
        api_key=os.getenv("OPENAI_API_KEY"),
        embedding_dim=128  # Use smaller dimension for testing
    )

    # Create memory store with real components
    memory_store = GenesisMemoryStore(
        backend=InMemoryBackend(),
        vector_db=vector_db,
        embedding_gen=embedding_gen
    )

    # Save some memories
    await memory_store.save_memory(
        namespace=("agent", "qa_001"),
        key="bug_python",
        value={"content": "Python exception: TypeError in data processing function"},
        index_for_search=True
    )
    await memory_store.save_memory(
        namespace=("agent", "qa_001"),
        key="bug_js",
        value={"content": "JavaScript error: Cannot read property of undefined"},
        index_for_search=True
    )

    # Search should find Python bug as most relevant
    results = await memory_store.semantic_search(
        query="Find Python bugs",
        top_k=2
    )

    assert len(results) > 0
    # First result should be Python bug (most semantically similar)
    assert "Python" in results[0]["value"]["content"]


# Test 9: Concurrency test (verify non-blocking behavior)
@pytest.mark.asyncio
async def test_semantic_search_concurrent_operations(memory_store_with_search):
    """
    Test that semantic search operations don't block event loop.

    This validates the async wrapper pattern for FAISS operations.
    """
    import time

    # Save multiple memories concurrently
    save_tasks = [
        memory_store_with_search.save_memory(
            namespace=("agent", "test"),
            key=f"memory_{i}",
            value={"content": f"Test memory content {i}"},
            index_for_search=True
        )
        for i in range(20)
    ]

    start_time = time.time()
    await asyncio.gather(*save_tasks)
    save_elapsed = time.time() - start_time

    # If blocking, would take 20 * operation_time
    # If non-blocking, should complete in roughly operation_time
    assert save_elapsed < 5.0, f"Save operations blocked event loop: {save_elapsed}s"

    # Search concurrently
    search_tasks = [
        memory_store_with_search.semantic_search(
            query="Find test memory",
            top_k=5
        )
        for _ in range(10)
    ]

    start_time = time.time()
    results = await asyncio.gather(*search_tasks)
    search_elapsed = time.time() - start_time

    # All searches should complete without blocking
    assert search_elapsed < 3.0, f"Search operations blocked event loop: {search_elapsed}s"
    assert len(results) == 10
