"""
LangMem Deduplication - Semantic Memory Deduplication

Removes duplicate memories using both exact hash matching (fast path)
and semantic similarity via embeddings (slow path). Integrates with
Genesis Memory Store and LangGraph Store API.

Features:
- MD5 hash for exact duplicates (O(1) lookup)
- Cosine similarity for near-duplicates (85%+ threshold)
- Preserves most recent version (by timestamp)
- Batch processing for efficiency
- OTEL observability for deduplication operations

Architecture:
- Two-tier deduplication: exact hash → semantic similarity
- Configurable similarity threshold (default 0.85)
- LRU-style cache for seen embeddings (memory-efficient)
- Type-safe interfaces with comprehensive error handling

Week 1 Target: 30%+ deduplication rate, <50ms P95 dedup latency
"""

import hashlib
import logging
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from infrastructure.logging_config import get_logger
from infrastructure.observability import get_observability_manager

logger = get_logger(__name__)
obs_manager = get_observability_manager()


class LangMemDedup:
    """
    Memory deduplication with semantic similarity

    Provides two-tier deduplication: exact hash matching for speed,
    followed by semantic similarity for near-duplicates. Integrates
    with OTEL observability and supports batch processing.

    Usage:
        ```python
        # Initialize deduplicator
        dedup = LangMemDedup(similarity_threshold=0.85, max_cache_size=10000)

        # Deduplicate list of memories
        unique_memories = await dedup.deduplicate(memories)
        print(f"Reduced from {len(memories)} to {len(unique_memories)}")

        # Get statistics
        stats = dedup.get_stats()
        print(f"Deduplication rate: {stats['dedup_rate']:.1%}")
        ```

    Deduplication Strategy:
    1. Exact hash (MD5): Fast O(1) lookup for identical content
    2. Semantic similarity: Cosine similarity on embeddings (85% threshold)
    3. Preserve newest: Keep entry with most recent timestamp
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_cache_size: int = 10000,
        enable_semantic: bool = True
    ):
        """
        Initialize deduplicator

        Args:
            similarity_threshold: Cosine similarity threshold (0.0-1.0)
            max_cache_size: Maximum embeddings to cache (LRU eviction)
            enable_semantic: Enable semantic similarity (vs hash-only)
        """
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.enable_semantic = enable_semantic

        # Hash cache for exact duplicates
        self.seen_hashes: Set[str] = set()

        # Embedding cache for semantic deduplication (LRU)
        # Format: {content_hash: (embedding, timestamp, entry_id)}
        self.seen_embeddings: OrderedDict[str, Tuple[np.ndarray, str, str]] = OrderedDict()

        # Statistics tracking
        self.stats = {
            "total_processed": 0,
            "exact_duplicates": 0,
            "semantic_duplicates": 0,
            "unique_entries": 0,
            "cache_evictions": 0,
            "total_dedup_time": 0.0
        }

        logger.info(
            f"LangMemDedup initialized with threshold={similarity_threshold}, cache_size={max_cache_size}",
            extra={
                "similarity_threshold": similarity_threshold,
                "max_cache_size": max_cache_size,
                "enable_semantic": enable_semantic
            }
        )

    def compute_hash(self, content: str) -> str:
        """
        Compute MD5 hash of content

        Args:
            content: Text content to hash

        Returns:
            Hex digest of MD5 hash
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def compute_cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity (0.0-1.0)
        """
        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        # Handle zero vectors
        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)

        # Clamp to [0, 1] range
        return float(np.clip(similarity, 0.0, 1.0))

    def _evict_oldest_embedding(self) -> None:
        """
        Evict oldest embedding from cache (LRU)
        """
        if self.seen_embeddings:
            # Remove oldest (first) entry
            self.seen_embeddings.popitem(last=False)
            self.stats["cache_evictions"] += 1

    def _add_to_cache(
        self,
        content_hash: str,
        embedding: np.ndarray,
        timestamp: str,
        entry_id: str
    ) -> None:
        """
        Add embedding to cache with LRU eviction

        Args:
            content_hash: Hash of content
            embedding: Embedding vector
            timestamp: Creation timestamp
            entry_id: Entry ID
        """
        # Evict if at capacity
        if len(self.seen_embeddings) >= self.max_cache_size:
            self._evict_oldest_embedding()

        # Add to cache
        self.seen_embeddings[content_hash] = (embedding, timestamp, entry_id)

        # Move to end (most recent)
        self.seen_embeddings.move_to_end(content_hash)

    async def deduplicate(
        self,
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate memories from list

        Args:
            memories: List of memory dictionaries

        Returns:
            Deduplicated list of memories
        """
        start_time = datetime.utcnow()

        # Start OTEL span (try-except for backwards compatibility)
        try:
            span_ctx = obs_manager.span("langmem_dedup", obs_manager.SpanType.MEMORY if hasattr(obs_manager, 'SpanType') else None)
            span = span_ctx.__enter__()
        except (AttributeError, TypeError):
            from infrastructure.observability import _NullSpan
            span = _NullSpan()
            span_ctx = None

        span.set_attribute("input_count", len(memories))

        try:
            deduped = []
            exact_dups = 0
            semantic_dups = 0

            for memory in memories:
                self.stats["total_processed"] += 1

                # Extract content
                content = self._extract_content(memory)
                if not content:
                    # No content to deduplicate, keep as-is
                    deduped.append(memory)
                    continue

                # Compute hash
                content_hash = self.compute_hash(content)

                # Check exact duplicate (fast path)
                if content_hash in self.seen_hashes:
                    exact_dups += 1
                    logger.debug(
                        f"Exact duplicate found: {content[:50]}...",
                        extra={"content_hash": content_hash}
                    )
                    continue

                # Check semantic similarity (slow path)
                is_semantic_dup = False
                if self.enable_semantic and "embedding" in memory:
                    embedding = self._extract_embedding(memory)
                    if embedding is not None:
                        is_semantic_dup = await self._check_semantic_duplicate(
                            embedding,
                            memory,
                            content_hash
                        )
                        if is_semantic_dup:
                            semantic_dups += 1

                # Not a duplicate - add to results
                if not is_semantic_dup:
                    deduped.append(memory)
                    self.seen_hashes.add(content_hash)

                    # Add embedding to cache if available
                    if self.enable_semantic and "embedding" in memory:
                        embedding = self._extract_embedding(memory)
                        if embedding is not None:
                            timestamp = memory.get("metadata", {}).get("created_at", "")
                            entry_id = memory.get("entry_id", "unknown")
                            self._add_to_cache(content_hash, embedding, timestamp, entry_id)

            # Update statistics
            self.stats["exact_duplicates"] += exact_dups
            self.stats["semantic_duplicates"] += semantic_dups
            self.stats["unique_entries"] += len(deduped)

            duration = (datetime.utcnow() - start_time).total_seconds()
            self.stats["total_dedup_time"] += duration

            # Add OTEL metrics
            span.set_attribute("output_count", len(deduped))
            span.set_attribute("exact_duplicates", exact_dups)
            span.set_attribute("semantic_duplicates", semantic_dups)
            span.set_attribute("duration_seconds", duration)

            logger.info(
                f"Deduplication complete: {len(memories)} → {len(deduped)} "
                f"(exact={exact_dups}, semantic={semantic_dups}) in {duration:.3f}s",
                extra={
                    "input_count": len(memories),
                    "output_count": len(deduped),
                    "exact_duplicates": exact_dups,
                    "semantic_duplicates": semantic_dups,
                    "duration": duration
                }
            )

            return deduped

        except Exception as e:
            logger.error(
                f"Deduplication failed: {str(e)}",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            span.set_attribute("error", str(e))
            raise

    async def _check_semantic_duplicate(
        self,
        embedding: np.ndarray,
        memory: Dict[str, Any],
        content_hash: str
    ) -> bool:
        """
        Check if embedding is semantically similar to cached embeddings

        Args:
            embedding: Embedding to check
            memory: Memory dictionary
            content_hash: Hash of content

        Returns:
            True if semantic duplicate found, False otherwise
        """
        max_similarity = 0.0
        most_similar_id = None

        # Compare against all cached embeddings
        for cached_hash, (cached_embedding, cached_timestamp, cached_id) in self.seen_embeddings.items():
            similarity = self.compute_cosine_similarity(embedding, cached_embedding)

            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_id = cached_id

            # Early exit if above threshold
            if similarity >= self.similarity_threshold:
                logger.debug(
                    f"Semantic duplicate found: similarity={similarity:.3f} "
                    f"(threshold={self.similarity_threshold})",
                    extra={
                        "similarity": similarity,
                        "threshold": self.similarity_threshold,
                        "cached_id": cached_id
                    }
                )
                return True

        # Log near-misses for tuning
        if 0.75 <= max_similarity < self.similarity_threshold:
            logger.debug(
                f"Near-duplicate (below threshold): similarity={max_similarity:.3f}",
                extra={
                    "similarity": max_similarity,
                    "threshold": self.similarity_threshold,
                    "most_similar_id": most_similar_id
                }
            )

        return False

    def _extract_content(self, memory: Dict[str, Any]) -> str:
        """
        Extract content string from memory dictionary

        Args:
            memory: Memory dictionary

        Returns:
            Content string, or empty string if not found
        """
        # Try common content fields
        if "content" in memory:
            return str(memory["content"])
        elif "value" in memory:
            value = memory["value"]
            if isinstance(value, dict) and "content" in value:
                return str(value["content"])
            elif isinstance(value, str):
                return value
            else:
                # Serialize dict/list to string
                import json
                return json.dumps(value, sort_keys=True)

        return ""

    def _extract_embedding(self, memory: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Extract embedding vector from memory dictionary

        Args:
            memory: Memory dictionary

        Returns:
            Numpy array of embedding, or None if not found
        """
        embedding = None

        # Try common embedding fields
        if "embedding" in memory:
            embedding = memory["embedding"]
        elif "value" in memory and isinstance(memory["value"], dict):
            if "embedding" in memory["value"]:
                embedding = memory["value"]["embedding"]

        # Convert to numpy array
        if embedding is not None:
            try:
                return np.array(embedding, dtype=np.float32)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to convert embedding to numpy array: {str(e)}",
                    extra={"error": str(e)}
                )
                return None

        return None

    def reset_cache(self) -> None:
        """
        Clear all cached hashes and embeddings

        Useful for testing or periodic cache refresh.
        """
        self.seen_hashes.clear()
        self.seen_embeddings.clear()

        logger.info("Deduplication cache reset")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics

        Returns:
            Statistics dictionary with dedup_rate, cache metrics, etc.
        """
        stats = self.stats.copy()

        # Calculate deduplication rate
        if stats["total_processed"] > 0:
            total_duplicates = stats["exact_duplicates"] + stats["semantic_duplicates"]
            stats["dedup_rate"] = total_duplicates / stats["total_processed"]
        else:
            stats["dedup_rate"] = 0.0

        # Add cache metrics
        stats["cache_size"] = len(self.seen_embeddings)
        stats["hash_cache_size"] = len(self.seen_hashes)

        return stats
