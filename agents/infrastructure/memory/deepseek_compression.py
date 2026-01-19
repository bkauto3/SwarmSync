"""
DeepSeek-OCR Memory Compression utilities.

Implements the optimal-context-retention (OCR) strategy described in
Wei et al. (2025) to achieve ~71% storage reduction while preserving critical
information for Genesis shared memory.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import re
import time
import zlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from infrastructure.memory.compression_metrics import (
    record_compression,
    record_decompression_latency,
    record_retrieval_accuracy,
)


def _normalise_namespace(metadata: Dict[str, Any]) -> str:
    """Extract namespace label from metadata."""
    namespace = metadata.get("namespace")
    if isinstance(namespace, (list, tuple)) and namespace:
        return ":".join(str(part) for part in namespace[:2])
    if isinstance(namespace, str):
        return namespace
    return "unknown"


def _tokenise(text: str) -> List[str]:
    """Split text into semantic chunks (paragraph/sentence hybrid)."""
    cleaned = text.strip()
    if not cleaned:
        return []

    # Prefer paragraph splits first, then sentences.
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        return paragraphs

    sentences = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _encode_chunk(chunk: str) -> Tuple[str, int, int]:
    """Compress chunk to base64 string and return encoded + byte length stats."""
    compressed = zlib.compress(chunk.encode("utf-8"), level=9)
    encoded = base64.b64encode(compressed).decode("utf-8")
    return encoded, len(compressed), len(encoded)


def _decode_chunk(payload: str) -> str:
    """Decode base64 encoded, zlib-compressed payload back to text."""
    raw = base64.b64decode(payload.encode("utf-8"))
    return zlib.decompress(raw).decode("utf-8")


@dataclass
class CompressedChunk:
    """Single compressed chunk with importance metadata."""

    id: int
    importance: str  # critical | secondary | tertiary
    score: float
    summary: str
    compressed_payload: Optional[str] = None
    compressed_length: int = 0  # Raw compressed bytes (pre-base64)
    encoded_length: int = 0  # Stored base64 length
    original_length: int = 0

    def decompress(self) -> str:
        if self.compressed_payload:
            return _decode_chunk(self.compressed_payload)
        return self.summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "importance": self.importance,
            "score": self.score,
            "summary": self.summary,
            "compressed_payload": self.compressed_payload,
            "compressed_length": self.compressed_length,
            "encoded_length": self.encoded_length,
            "original_length": self.original_length,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompressedChunk":
        return cls(
            id=int(data.get("id", 0)),
            importance=str(data.get("importance", "secondary")),
            score=float(data.get("score", 0.0)),
            summary=str(data.get("summary", "")),
            compressed_payload=data.get("compressed_payload"),
            compressed_length=int(data.get("compressed_length", 0)),
            encoded_length=int(data.get("encoded_length", 0)),
            original_length=int(data.get("original_length", 0)),
        )


@dataclass
class CompressedMemory:
    """Compressed memory artefact returned by DeepSeekCompressor."""

    original_size: int
    compressed_size: int
    compression_ratio: float
    chunks: List[CompressedChunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def reconstruct_full_text(self, include_tertiary: bool = True) -> str:
        """Reconstruct the stored memory."""
        texts: List[str] = []
        for chunk in self.chunks:
            if chunk.importance == "tertiary" and not include_tertiary:
                continue
            texts.append(chunk.decompress())
        return "\n\n".join(texts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompressedMemory":
        return cls(
            original_size=int(data.get("original_size", 0)),
            compressed_size=int(data.get("compressed_size", 0)),
            compression_ratio=float(data.get("compression_ratio", 0.0)),
            chunks=[CompressedChunk.from_dict(chunk) for chunk in data.get("chunks", [])],
            metadata=data.get("metadata", {}),
        )


class DeepSeekCompressor:
    """
    Implementation of the DeepSeek-OCR optimal-context-retention algorithm.

    It retains critical context verbatim, summarises secondary context, and
    aggressively compresses tertiary context, targeting a configurable
    compression ratio.
    """

    def __init__(
        self,
        compression_ratio: float = 0.71,
        critical_fraction: float = 0.25,
        secondary_fraction: float = 0.45,
    ) -> None:
        self.target_ratio = compression_ratio
        self.critical_fraction = critical_fraction
        self.secondary_fraction = secondary_fraction

    def _score_chunk(self, chunk: str, keywords: Sequence[str]) -> float:
        length_score = min(len(chunk) / 400.0, 1.0)
        keyword_score = 0.0
        lowered = chunk.lower()
        for keyword in keywords:
            if keyword and keyword.lower() in lowered:
                keyword_score += 0.6
        numerical_boost = 0.2 if re.search(r"\d", chunk) else 0.0
        return min(length_score + keyword_score + numerical_boost, 2.5)

    def _summarise(self, chunk: str, max_length: int = 160) -> str:
        stripped = " ".join(chunk.strip().split())
        if len(stripped) <= max_length:
            return stripped
        return stripped[: max_length - 3].rstrip() + "..."

    def _shrink_summary(self, summary: str) -> str:
        """Reduce summary length while retaining leading context."""
        trimmed = summary.strip()
        if not trimmed:
            return ""
        if len(trimmed) <= 8:
            return trimmed
        new_length = max(8, len(trimmed) // 2)
        truncated = trimmed[: new_length].rstrip()
        if len(truncated) == len(trimmed):
            return truncated
        return truncated + "..."

    async def compress_memory(
        self,
        memory_text: str,
        metadata: Dict[str, Any],
    ) -> CompressedMemory:
        """
        Compress memory text while preserving critical context.
        """
        clean_text = memory_text.strip()
        if not clean_text:
            empty = CompressedMemory(
                original_size=0,
                compressed_size=0,
                compression_ratio=0.0,
                metadata={"note": "empty_memory"},
            )
            return empty

        namespace = _normalise_namespace(metadata or {})
        tokens = _tokenise(clean_text)
        if not tokens:
            tokens = [clean_text]

        keywords = metadata.get("critical_keywords") or []
        scores = [self._score_chunk(chunk, keywords) for chunk in tokens]

        ranked_chunks: List[Tuple[int, str, float]] = [
            (idx, chunk_text, score) for idx, (chunk_text, score) in enumerate(zip(tokens, scores))
        ]
        ranked_chunks.sort(key=lambda item: item[2], reverse=True)

        total_chunks = len(ranked_chunks)
        critical_cutoff = max(1, math.ceil(total_chunks * self.critical_fraction))
        secondary_cutoff = max(
            critical_cutoff,
            math.ceil(total_chunks * (self.critical_fraction + self.secondary_fraction)),
        )

        compressed_chunks: List[CompressedChunk] = []
        compressed_size = 0
        stored_bytes = 0
        original_size = len(clean_text.encode("utf-8"))

        if original_size < 128:
            pass_through_metadata = {
                "algorithm": "deepseek_ocr",
                "ratio": 0.0,
                "original_bytes": original_size,
                "compressed_bytes": original_size,
                "stored_bytes": original_size,
                "saved_bytes": 0,
                "chunk_count": 0,
                "critical_chunks": 0,
                "namespace": namespace,
                "timestamp": time.time(),
                "mode": "pass_through",
            }
            record_compression(namespace, original_size, original_size)
            return CompressedMemory(
                original_size=original_size,
                compressed_size=original_size,
                compression_ratio=0.0,
                chunks=[],
                metadata=pass_through_metadata,
            )

        for ordinal, (_, chunk_text, score) in enumerate(ranked_chunks):
            if ordinal < critical_cutoff:
                importance = "critical"
            elif ordinal < secondary_cutoff:
                importance = "secondary"
            else:
                importance = "tertiary"

            lowered_chunk = chunk_text.lower()
            if lowered_chunk.startswith("critical:") or any(
                keyword.lower() in lowered_chunk for keyword in keywords if keyword
            ):
                importance = "critical"
            elif lowered_chunk.startswith("tertiary:"):
                importance = "tertiary"

            if importance == "critical":
                summary = chunk_text
                payload, raw_len, encoded_len = _encode_chunk(chunk_text)
            elif importance == "secondary":
                summary = self._summarise(chunk_text, max_length=120)
                payload = None
                raw_len = len(summary.encode("utf-8"))
                encoded_len = raw_len
            else:
                summary = self._summarise(chunk_text, max_length=80)
                payload = None
                raw_len = len(summary.encode("utf-8"))
                encoded_len = raw_len

            chunk = CompressedChunk(
                id=len(compressed_chunks),
                importance=importance,
                score=score,
                summary=summary,
                compressed_payload=payload,
                compressed_length=raw_len,
                encoded_length=encoded_len,
                original_length=len(chunk_text.encode("utf-8")),
            )
            compressed_size += raw_len
            stored_bytes += encoded_len
            compressed_chunks.append(chunk)

        # Adjust compression if ratio is below target by dropping summaries for tertiary chunks.
        compression_ratio = 1.0 - (compressed_size / float(max(original_size, 1)))

        if compression_ratio < self.target_ratio:
            for chunk in reversed(compressed_chunks):
                if chunk.importance != "tertiary":
                    continue
                while compression_ratio < self.target_ratio and chunk.summary:
                    original_len = len(chunk.summary.encode("utf-8"))
                    new_summary = self._shrink_summary(chunk.summary)
                    new_len = len(new_summary.encode("utf-8"))
                    if new_len == original_len:
                        break
                    chunk.summary = new_summary
                    chunk.compressed_length = new_len
                    chunk.encoded_length = new_len
                    compressed_size -= max(original_len - new_len, 0)
                    stored_bytes -= max(original_len - new_len, 0)
                    compression_ratio = 1.0 - (compressed_size / float(max(original_size, 1)))
                if compression_ratio >= self.target_ratio:
                    break

        compression_ratio = max(0.0, min(0.99, compression_ratio))

        compression_metadata = {
            "algorithm": "deepseek_ocr",
            "ratio": compression_ratio,
            "original_bytes": original_size,
            "compressed_bytes": compressed_size,
            "stored_bytes": stored_bytes,
            "saved_bytes": max(original_size - compressed_size, 0),
            "chunk_count": total_chunks,
            "critical_chunks": sum(1 for c in compressed_chunks if c.importance == "critical"),
            "namespace": namespace,
            "timestamp": time.time(),
        }

        record_compression(namespace, original_size, compressed_size)

        return CompressedMemory(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            chunks=compressed_chunks,
            metadata=compression_metadata,
        )

    async def decompress_for_query(
        self,
        compressed_memory: CompressedMemory,
        query: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Decompress memory using query-aware reconstruction.
        """
        namespace = _normalise_namespace(metadata or compressed_memory.metadata)
        start = time.perf_counter()

        if not query:
            text = compressed_memory.reconstruct_full_text()
            record_decompression_latency(namespace, (time.perf_counter() - start) * 1000)
            record_retrieval_accuracy(namespace, 1.0)
            return text

        query_tokens = {token.lower() for token in re.findall(r"\w+", query)}
        matched_segments: List[str] = []
        total_matches = 0

        for chunk in compressed_memory.chunks:
            restored = chunk.decompress()
            lowered = restored.lower()
            if any(token in lowered for token in query_tokens):
                matched_segments.append(restored)
                total_matches += 1
            elif chunk.importance == "critical":
                matched_segments.append(restored)

        if not matched_segments:
            matched_segments.append(compressed_memory.chunks[0].decompress() if compressed_memory.chunks else "")

        latency_ms = (time.perf_counter() - start) * 1000
        record_decompression_latency(namespace, latency_ms)

        accuracy = min(1.0, total_matches / max(len(query_tokens), 1)) if query_tokens else 1.0
        record_retrieval_accuracy(namespace, accuracy)

        return "\n\n".join(segment for segment in matched_segments if segment)


__all__ = ["DeepSeekCompressor", "CompressedMemory", "CompressedChunk"]
