"""
Prometheus metrics for memory compression.

When Prometheus is unavailable the module falls back to no-op collectors so
callers can record metrics without guarding their code.
"""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - optional dependency
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore
except Exception:  # pragma: no cover - fallback to no-op collectors

    class _NoopCollector:
        def labels(self, *args: Any, **kwargs: Any) -> "_NoopCollector":
            return self

        def set(self, *args: Any, **kwargs: Any) -> None:
            return None

        def inc(self, *args: Any, **kwargs: Any) -> None:
            return None

        def observe(self, *args: Any, **kwargs: Any) -> None:
            return None

    def Gauge(*args: Any, **kwargs: Any) -> _NoopCollector:  # type: ignore
        return _NoopCollector()

    def Counter(*args: Any, **kwargs: Any) -> _NoopCollector:  # type: ignore
        return _NoopCollector()

    def Histogram(*args: Any, **kwargs: Any) -> _NoopCollector:  # type: ignore
        return _NoopCollector()


memory_compression_ratio = Gauge(
    "memory_compression_ratio",
    "Current memory compression ratio (0-1, higher is better)",
    ["namespace"],
)

memory_storage_bytes_saved = Counter(
    "memory_storage_bytes_saved_total",
    "Total bytes saved through memory compression",
    ["namespace"],
)

memory_decompression_latency_ms = Histogram(
    "memory_decompression_latency_ms",
    "Latency of query-aware decompression in milliseconds",
    ["namespace"],
    buckets=(1, 5, 10, 25, 50, 75, 100, 150, 200, 300, 500, 1000),
)

memory_retrieval_accuracy = Histogram(
    "memory_retrieval_accuracy",
    "Accuracy of decompressed memory retrieval (0-1)",
    ["namespace"],
    buckets=(0, 0.25, 0.5, 0.75, 0.9, 0.95, 0.98, 1.0),
)


def record_compression(namespace: str, original_bytes: int, compressed_bytes: int) -> float:
    """
    Record compression metrics and return the computed ratio.
    """
    namespace_label = namespace or "unknown"
    original = max(original_bytes, 1)
    compressed = max(compressed_bytes, 0)
    ratio = 1.0 - (compressed / float(original))

    memory_compression_ratio.labels(namespace_label).set(ratio)
    saved = max(original - compressed, 0)
    if saved:
        memory_storage_bytes_saved.labels(namespace_label).inc(saved)
    return ratio


def record_decompression_latency(namespace: str, latency_ms: float) -> None:
    """
    Record decompression latency in milliseconds.
    """
    namespace_label = namespace or "unknown"
    memory_decompression_latency_ms.labels(namespace_label).observe(max(latency_ms, 0.0))


def record_retrieval_accuracy(namespace: str, accuracy: float) -> None:
    """
    Record retrieval accuracy (0-1 range).
    """
    namespace_label = namespace or "unknown"
    clamped = max(0.0, min(1.0, accuracy))
    memory_retrieval_accuracy.labels(namespace_label).observe(clamped)


__all__ = [
    "memory_compression_ratio",
    "memory_storage_bytes_saved",
    "memory_decompression_latency_ms",
    "memory_retrieval_accuracy",
    "record_compression",
    "record_decompression_latency",
    "record_retrieval_accuracy",
]
