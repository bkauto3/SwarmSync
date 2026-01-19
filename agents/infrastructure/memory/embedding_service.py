"""
Embedding Service for Agentic RAG

Provides text embedding generation with caching and batch processing:
- OpenAI text-embedding-3-small (1536 dimensions, $0.02/1M tokens)
- Redis caching for hot embeddings (80%+ cache hit rate)
- Batch processing for efficiency (up to 2048 texts per API call)
- Automatic retry with exponential backoff
- OTEL observability integration

Performance Targets:
- Cache hit: <5ms P95
- Cache miss + generate: <100ms P95
- Batch processing: 100+ embeddings/second
- Cache hit rate: >80% for repeated queries

Cost Optimization:
- Redis caching reduces API calls by 80%+
- Batch processing reduces overhead
- Dimension reduction option (256/512/1024 vs 1536)

Version: 1.0
Created: November 2, 2025
"""

import asyncio
import hashlib
import json
import os
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

import redis.asyncio as aioredis
from openai import AsyncOpenAI, OpenAIError, RateLimitError

from infrastructure.observability import (
    get_observability_manager,
    SpanType,
)

obs_manager = get_observability_manager()


@dataclass
class EmbeddingStats:
    """Statistics for embedding service."""
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    errors: int = 0
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate,
            "api_calls": self.api_calls,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "errors": self.errors
        }


class EmbeddingService:
    """
    Text embedding service with Redis caching and batch processing.
    
    Features:
    - OpenAI text-embedding-3-small (1536 dimensions)
    - Redis caching with 24-hour TTL
    - Batch processing (up to 2048 texts)
    - Automatic retry with exponential backoff
    - OTEL observability
    
    Usage:
        service = EmbeddingService()
        await service.connect()
        
        # Single embedding
        embedding = await service.embed_text("Hello world")
        
        # Batch embeddings
        embeddings = await service.embed_batch(["text1", "text2", "text3"])
        
        # Get statistics
        stats = service.get_stats()
        print(f"Cache hit rate: {stats.cache_hit_rate:.1%}")
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        redis_url: str = "redis://localhost:6379/0",
        model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
        batch_size: int = 100,
        cache_ttl_seconds: int = 86400,  # 24 hours
        max_retries: int = 3,
        timeout_seconds: float = 30.0
    ):
        """
        Initialize embedding service.
        
        Args:
            openai_api_key: OpenAI API key (reads from env if None)
            redis_url: Redis connection URL
            model: OpenAI embedding model name
            embedding_dim: Embedding dimension (1536 for full, or 256/512/1024)
            batch_size: Maximum texts per API call (1-2048)
            cache_ttl_seconds: Redis cache TTL (default: 24 hours)
            max_retries: Maximum retry attempts on failure
            timeout_seconds: API request timeout
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key required (set OPENAI_API_KEY env var)")
        
        self.redis_url = redis_url
        self.model = model
        self.embedding_dim = embedding_dim
        self.batch_size = batch_size
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        
        # Initialize clients
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key, timeout=timeout_seconds)
        self.redis_client: Optional[aioredis.Redis] = None
        self._connected = False
        
        # Statistics
        self.stats = EmbeddingStats()
        
        # Cost per 1M tokens (text-embedding-3-small)
        self.cost_per_million_tokens = 0.02
    
    async def connect(self) -> None:
        """Connect to Redis cache."""
        if self._connected:
            return
        
        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle JSON encoding
                socket_connect_timeout=5.0,
                socket_timeout=5.0
            )
            
            # Test connection
            await self.redis_client.ping()
            self._connected = True
            
            print(f"[EmbeddingService] Connected to Redis: {self.redis_url}")
        
        except Exception as e:
            print(f"[EmbeddingService] WARNING: Redis connection failed: {e}")
            print("[EmbeddingService] Running without cache (degraded mode)")
            self.redis_client = None
            self._connected = False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self._connected = False
    
    def _make_cache_key(self, text: str) -> str:
        """
        Generate cache key for text.
        
        Uses SHA256 hash of text + model + dimension for uniqueness.
        """
        content = f"{self.model}:{self.embedding_dim}:{text}"
        hash_digest = hashlib.sha256(content.encode()).hexdigest()
        return f"embedding:{hash_digest}"
    
    async def _get_from_cache(self, text: str) -> Optional[List[float]]:
        """Get embedding from Redis cache."""
        if not self._connected or not self.redis_client:
            return None
        
        cache_key = self._make_cache_key(text)
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                self.stats.cache_hits += 1
                embedding = json.loads(cached_data)
                return embedding
            else:
                self.stats.cache_misses += 1
                return None
        
        except Exception as e:
            print(f"[EmbeddingService] Cache get error: {e}")
            return None
    
    async def _set_in_cache(self, text: str, embedding: List[float]) -> None:
        """Set embedding in Redis cache."""
        if not self._connected or not self.redis_client:
            return
        
        cache_key = self._make_cache_key(text)
        
        try:
            embedding_json = json.dumps(embedding)
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl_seconds,
                embedding_json
            )
        
        except Exception as e:
            print(f"[EmbeddingService] Cache set error: {e}")
    
    async def _generate_embeddings(
        self,
        texts: List[str],
        retry_count: int = 0
    ) -> List[List[float]]:
        """
        Generate embeddings via OpenAI API.
        
        Includes automatic retry with exponential backoff.
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.embedding_dim if self.embedding_dim < 1536 else None
            )
            
            # Extract embeddings
            embeddings = [item.embedding for item in response.data]
            
            # Update statistics
            self.stats.api_calls += 1
            self.stats.total_tokens += response.usage.total_tokens
            cost = (response.usage.total_tokens / 1_000_000) * self.cost_per_million_tokens
            self.stats.total_cost_usd += cost
            
            return embeddings
        
        except RateLimitError as e:
            if retry_count < self.max_retries:
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** retry_count
                print(f"[EmbeddingService] Rate limit hit, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._generate_embeddings(texts, retry_count + 1)
            else:
                self.stats.errors += 1
                raise
        
        except OpenAIError as e:
            self.stats.errors += 1
            print(f"[EmbeddingService] OpenAI API error: {e}")
            raise
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text.
        
        Checks cache first, generates if miss.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector (1536 dimensions)
        """
        with obs_manager.timed_operation(
            "embedding_service.embed_text",
            SpanType.EXECUTION
        ) as span:
            span.set_attribute("text_length", len(text))
            span.set_attribute("model", self.model)
            
            # Check cache
            cached_embedding = await self._get_from_cache(text)
            if cached_embedding:
                span.set_attribute("cache_hit", True)
                return cached_embedding
            
            span.set_attribute("cache_hit", False)
            
            # Generate embedding
            embeddings = await self._generate_embeddings([text])
            embedding = embeddings[0]
            
            # Cache result
            await self._set_in_cache(text, embedding)
            
            return embedding
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for batch of texts.
        
        Processes in batches of batch_size, checks cache for each text.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List of embedding vectors
        """
        with obs_manager.timed_operation(
            "embedding_service.embed_batch",
            SpanType.EXECUTION
        ) as span:
            span.set_attribute("batch_size", len(texts))
            span.set_attribute("model", self.model)
            
            embeddings: List[Optional[List[float]]] = [None] * len(texts)
            texts_to_generate: List[tuple[int, str]] = []
            
            # Check cache for all texts
            for i, text in enumerate(texts):
                cached_embedding = await self._get_from_cache(text)
                if cached_embedding:
                    embeddings[i] = cached_embedding
                else:
                    texts_to_generate.append((i, text))
            
            span.set_attribute("cache_hits", len(texts) - len(texts_to_generate))
            span.set_attribute("cache_misses", len(texts_to_generate))
            
            # Generate embeddings for cache misses in batches
            if texts_to_generate:
                for batch_start in range(0, len(texts_to_generate), self.batch_size):
                    batch_end = min(batch_start + self.batch_size, len(texts_to_generate))
                    batch = texts_to_generate[batch_start:batch_end]
                    
                    batch_texts = [text for _, text in batch]
                    batch_embeddings = await self._generate_embeddings(batch_texts)
                    
                    # Store results and cache
                    for (original_idx, text), embedding in zip(batch, batch_embeddings):
                        embeddings[original_idx] = embedding
                        await self._set_in_cache(text, embedding)
            
            # Ensure all embeddings are present
            assert all(e is not None for e in embeddings), "Missing embeddings"
            
            return embeddings  # type: ignore
    
    def get_stats(self) -> EmbeddingStats:
        """Get service statistics."""
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats = EmbeddingStats()


# Singleton instance for global access
_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service(
    openai_api_key: Optional[str] = None,
    redis_url: str = "redis://localhost:6379/0",
    **kwargs
) -> EmbeddingService:
    """
    Get or create singleton EmbeddingService instance.
    
    Args:
        openai_api_key: OpenAI API key (reads from env if None)
        redis_url: Redis connection URL
        **kwargs: Additional arguments passed to EmbeddingService
    
    Returns:
        Singleton service instance
    """
    global _embedding_service_instance
    
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService(
            openai_api_key=openai_api_key,
            redis_url=redis_url,
            **kwargs
        )
    
    return _embedding_service_instance
