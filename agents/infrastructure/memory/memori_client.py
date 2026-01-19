"""
Memori Client Adapter
=====================

Implements a lightweight adapter for the open-source Memori project
(https://github.com/GibsonAI/Memori) so Genesis can run a SQL-native
memory backend without deploying an external service.

The adapter intentionally keeps the surface area narrow:

- General purpose key/value storage via the ``memories`` table
- Specialized tables for trajectories, cases, and A2A audit logs
- Thread-safe upserts with WAL journaling for concurrent agents
- Optional asyncio helpers for callers that rely on async/await

The real Memori engine runs as a network service backed by Postgres.
For local development and CI we emulate the public API with sqlite.
Swapping to a remote Memori deployment only requires pointing the
``MEMORI_DB_PATH`` environment variable at a ``postgresql://`` DSN
once the upstream project ships official Python bindings.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DEFAULT_DB_PATH = Path("data/memori/genesis_memori.db")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def _deserialize(payload: Optional[str]) -> Any:
    if payload is None:
        return None
    return json.loads(payload)


@dataclass
class MemoryRecord:
    namespace: str
    subject: Optional[str]
    key: str
    value: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    ttl_seconds: Optional[int]
    expires_at: Optional[datetime]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data


class MemoriClient:
    """
    SQLite-backed drop-in replacement for Memori.

    The adapter trades some of Memori's distributed features for a
    zero-dependency footprint that works inside the Codex sandbox.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        resolved = Path(db_path or os.getenv("MEMORI_DB_PATH", DEFAULT_DB_PATH))
        resolved.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(resolved, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._lock = threading.RLock()
        self._init_schema()

    # ------------------------------------------------------------------
    # schema
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        with self._conn:  # auto commit
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL,
                    subject TEXT,
                    record_key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    ttl_seconds INTEGER,
                    expires_at TEXT,
                    UNIQUE(namespace, subject, record_key)
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_namespace ON memories(namespace)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_expiry ON memories(expires_at)"
            )

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trajectories (
                    trajectory_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    generation INTEGER,
                    status TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reward REAL NOT NULL,
                    metadata_json TEXT,
                    embedding_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS a2a_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    agent_name TEXT,
                    tool_name TEXT,
                    status TEXT,
                    payload_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    # ------------------------------------------------------------------
    # utility helpers
    # ------------------------------------------------------------------
    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # memory primitives -------------------------------------------------
    def upsert_memory(
        self,
        namespace: str,
        subject: Optional[str],
        key: str,
        value: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> MemoryRecord:
        now = _now()
        expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        metadata = metadata or {}

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO memories (
                    namespace, subject, record_key, value_json, metadata_json,
                    created_at, updated_at, ttl_seconds, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, subject, record_key) DO UPDATE SET
                    value_json=excluded.value_json,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at,
                    ttl_seconds=excluded.ttl_seconds,
                    expires_at=excluded.expires_at
                """,
                (
                    namespace,
                    subject,
                    key,
                    _serialize(value),
                    _serialize(metadata),
                    now.isoformat(),
                    now.isoformat(),
                    ttl_seconds,
                    expires_at.isoformat() if expires_at else None,
                ),
            )

        return MemoryRecord(
            namespace=namespace,
            subject=subject,
            key=key,
            value=value,
            metadata=metadata,
            created_at=now,
            updated_at=now,
            ttl_seconds=ttl_seconds,
            expires_at=expires_at,
        )

    def get_memory(
        self,
        namespace: str,
        subject: Optional[str],
        key: str,
    ) -> Optional[MemoryRecord]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT value_json, metadata_json, created_at, updated_at, ttl_seconds, expires_at
                FROM memories
                WHERE namespace=? AND subject IS ?
                  AND record_key=?
                """,
                (namespace, subject, key),
            ).fetchone()

        if not row:
            return None

        expires_at = row[5]
        if expires_at and datetime.fromisoformat(expires_at) < _now():
            self.delete_memory(namespace, subject, key)
            return None

        return MemoryRecord(
            namespace=namespace,
            subject=subject,
            key=key,
            value=_deserialize(row[0]),
            metadata=_deserialize(row[1]) or {},
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            ttl_seconds=row[4],
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
        )

    def delete_memory(self, namespace: str, subject: Optional[str], key: str) -> bool:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM memories WHERE namespace=? AND subject IS ? AND record_key=?",
                (namespace, subject, key),
            )
        return cursor.rowcount > 0

    def search_memories(
        self,
        namespace: str,
        subject: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[MemoryRecord]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT record_key, value_json, metadata_json,
                       created_at, updated_at, ttl_seconds, expires_at, subject
                FROM memories
                WHERE namespace=? AND (? IS NULL OR subject=?)
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (namespace, subject, subject, limit * 2),  # over-fetch for filter
            ).fetchall()

        records: List[MemoryRecord] = []
        for row in rows:
            record = MemoryRecord(
                namespace=namespace,
                subject=row[7],
                key=row[0],
                value=_deserialize(row[1]),
                metadata=_deserialize(row[2]) or {},
                created_at=datetime.fromisoformat(row[3]),
                updated_at=datetime.fromisoformat(row[4]),
                ttl_seconds=row[5],
                expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
            )

            if record.expires_at and record.expires_at < _now():
                continue

            if self._matches_filters(record, filters):
                records.append(record)

            if len(records) >= limit:
                break

        return records

    def _matches_filters(
        self,
        record: MemoryRecord,
        filters: Optional[Dict[str, Any]],
    ) -> bool:
        if not filters:
            return True

        for key, expected in filters.items():
            if key.startswith("value."):
                actual = self._lookup_nested(record.value, key[6:])
            elif key.startswith("metadata."):
                actual = self._lookup_nested(record.metadata, key[9:])
            else:
                actual = None

            if isinstance(expected, dict) and "$contains" in expected:
                if not isinstance(actual, str) or expected["$contains"] not in actual:
                    return False
            elif actual != expected:
                return False
        return True

    def _lookup_nested(self, data: Any, dotted: str) -> Any:
        current = data
        for part in dotted.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    # specialized tables ------------------------------------------------
    def upsert_trajectory(self, trajectory_id: str, agent_name: str, payload: Dict[str, Any]) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO trajectories (trajectory_id, agent_name, generation, status, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(trajectory_id) DO UPDATE SET
                    agent_name=excluded.agent_name,
                    generation=excluded.generation,
                    status=excluded.status,
                    payload_json=excluded.payload_json
                """,
                (
                    trajectory_id,
                    agent_name,
                    payload.get("generation"),
                    payload.get("status"),
                    _serialize(payload),
                    _now().isoformat(),
                ),
            )

    def list_recent_trajectories(self, agent_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT payload_json FROM trajectories
                WHERE agent_name=?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (agent_name, limit),
            ).fetchall()
        return [_deserialize(row[0]) for row in rows]

    def upsert_case(self, case_payload: Dict[str, Any]) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO cases (case_id, state, action, reward, metadata_json, embedding_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    state=excluded.state,
                    action=excluded.action,
                    reward=excluded.reward,
                    metadata_json=excluded.metadata_json,
                    embedding_json=excluded.embedding_json
                """,
                (
                    case_payload["case_id"],
                    case_payload["state"],
                    case_payload["action"],
                    case_payload["reward"],
                    _serialize(case_payload.get("metadata", {})),
                    _serialize(case_payload.get("embedding")),
                    case_payload["metadata"].get("timestamp", _now().isoformat()),
                ),
            )

    def fetch_cases(self, limit: int = 500) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT state, action, reward, metadata_json, embedding_json, case_id FROM cases LIMIT ?",
                (limit,),
            ).fetchall()
        cases = []
        for row in rows:
            cases.append(
                {
                    "state": row[0],
                    "action": row[1],
                    "reward": row[2],
                    "metadata": _deserialize(row[3]) or {},
                    "embedding": _deserialize(row[4]),
                    "case_id": row[5],
                }
            )
        return cases

    def clear_cases(self, agent_filter: Optional[str] = None) -> int:
        with self._lock, self._conn:
            if agent_filter is None:
                cursor = self._conn.execute("DELETE FROM cases")
                return cursor.rowcount

            rows = self._conn.execute("SELECT case_id, metadata_json FROM cases").fetchall()
            targets = []
            for case_id, metadata_json in rows:
                metadata = _deserialize(metadata_json) or {}
                if metadata.get("agent") == agent_filter:
                    targets.append(case_id)

            if not targets:
                return 0

            cursor = self._conn.executemany(
                "DELETE FROM cases WHERE case_id=?",
                [(case_id,) for case_id in targets],
            )
            return cursor.rowcount

    def log_a2a_event(
        self,
        task_id: str,
        agent_name: str,
        tool_name: str,
        status: str,
        payload: Dict[str, Any],
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO a2a_events (task_id, agent_name, tool_name, status, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (task_id, agent_name, tool_name, status, _serialize(payload), _now().isoformat()),
            )

    def clear_namespace(self, namespace: str, subject: Optional[str] = None) -> int:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM memories WHERE namespace=? AND (? IS NULL OR subject=?)",
                (namespace, subject, subject),
            )
        return cursor.rowcount

    def list_namespaces(self) -> List[Tuple[str, Optional[str]]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT namespace, subject FROM memories"
            ).fetchall()
        return [(row[0], row[1]) for row in rows]

    # asyncio wrappers --------------------------------------------------
    async def aput(self, *args, **kwargs) -> MemoryRecord:
        return await asyncio.to_thread(self.upsert_memory, *args, **kwargs)

    async def aget(self, *args, **kwargs) -> Optional[MemoryRecord]:
        return await asyncio.to_thread(self.get_memory, *args, **kwargs)

    async def adelete(self, *args, **kwargs) -> bool:
        return await asyncio.to_thread(self.delete_memory, *args, **kwargs)

    async def asearch(self, *args, **kwargs) -> List[MemoryRecord]:
        return await asyncio.to_thread(self.search_memories, *args, **kwargs)

    async def alog_event(self, *args, **kwargs) -> None:
        await asyncio.to_thread(self.log_a2a_event, *args, **kwargs)

    async def aupsert_case(self, payload: Dict[str, Any]) -> None:
        await asyncio.to_thread(self.upsert_case, payload)

    async def aupsert_trajectory(self, *args, **kwargs) -> None:
        await asyncio.to_thread(self.upsert_trajectory, *args, **kwargs)

    async def alist_trajectories(self, *args, **kwargs) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.list_recent_trajectories, *args, **kwargs)

    async def aclear_namespace(self, namespace: str, subject: Optional[str]) -> int:
        return await asyncio.to_thread(self.clear_namespace, namespace, subject)

    async def alist_namespaces(self) -> List[Tuple[str, Optional[str]]]:
        return await asyncio.to_thread(self.list_namespaces)

    async def aclear_cases(self, agent_filter: Optional[str] = None) -> int:
        return await asyncio.to_thread(self.clear_cases, agent_filter)


__all__ = ["MemoriClient", "MemoryRecord"]
