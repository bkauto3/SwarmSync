"""
Hybrid Memory Store (Memori + Vector Sidecar + Knowledge Graph Overlay)
======================================================================

This module augments the Memori SQL store with:

- A lightweight vector sidecar for semantic search (no external dependencies)
- Deterministic hash-based embeddings (optionally replaceable with TEI)
- A knowledge-graph style overlay for entity relationships and attribute lookups

The implementation intentionally avoids heavyweight services so that it can be
executed in CI and local developer environments without Postgres or pgvector.
The design mirrors the hybrid recommendation from the Genesis memory whitepaper:
structured SQL storage backed by semantic search and relationship reasoning.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from infrastructure.memory.memori_client import MemoriClient, MemoryRecord


class HybridMemoryStore:
    """Combines Memori storage with vector search and entity relationship indexing."""

    DEFAULT_VECTOR_DB = Path("data/memori/hybrid_vectors.db")

    def __init__(
        self,
        *,
        memori_client: Optional[MemoriClient] = None,
        vector_db_path: Optional[Path | str] = None,
        embedding_dim: int = 32,
        use_async: bool = False,
    ) -> None:
        self.memori = memori_client or MemoriClient()
        self.embedding_dim = embedding_dim
        self.use_async = use_async  # reserved for future async hooks
        self._lock = threading.RLock()

        self._vector_path = Path(vector_db_path or self.DEFAULT_VECTOR_DB)
        self._vector_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._vector_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

        # In-memory knowledge graph overlay: entity_type -> entity_id -> attr -> set(values)
        self._entity_relations: Dict[str, Dict[str, Dict[str, set[str]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(set))
        )
        # Map entity back to Memori coordinates
        self._entity_index: Dict[Tuple[str, str], Tuple[str, Optional[str], str]] = {}
        self._load_entities_into_memory()

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def upsert_memory(
        self,
        *,
        namespace: str,
        subject: Optional[str],
        key: str,
        value: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecord:
        """
        Store a record in Memori, mirror it to the vector sidecar, and update entity graph.

        Args:
            namespace: Memori namespace (e.g., "user", "session")
            subject: Optional subject (user ID, session ID, etc.)
            key: Record key
            value: Memory payload (dict)
            metadata: Optional metadata dict
        """
        meta = metadata.copy() if metadata else {}
        record = self.memori.upsert_memory(
            namespace=namespace,
            subject=subject,
            key=key,
            value=value,
            metadata=meta,
            ttl_seconds=meta.get("ttl_seconds"),
        )

        self._upsert_embedding(namespace, subject, key, value, meta)
        entity_info = meta.get("entity")
        if entity_info:
            self._index_entity(namespace, subject, key, entity_info)

        return record

    def search_semantic(
        self,
        *,
        namespace: str,
        subject: Optional[str],
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Perform cosine-similarity search over the vector sidecar and return Memori records.
        """
        if not query:
            return []

        query_vec = self._embed_text(query)
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                SELECT embedding, norm, record_key
                FROM embeddings
                WHERE namespace = ? AND subject = ?
                """,
                (namespace, self._normalize_subject(subject)),
            )
            candidates = cursor.fetchall()

        scored: List[Tuple[str, float]] = []
        for row in candidates:
            embedding = np.frombuffer(row["embedding"], dtype=np.float32)
            denom = row["norm"] * np.linalg.norm(query_vec)
            if not denom:
                score = 0.0
            else:
                score = float(np.dot(query_vec, embedding) / denom)
            if score >= min_score:
                scored.append((row["record_key"], score))

        scored.sort(key=lambda item: item[1], reverse=True)
        top = scored[:limit]

        results: List[Dict[str, Any]] = []
        for record_key, score in top:
            record = self.memori.get_memory(namespace, subject, record_key)
            if record:
                doc = record.to_dict()
                doc.setdefault("metadata", {})["semantic_score"] = score
                results.append(doc)
        return results

    def query_entities(
        self,
        *,
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query the entity overlay using structured filters.

        Example:
            query_entities(entity_type="trip", filters={"user": "user_123", "city": "Paris"})
        """
        filters = filters or {}
        matches: List[Dict[str, Any]] = []

        with self._lock:
            bucket = self._entity_relations.get(entity_type, {})
            for entity_id, attributes in bucket.items():
                if self._entity_matches(attributes, filters):
                    namespace, subject, record_key = self._entity_index.get(
                        (entity_type, entity_id), (None, None, None)
                    )
                    if namespace is None or record_key is None:
                        continue
                    record = self.memori.get_memory(namespace, subject, record_key)
                    if record:
                        matches.append(record.to_dict())
        return matches

    # ------------------------------------------------------------------ #
    # vector sidecar helpers
    # ------------------------------------------------------------------ #
    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    namespace TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    record_key TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    norm REAL NOT NULL,
                    metadata_json TEXT,
                    PRIMARY KEY (namespace, subject, record_key)
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entities (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    record_key TEXT NOT NULL,
                    attributes_json TEXT NOT NULL,
                    PRIMARY KEY (entity_type, entity_id)
                )
                """
            )

    def _upsert_embedding(
        self,
        namespace: str,
        subject: Optional[str],
        key: str,
        value: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> None:
        text_to_embed = self._stringify_value(value)
        embedding = self._embed_text(text_to_embed)
        norm = float(np.linalg.norm(embedding))
        blob = embedding.astype(np.float32).tobytes()

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO embeddings (namespace, subject, record_key, embedding, norm, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    namespace,
                    self._normalize_subject(subject),
                    key,
                    blob,
                    norm,
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )

    # ------------------------------------------------------------------ #
    # entity overlay
    # ------------------------------------------------------------------ #
    def _index_entity(
        self,
        namespace: str,
        subject: Optional[str],
        key: str,
        entity_info: Dict[str, Any],
    ) -> None:
        entity_type = entity_info.get("type")
        if not entity_type:
            return

        entity_id = str(entity_info.get("id") or key)
        attributes = entity_info.get("attributes", {})

        normalized_subject = self._normalize_subject(subject)
        attributes_json = json.dumps(attributes, ensure_ascii=False)

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO entities (entity_type, entity_id, namespace, subject, record_key, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entity_type,
                    entity_id,
                    namespace,
                    normalized_subject,
                    key,
                    attributes_json,
                ),
            )
            self._update_entity_cache(
                entity_type=entity_type,
                entity_id=entity_id,
                namespace=namespace,
                subject=subject,
                key=key,
                attributes=attributes,
            )

    def _load_entities_into_memory(self) -> None:
        with self._lock, self._conn:
            cursor = self._conn.execute("SELECT * FROM entities")
            rows = cursor.fetchall()
        for row in rows:
            attributes = json.loads(row["attributes_json"])
            self._update_entity_cache(
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                namespace=row["namespace"],
                subject=self._denormalize_subject(row["subject"]),
                key=row["record_key"],
                attributes=attributes,
            )

    def _update_entity_cache(
        self,
        *,
        entity_type: str,
        entity_id: str,
        namespace: str,
        subject: Optional[str],
        key: str,
        attributes: Dict[str, Any],
    ) -> None:
        attr_bucket = self._entity_relations[entity_type][entity_id]
        for attr_name, attr_values in attributes.items():
            if isinstance(attr_values, (list, tuple, set)):
                values_iter: Iterable[Any] = attr_values
            else:
                values_iter = [attr_values]
            for value in values_iter:
                attr_bucket[attr_name].add(str(value))
        self._entity_index[(entity_type, entity_id)] = (namespace, subject, key)

    def _entity_matches(self, attributes: Dict[str, set[str]], filters: Dict[str, Any]) -> bool:
        for attr_name, expected in filters.items():
            expected_value = str(expected)
            if expected_value not in attributes.get(attr_name, set()):
                return False
        return True

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _embed_text(self, text: str) -> np.ndarray:
        """
        Deterministic hash-based embedding (fallback when TEI/LiteLLM unavailable).
        Produces a unit vector of length `embedding_dim`.
        """
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        repeats = (self.embedding_dim + len(digest) - 1) // len(digest)
        raw = (digest * repeats)[: self.embedding_dim]
        vector = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) / 255.0
        norm = np.linalg.norm(vector)
        if norm == 0.0:
            return vector
        return vector / norm

    @staticmethod
    def _stringify_value(value: Dict[str, Any]) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _normalize_subject(subject: Optional[str]) -> str:
        return subject or ""

    @staticmethod
    def _denormalize_subject(subject: Optional[str]) -> Optional[str]:
        return subject or None


__all__ = ["HybridMemoryStore"]

