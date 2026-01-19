"""
X402 Vendor Capability Cache
============================

Maintains a lightweight cache of vendor payment capabilities (accepted tokens,
preferred chains, typical pricing) so agents can make smarter payment
decisions before issuing a request.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class X402VendorCache:
    """Caches vendor capabilities with automatic persistence and TTL refresh."""

    def __init__(
        self,
        cache_path: str = "data/x402/vendor_capabilities.json",
        *,
        ttl_seconds: Optional[int] = None,
    ):
        self.path = Path(cache_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds or int(os.getenv("X402_VENDOR_CACHE_TTL", "86400"))
        self._lock = threading.Lock()
        self._loaded_at = 0.0
        self._data: Dict[str, Any] = {"vendors": {}, "last_refresh": None}
        self._load()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def lookup(self, vendor: str) -> Dict[str, Any]:
        """Return cached capabilities for a vendor (may be empty)."""
        self._refresh_if_stale()
        with self._lock:
            return dict(self._data["vendors"].get(vendor, {}))

    def record_observation(
        self,
        vendor: str,
        *,
        token: Optional[str] = None,
        chain: Optional[str] = None,
        price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update cache with details from a recent payment challenge/response."""
        self._refresh_if_stale()
        timestamp = datetime.now(timezone.utc).isoformat()
        capability = {
            "last_updated": timestamp,
            "accepted_tokens": [],
            "preferred_chain": chain or "base",
            "recent_prices": [],
            "metadata_samples": [],
        }
        with self._lock:
            entry = self._data["vendors"].setdefault(vendor, capability)
            if token and chain:
                token_str = f"{token.lower()}:{chain.lower()}"
                tokens = set(entry.get("accepted_tokens", []))
                tokens.add(token_str)
                entry["accepted_tokens"] = sorted(tokens)
                entry["preferred_chain"] = chain.lower()
            if isinstance(price, (int, float)):
                prices = entry.get("recent_prices", [])
                prices.append(round(float(price), 4))
                entry["recent_prices"] = prices[-20:]
            if metadata:
                samples = entry.get("metadata_samples", [])
                samples.append({k: metadata.get(k) for k in sorted(metadata.keys()) if k in {"category", "purpose", "agent_name"}})
                entry["metadata_samples"] = samples[-20:]
            entry["last_updated"] = timestamp
            self._persist_locked()

    def refresh_now(self) -> None:
        """Force reload from disk."""
        self._load()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _refresh_if_stale(self) -> None:
        if time.time() - self._loaded_at < self.ttl_seconds:
            return
        self._load()

    def _load(self) -> None:
        with self._lock:
            if self.path.exists():
                try:
                    self._data = json.loads(self.path.read_text(encoding="utf-8"))
                except Exception:
                    # Corrupt cache; reset
                    self._data = {"vendors": {}, "last_refresh": None}
            else:
                self._data = {"vendors": {}, "last_refresh": None}
            self._data.setdefault("vendors", {})
            self._data["last_refresh"] = datetime.now(timezone.utc).isoformat()
            self._loaded_at = time.time()

    def _persist_locked(self) -> None:
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        temp_path.replace(self.path)


_VENDOR_CACHE: Optional[X402VendorCache] = None


def get_x402_vendor_cache() -> X402VendorCache:
    """Singleton accessor so every agent shares the same cache."""
    global _VENDOR_CACHE
    if _VENDOR_CACHE is None:
        _VENDOR_CACHE = X402VendorCache()
    return _VENDOR_CACHE

