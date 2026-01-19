from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CodebookStore:
    """Persist reusable reasoning snippets extracted from trajectories."""

    def __init__(self, path: Optional[Path] = None, max_entries: int = 200):
        self.path = path or Path("data/codebooks.json")
        self.max_entries = max_entries
        self._data = self._load()

    def _load(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            logger.warning("Codebook store corrupted, starting fresh")
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    def record_entry(
        self,
        agent_name: str,
        snippet: str,
        context: Optional[Dict[str, Any]] = None,
        status: str = "unknown",
        score: float = 0.0,
    ) -> Dict[str, Any]:
        if not snippet:
            snippet = "N/A"
        entry = {
            "snippet": snippet[:600],
            "context": context or {},
            "status": status,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        buffer = self._data.setdefault(agent_name, [])
        buffer.append(entry)
        if len(buffer) > self.max_entries:
            self._data[agent_name] = buffer[-self.max_entries :]
        self._save()
        return entry

    def recent(self, agent_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        entries = self._data.get(agent_name, [])
        return list(reversed(entries[-limit:]))

    def failure_trend(self, agent_name: str, window: int = 20) -> Optional[Dict[str, float]]:
        entries = self._data.get(agent_name, [])
        if not entries:
            return None
        sample = entries[-window:]
        total = len(sample)
        failures = sum(1 for entry in sample if entry["status"].lower().startswith("fail"))
        return {
            "window": total,
            "failure_rate": failures / total if total else 0.0,
        }


_CODEBOOK_STORE: Optional[CodebookStore] = None


def get_codebook_store() -> CodebookStore:
    global _CODEBOOK_STORE
    if _CODEBOOK_STORE is None:
        _CODEBOOK_STORE = CodebookStore()
    return _CODEBOOK_STORE
