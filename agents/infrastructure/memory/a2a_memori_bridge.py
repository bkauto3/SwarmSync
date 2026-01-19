"""
A2A ↔︎ Memori Bridge
====================

Persists A2A execution telemetry into the Memori SQL backend so agent
to agent interactions become queryable from LangGraph / MemoryRouter.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Optional

from infrastructure.memory.genesis_sql_memory import memori_enabled
from infrastructure.memory.memori_client import MemoriClient


class A2AMemoryBridge:
    """
    Minimal bridge that records every tool invocation and response.
    """

    def __init__(self, client: Optional[MemoriClient] = None) -> None:
        if not memori_enabled():
            raise RuntimeError("A2AMemoryBridge requires GENESIS_MEMORY_BACKEND=memori")
        self.client = client or MemoriClient()

    async def record_execution(
        self,
        task_id: str,
        agent_name: str,
        tool_name: str,
        status: str,
        payload: Dict[str, Any],
    ) -> None:
        await self.client.alog_event(task_id, agent_name, tool_name, status, payload)


def build_bridge_if_enabled() -> Optional[A2AMemoryBridge]:
    if not memori_enabled():
        return None
    try:
        return A2AMemoryBridge()
    except Exception:
        return None


__all__ = ["A2AMemoryBridge", "build_bridge_if_enabled"]
