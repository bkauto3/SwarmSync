"""
LangMem TTL (Time-To-Live) Memory Expiration

Automatic expiration of old memories with configurable TTL per memory type.
Integrates with LangGraph Store API and Genesis Memory Store.

Features:
- Configurable TTL per memory type (short/medium/long/permanent)
- Background cleanup task with configurable intervals
- OTEL observability for cleanup operations
- Graceful handling of expired memories during retrieval
- Batch deletion for efficiency

Architecture:
- Stores timestamp metadata with each memory entry
- Periodic background task scans for expired entries
- Cleanup operations tracked with metrics (deleted_count, cleanup_duration)
- Type-safe interfaces with comprehensive error handling

Week 1 Target: Automatic expiration working, zero manual cleanup needed
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from infrastructure.logging_config import get_logger
from infrastructure.observability import get_observability_manager

logger = get_logger(__name__)
obs_manager = get_observability_manager()


class LangMemTTL:
    """
    Time-To-Live memory expiration for Genesis Memory Store

    Provides automatic expiration of old memories with configurable TTL
    per memory type. Runs background cleanup task and integrates with
    OTEL observability.

    Memory Types and Default TTLs:
    - short_term: 24 hours (temporary working data)
    - medium_term: 168 hours / 7 days (recent context)
    - long_term: 8760 hours / 365 days (historical data)
    - permanent: Never expires (core knowledge)

    Usage:
        ```python
        # Initialize with memory store backend
        ttl = LangMemTTL(memory_backend, default_ttl_hours=168)

        # Start background cleanup (runs every 1 hour)
        await ttl.start_background_cleanup(interval_seconds=3600)

        # Manual cleanup
        stats = await ttl.cleanup_expired()
        print(f"Deleted {stats['deleted_count']} expired memories")

        # Stop background task
        await ttl.stop_background_cleanup()
        ```
    """

    def __init__(
        self,
        backend: Any,
        default_ttl_hours: int = 168,
        cleanup_batch_size: int = 100
    ):
        """
        Initialize TTL manager

        Args:
            backend: Memory backend (InMemoryBackend or MongoDB adapter)
            default_ttl_hours: Default TTL for unspecified memory types
            cleanup_batch_size: Number of entries to delete per batch
        """
        self.backend = backend
        self.default_ttl_hours = default_ttl_hours
        self.cleanup_batch_size = cleanup_batch_size

        # TTL configuration per memory type (in hours)
        self.ttl_config: Dict[str, Optional[int]] = {
            "short_term": 24,        # 1 day
            "medium_term": 168,      # 1 week (7 days)
            "long_term": 8760,       # 1 year (365 days)
            "permanent": None,       # Never expire
            "agent": 720,            # 30 days for agent-specific
            "business": 4320,        # 180 days for business-level
            "system": None,          # Never expire system-wide knowledge
        }

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics tracking
        self.stats = {
            "total_cleanups": 0,
            "total_deleted": 0,
            "last_cleanup": None,
            "last_cleanup_duration": 0.0
        }

        logger.info(
            f"LangMemTTL initialized with default_ttl={default_ttl_hours}h",
            extra={
                "default_ttl_hours": default_ttl_hours,
                "ttl_config": self.ttl_config
            }
        )

    def get_ttl_for_namespace(self, namespace: Tuple[str, str]) -> Optional[int]:
        """
        Get TTL (in hours) for a namespace

        Args:
            namespace: (namespace_type, namespace_id) tuple

        Returns:
            TTL in hours, or None if permanent
        """
        namespace_type = namespace[0]

        # Check if namespace type has configured TTL
        if namespace_type in self.ttl_config:
            return self.ttl_config[namespace_type]

        # Default TTL
        return self.default_ttl_hours

    def is_expired(
        self,
        created_at: str,
        namespace: Tuple[str, str],
        now: Optional[datetime] = None
    ) -> bool:
        """
        Check if a memory entry is expired

        Args:
            created_at: ISO format timestamp
            namespace: (namespace_type, namespace_id) tuple
            now: Current time (default: utcnow)

        Returns:
            True if expired, False otherwise
        """
        ttl_hours = self.get_ttl_for_namespace(namespace)

        # Permanent memories never expire
        if ttl_hours is None:
            return False

        # Parse creation timestamp
        try:
            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            logger.warning(
                f"Invalid timestamp format: {created_at}, treating as not expired",
                extra={"created_at": created_at, "error": str(e)}
            )
            return False

        # Calculate expiration
        now = now or datetime.now(timezone.utc)
        expiration_time = created_time + timedelta(hours=ttl_hours)

        return now >= expiration_time

    async def cleanup_expired(
        self,
        namespace_filter: Optional[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Remove expired memories from storage

        Args:
            namespace_filter: Optional namespace to limit cleanup

        Returns:
            Statistics dict with deleted_count, duration, namespaces_scanned
        """
        start_time = datetime.now(timezone.utc)
        deleted_count = 0
        namespaces_scanned = 0

        # Start OTEL span (try-except for backwards compatibility)
        try:
            span_ctx = obs_manager.span("langmem_ttl_cleanup", obs_manager.SpanType.MEMORY if hasattr(obs_manager, 'SpanType') else None)
            span = span_ctx.__enter__()
        except (AttributeError, TypeError):
            from infrastructure.observability import _NullSpan
            span = _NullSpan()
            span_ctx = None

        span.set_attribute("namespace_filter", str(namespace_filter))

        try:
            # Get all namespaces to scan
            if namespace_filter:
                namespaces_to_scan = [namespace_filter]
            else:
                # Scan all namespaces (from backend storage)
                namespaces_to_scan = await self._get_all_namespaces()

            now = datetime.now(timezone.utc)

            # Process each namespace
            for namespace in namespaces_to_scan:
                namespaces_scanned += 1

                # Get TTL for this namespace
                ttl_hours = self.get_ttl_for_namespace(namespace)

                # Skip permanent namespaces
                if ttl_hours is None:
                    logger.debug(
                        f"Skipping permanent namespace: {namespace}",
                        extra={"namespace": namespace}
                    )
                    continue

                # Calculate cutoff time
                cutoff = now - timedelta(hours=ttl_hours)

                # Get all keys in namespace
                keys = await self.backend.list_keys(namespace)

                # Check each entry for expiration
                expired_keys = []
                for key in keys:
                    entry = await self.backend.get(namespace, key)
                    if entry and entry.metadata.created_at:
                        if self.is_expired(entry.metadata.created_at, namespace, now):
                            expired_keys.append(key)

                # Batch delete expired entries
                for i in range(0, len(expired_keys), self.cleanup_batch_size):
                    batch = expired_keys[i:i + self.cleanup_batch_size]
                    for key in batch:
                        await self.backend.delete(namespace, key)
                        deleted_count += 1

                    logger.debug(
                        f"Deleted {len(batch)} expired entries from {namespace}",
                        extra={
                            "namespace": namespace,
                            "batch_size": len(batch),
                            "total_deleted": deleted_count
                        }
                    )

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # Update statistics
            self.stats["total_cleanups"] += 1
            self.stats["total_deleted"] += deleted_count
            self.stats["last_cleanup"] = end_time.isoformat()
            self.stats["last_cleanup_duration"] = duration

            # Add OTEL metrics
            span.set_attribute("deleted_count", deleted_count)
            span.set_attribute("namespaces_scanned", namespaces_scanned)
            span.set_attribute("duration_seconds", duration)

            logger.info(
                f"TTL cleanup complete: deleted {deleted_count} entries from {namespaces_scanned} namespaces in {duration:.2f}s",
                extra={
                    "deleted_count": deleted_count,
                    "namespaces_scanned": namespaces_scanned,
                    "duration": duration
                }
            )

            return {
                "deleted_count": deleted_count,
                "namespaces_scanned": namespaces_scanned,
                "duration": duration,
                "timestamp": end_time.isoformat()
            }

        except Exception as e:
            logger.error(
                f"TTL cleanup failed: {str(e)}",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            span.set_attribute("error", str(e))
            raise

    async def _get_all_namespaces(self) -> List[Tuple[str, str]]:
        """
        Get all namespaces from backend storage

        Returns:
            List of (namespace_type, namespace_id) tuples
        """
        # For InMemoryBackend, access internal storage
        if hasattr(self.backend, '_storage'):
            return list(self.backend._storage.keys())

        # For MongoDBBackend, query all collections for distinct namespaces
        if hasattr(self.backend, 'db'):
            namespaces = set()
            # Query all 4 collections
            collections = [
                'persona_libraries',    # agent namespace
                'consensus_memory',     # business namespace
                'whiteboard_methods',   # system namespace
                'evolution_archive'     # short_term namespace
            ]
            for collection_name in collections:
                collection = self.backend.db[collection_name]
                # Find all documents and extract unique namespaces
                # MongoDB's distinct() flattens arrays, so we need to query documents directly
                for doc in collection.find({}, {'namespace': 1}):
                    ns = doc.get('namespace')
                    if isinstance(ns, list) and len(ns) == 2:
                        namespaces.add(tuple(ns))
            return list(namespaces)

        # For other backends, would need backend-specific implementation
        logger.warning("_get_all_namespaces not fully implemented for this backend")
        return []

    async def start_background_cleanup(
        self,
        interval_seconds: int = 3600
    ) -> None:
        """
        Start background cleanup task

        Runs periodic cleanup at specified interval. Safe to call multiple times.

        Args:
            interval_seconds: Seconds between cleanup runs (default: 1 hour)
        """
        if self._running:
            logger.warning("Background cleanup already running")
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(
            self._cleanup_loop(interval_seconds)
        )

        logger.info(
            f"Background TTL cleanup started (interval={interval_seconds}s)",
            extra={"interval_seconds": interval_seconds}
        )

    async def stop_background_cleanup(self) -> None:
        """
        Stop background cleanup task

        Gracefully cancels the cleanup task and waits for completion.
        """
        if not self._running:
            logger.warning("Background cleanup not running")
            return

        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Background TTL cleanup stopped")

    async def _cleanup_loop(self, interval_seconds: int) -> None:
        """
        Internal cleanup loop

        Args:
            interval_seconds: Seconds between cleanup runs
        """
        while self._running:
            try:
                # Run cleanup
                await self.cleanup_expired()

                # Wait for next interval
                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Cleanup loop error: {str(e)}",
                    extra={"error": str(e), "error_type": type(e).__name__}
                )
                # Continue running despite errors
                await asyncio.sleep(interval_seconds)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get TTL cleanup statistics

        Returns:
            Statistics dictionary
        """
        return self.stats.copy()
