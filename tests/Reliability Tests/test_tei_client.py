"""
Tests for TEI Client

Validates TEI client functionality:
- Single embedding generation
- Batch embedding generation
- Reranking
- Error handling and retry logic
- OpenAI fallback
- Statistics tracking

Author: Alex (E2E Testing Lead)
Date: November 4, 2025
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

from infrastructure.tei_client import (
    TEIClient,
    TEIConfig,
    EmbeddingMetrics,
    get_tei_client,
    reset_tei_client
)


@pytest.fixture
def tei_client():
    """Create TEI client for testing."""
    config = TEIConfig(
        endpoint="http://localhost:8081",
        enable_metrics=True
    )
    client = TEIClient(config=config)
    yield client
    asyncio.run(client.close())


@pytest.fixture
def mock_tei_response():
    """Mock TEI API response."""
    return [[0.1] * 384, [0.2] * 384, [0.3] * 384]


class TestEmbeddingMetrics:
    """Test embedding metrics."""

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = EmbeddingMetrics()
        assert metrics.total_requests == 0
        assert metrics.total_embeddings == 0
        assert metrics.errors == 0
        assert metrics.avg_latency_ms == 0.0

    def test_metrics_avg_latency(self):
        """Test average latency calculation."""
        metrics = EmbeddingMetrics(total_requests=10, total_latency_ms=500.0)
        assert metrics.avg_latency_ms == 50.0

    def test_metrics_record_request(self):
        """Test recording a request."""
        metrics = EmbeddingMetrics()
        metrics.record_request(num_embeddings=10, latency_ms=50.0, tokens=100)
        assert metrics.total_requests == 1
        assert metrics.total_embeddings == 10
        assert metrics.total_tokens == 100

    def test_metrics_to_dict(self):
        """Test metrics to dictionary conversion."""
        metrics = EmbeddingMetrics(total_requests=5, total_embeddings=50, total_tokens=500)
        result = metrics.to_dict()
        assert result["total_requests"] == 5
        assert result["total_embeddings"] == 50
        assert result["total_tokens"] == 500


class TestTEIClient:
    """Test TEI client."""
    
    def test_client_initialization(self, tei_client):
        """Test client initialization."""
        assert tei_client.endpoint == "http://localhost:8081"
        assert tei_client.model == "BAAI/bge-base-en-v1.5"
        assert tei_client.embedding_dim == 768
        assert tei_client.timeout == 30.0
        assert tei_client.max_retries == 3
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, tei_client):
        """Test health check success."""
        with patch.object(tei_client.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = await tei_client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, tei_client):
        """Test health check failure."""
        with patch.object(tei_client.client, 'get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            
            result = await tei_client.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_embed_single(self, tei_client, mock_tei_response):
        """Test single embedding generation."""
        with patch.object(tei_client, '_embed_batch_internal') as mock_call:
            mock_call.return_value = mock_tei_response[:1]

            embedding = await tei_client.embed_single("test text")

            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (384,)
            assert tei_client.metrics.total_requests == 1
            assert tei_client.metrics.total_embeddings == 1

    @pytest.mark.asyncio
    async def test_embed_batch(self, tei_client, mock_tei_response):
        """Test batch embedding generation."""
        with patch.object(tei_client, '_embed_batch_internal') as mock_call:
            mock_call.return_value = mock_tei_response

            texts = ["text1", "text2", "text3"]
            embeddings = await tei_client.embed_batch(texts)

            assert isinstance(embeddings, list)
            assert len(embeddings) == 3
            assert tei_client.metrics.total_requests == 1
            assert tei_client.metrics.total_embeddings == 3
    
    @pytest.mark.asyncio
    async def test_embed_batch_empty(self, tei_client):
        """Test batch embedding with empty list."""
        embeddings = await tei_client.embed_batch([])
        assert isinstance(embeddings, list)
        assert len(embeddings) == 0
    
    @pytest.mark.asyncio
    async def test_rerank(self, tei_client):
        """Test reranking."""
        with patch.object(tei_client, '_call_tei_with_retry') as mock_call:
            mock_call.return_value = [
                {"index": 1, "score": 0.9},
                {"index": 0, "score": 0.7},
                {"index": 2, "score": 0.5}
            ]
            
            query = "test query"
            documents = ["doc1", "doc2", "doc3"]
            results = await tei_client.rerank(query, documents)
            
            assert len(results) == 3
            assert results[0]["index"] == 1
            assert results[0]["score"] == 0.9
            assert results[0]["text"] == "doc2"
    
    @pytest.mark.asyncio
    async def test_rerank_empty(self, tei_client):
        """Test reranking with empty documents."""
        results = await tei_client.rerank("query", [])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, tei_client):
        """Test retry logic with exponential backoff."""
        with patch.object(tei_client.client, 'post') as mock_post:
            # First two attempts fail, third succeeds
            mock_response_fail = Mock()
            mock_response_fail.status_code = 500
            mock_response_fail.raise_for_status.side_effect = Exception("Server error")
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = [[0.1] * 768]
            
            mock_post.side_effect = [
                mock_response_fail,
                mock_response_fail,
                mock_response_success
            ]
            
            result = await tei_client._call_tei_with_retry(
                endpoint="/embed",
                payload={"inputs": ["test"]}
            )
            
            assert result == [[0.1] * 768]
            assert mock_post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_fallback_to_openai(self):
        """Test fallback to OpenAI when TEI unavailable."""
        client = TEIClient(
            endpoint="http://localhost:8081",
            fallback_to_openai=True,
            enable_otel=False
        )
        
        with patch.object(client, '_call_tei_with_retry') as mock_tei:
            mock_tei.side_effect = Exception("TEI unavailable")
            
            with patch.object(client, '_fallback_to_openai_batch') as mock_openai:
                mock_openai.return_value = np.array([[0.1] * 1536])
                
                embeddings = await client.embed_batch(["test"])
                
                assert mock_openai.called
                assert client.stats.fallback_to_openai == 1
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_error_handling_no_fallback(self, tei_client):
        """Test error handling without fallback."""
        with patch.object(tei_client, '_call_tei_with_retry') as mock_call:
            mock_call.side_effect = Exception("TEI error")
            
            with pytest.raises(Exception):
                await tei_client.embed_single("test")
            
            assert tei_client.stats.errors == 1
    
    def test_get_stats(self, tei_client):
        """Test get statistics."""
        tei_client.stats.total_requests = 10
        tei_client.stats.total_embeddings = 100
        
        stats = tei_client.get_stats()
        assert stats.total_requests == 10
        assert stats.total_embeddings == 100
    
    def test_reset_stats(self, tei_client):
        """Test reset statistics."""
        tei_client.stats.total_requests = 10
        tei_client.reset_stats()
        
        assert tei_client.stats.total_requests == 0


class TestTEISingleton:
    """Test TEI singleton pattern."""
    
    def test_get_tei_client(self):
        """Test get singleton instance."""
        reset_tei_client()
        
        client1 = get_tei_client()
        client2 = get_tei_client()
        
        assert client1 is client2
    
    def test_reset_tei_client(self):
        """Test reset singleton."""
        reset_tei_client()
        
        client1 = get_tei_client()
        reset_tei_client()
        client2 = get_tei_client()
        
        assert client1 is not client2


class TestTEIIntegration:
    """Integration tests (require running TEI server)."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_tei_server(self):
        """Test with real TEI server (skip if not available)."""
        client = TEIClient(endpoint="http://localhost:8081", enable_otel=False)
        
        # Check if server is available
        healthy = await client.health_check()
        if not healthy:
            pytest.skip("TEI server not available")
        
        # Test single embedding
        embedding = await client.embed_single("Genesis agent system")
        assert embedding.shape == (768,)
        
        # Test batch embedding
        embeddings = await client.embed_batch(["text1", "text2", "text3"])
        assert embeddings.shape == (3, 768)
        
        await client.close()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_performance_targets(self):
        """Test performance targets (skip if server not available)."""
        client = TEIClient(endpoint="http://localhost:8081", enable_otel=False)
        
        healthy = await client.health_check()
        if not healthy:
            pytest.skip("TEI server not available")
        
        import time
        
        # Test single embedding latency (<50ms target)
        start = time.time()
        await client.embed_single("test text")
        latency_ms = (time.time() - start) * 1000
        
        assert latency_ms < 50, f"Single embedding latency {latency_ms:.1f}ms exceeds 50ms target"
        
        # Test batch 100 latency (<500ms target)
        texts = [f"text {i}" for i in range(100)]
        start = time.time()
        await client.embed_batch(texts)
        latency_ms = (time.time() - start) * 1000
        
        assert latency_ms < 500, f"Batch 100 latency {latency_ms:.1f}ms exceeds 500ms target"
        
        await client.close()

