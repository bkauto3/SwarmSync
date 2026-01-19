"""
Tests for OpenAI Embedding Generator

This test suite validates the EmbeddingGenerator implementation including:
- Single and batch embedding generation
- Caching mechanisms
- Cost estimation
- Error handling
- Performance characteristics

Note: Most tests use mocking to avoid real API calls. A few integration tests
at the end can be run with a real API key for validation.

Author: Thon (Python Expert)
Date: October 23, 2025
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from infrastructure.embedding_generator import EmbeddingGenerator, EmbeddingStats


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=np.random.randn(1536).tolist())
    ]
    mock_response.usage = MagicMock(total_tokens=50)
    return mock_response


@pytest.fixture
def mock_openai_batch_response():
    """Mock OpenAI API batch response"""
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=np.random.randn(1536).tolist())
        for _ in range(5)
    ]
    mock_response.usage = MagicMock(total_tokens=250)
    return mock_response


@pytest.fixture
def generator():
    """Create embedding generator with mock client"""
    return EmbeddingGenerator(
        api_key="test-key",
        model="text-embedding-3-small",
        batch_size=100,
        cache_size=1000
    )


# Basic Functionality Tests


@pytest.mark.asyncio
async def test_generate_embedding_shape(generator, mock_openai_response):
    """Test that generated embedding has correct shape"""
    with patch.object(generator.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response

        embedding = await generator.generate_embedding("Test text")

        assert embedding.shape == (1536,)
        assert embedding.dtype == np.float32


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(generator):
    """Test error on empty text"""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await generator.generate_embedding("")

    with pytest.raises(ValueError, match="Text cannot be empty"):
        await generator.generate_embedding("   ")  # Whitespace only


@pytest.mark.asyncio
async def test_generate_batch_embeddings(generator, mock_openai_batch_response):
    """Test batch embedding generation"""
    with patch.object(generator.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_batch_response

        texts = [f"Text {i}" for i in range(5)]
        embeddings = await generator.generate_embeddings_batch(texts)

        assert len(embeddings) == 5
        assert all(emb.shape == (1536,) for emb in embeddings)
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_generate_batch_empty_list(generator):
    """Test batch generation with empty list"""
    embeddings = await generator.generate_embeddings_batch([])
    assert embeddings == []


@pytest.mark.asyncio
async def test_generate_batch_with_empty_text(generator):
    """Test error on batch with empty text"""
    texts = ["Text 1", "", "Text 3"]

    with pytest.raises(ValueError, match="Text at index 1 is empty"):
        await generator.generate_embeddings_batch(texts)


# Caching Tests


@pytest.mark.asyncio
async def test_cache_hit(generator, mock_openai_response):
    """Test that cache avoids redundant API calls"""
    with patch.object(generator.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response

        # First call - should hit API
        embedding1 = await generator.generate_embedding("Test text")
        assert mock_create.call_count == 1

        # Second call with same text - should use cache
        embedding2 = await generator.generate_embedding("Test text")
        assert mock_create.call_count == 1  # No additional API call

        # Embeddings should be identical
        np.testing.assert_array_equal(embedding1, embedding2)

        # Check stats
        assert generator.stats.cache_hits == 1
        assert generator.stats.cache_misses == 1


@pytest.mark.asyncio
async def test_cache_disabled(generator, mock_openai_response):
    """Test that use_cache=False bypasses cache"""
    with patch.object(generator.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response

        # Two calls with cache disabled
        await generator.generate_embedding("Test text", use_cache=False)
        await generator.generate_embedding("Test text", use_cache=False)

        # Should make 2 API calls
        assert mock_create.call_count == 2


@pytest.mark.asyncio
async def test_cache_lru_eviction(generator, mock_openai_response):
    """Test LRU cache eviction when full"""
    # Create generator with small cache
    small_cache_gen = EmbeddingGenerator(api_key="test-key", cache_size=3)

    with patch.object(small_cache_gen.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response

        # Add 4 items (cache size is 3)
        for i in range(4):
            await small_cache_gen.generate_embedding(f"Text {i}")

        # First item should be evicted
        assert len(small_cache_gen._cache) == 3
        assert len(small_cache_gen._cache_order) == 3

        # Verify correct items are cached (most recent 3)
        text_hash_0 = small_cache_gen._hash_text("Text 0")
        text_hash_3 = small_cache_gen._hash_text("Text 3")

        assert text_hash_0 not in small_cache_gen._cache  # Evicted
        assert text_hash_3 in small_cache_gen._cache  # Kept


@pytest.mark.asyncio
async def test_cache_clear(generator, mock_openai_response):
    """Test clearing cache"""
    with patch.object(generator.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response

        # Generate and cache embedding
        await generator.generate_embedding("Test text")
        assert len(generator._cache) == 1

        # Clear cache
        await generator.clear_cache()
        assert len(generator._cache) == 0
        assert len(generator._cache_order) == 0


# Normalization Tests


@pytest.mark.asyncio
async def test_l2_normalization(generator, mock_openai_response):
    """Test L2 normalization"""
    generator_with_norm = EmbeddingGenerator(api_key="test-key", normalize=True)

    with patch.object(generator_with_norm.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response

        embedding = await generator_with_norm.generate_embedding("Test text")

        # Check that embedding is normalized (L2 norm should be 1)
        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=1e-6)


# Statistics Tests


@pytest.mark.asyncio
async def test_stats_tracking(generator, mock_openai_response):
    """Test that statistics are tracked correctly"""
    with patch.object(generator.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response

        # Generate embeddings
        await generator.generate_embedding("Test 1")
        await generator.generate_embedding("Test 2")

        stats = generator.get_stats()

        assert stats["total_requests"] == 2
        assert stats["total_tokens"] == 100  # 50 per request
        assert stats["total_cost_usd"] > 0
        assert stats["cache_misses"] == 2
        assert stats["avg_latency_ms"] > 0


@pytest.mark.asyncio
async def test_cost_estimation(generator):
    """Test cost estimation"""
    # Estimate for 1000 texts with avg 50 tokens each
    cost = generator.estimate_cost(1000, avg_tokens_per_text=50)

    # 1000 * 50 = 50,000 tokens
    # Cost = 50,000 / 1,000,000 * $0.02 = $0.001
    assert np.isclose(cost, 0.001, rtol=0.01)


# Batch Processing Tests


@pytest.mark.asyncio
async def test_large_batch_splitting(generator):
    """Test that large batches are split correctly"""
    # Create generator with small batch size
    small_batch_gen = EmbeddingGenerator(api_key="test-key", batch_size=10)

    # Mock needs to return correct number of embeddings per batch
    def create_mock_response(input_texts):
        batch_size = len(input_texts) if isinstance(input_texts, list) else 1
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=np.random.randn(1536).tolist()) for _ in range(batch_size)]
        mock_response.usage = MagicMock(total_tokens=50 * batch_size)
        return mock_response

    with patch.object(small_batch_gen.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = lambda **kwargs: create_mock_response(kwargs['input'])

        # Generate 25 embeddings (should split into 3 batches: 10 + 10 + 5)
        texts = [f"Text {i}" for i in range(25)]
        embeddings = await small_batch_gen.generate_embeddings_batch(texts)

        assert len(embeddings) == 25
        assert mock_create.call_count == 3  # 3 API calls


@pytest.mark.asyncio
async def test_batch_preserves_order(generator):
    """Test that batch processing preserves input order"""
    # Mock responses with identifiable embeddings
    def create_mock_response(batch_size):
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[float(i)] * 1536)
            for i in range(batch_size)
        ]
        mock_response.usage = MagicMock(total_tokens=batch_size * 50)
        return mock_response

    with patch.object(generator.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = create_mock_response(5)

        texts = [f"Text {i}" for i in range(5)]
        embeddings = await generator.generate_embeddings_batch(texts)

        # Check that order is preserved
        for i, embedding in enumerate(embeddings):
            assert embedding[0] == float(i)


# Concurrent Request Coalescing Tests


@pytest.mark.asyncio
async def test_request_coalescing(generator, mock_openai_response):
    """Test that concurrent identical requests are coalesced"""
    with patch.object(generator.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response

        # Make 3 concurrent identical requests
        tasks = [
            generator.generate_embedding("Same text"),
            generator.generate_embedding("Same text"),
            generator.generate_embedding("Same text")
        ]
        embeddings = await asyncio.gather(*tasks)

        # Should only make 1 API call (others wait and use cache)
        assert mock_create.call_count == 1

        # All embeddings should be identical
        np.testing.assert_array_equal(embeddings[0], embeddings[1])
        np.testing.assert_array_equal(embeddings[1], embeddings[2])


# Dimension Reduction Tests


@pytest.mark.asyncio
async def test_dimension_reduction(mock_openai_response):
    """Test embedding dimension reduction"""
    generator_512 = EmbeddingGenerator(api_key="test-key", embedding_dim=512)

    # Mock response with 512 dimensions
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=np.random.randn(512).tolist())]
    mock_response.usage = MagicMock(total_tokens=50)

    with patch.object(generator_512.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response

        embedding = await generator_512.generate_embedding("Test text")

        assert embedding.shape == (512,)
        # Check that dimensions parameter was passed to API
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("dimensions") == 512


# Integration Tests (commented out by default - require real API key)


# @pytest.mark.integration
# @pytest.mark.asyncio
# async def test_real_api_call():
#     """Test with real OpenAI API (requires API key in environment)"""
#     import os
#     api_key = os.environ.get("OPENAI_API_KEY")
#     if not api_key:
#         pytest.skip("OPENAI_API_KEY not set")
#
#     generator = EmbeddingGenerator(api_key=api_key)
#     embedding = await generator.generate_embedding("Hello, world!")
#
#     assert embedding.shape == (1536,)
#     assert not np.allclose(embedding, 0)  # Should not be all zeros
#
#
# @pytest.mark.integration
# @pytest.mark.asyncio
# async def test_real_batch_api_call():
#     """Test batch with real OpenAI API"""
#     import os
#     api_key = os.environ.get("OPENAI_API_KEY")
#     if not api_key:
#         pytest.skip("OPENAI_API_KEY not set")
#
#     generator = EmbeddingGenerator(api_key=api_key, batch_size=10)
#     texts = [f"Test text number {i}" for i in range(5)]
#     embeddings = await generator.generate_embeddings_batch(texts)
#
#     assert len(embeddings) == 5
#     assert all(emb.shape == (1536,) for emb in embeddings)
#     # Embeddings should be different for different texts
#     assert not np.allclose(embeddings[0], embeddings[1])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
