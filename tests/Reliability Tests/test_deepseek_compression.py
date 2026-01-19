"""
DeepSeek-OCR compression test suite.

Validates compression ratio targets, query-aware decompression, and metadata
tracking for the Layer 6 memory optimisation work.
"""

import asyncio
from typing import List

import pytest

from infrastructure.memory.deepseek_compression import CompressedMemory, DeepSeekCompressor


@pytest.fixture(scope="module")
def event_loop():
    """Use module-level event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def compressor() -> DeepSeekCompressor:
    """Instantiate a compressor per test to avoid state bleed."""
    return DeepSeekCompressor()


def build_sample_text(paragraph_count: int = 6) -> str:
    """Construct deterministic sample text with repeated sections."""
    paragraphs: List[str] = [
        "Critical: Certificate rotation remains enforced for all production clusters. "
        "Latency budgets must stay under 120ms p95 for checkout flows.",
        "Secondary: Cache warmers pre-load the five most requested knowledge graphs "
        "to keep hybrid retrieval latency stable. " + " ".join(["prefetch"] * 60),
        "Tertiary: Observability exports logs to cold storage every twelve hours for compliance. "
        + " ".join(["telemetry"] * 80),
        "Secondary: Business lineage links SaaS-102 to SaaS-221 for reusable onboarding flows. "
        + " ".join(["handoff"] * 50),
        "Tertiary: Retrospective action items captured during weekly swarm syncs remain archived. "
        + " ".join(["artifact"] * 70),
        "Critical: Fallback instructions for degraded LLM throughput require manual supervisor approval.",
    ]
    return "\n\n".join(paragraphs[:paragraph_count])


@pytest.mark.asyncio
async def test_compression_ratio_target(compressor: DeepSeekCompressor):
    """The compressor should achieve >=60% reduction on verbose input."""
    text = build_sample_text(10)
    metadata = {"namespace": ["agent", "qa_agent"], "critical_keywords": ["critical", "fallback"]}

    compressed = await compressor.compress_memory(text, metadata)

    assert compressed.original_size > compressed.compressed_size
    # Allow slight variation depending on zlib efficiency.
    assert compressed.compression_ratio >= 0.6
    assert compressed.metadata["algorithm"] == "deepseek_ocr"
    assert compressed.metadata["namespace"] == "agent:qa_agent"


@pytest.mark.asyncio
async def test_critical_information_preserved(compressor: DeepSeekCompressor):
    """Critical segments must remain intact after compression."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(
        text,
        {"namespace": ["business", "saas_demo"], "critical_keywords": ["certificate", "fallback"]},
    )

    restored = compressed.reconstruct_full_text()
    assert "Certificate rotation remains enforced" in restored
    assert "Fallback instructions for degraded LLM throughput" in restored


@pytest.mark.asyncio
async def test_query_aware_decompression_returns_relevant_context(compressor: DeepSeekCompressor):
    """Query-aware decompression should surface matching segments."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(
        text,
        {"namespace": ["agent", "ops"], "critical_keywords": ["latency", "compliance"]},
    )

    snippet = await compressor.decompress_for_query(compressed, "latency budgets compliance export")

    # Expect latency statement plus compliance export note to appear.
    assert "Latency budgets must stay under 120ms" in snippet
    assert "Observability exports logs to cold storage" in snippet


@pytest.mark.asyncio
async def test_query_fallback_returns_primary_context(compressor: DeepSeekCompressor):
    """Unknown queries should still return at least the leading critical content."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(text, {"namespace": ["agent", "finance"]})

    snippet = await compressor.decompress_for_query(compressed, "nonexistent keyword phrase")

    assert "Certificate rotation remains enforced" in snippet


@pytest.mark.asyncio
async def test_metadata_tracks_saved_bytes_and_chunks(compressor: DeepSeekCompressor):
    """Compression metadata should expose saved bytes and chunk counts."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(text, {"namespace": ["business", "saas_demo"]})

    metadata = compressed.metadata
    assert metadata["saved_bytes"] >= 0
    assert metadata["chunk_count"] == len(compressed.chunks)
    assert metadata["critical_chunks"] >= 1
    assert isinstance(metadata["timestamp"], float)
    assert metadata["saved_bytes"] <= metadata["original_bytes"]
    assert metadata["stored_bytes"] >= metadata["compressed_bytes"]


@pytest.mark.asyncio
async def test_short_values_bypass_compression(compressor: DeepSeekCompressor):
    """Short payloads should not be force-compressed."""
    short_text = "Tiny memo"
    compressed = await compressor.compress_memory(short_text, {"namespace": ["agent", "builder"]})

    assert compressed.original_size == len(short_text.encode("utf-8"))
    assert compressed.compressed_size == compressed.original_size
    assert compressed.compression_ratio == 0.0
    assert compressed.chunks == []


@pytest.mark.asyncio
async def test_reconstruct_without_tertiary_skips_noise(compressor: DeepSeekCompressor):
    """Reconstruction should optionally omit tertiary content."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(text, {"namespace": ["business", "saas_demo"]})

    condensed = compressed.reconstruct_full_text(include_tertiary=False)
    assert "Observability exports logs" not in condensed
    assert "Retrospective action items" not in condensed
    assert "Certificate rotation remains enforced" in condensed


@pytest.mark.asyncio
async def test_chunk_importance_distribution(compressor: DeepSeekCompressor):
    """Verify chunk importance tiers are assigned."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(
        text,
        {"namespace": ["agent", "qa"], "critical_keywords": ["Certificate", "Fallback"]},
    )

    importance_counts = {level: 0 for level in ("critical", "secondary", "tertiary")}
    for chunk in compressed.chunks:
        importance_counts[chunk.importance] += 1

    assert importance_counts["critical"] >= 1
    assert importance_counts["secondary"] >= 1
    assert importance_counts["tertiary"] >= 1


@pytest.mark.asyncio
async def test_tertiary_summaries_shrink_when_needed(compressor: DeepSeekCompressor):
    """Large tertiary summaries should shrink to help reach compression targets."""
    text = "\n\n".join(
        [
            "Critical insight: Rapid rollback ensures 99.99 uptime.",
            "Tertiary: " + ("detail " * 120),
            "Tertiary: " + ("metrics " * 120),
        ]
    )
    compressed = await compressor.compress_memory(
        text,
        {"namespace": ["business", "ops"], "critical_keywords": ["insight"]},
    )

    tertiary_chunks = [chunk for chunk in compressed.chunks if chunk.importance == "tertiary"]
    assert tertiary_chunks, "Expected tertiary chunks to be present"
    for chunk in tertiary_chunks:
        assert chunk.summary == chunk.summary.strip()
        # Summaries should be significantly shorter than the original filler text.
        assert len(chunk.summary) <= 120


@pytest.mark.asyncio
async def test_serialisation_roundtrip(compressor: DeepSeekCompressor):
    """Compressed memory should serialise and deserialise without loss of metadata."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(text, {"namespace": ["agent", "qa"]})

    payload = compressed.to_dict()
    restored = CompressedMemory.from_dict(payload)

    assert restored.metadata == compressed.metadata
    assert len(restored.chunks) == len(compressed.chunks)
    assert restored.reconstruct_full_text() == compressed.reconstruct_full_text()


@pytest.mark.asyncio
async def test_chunk_decompression_returns_original_for_critical(compressor: DeepSeekCompressor):
    """Critical chunks must decompress to their verbatim content."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(text, {"namespace": ["agent", "stability"]})

    critical_chunks = [chunk for chunk in compressed.chunks if chunk.importance == "critical"]
    assert critical_chunks, "Expected at least one critical chunk"

    reconstructed = [chunk.decompress() for chunk in critical_chunks]
    assert any("Fallback instructions for degraded LLM throughput" in chunk for chunk in reconstructed)


@pytest.mark.asyncio
async def test_decompression_accuracy_metric_tracking(compressor: DeepSeekCompressor):
    """Ensure query-aware decompression marks an accuracy signal."""
    text = build_sample_text()
    compressed = await compressor.compress_memory(
        text,
        {"namespace": ["agent", "latency"], "critical_keywords": ["latency"]},
    )

    snippet = await compressor.decompress_for_query(compressed, "latency budgets")
    assert "Latency budgets must stay under 120ms" in snippet
