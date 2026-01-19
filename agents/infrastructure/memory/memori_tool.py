"""
Memori Memory Toolset
=====================

Provides a lightweight "memory-as-a-tool" interface on top of ``MemoriClient`` so
agents can store, retrieve, and search memories without dealing with SQL details.

Usage:
    from infrastructure.memory.memori_tool import MemoriMemoryToolset
    toolset = MemoriMemoryToolset()
    toolset.store_user_fact("user-123", "preference", "Window seat")
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from infrastructure.memory.memori_client import MemoriClient

logger = logging.getLogger(__name__)


class MemoriMemoryToolset:
    """
    High-level helper that exposes Memori operations as ergonomic tool methods.

    All methods return plain dictionaries so agents can feed responses directly
    back to users or other agents.
    """

    def __init__(
        self,
        client: Optional[MemoriClient] = None,
        namespace: str = "user",
    ):
        self.client = client or MemoriClient()
        self.namespace = namespace

    # ------------------------------------------------------------------ #
    # tool-style APIs
    # ------------------------------------------------------------------ #
    def store_user_fact(
        self,
        user_id: str,
        fact_key: str,
        fact_value: str,
        *,
        importance: str = "normal",
        labels: Optional[List[str]] = None,
        ttl_hours: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        scope: str = "user",
        provenance: str = "memori_toolset",
    ) -> Dict[str, Any]:
        """
        Persist a user-specific fact that the agent can recall later.
        """
        payload = {
            "content": fact_value,
            "importance": importance,
        }
        if labels:
            payload["labels"] = labels

        meta = metadata.copy() if metadata else {}
        if labels:
            meta.setdefault("labels", labels)
        meta.setdefault("scope", scope)
        meta.setdefault("provenance", provenance)
        meta.setdefault("namespace", self.namespace)

        ttl_seconds = int(ttl_hours * 3600) if ttl_hours else None
        record = self.client.upsert_memory(
            namespace=self.namespace,
            subject=user_id,
            key=fact_key,
            value=payload,
            metadata=meta,
            ttl_seconds=ttl_seconds,
        )
        result = record.to_dict()
        result["namespace"] = self.namespace
        logger.info(
            "Memori store_user_fact | user=%s key=%s importance=%s labels=%s ttl=%s",
            user_id,
            fact_key,
            importance,
            labels,
            ttl_hours,
        )
        return result

    def retrieve_user_fact(self, user_id: str, fact_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific fact for a user.
        """
        record = self.client.get_memory(
            namespace=self.namespace,
            subject=user_id,
            key=fact_key,
        )
        logger.info("Memori retrieve_user_fact | user=%s key=%s hit=%s", user_id, fact_key, bool(record))
        return record.to_dict() if record else None

    def search_user_facts(
        self,
        user_id: str,
        query: Optional[str] = None,
        *,
        label: Optional[str] = None,
        scope: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search memories for a user via substring match on the stored value or labels.
        """
        filters: Dict[str, Any] = {}
        if query:
            filters["value.content"] = {"$contains": query}
        if label:
            filters["metadata.labels"] = {"$contains": label}
        if scope:
            filters["metadata.scope"] = scope

        records = self.client.search_memories(
            namespace=self.namespace,
            subject=user_id,
            filters=filters or None,
            limit=limit,
        )
        logger.info(
            "Memori search_user_facts | user=%s query=%s label=%s returned=%s",
            user_id,
            query,
            label,
            len(records),
        )
        return [record.to_dict() for record in records]

    def clear_user_fact(self, user_id: str, fact_key: str) -> bool:
        """
        Delete a stored fact (used when the agent wants to forget outdated info).
        """
        deleted = self.client.delete_memory(self.namespace, user_id, fact_key)
        logger.info("Memori clear_user_fact | user=%s key=%s deleted=%s", user_id, fact_key, deleted)
        return deleted

    # ------------------------------------------------------------------ #
    # tool metadata helpers
    # ------------------------------------------------------------------ #
    def get_tool_spec(self) -> Dict[str, Any]:
        """
        Return an OpenAI-compatible tool specification describing the memory operations.

        Agents can introspect this schema to decide when to call each function.
        """
        return {
            "name": "memori_memory_toolset",
            "description": (
                "Interact with the Memori SQL memory store. "
                "Supports storing scoped memories, retrieving precise facts, "
                "and searching recent context without leaking data across scopes."
            ),
            "functions": [
                {
                    "name": "store_user_fact",
                    "description": (
                        "Store a scoped fact for a user, session, or application with provenance metadata."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "description": "Logical owner of the memory."},
                            "fact_key": {"type": "string", "description": "Stable identifier for the fact."},
                            "fact_value": {"type": "string", "description": "Natural language content to persist."},
                            "importance": {
                                "type": "string",
                                "enum": ["low", "normal", "high"],
                                "default": "normal",
                                "description": "Retention priority hint.",
                            },
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional topic tags used for search filters.",
                            },
                            "ttl_hours": {
                                "type": "number",
                                "description": "Optional time to live in hours before expiry.",
                            },
                            "scope": {
                                "type": "string",
                                "enum": ["user", "session", "app"],
                                "default": "user",
                                "description": "Visibility boundary for the memory.",
                            },
                            "provenance": {
                                "type": "string",
                                "default": "memori_toolset",
                                "description": "Source identifier recorded in metadata.",
                            },
                            "metadata": {
                                "type": "object",
                                "additionalProperties": True,
                                "description": "Additional metadata merged into the record.",
                            },
                        },
                        "required": ["user_id", "fact_key", "fact_value"],
                    },
                },
                {
                    "name": "retrieve_user_fact",
                    "description": "Fetch a single fact for a user by key.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "fact_key": {"type": "string"},
                        },
                        "required": ["user_id", "fact_key"],
                    },
                },
                {
                    "name": "search_user_facts",
                    "description": "Search memories using keywords, labels, or scope filters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "query": {"type": "string"},
                            "label": {"type": "string"},
                            "scope": {
                                "type": "string",
                                "enum": ["user", "session", "app"],
                                "description": "Restrict results to a specific scope.",
                            },
                            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
                        },
                        "required": ["user_id"],
                    },
                },
                {
                    "name": "clear_user_fact",
                    "description": "Delete a stored fact when it is no longer valid.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "fact_key": {"type": "string"},
                        },
                        "required": ["user_id", "fact_key"],
                    },
                },
            ],
        }


__all__ = ["MemoriMemoryToolset"]
