"""
Session ⇢ Memori Bridge
=======================

Synchronises recent session events from :mod:`SessionStore` into Memori so that
agents can retrieve a compact summary of the latest conversation without
re-reading the full transcript.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from infrastructure.memory.memori_tool import MemoriMemoryToolset
from infrastructure.session_store import SessionStore

logger = logging.getLogger(__name__)


class SessionMemoriBridge:
    """
    Bridge that mirrors session summaries into Memori.

    Each session gets a single Memori record with key ``session::{session_id}``
    scoped per user. Metadata tracks the last sequence number mirrored so we
    can skip redundant writes.
    """

    def __init__(
        self,
        session_store: SessionStore,
        *,
        memori_toolset: Optional[MemoriMemoryToolset] = None,
        max_events: int = 20,
        ttl_hours: int = 720,
    ):
        self.session_store = session_store
        self.memori_toolset = memori_toolset or MemoriMemoryToolset(namespace="session_summary")
        self.max_events = max(5, max_events)
        self.ttl_hours = max(1, ttl_hours)

    # ------------------------------------------------------------------ #
    def sync_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Mirror the most recent events for ``session_id`` into Memori.

        Returns summary metadata if an update occurred, otherwise ``None``.
        """
        if not session_id:
            return None

        try:
            session = self.session_store.get_session(
                user_id=user_id,
                session_id=session_id,
            )
        except Exception as exc:
            logger.debug("SessionMemoriBridge failed to load session %s: %s", session_id, exc)
            return None

        events = session.get("events", [])
        if not events:
            return None

        tail = events[-self.max_events :]
        last_sequence = tail[-1]["sequence"]
        fact_key = f"session::{session_id}"

        existing = self.memori_toolset.retrieve_user_fact(user_id, fact_key)
        existing_meta = (existing or {}).get("metadata", {})
        if existing_meta.get("last_sequence", 0) >= last_sequence:
            return None  # Already up-to-date

        summary = self._summarize_events(tail)
        record = self.memori_toolset.store_user_fact(
            user_id=user_id,
            fact_key=fact_key,
            fact_value=summary,
            labels=["session_summary"],
            ttl_hours=self.ttl_hours,
            metadata={
                "session_id": session_id,
                "last_sequence": last_sequence,
                "source": "session_store",
            },
            scope="session",
            provenance="session_memori_bridge",
        )
        logger.debug("SessionMemoriBridge synced %s sequence %s", session_id, last_sequence)
        return {
            "session_id": session_id,
            "last_sequence": last_sequence,
            "memori_record": record,
        }

    # ------------------------------------------------------------------ #
    def _summarize_events(self, events: Any) -> str:
        """
        Create a deterministic summary string from recent events.
        """
        lines = []
        for event in events:
            content = (event.get("content") or "").strip().replace("\n", " ")
            if len(content) > 220:
                content = content[:217] + "..."
            lines.append(f"{event.get('sequence')}. {event.get('role')}: {content}")
        summary = "\n".join(lines)
        if len(summary) > 1600:
            summary = summary[:1597] + "..."
        return summary


__all__ = ["SessionMemoriBridge"]
