"""
Creative Asset Registry
======================

Keeps track of recently purchased creative assets (stock media, ad creative,
localized variants) so agents can reuse them instead of repurchasing the same
asset within a TTL window.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional


@dataclass
class AssetEntry:
    signature: str
    agent_name: str
    vendor: str
    amount: float
    metadata: Dict[str, object]
    timestamp: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "signature": self.signature,
            "agent_name": self.agent_name,
            "vendor": self.vendor,
            "amount": self.amount,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class CreativeAssetRegistry:
    """Simple JSON-backed registry for creative asset purchases."""

    def __init__(self, agent_name: str, path: str = "data/creative_assets/registry.json"):
        self.agent_name = agent_name
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[str, AssetEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for signature, payload in data.items():
                self._entries[signature] = AssetEntry(
                    signature=signature,
                    agent_name=payload.get("agent_name", ""),
                    vendor=payload.get("vendor", ""),
                    amount=payload.get("amount", 0.0),
                    metadata=payload.get("metadata", {}),
                    timestamp=payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
                )
        except Exception:
            # Corrupt registry - start fresh
            self._entries = {}

    def _persist(self) -> None:
        data = {sig: entry.to_dict() for sig, entry in self._entries.items()}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def should_reuse(self, signature: str, ttl_hours: int) -> Optional[AssetEntry]:
        """Return the cached entry if it's still within the TTL."""
        entry = self._entries.get(signature)
        if not entry:
            return None
        ttl = timedelta(hours=max(1, ttl_hours))
        ts = datetime.fromisoformat(entry.timestamp)
        if datetime.now(timezone.utc) - ts <= ttl:
            return entry
        return None

    def record_purchase(
        self,
        *,
        signature: str,
        vendor: str,
        amount: float,
        metadata: Optional[Dict[str, object]] = None,
    ) -> AssetEntry:
        entry = AssetEntry(
            signature=signature,
            agent_name=self.agent_name,
            vendor=vendor,
            amount=amount,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._entries[signature] = entry
        self._persist()
        return entry


def get_asset_registry(agent_name: str) -> CreativeAssetRegistry:
    """Factory helper to share registry path configuration via env."""
    registry_path = os.getenv("CREATIVE_ASSET_REGISTRY_PATH", "data/creative_assets/registry.json")
    return CreativeAssetRegistry(agent_name=agent_name, path=registry_path)

