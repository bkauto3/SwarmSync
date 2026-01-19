"""
Simple Tests for TEI Client

Validates core TEI client functionality matching actual implementation.

Author: Hudson (Code Quality Lead)
Date: November 5, 2025
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from infrastructure.tei_client import (
    TEIClient,
    TEIConfig,
    EmbeddingMetrics
)


@pytest.fixture
def tei_config():
    """Create TEI config for testing."""
    return TEIConfig(
        endpoint="http://localhost:8081",
        embedding_dim=384,
        enable_metrics=True
    )


@pytest.fixture
def tei_client(tei_config):
    """Create TEI client for testing."""
    client = TEIClient(config=tei_config)
    yield client
    asyncio.run(client.close())


class TestEmbeddingMetrics:
    """Test embedding metrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = EmbeddingMetrics()
        assert metrics.total_requests == 0
        assert metrics.total_embeddings == 0
        assert metrics.errors == 0
        assert metrics.avg_latency_ms == 0.0
    
    def test_metrics_record_request(self):
        """Test recording a request."""
        metrics = EmbeddingMetrics()
        metrics.record_request(num_embeddings=10, latency_ms=50.0, tokens=100)
        assert metrics.total_requests == 1
        assert metrics.total_embeddings == 10
        assert metrics.total_tokens == 100
        assert metrics.avg_latency_ms == 50.0
    
    def test_metrics_avg_latency(self):
        """Test average latency calculation."""
        metrics = EmbeddingMetrics()
        metrics.record_request(num_embeddings=5, latency_ms=100.0)
        metrics.record_request(num_embeddings=5, latency_ms=200.0)
        assert metrics.avg_latency_ms == 150.0
    
    def test_metrics_cost_calculation(self):
        """Test cost calculation."""
        metrics = EmbeddingMetrics()
        metrics.record_request(num_embeddings=10, latency_ms=50.0, tokens=1_000_000)
        assert metrics.cost_usd == pytest.approx(0.00156, rel=0.01)
    
    def test_metrics_to_dict(self):
        """Test metrics to dictionary conversion."""
        metrics = EmbeddingMetrics()
        metrics.record_request(num_embeddings=10, latency_ms=50.0, tokens=100)
        result = metrics.to_dict()
        assert result["total_requests"] == 1
        assert result["total_embeddings"] == 10
        assert result["total_tokens"] == 100


class TestTEIClient:
    """Test TEI client."""
    
    def test_client_initialization(self, tei_client):
        """Test client initialization."""
        assert tei_client.config.endpoint == "http://localhost:8081"
        assert tei_client.config.embedding_dim == 384
        assert tei_client.metrics is not None
    
    @pytest.mark.asyncio
    async def test_embed_single(self, tei_client):
        """Test single text embedding."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [[0.1] * 384]
        
        with patch.object(tei_client.client, 'post', return_value=mock_response):
            embedding = await tei_client.embed_single("test text")
            
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (384,)
            assert tei_client.metrics.total_requests == 1
            assert tei_client.metrics.total_embeddings == 1
    
    @pytest.mark.asyncio
    async def test_embed_batch(self, tei_client):
        """Test batch embedding generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
        
        with patch.object(tei_client.client, 'post', return_value=mock_response):
            texts = ["text1", "text2", "text3"]
            embeddings = await tei_client.embed_batch(texts)
            
            assert isinstance(embeddings, list)
            assert len(embeddings) == 3
            assert all(isinstance(e, np.ndarray) for e in embeddings)
            assert all(e.shape == (384,) for e in embeddings)
    
    @pytest.mark.asyncio
    async def test_embed_batch_empty(self, tei_client):
        """Test batch embedding with empty list."""
        embeddings = await tei_client.embed_batch([])
        assert isinstance(embeddings, list)
        assert len(embeddings) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, tei_client):
        """Test error handling with retries."""
        with patch.object(tei_client.client, 'post', side_effect=Exception("Connection error")):
            with pytest.raises(RuntimeError, match="Failed to embed texts"):
                await tei_client.embed_single("test")
            
            assert tei_client.metrics.errors == 1
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, tei_client):
        """Test health check success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(tei_client.client, 'get', return_value=mock_response):
            result = await tei_client.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, tei_client):
        """Test health check failure."""
        with patch.object(tei_client.client, 'get', side_effect=Exception("Connection error")):
            result = await tei_client.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, tei_client):
        """Test get metrics."""
        tei_client.metrics.total_requests = 10
        tei_client.metrics.total_embeddings = 100
        
        metrics = await tei_client.get_metrics()
        assert metrics["total_requests"] == 10
        assert metrics["total_embeddings"] == 100
    
    @pytest.mark.asyncio
    async def test_retry_logic(self, tei_client):
        """Test retry logic on failures."""
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Internal Server Error"
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = [[0.1] * 384]
        
        # First call fails, second succeeds
        with patch.object(tei_client.client, 'post', side_effect=[mock_response_fail, mock_response_success]):
            embedding = await tei_client.embed_single("test")
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (384,)


class TestTEIConfig:
    """Test TEI configuration."""
    
    def test_config_defaults(self):
        """Test default configuration."""
        config = TEIConfig()
        assert config.endpoint == "http://localhost:8081"
        assert config.model_name == "BAAI/bge-small-en-v1.5"
        assert config.embedding_dim == 384
        assert config.max_retries == 3
        assert config.timeout_seconds == 30.0
        assert config.max_batch_size == 32
        assert config.enable_metrics is True
    
    def test_config_custom(self):
        """Test custom configuration."""
        config = TEIConfig(
            endpoint="http://custom:9000",
            embedding_dim=768,
            max_retries=5
        )
        assert config.endpoint == "http://custom:9000"
        assert config.embedding_dim == 768
        assert config.max_retries == 5


@pytest.mark.integration
class TestTEIIntegration:
    """Integration tests requiring running TEI server."""
    
    @pytest.mark.asyncio
    async def test_real_embedding(self):
        """Test real embedding generation (requires TEI server)."""
        client = TEIClient()
        
        # Check if server is available
        if not await client.health_check():
            pytest.skip("TEI server not available")
        
        try:
            embedding = await client.embed_single("Genesis agent system")
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (384,)
            assert client.metrics.total_requests == 1
        finally:
            await client.close()
    
    @pytest.mark.asyncio
    async def test_real_batch_embedding(self):
        """Test real batch embedding (requires TEI server)."""
        client = TEIClient()
        
        if not await client.health_check():
            pytest.skip("TEI server not available")
        
        try:
            texts = ["text1", "text2", "text3"]
            embeddings = await client.embed_batch(texts)
            assert len(embeddings) == 3
            assert all(isinstance(e, np.ndarray) for e in embeddings)
        finally:
            await client.close()

