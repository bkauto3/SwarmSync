"""
Multimodal Memory Ingestion Pipeline
====================================

Transforms raw audio/image uploads into textual insights before storing them in
Memori via the HybridMemoryStore. The pipeline keeps a pointer to the original
asset URI so agents can retrieve or re-process high-fidelity data when needed.
"""

from __future__ import annotations

import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from infrastructure.memory.hybrid_memory import HybridMemoryStore


@dataclass
class IngestionResult:
    """Structured output describing an ingested multimodal artifact."""

    summary: str
    details: Dict[str, object]
    asset_type: str
    source_uri: str

    def to_dict(self) -> Dict[str, object]:
        payload = {
            "summary": self.summary,
            "details": self.details,
            "asset_type": self.asset_type,
            "source_uri": self.source_uri,
        }
        return payload


class MultimodalMemoryPipeline:
    """
    Convert multimodal assets into textual insights and persist them to Memori.
    """

    def __init__(
        self,
        hybrid_store: HybridMemoryStore,
        *,
        namespace: str = "multimodal_insight",
    ) -> None:
        self.hybrid_store = hybrid_store
        self.namespace = namespace

    # ------------------------------------------------------------------ #
    # ingestion
    # ------------------------------------------------------------------ #
    def ingest_asset(
        self,
        asset_path: str | Path,
        asset_type: str,
        *,
        source_uri: Optional[str] = None,
    ) -> IngestionResult:
        """
        Generate textual summary + structured details for the asset.
        """
        path = Path(asset_path)
        if not path.exists():
            raise FileNotFoundError(f"Asset not found: {path}")

        canonical_type = self._canonical_asset_type(asset_type, path.suffix)
        if canonical_type == "image":
            details = self._extract_image_features(path)
            summary = f"Image {details['width']}x{details['height']} px ({details['format']})"
        elif canonical_type == "audio":
            details = self._extract_audio_features(path)
            summary = (
                f"Audio clip {details['duration_seconds']:.2f}s "
                f"({details['channels']}ch @ {details['sample_rate_hz']} Hz)"
            )
        else:
            raise ValueError(f"Unsupported asset type: {asset_type}")

        result = IngestionResult(
            summary=summary,
            details=details,
            asset_type=canonical_type,
            source_uri=str(source_uri or path),
        )
        return result

    def ingest_and_store(
        self,
        *,
        user_id: str,
        session_id: str,
        asset_path: str | Path,
        asset_type: str,
        labels: Optional[list[str]] = None,
        extra_metadata: Optional[Dict[str, object]] = None,
        source_uri: Optional[str] = None,
    ) -> Dict[str, object]:
        """
        Ingest the asset and persist the insight via the hybrid memory store.
        """
        ingestion = self.ingest_asset(asset_path, asset_type, source_uri=source_uri)

        key = f"{session_id}:{Path(asset_path).name}"
        value = {
            "insight": ingestion.summary,
            "details": ingestion.details,
        }

        metadata: Dict[str, object] = {
            "scope": "session",
            "provenance": "multimodal_ingestion",
            "session_id": session_id,
            "asset_type": ingestion.asset_type,
            "source_uri": ingestion.source_uri,
        }
        if labels:
            metadata["labels"] = labels
        if extra_metadata:
            metadata.update(extra_metadata)

        metadata["entity"] = {
            "type": "asset",
            "id": key,
            "attributes": {
                "user": user_id,
                "asset_type": ingestion.asset_type,
            },
        }

        record = self.hybrid_store.upsert_memory(
            namespace=self.namespace,
            subject=user_id,
            key=key,
            value=value,
            metadata=metadata,
        )

        payload = {
            "summary": ingestion.summary,
            "details": ingestion.details,
            "memori_record": record.to_dict(),
        }
        return payload

    # ------------------------------------------------------------------ #
    # feature extraction helpers
    # ------------------------------------------------------------------ #
    def _extract_image_features(self, path: Path) -> Dict[str, object]:
        data = path.read_bytes()
        if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
            width = struct.unpack(">I", data[16:20])[0]
            height = struct.unpack(">I", data[20:24])[0]
            color_type = data[25] if len(data) > 25 else None
            return {
                "format": "png",
                "width": int(width),
                "height": int(height),
                "color_type": color_type,
                "filesize_bytes": path.stat().st_size,
            }

        # Fallback metadata for unsupported formats
        return {
            "format": path.suffix.lower().lstrip(".") or "unknown",
            "width": None,
            "height": None,
            "filesize_bytes": path.stat().st_size,
        }

    def _extract_audio_features(self, path: Path) -> Dict[str, object]:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            framerate = wf.getframerate() or 1
            duration = frames / float(framerate)
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()

        return {
            "format": "wav",
            "duration_seconds": float(duration),
            "channels": int(channels),
            "sample_rate_hz": int(framerate),
            "sample_width_bytes": int(sample_width),
            "filesize_bytes": path.stat().st_size,
        }

    @staticmethod
    def _canonical_asset_type(asset_type: str, suffix: str) -> str:
        lowered = asset_type.lower()
        if lowered in {"image", "png", "jpg", "jpeg"}:
            return "image"
        if lowered in {"audio", "wav", "mp3"}:
            return "audio"

        # Infer from suffix if caller omitted explicit modality
        ext = suffix.lower()
        if ext in {".png", ".jpg", ".jpeg"}:
            return "image"
        if ext in {".wav", ".mp3"}:
            return "audio"

        return lowered


__all__ = ["MultimodalMemoryPipeline", "IngestionResult"]

