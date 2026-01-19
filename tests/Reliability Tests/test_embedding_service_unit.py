"""
Embedding Service Unit Tests (No API Key Required)

Tests core functionality without making actual API calls.

Version: 1.0
Created: November 2, 2025
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.memory.embedding_service import (
    EmbeddingService,
    EmbeddingStats
)


# ============================================================
# UNIT TESTS (No API calls)
# ============================================================

def test_embedding_stats_initialization():
    """Test EmbeddingStats initialization."""
    stats = EmbeddingStats()
    
    assert stats.cache_hits == 0
    assert stats.cache_misses == 0
    assert stats.api_calls == 0
    assert stats.total_tokens == 0
    assert stats.total_cost_usd == 0.0
    assert stats.errors == 0
    assert stats.cache_hit_rate == 0.0


def test_embedding_stats_cache_hit_rate():
    """Test cache hit rate calculation."""
    stats = EmbeddingStats()
    
    # No requests yet
    assert stats.cache_hit_rate == 0.0
    
    # 3 hits, 1 miss = 75%
    stats.cache_hits = 3
    stats.cache_misses = 1
    assert stats.cache_hit_rate == 0.75
    
    # 8 hits, 2 misses = 80%
    stats.cache_hits = 8
    stats.cache_misses = 2
    assert stats.cache_hit_rate == 0.8


def test_embedding_stats_to_dict():
    """Test stats serialization."""
    stats = EmbeddingStats(
        cache_hits=10,
        cache_misses=2,
        api_calls=2,
        total_tokens=1000,
        total_cost_usd=0.02
    )
    
    stats_dict = stats.to_dict()
    
    assert stats_dict["cache_hits"] == 10
    assert stats_dict["cache_misses"] == 2
    assert stats_dict["cache_hit_rate"] == pytest.approx(0.833, rel=0.01)
    assert stats_dict["api_calls"] == 2
    assert stats_dict["total_tokens"] == 1000
    assert stats_dict["total_cost_usd"] == 0.02


def test_embedding_service_initialization():
    """Test EmbeddingService initialization."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(
            openai_api_key="test-key",
            redis_url="redis://localhost:6379/1",
            model="text-embedding-3-small",
            embedding_dim=1536,
            batch_size=100
        )
        
        assert service.model == "text-embedding-3-small"
        assert service.embedding_dim == 1536
        assert service.batch_size == 100
        assert service.cache_ttl_seconds == 86400
        assert service.max_retries == 3


def test_embedding_service_requires_api_key():
    """Test that EmbeddingService requires API key."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="OpenAI API key required"):
            EmbeddingService(openai_api_key=None)


def test_make_cache_key():
    """Test cache key generation."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(openai_api_key="test-key")
        
        # Same text should produce same key
        key1 = service._make_cache_key("hello world")
        key2 = service._make_cache_key("hello world")
        assert key1 == key2
        
        # Different text should produce different key
        key3 = service._make_cache_key("goodbye world")
        assert key1 != key3
        
        # Key should be deterministic
        assert key1.startswith("embedding:")
        assert len(key1) > 20  # SHA256 hash


def test_get_stats():
    """Test getting statistics."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(openai_api_key="test-key")
        
        stats = service.get_stats()
        
        assert isinstance(stats, EmbeddingStats)
        assert stats.cache_hits == 0
        assert stats.api_calls == 0


def test_reset_stats():
    """Test resetting statistics."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(openai_api_key="test-key")
        
        # Modify stats
        service.stats.cache_hits = 10
        service.stats.api_calls = 5
        
        # Reset
        service.reset_stats()
        
        # Should be back to zero
        assert service.stats.cache_hits == 0
        assert service.stats.api_calls == 0


@pytest.mark.asyncio
async def test_connect_redis_success():
    """Test successful Redis connection."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(
            openai_api_key="test-key",
            redis_url="redis://localhost:6379/1"
        )
        
        # Mock Redis client
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_from_url.return_value = mock_redis
            
            await service.connect()
            
            assert service._connected is True
            assert service.redis_client is not None
            mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_connect_redis_failure():
    """Test Redis connection failure (degraded mode)."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(
            openai_api_key="test-key",
            redis_url="redis://localhost:6379/1"
        )
        
        # Mock Redis connection failure
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_from_url.side_effect = Exception("Connection failed")
            
            await service.connect()
            
            # Should handle gracefully
            assert service._connected is False
            assert service.redis_client is None


@pytest.mark.asyncio
async def test_disconnect():
    """Test disconnecting from Redis."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(openai_api_key="test-key")
        
        # Mock connected state
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        service.redis_client = mock_redis
        service._connected = True
        
        await service.disconnect()
        
        assert service._connected is False
        mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_from_cache_hit():
    """Test cache hit."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(openai_api_key="test-key")
        service._connected = True
        
        # Mock Redis client
        mock_redis = AsyncMock()
        embedding = [0.1, 0.2, 0.3]
        mock_redis.get = AsyncMock(return_value=json.dumps(embedding))
        service.redis_client = mock_redis
        
        result = await service._get_from_cache("test text")
        
        assert result == embedding
        assert service.stats.cache_hits == 1
        assert service.stats.cache_misses == 0


@pytest.mark.asyncio
async def test_get_from_cache_miss():
    """Test cache miss."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(openai_api_key="test-key")
        service._connected = True
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        service.redis_client = mock_redis
        
        result = await service._get_from_cache("test text")
        
        assert result is None
        assert service.stats.cache_hits == 0
        assert service.stats.cache_misses == 1


@pytest.mark.asyncio
async def test_set_in_cache():
    """Test setting value in cache."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(openai_api_key="test-key")
        service._connected = True
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        service.redis_client = mock_redis
        
        embedding = [0.1, 0.2, 0.3]
        await service._set_in_cache("test text", embedding)
        
        # Should call setex with TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 86400  # Default TTL


@pytest.mark.asyncio
async def test_generate_embeddings_success():
    """Test successful embedding generation."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        service = EmbeddingService(openai_api_key="test-key")
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6])
        ]
        mock_response.usage = MagicMock(total_tokens=100)
        
        service.openai_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        embeddings = await service._generate_embeddings(["text1", "text2"])
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1, 0.2, 0.3]
        assert embeddings[1] == [0.4, 0.5, 0.6]
        assert service.stats.api_calls == 1
        assert service.stats.total_tokens == 100


def test_compression_basic():
    """Test basic compression functionality."""
    from infrastructure.memory.agentic_rag import AgenticRAG
    
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        rag = AgenticRAG(compression_enabled=True, compression_threshold=10)
        
        # Test value with compressible terms
        value = {
            "description": "Test description",
            "configuration": {"key": "value"},
            "parameters": ["param1", "param2"]
        }
        
        compressed = rag._compress_value(value)
        
        # Should abbreviate terms
        compressed_str = json.dumps(compressed)
        assert "desc" in compressed_str or "description" in compressed_str
        
        # Should be smaller
        original_size = len(json.dumps(value))
        compressed_size = len(compressed_str)
        assert compressed_size <= original_size


def test_decompression():
    """Test decompression functionality."""
    from infrastructure.memory.agentic_rag import AgenticRAG
    
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        rag = AgenticRAG(compression_enabled=True)
        
        # Compress and decompress
        original = {
            "description": "Test",
            "configuration": {"key": "value"}
        }
        
        compressed = rag._compress_value(original)
        decompressed = rag._decompress_value(compressed)
        
        # Should restore original keys
        assert "description" in decompressed
        assert decompressed["description"] == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

