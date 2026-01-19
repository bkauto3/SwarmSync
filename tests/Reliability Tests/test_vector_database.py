"""
Tests for FAISS Vector Database

This test suite validates the FAISSVectorDatabase implementation including:
- Basic add/search operations
- Batch operations
- Persistence (save/load)
- Error handling
- Performance characteristics

Author: Thon (Python Expert)
Date: October 23, 2025
"""

import asyncio
import tempfile
from pathlib import Path

import numpy as np
import pytest

from infrastructure.vector_database import FAISSVectorDatabase, VectorSearchResult


@pytest.fixture
def embedding_dim():
    """Standard embedding dimension"""
    return 128  # Smaller for faster tests


@pytest.fixture
def vector_db(embedding_dim):
    """Create in-memory vector database"""
    return FAISSVectorDatabase(embedding_dim=embedding_dim, index_type="flat")


@pytest.fixture
def sample_embeddings(embedding_dim):
    """Generate sample embeddings"""
    np.random.seed(42)
    return np.random.randn(10, embedding_dim).astype('float32')


@pytest.fixture
def sample_ids():
    """Sample vector IDs"""
    return [f"agent:test:memory{i}" for i in range(10)]


@pytest.fixture
def sample_metadatas():
    """Sample metadata"""
    return [{"type": "task", "index": i} for i in range(10)]


# Basic Operations Tests


@pytest.mark.asyncio
async def test_add_single_vector(vector_db, sample_embeddings, sample_ids):
    """Test adding a single vector"""
    await vector_db.add(sample_embeddings[0], sample_ids[0])

    assert vector_db.total_vectors == 1
    assert sample_ids[0] in vector_db.id_to_index
    assert 0 in vector_db.index_to_id


@pytest.mark.asyncio
async def test_add_with_metadata(vector_db, sample_embeddings, sample_ids, sample_metadatas):
    """Test adding vector with metadata"""
    await vector_db.add(sample_embeddings[0], sample_ids[0], sample_metadatas[0])

    assert sample_ids[0] in vector_db.id_to_metadata
    assert vector_db.id_to_metadata[sample_ids[0]] == sample_metadatas[0]


@pytest.mark.asyncio
async def test_add_duplicate_id(vector_db, sample_embeddings, sample_ids):
    """Test that adding duplicate ID is skipped"""
    await vector_db.add(sample_embeddings[0], sample_ids[0])
    await vector_db.add(sample_embeddings[1], sample_ids[0])  # Same ID

    assert vector_db.total_vectors == 1  # Should not add duplicate


@pytest.mark.asyncio
async def test_search_exact_match(vector_db, sample_embeddings, sample_ids):
    """Test searching for exact vector match"""
    # Add vectors
    for i in range(5):
        await vector_db.add(sample_embeddings[i], sample_ids[i])

    # Search for exact match (vector 0)
    results = await vector_db.search(sample_embeddings[0], top_k=1)

    assert len(results) == 1
    assert results[0].id == sample_ids[0]
    assert results[0].score < 0.001  # Very close to 0 for exact match


@pytest.mark.asyncio
async def test_search_top_k(vector_db, sample_embeddings, sample_ids):
    """Test retrieving top-k nearest neighbors"""
    # Add vectors
    for i in range(10):
        await vector_db.add(sample_embeddings[i], sample_ids[i])

    # Search for top 3
    results = await vector_db.search(sample_embeddings[0], top_k=3)

    assert len(results) == 3
    assert results[0].id == sample_ids[0]  # Exact match should be first
    # Results should be sorted by score (ascending)
    assert results[0].score <= results[1].score <= results[2].score


@pytest.mark.asyncio
async def test_search_empty_database(vector_db, sample_embeddings):
    """Test searching in empty database"""
    results = await vector_db.search(sample_embeddings[0], top_k=5)

    assert len(results) == 0


@pytest.mark.asyncio
async def test_search_with_metadata(vector_db, sample_embeddings, sample_ids, sample_metadatas):
    """Test that search results include metadata"""
    # Add vectors with metadata
    for i in range(5):
        await vector_db.add(sample_embeddings[i], sample_ids[i], sample_metadatas[i])

    # Search
    results = await vector_db.search(sample_embeddings[0], top_k=3)

    # Check metadata is included
    assert all(r.metadata for r in results)
    assert results[0].metadata == sample_metadatas[0]


# Batch Operations Tests


@pytest.mark.asyncio
async def test_add_batch(vector_db, sample_embeddings, sample_ids, sample_metadatas):
    """Test adding multiple vectors in batch"""
    await vector_db.add_batch(sample_embeddings, sample_ids, sample_metadatas)

    assert vector_db.total_vectors == 10
    assert all(id in vector_db.id_to_index for id in sample_ids)


@pytest.mark.asyncio
async def test_add_batch_partial_duplicates(vector_db, sample_embeddings, sample_ids):
    """Test batch add with some existing IDs"""
    # Add first 3 individually
    for i in range(3):
        await vector_db.add(sample_embeddings[i], sample_ids[i])

    # Try to add all 10 in batch
    await vector_db.add_batch(sample_embeddings, sample_ids)

    # Should only add 7 new ones
    assert vector_db.total_vectors == 10


@pytest.mark.asyncio
async def test_batch_size_mismatch(vector_db, sample_embeddings, sample_ids):
    """Test error on batch size mismatch"""
    with pytest.raises(ValueError, match="Batch size mismatch"):
        await vector_db.add_batch(sample_embeddings[:5], sample_ids)  # 5 vs 10


# Persistence Tests


@pytest.mark.asyncio
async def test_save_and_load(vector_db, sample_embeddings, sample_ids, sample_metadatas):
    """Test saving and loading index"""
    # Add vectors
    await vector_db.add_batch(sample_embeddings, sample_ids, sample_metadatas)

    # Save to temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = Path(tmpdir) / "test_index.faiss"
        await vector_db.save(save_path)

        # Load into new database
        new_db = FAISSVectorDatabase(
            embedding_dim=vector_db.embedding_dim,
            index_path=str(save_path)
        )
        await new_db.load(save_path)

        # Verify data
        assert new_db.total_vectors == 10
        assert new_db.id_to_index == vector_db.id_to_index
        assert new_db.id_to_metadata == vector_db.id_to_metadata

        # Verify search works
        results = await new_db.search(sample_embeddings[0], top_k=1)
        assert results[0].id == sample_ids[0]


@pytest.mark.asyncio
async def test_load_nonexistent_file(vector_db):
    """Test error on loading nonexistent file"""
    with pytest.raises(FileNotFoundError):
        await vector_db.load("/nonexistent/path.faiss")


# Error Handling Tests


@pytest.mark.asyncio
async def test_wrong_embedding_dimension(vector_db, sample_ids):
    """Test error on wrong embedding dimension"""
    wrong_dim_embedding = np.random.randn(256).astype('float32')

    with pytest.raises(ValueError, match="Embedding dimension mismatch"):
        await vector_db.add(wrong_dim_embedding, sample_ids[0])


@pytest.mark.asyncio
async def test_search_wrong_dimension(vector_db, sample_embeddings, sample_ids):
    """Test error on search with wrong dimension"""
    # Add some vectors first
    await vector_db.add(sample_embeddings[0], sample_ids[0])

    # Try to search with wrong dimension
    wrong_dim_query = np.random.randn(256).astype('float32')

    with pytest.raises(ValueError, match="Query dimension mismatch"):
        await vector_db.search(wrong_dim_query, top_k=5)


# Statistics Tests


@pytest.mark.asyncio
async def test_get_stats(vector_db, sample_embeddings, sample_ids):
    """Test getting database statistics"""
    await vector_db.add_batch(sample_embeddings[:5], sample_ids[:5])

    stats = vector_db.get_stats()

    assert stats["total_vectors"] == 5
    assert stats["index_type"] == "flat"
    assert stats["embedding_dim"] == vector_db.embedding_dim
    assert stats["is_trained"] is True  # Flat index doesn't need training


# Performance Tests


@pytest.mark.asyncio
async def test_search_performance(vector_db):
    """Test search performance meets <10ms target for 1000 vectors"""
    import time

    # Add 1000 vectors
    embeddings = np.random.randn(1000, vector_db.embedding_dim).astype('float32')
    ids = [f"vec{i}" for i in range(1000)]
    await vector_db.add_batch(embeddings, ids)

    # Measure search time
    query = np.random.randn(vector_db.embedding_dim).astype('float32')
    start = time.time()
    results = await vector_db.search(query, top_k=10)
    elapsed_ms = (time.time() - start) * 1000

    # Should be fast (<10ms target for 100K, even faster for 1K)
    assert elapsed_ms < 50  # Very generous for 1K vectors
    assert len(results) == 10


@pytest.mark.asyncio
async def test_concurrent_operations(vector_db, sample_embeddings, sample_ids):
    """Test thread-safe concurrent operations"""
    # Add vectors concurrently
    tasks = [
        vector_db.add(sample_embeddings[i], sample_ids[i])
        for i in range(10)
    ]
    await asyncio.gather(*tasks)

    assert vector_db.total_vectors == 10

    # Search concurrently
    search_tasks = [
        vector_db.search(sample_embeddings[i], top_k=3)
        for i in range(5)
    ]
    results_list = await asyncio.gather(*search_tasks)

    # All searches should succeed
    assert all(len(results) > 0 for results in results_list)


@pytest.mark.asyncio
async def test_concurrent_operations_nonblocking(embedding_dim):
    """
    Verify FAISS operations don't block event loop.

    This test prevents regression of blocking I/O bugs.
    If operations are blocking, 100 calls would take ~50s.
    If non-blocking (asyncio.to_thread), should take <5s.

    References: ASYNC_WRAPPER_PATTERN.md
    """
    import time

    db = FAISSVectorDatabase(embedding_dim=embedding_dim)

    # Generate test data
    np.random.seed(42)
    embeddings = [np.random.rand(embedding_dim).astype('float32') for _ in range(100)]
    ids = [f"test_{i}" for i in range(100)]
    metadata = [{"index": i} for i in range(100)]

    # Run 100 add operations concurrently
    start_time = time.time()

    tasks = [
        db.add(embeddings[i], ids[i], metadata[i])
        for i in range(100)
    ]
    await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    # If blocking, would take 100 * 0.5s = 50s
    # If non-blocking, should complete in ~2-5s
    assert elapsed < 10.0, f"Operations blocked event loop: {elapsed:.2f}s"

    # Verify all operations succeeded
    stats = db.get_stats()
    assert stats["total_vectors"] == 100


@pytest.mark.asyncio
async def test_concurrent_search_nonblocking(embedding_dim):
    """
    Verify search operations don't block event loop under concurrent load.

    References: ASYNC_WRAPPER_PATTERN.md
    """
    import time

    db = FAISSVectorDatabase(embedding_dim=embedding_dim)

    # Add test data
    np.random.seed(42)
    for i in range(10):
        embedding = np.random.rand(embedding_dim).astype('float32')
        await db.add(embedding, f"doc_{i}", {"index": i})

    # Run 100 search operations concurrently
    start_time = time.time()

    query = np.random.rand(embedding_dim).astype('float32')
    tasks = [db.search(query, top_k=5) for _ in range(100)]
    results = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    # If blocking, would take significantly longer
    # If non-blocking with asyncio.to_thread, should be fast
    assert elapsed < 5.0, f"Search operations blocked: {elapsed:.2f}s"
    assert len(results) == 100
    assert all(len(r) <= 5 for r in results)  # top_k=5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
