"""
Genesis SQL Memory Backend (Memori Integration)
==============================================

Provides an async-compatible wrapper around :mod:`MemoriClient` so
existing LangGraph integrations can switch from MongoDB to the SQL
Memori engine via ``GENESIS_MEMORY_BACKEND=memori``.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from infrastructure.memory.memori_client import MemoriClient, MemoryRecord


def _namespace_to_key(namespace: Sequence[str]) -> Tuple[str, Optional[str]]:
    """
    Convert a LangGraph namespace tuple into the ``namespace`` + ``subject``
    columns used by Memori.
    """
    if not namespace:
        raise ValueError("Namespace must be non-empty")
    namespace_type = namespace[0]
    subject = "/".join(namespace[1:]) if len(namespace) > 1 else None
    return namespace_type, subject


class GenesisSQLMemoryBackend:
    """
    Async façade over :class:`MemoriClient`.

    Existing LangGraph code expects coroutine-style methods while
    MemoriClient runs synchronously on sqlite.  The backend forwards
    calls via ``asyncio.to_thread`` so we stay non-blocking without
    duplicating logic.
    """

    def __init__(self, client: Optional[MemoriClient] = None) -> None:
        self.client = client or MemoriClient()

    # ------------------------------------------------------------------
    async def put(
        self,
        namespace: Sequence[str],
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> Dict[str, Any]:
        ns, subject = _namespace_to_key(namespace)
        record = await self.client.aput(ns, subject, key, value, metadata, ttl)
        return record.to_dict()

    async def get(self, namespace: Sequence[str], key: str) -> Optional[Dict[str, Any]]:
        ns, subject = _namespace_to_key(namespace)
        record = await self.client.aget(ns, subject, key)
        return record.to_dict() if record else None

    async def delete(self, namespace: Sequence[str], key: str) -> bool:
        ns, subject = _namespace_to_key(namespace)
        return await self.client.adelete(ns, subject, key)

    async def search(
        self,
        namespace: Sequence[str],
        query: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        ns, subject = _namespace_to_key(namespace)
        records = await self.client.asearch(ns, subject, query, limit)
        return [record.to_dict() for record in records]

    async def stream_namespace(
        self,
        namespace: Sequence[str],
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Alias for search with only namespace constraint."""
        return await self.search(namespace, None, limit)

    async def health_check(self) -> Dict[str, Any]:
        records = await self.search(("agent",), limit=1)
        return {
            "status": "healthy",
            "backend": "memori",
            "sample_records": len(records),
        }

    async def close(self) -> None:
        await asyncio.to_thread(self.client.close)

    # ------------------------------------------------------------------
    # helper APIs consumed by other components
    # ------------------------------------------------------------------
    async def record_trajectory(self, payload: Dict[str, Any]) -> None:
        await self.client.aupsert_trajectory(
            payload.get("trajectory_id"),
            payload.get("agent_name"),
            payload,
        )

    async def recent_trajectories(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        return await self.client.alist_trajectories(agent_name, limit)

    async def store_case(self, case_payload: Dict[str, Any]) -> None:
        await self.client.aupsert_case(case_payload)

    async def fetch_cases(self, limit: int = 500) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.client.fetch_cases, limit)

    async def clear_namespace(self, namespace: Sequence[str]) -> int:
        ns, subject = _namespace_to_key(namespace)
        return await self.client.aclear_namespace(ns, subject)

    async def list_namespaces(self) -> List[Tuple[str, ...]]:
        raw = await self.client.alist_namespaces()
        namespaces: List[Tuple[str, ...]] = []
        for ns, subject in raw:
            parts = [ns]
            if subject:
                parts.extend(subject.split("/"))
            namespaces.append(tuple(parts))
        return sorted(namespaces)


def memori_enabled() -> bool:
    return os.getenv("GENESIS_MEMORY_BACKEND", "mongo").lower() == "memori"


__all__ = ["GenesisSQLMemoryBackend", "memori_enabled"]
