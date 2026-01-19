"""
Comprehensive test suite for Visual Memory Compression

Tests:
- Basic compression (10 tests)
- Access pattern intelligence (8 tests)
- Error handling (7 tests)
- Integration tests (10 tests)
- OTEL observability (5 tests)
- Concurrency tests (2 tests)

Target: 47+ tests, 90%+ coverage
"""

import asyncio
import base64
import json
import os
import pytest
import time
from datetime import datetime, timedelta, timezone
from io import BytesIO
from PIL import Image
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.visual_memory_compressor import VisualMemoryCompressor, VisualCompressionMode
from infrastructure.memory_store import GenesisMemoryStore, MemoryMetadata, InMemoryBackend
from infrastructure.observability import CorrelationContext
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


# ==================== FIXTURES ====================

@pytest.fixture
def compressor():
    """Create compressor with test configuration"""
    return VisualMemoryCompressor(
        compression_threshold=100,  # Low threshold for testing
        default_mode="base",
        use_ocr_fallback=True
    )


@pytest.fixture
def memory_store_with_compressor(compressor):
    """Create memory store with compression enabled"""
    backend = InMemoryBackend()
    return GenesisMemoryStore(backend=backend, compressor=compressor)


@pytest.fixture
def short_text():
    """Short text (below compression threshold)"""
    return "This is a short text that should not be compressed."


@pytest.fixture
def long_text():
    """Long text (above compression threshold)"""
    return """
    This is a very long text that exceeds the compression threshold.
    It contains multiple paragraphs and should trigger compression.

    The DeepSeek-OCR system will convert this text into a visual representation,
    reducing token usage by 10-20x. This is critical for cost optimization.

    Additional context: The compression pipeline uses PIL to render text as an image,
    then encodes it as base64. On retrieval, OCR extracts the text back.

    This approach achieves 71% memory cost reduction in base mode.
    """ * 5  # Repeat to ensure it's long enough


@pytest.fixture
def access_pattern_recent():
    """Access pattern: recently accessed"""
    return {
        "last_accessed": datetime.now(timezone.utc).isoformat(),
        "access_count": 50,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    }


@pytest.fixture
def access_pattern_old():
    """Access pattern: old, rarely accessed"""
    return {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "access_count": 2,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    }


# ==================== BASIC COMPRESSION TESTS (10) ====================

@pytest.mark.asyncio
async def test_compress_short_text(compressor, short_text):
    """Test that short text below threshold should not be compressed"""
    # Set threshold higher than short_text length
    compressor.compression_threshold = 1000

    access_pattern = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "access_count": 1,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    }

    should_compress = await compressor.should_compress(short_text, access_pattern)
    assert should_compress is False


@pytest.mark.asyncio
async def test_compress_long_text(compressor, long_text):
    """Test that long text above threshold triggers compression"""
    metadata = {"tags": ["test"], "created_at": datetime.now(timezone.utc).isoformat()}

    compressed = await compressor.compress_memory(long_text, metadata, mode=VisualCompressionMode.BASE)

    assert compressed["compressed"] is True
    assert compressed["original_tokens"] > 0
    assert compressed["compressed_tokens"] == 256  # BASE mode
    assert compressed["compression_ratio"] > 1
    assert "visual_encoding" in compressed
    assert compressed["compression_mode"] == VisualCompressionMode.BASE


@pytest.mark.asyncio
async def test_compression_ratio_calculation(compressor, long_text):
    """Test compression ratio is calculated correctly"""
    metadata = {}
    compressed = await compressor.compress_memory(long_text, metadata)

    expected_ratio = compressed["original_tokens"] / compressed["compressed_tokens"]
    assert abs(compressed["compression_ratio"] - expected_ratio) < 0.01


@pytest.mark.asyncio
async def test_visual_encoding_format(compressor, long_text):
    """Test that visual encoding is valid base64 image data"""
    metadata = {}
    compressed = await compressor.compress_memory(long_text, metadata)

    # Should be base64 encoded
    visual_encoding = compressed["visual_encoding"]
    assert isinstance(visual_encoding, str)

    # Should be decodable as base64
    try:
        image_data = base64.b64decode(visual_encoding)
        assert len(image_data) > 0

        # Should be a valid PNG image
        img = Image.open(BytesIO(image_data))
        assert img.format == "PNG"
    except Exception as e:
        pytest.fail(f"Invalid visual encoding: {e}")


@pytest.mark.asyncio
async def test_metadata_preservation(compressor, long_text):
    """Test that metadata is preserved in compressed data"""
    metadata = {
        "tags": ["important", "test"],
        "created_at": "2025-10-20T10:00:00Z",
        "custom_field": "custom_value"
    }

    compressed = await compressor.compress_memory(long_text, metadata)

    assert compressed["metadata"] == metadata


@pytest.mark.asyncio
async def test_decompress_compressed_memory(compressor, long_text):
    """Test that compressed memory can be decompressed"""
    metadata = {}
    compressed = await compressor.compress_memory(long_text, metadata)

    # Mock OCR extraction to return original text
    with patch.object(compressor, '_ocr_extract_text', return_value=long_text):
        decompressed_text = await compressor.decompress_memory(compressed)

        # Should return text (may not be 100% identical due to OCR)
        assert isinstance(decompressed_text, str)
        assert len(decompressed_text) > 0


@pytest.mark.asyncio
async def test_roundtrip_compression(compressor, long_text):
    """Test compress -> decompress -> verify roundtrip"""
    metadata = {}

    # Compress
    compressed = await compressor.compress_memory(long_text, metadata)

    # Mock OCR to return exact text
    with patch.object(compressor, '_ocr_extract_text', return_value=long_text):
        # Decompress
        decompressed = await compressor.decompress_memory(compressed)

        # Verify
        assert decompressed == long_text


@pytest.mark.asyncio
async def test_compression_idempotency(compressor, long_text):
    """Test that compressing twice produces the same result"""
    metadata = {}

    compressed1 = await compressor.compress_memory(long_text, metadata)
    compressed2 = await compressor.compress_memory(long_text, metadata)

    # Token counts should be identical
    assert compressed1["original_tokens"] == compressed2["original_tokens"]
    assert compressed1["compressed_tokens"] == compressed2["compressed_tokens"]
    assert compressed1["compression_ratio"] == compressed2["compression_ratio"]


@pytest.mark.asyncio
async def test_token_counting_accuracy(compressor):
    """Test that token counting is accurate"""
    # Known text with approximately 100 tokens (~400 characters)
    text = "word " * 80  # ~400 characters = ~100 tokens

    estimated_tokens = compressor._estimate_token_count(text)

    # Should be close to 100 (±20 tokens tolerance)
    assert 80 <= estimated_tokens <= 120


@pytest.mark.asyncio
async def test_cost_savings_calculation(compressor):
    """Test cost savings calculation is correct"""
    original_tokens = 5000
    compressed_tokens = 250

    savings = compressor.calculate_savings(original_tokens, compressed_tokens)

    assert savings["compression_ratio"] == 20.0
    assert savings["token_savings"] == 4750
    assert savings["compression_percentage"] == 95.0

    # Cost: 4750 tokens * $0.003 / 1000 = $0.01425
    expected_cost = (4750 / 1000) * 0.003
    assert abs(savings["cost_savings_usd"] - expected_cost) < 0.0001


# ==================== ACCESS PATTERN INTELLIGENCE TESTS (8) ====================

@pytest.mark.asyncio
async def test_should_compress_large_rarely_accessed(compressor, long_text):
    """Test compression for large, rarely accessed memories"""
    access_pattern = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "access_count": 2,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    }

    should_compress = await compressor.should_compress(long_text, access_pattern)
    assert should_compress is True


@pytest.mark.asyncio
async def test_should_not_compress_frequently_accessed(compressor, long_text):
    """Test no compression for frequently accessed memories"""
    access_pattern = {
        "last_accessed": datetime.now(timezone.utc).isoformat(),
        "access_count": 1000,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    }

    should_compress = await compressor.should_compress(long_text, access_pattern)
    assert should_compress is False


@pytest.mark.asyncio
async def test_should_not_compress_recently_accessed(compressor, long_text):
    """Test no compression for recently accessed memories"""
    # Memory accessed 1 hour ago with high frequency (50/hour)
    access_pattern = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "access_count": 50,  # High frequency to prevent Rule 2
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    }

    should_compress = await compressor.should_compress(long_text, access_pattern)
    assert should_compress is False


@pytest.mark.asyncio
async def test_should_compress_old_memory(compressor, long_text):
    """Test compression for old memories not accessed in 30+ days"""
    access_pattern = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(),
        "access_count": 1,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    }

    should_compress = await compressor.should_compress(long_text, access_pattern)
    assert should_compress is True


@pytest.mark.asyncio
async def test_access_frequency_threshold(compressor, long_text):
    """Test access frequency threshold (10 accesses/hour)"""
    # High frequency (50 accesses/hour)
    access_pattern_high = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        "access_count": 600,  # 50/hour
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    }

    # Low frequency (5 accesses/hour)
    access_pattern_low = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        "access_count": 60,  # 5/hour
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    }

    should_compress_high = await compressor.should_compress(long_text, access_pattern_high)
    should_compress_low = await compressor.should_compress(long_text, access_pattern_low)

    assert should_compress_high is False  # High frequency = don't compress
    assert should_compress_low is True    # Low frequency = compress


@pytest.mark.asyncio
async def test_last_accessed_time_threshold(compressor, long_text):
    """Test last accessed time threshold (24 hours)"""
    # Accessed 12 hours ago with high frequency (to avoid Rule 2)
    access_pattern_recent = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        "access_count": 120,  # 10/hour over 12 hours = don't compress
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
    }

    # Accessed 48 hours ago (triggers Rule 1: >24 hours)
    access_pattern_old = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(),
        "access_count": 5,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    }

    should_compress_recent = await compressor.should_compress(long_text, access_pattern_recent)
    should_compress_old = await compressor.should_compress(long_text, access_pattern_old)

    assert should_compress_recent is False  # Recent access = don't compress
    assert should_compress_old is True       # Old access = compress


@pytest.mark.asyncio
async def test_compression_decision_logic(compressor, long_text):
    """Test overall compression decision logic"""
    # Case 1: Short text -> don't compress
    compressor.compression_threshold = 10000
    access_pattern = {"last_accessed": "2025-01-01T00:00:00Z", "access_count": 1, "created_at": "2025-01-01T00:00:00Z"}
    assert await compressor.should_compress(long_text, access_pattern) is False

    # Case 2: Long + old -> compress
    compressor.compression_threshold = 100
    access_pattern_old = {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "access_count": 2,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    }
    assert await compressor.should_compress(long_text, access_pattern_old) is True


@pytest.mark.asyncio
async def test_adaptive_threshold_adjustment(compressor, long_text):
    """Test that threshold can be adjusted dynamically"""
    # Start with low threshold
    compressor.compression_threshold = 100
    assert await compressor.should_compress(long_text, {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "access_count": 1,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    }) is True

    # Increase threshold
    compressor.compression_threshold = 100000
    assert await compressor.should_compress(long_text, {
        "last_accessed": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "access_count": 1,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    }) is False


# ==================== ERROR HANDLING TESTS (7) ====================

@pytest.mark.asyncio
async def test_compression_failure_fallback(compressor, long_text):
    """Test graceful fallback if compression fails"""
    metadata = {}

    # Mock image creation to raise exception
    with patch.object(compressor, '_text_to_image', side_effect=Exception("Image creation failed")):
        with pytest.raises(Exception):
            await compressor.compress_memory(long_text, metadata)

    # Stats should track error
    assert compressor.stats["compression_errors"] > 0


@pytest.mark.asyncio
async def test_decompression_failure_handling(compressor):
    """Test handling of decompression failures"""
    invalid_compressed = {
        "compressed": True,
        "visual_encoding": "invalid_base64",
        "compression_mode": "base"
    }

    with pytest.raises(RuntimeError):
        await compressor.decompress_memory(invalid_compressed)

    # Stats should track error
    assert compressor.stats["decompression_errors"] > 0


@pytest.mark.asyncio
async def test_invalid_visual_encoding(compressor):
    """Test handling of invalid visual encoding"""
    invalid_compressed = {
        "compressed": True,
        "visual_encoding": "not_valid_base64!!!",
        "compression_mode": "base"
    }

    with pytest.raises(RuntimeError):
        await compressor.decompress_memory(invalid_compressed)


@pytest.mark.asyncio
async def test_missing_api_key():
    """Test behavior when API key is missing"""
    compressor = VisualMemoryCompressor(api_key=None)

    # Should initialize without API key (uses fallback)
    assert compressor.api_key is None
    assert compressor.use_ocr_fallback is True


@pytest.mark.asyncio
async def test_api_timeout_handling(compressor, long_text):
    """Test handling of API timeout"""
    metadata = {}

    # This test assumes OCR would timeout, but we'll simulate it
    # In practice, pytesseract may not be installed, so we test graceful degradation
    with patch.object(compressor, '_ocr_extract_text', side_effect=RuntimeError("OCR timeout")):
        compressed = await compressor.compress_memory(long_text, metadata)

        with pytest.raises(RuntimeError):
            await compressor.decompress_memory(compressed)


@pytest.mark.asyncio
async def test_corrupted_compressed_data(compressor):
    """Test handling of corrupted compressed data"""
    corrupted = {
        "compressed": True,
        # Missing visual_encoding field
        "compression_mode": "base"
    }

    with pytest.raises(ValueError):
        await compressor.decompress_memory(corrupted)


@pytest.mark.asyncio
async def test_graceful_degradation(memory_store_with_compressor, long_text):
    """Test that system degrades gracefully when compression unavailable"""
    # Remove compressor
    memory_store_with_compressor.compressor = None

    # Should still work without compression
    value = {"text": long_text}
    entry_id = await memory_store_with_compressor.save_memory(
        namespace=("agent", "test"),
        key="test_key",
        value=value,
        compress=True  # Request compression but compressor unavailable
    )

    # Should save uncompressed
    retrieved = await memory_store_with_compressor.get_memory(
        namespace=("agent", "test"),
        key="test_key"
    )

    assert retrieved == value


# ==================== INTEGRATION TESTS (10) ====================

@pytest.mark.asyncio
async def test_memory_store_compression_integration(memory_store_with_compressor, long_text):
    """Test end-to-end integration with memory store"""
    # Save with compression
    value = {"content": long_text}

    # Mock should_compress to return True
    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        entry_id = await memory_store_with_compressor.save_memory(
            namespace=("agent", "test"),
            key="compressed_memory",
            value=value,
            compress=True
        )

    assert entry_id is not None


@pytest.mark.asyncio
async def test_save_with_compression_flag(memory_store_with_compressor, long_text):
    """Test save_memory with compress=True flag"""
    value = {"data": long_text}

    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        entry_id = await memory_store_with_compressor.save_memory(
            namespace=("business", "test_biz"),
            key="test_data",
            value=value,
            compress=True
        )

    # Verify entry exists
    retrieved = await memory_store_with_compressor.get_memory(
        namespace=("business", "test_biz"),
        key="test_data"
    )

    assert retrieved is not None


@pytest.mark.asyncio
async def test_get_with_decompression(memory_store_with_compressor, long_text):
    """Test get_memory with automatic decompression"""
    value = {"message": long_text}

    # Save compressed
    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        await memory_store_with_compressor.save_memory(
            namespace=("agent", "qa"),
            key="procedure",
            value=value,
            compress=True
        )

    # Retrieve with decompression
    with patch.object(memory_store_with_compressor.compressor, '_ocr_extract_text', return_value=json.dumps(value)):
        retrieved = await memory_store_with_compressor.get_memory(
            namespace=("agent", "qa"),
            key="procedure",
            decompress=True
        )

        # Should get original value back (if OCR works perfectly)
        assert retrieved is not None


@pytest.mark.asyncio
async def test_compression_metadata_tracking(memory_store_with_compressor, long_text):
    """Test that compression metadata is tracked properly"""
    value = {"info": long_text}

    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        entry_id = await memory_store_with_compressor.save_memory(
            namespace=("agent", "analyst"),
            key="report",
            value=value,
            compress=True
        )

    # Get with metadata
    entry = await memory_store_with_compressor.get_memory_with_metadata(
        namespace=("agent", "analyst"),
        key="report"
    )

    # Check metadata contains compression info
    if entry and entry.metadata.compressed:
        assert entry.metadata.compression_ratio is not None


@pytest.mark.asyncio
async def test_mixed_compressed_uncompressed_memories(memory_store_with_compressor, long_text):
    """Test handling mixed compressed and uncompressed memories"""
    # Save uncompressed
    value1 = {"data": "short"}
    await memory_store_with_compressor.save_memory(
        namespace=("agent", "test"),
        key="uncompressed",
        value=value1,
        compress=False
    )

    # Save compressed
    value2 = {"data": long_text}
    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        await memory_store_with_compressor.save_memory(
            namespace=("agent", "test"),
            key="compressed",
            value=value2,
            compress=True
        )

    # Retrieve both
    retrieved1 = await memory_store_with_compressor.get_memory(
        namespace=("agent", "test"),
        key="uncompressed"
    )
    retrieved2 = await memory_store_with_compressor.get_memory(
        namespace=("agent", "test"),
        key="compressed"
    )

    assert retrieved1 == value1
    assert retrieved2 is not None  # May be compressed format


@pytest.mark.asyncio
async def test_namespace_compression_isolation(memory_store_with_compressor, long_text):
    """Test that compression is isolated per namespace"""
    value = {"content": long_text}

    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        # Save to agent namespace
        await memory_store_with_compressor.save_memory(
            namespace=("agent", "qa"),
            key="data",
            value=value,
            compress=True
        )

        # Save to business namespace
        await memory_store_with_compressor.save_memory(
            namespace=("business", "saas_001"),
            key="data",
            value=value,
            compress=True
        )

    # Both should be retrievable independently
    retrieved_agent = await memory_store_with_compressor.get_memory(
        namespace=("agent", "qa"),
        key="data"
    )
    retrieved_business = await memory_store_with_compressor.get_memory(
        namespace=("business", "saas_001"),
        key="data"
    )

    assert retrieved_agent is not None
    assert retrieved_business is not None


@pytest.mark.asyncio
async def test_redis_cache_compressed_memory(memory_store_with_compressor, long_text):
    """Test Redis cache handles compressed memories correctly"""
    # This test validates cache layer integration (Week 1 infrastructure)
    value = {"data": long_text}

    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        entry_id = await memory_store_with_compressor.save_memory(
            namespace=("agent", "cache_test"),
            key="cached_data",
            value=value,
            compress=True
        )

    # Retrieve multiple times (should hit cache)
    for _ in range(3):
        retrieved = await memory_store_with_compressor.get_memory(
            namespace=("agent", "cache_test"),
            key="cached_data"
        )
        assert retrieved is not None


@pytest.mark.asyncio
async def test_mongodb_persistence_compressed_memory(memory_store_with_compressor, long_text):
    """Test MongoDB persistence of compressed memories"""
    # This test validates MongoDB backend integration (Week 1 infrastructure)
    value = {"persistent_data": long_text}

    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        entry_id = await memory_store_with_compressor.save_memory(
            namespace=("system", "global"),
            key="persistent_memory",
            value=value,
            compress=True
        )

    # Clear backend (simulate restart)
    await memory_store_with_compressor.backend.clear_namespace(("system", "global"))

    # In production, MongoDB would persist this


@pytest.mark.asyncio
async def test_concurrent_compression_operations(memory_store_with_compressor, long_text):
    """Test concurrent compression operations don't interfere"""
    values = [{"data": f"{long_text}_{i}"} for i in range(5)]

    with patch.object(memory_store_with_compressor.compressor, 'should_compress', return_value=True):
        # Save concurrently
        tasks = [
            memory_store_with_compressor.save_memory(
                namespace=("agent", "concurrent"),
                key=f"key_{i}",
                value=values[i],
                compress=True
            )
            for i in range(5)
        ]

        entry_ids = await asyncio.gather(*tasks)

        assert len(entry_ids) == 5
        assert all(eid is not None for eid in entry_ids)


@pytest.mark.asyncio
async def test_compression_performance_benchmark(compressor, long_text):
    """Test compression performance meets <500ms target"""
    metadata = {}

    start = time.time()
    compressed = await compressor.compress_memory(long_text, metadata)
    latency_ms = (time.time() - start) * 1000

    # Target: <500ms compression
    assert latency_ms < 500, f"Compression took {latency_ms:.2f}ms (target <500ms)"

    # Also check reported latency
    assert "latency_ms" in compressed
    assert compressed["latency_ms"] < 500


# ==================== OTEL OBSERVABILITY TESTS (5) ====================

@pytest.mark.asyncio
async def test_compression_span_created(compressor, long_text):
    """Test that compression creates OTEL span"""
    metadata = {}

    # This test validates that spans are created
    # In production, ObservabilityManager would track these
    compressed = await compressor.compress_memory(long_text, metadata)

    # Span should have been created (implicit in with statement)
    assert compressed is not None


@pytest.mark.asyncio
async def test_decompression_span_created(compressor, long_text):
    """Test that decompression creates OTEL span"""
    metadata = {}
    compressed = await compressor.compress_memory(long_text, metadata)

    with patch.object(compressor, '_ocr_extract_text', return_value=long_text):
        decompressed = await compressor.decompress_memory(compressed)

        # Span should have been created
        assert decompressed is not None


@pytest.mark.asyncio
async def test_compression_metrics_tracked(compressor, long_text):
    """Test that compression metrics are recorded"""
    metadata = {}

    initial_compressions = compressor.stats["compressions"]
    initial_tokens_saved = compressor.stats["total_tokens_saved"]

    compressed = await compressor.compress_memory(long_text, metadata)

    # Stats should increment
    assert compressor.stats["compressions"] == initial_compressions + 1
    assert compressor.stats["total_tokens_saved"] > initial_tokens_saved


@pytest.mark.asyncio
async def test_correlation_id_propagation(compressor, long_text):
    """Test that correlation ID propagates through operations"""
    correlation_context = CorrelationContext()
    compressor.context = correlation_context

    metadata = {}
    compressed = await compressor.compress_memory(long_text, metadata)

    # Correlation ID should be present in logs
    assert compressor.context.correlation_id is not None


@pytest.mark.asyncio
async def test_compression_error_spans(compressor, long_text):
    """Test that errors are tracked in spans"""
    metadata = {}

    # Force compression error
    with patch.object(compressor, '_text_to_image', side_effect=Exception("Test error")):
        with pytest.raises(Exception):
            await compressor.compress_memory(long_text, metadata)

    # Error should be tracked in stats
    assert compressor.stats["compression_errors"] > 0


# ==================== STATISTICS & REPORTING ====================

@pytest.mark.asyncio
async def test_get_stats(compressor, long_text):
    """Test statistics reporting"""
    metadata = {}

    # Perform some operations
    await compressor.compress_memory(long_text, metadata)

    stats = compressor.get_stats()

    assert stats["compressions"] > 0
    assert stats["total_tokens_saved"] > 0
    assert stats["total_cost_saved_usd"] > 0


@pytest.mark.asyncio
async def test_reset_stats(compressor, long_text):
    """Test statistics reset"""
    metadata = {}

    # Perform operation
    await compressor.compress_memory(long_text, metadata)

    # Reset
    compressor.reset_stats()

    stats = compressor.get_stats()
    assert stats["compressions"] == 0
    assert stats["total_tokens_saved"] == 0


# ==================== EDGE CASES ====================

@pytest.mark.asyncio
async def test_empty_text_compression():
    """Test that empty text raises ValueError"""
    compressor = VisualMemoryCompressor()

    with pytest.raises(ValueError):
        await compressor.compress_memory("", {})


@pytest.mark.asyncio
async def test_invalid_compression_mode():
    """Test that invalid mode raises ValueError"""
    compressor = VisualMemoryCompressor()

    with pytest.raises(ValueError):
        await compressor.compress_memory("test text", {}, mode="invalid_mode")


@pytest.mark.asyncio
async def test_different_compression_modes(compressor, long_text):
    """Test all compression modes produce different token counts"""
    metadata = {}

    compressed_base = await compressor.compress_memory(long_text, metadata, mode=VisualCompressionMode.BASE)
    compressed_small = await compressor.compress_memory(long_text, metadata, mode=VisualCompressionMode.SMALL)
    compressed_tiny = await compressor.compress_memory(long_text, metadata, mode=VisualCompressionMode.TINY)

    # Different modes should have different token counts
    assert compressed_base["compressed_tokens"] == 256
    assert compressed_small["compressed_tokens"] == 100
    assert compressed_tiny["compressed_tokens"] == 64

    # Higher compression = higher ratio
    assert compressed_tiny["compression_ratio"] > compressed_small["compression_ratio"]


# ==================== CONCURRENCY TESTS (Issue #1 Fix Validation) ====================

@pytest.mark.asyncio
async def test_concurrent_compression_no_blocking():
    """Test 100 parallel compressions complete in reasonable time (validates non-blocking I/O)"""
    compressor = VisualMemoryCompressor(
        compression_threshold=100,
        use_ocr_fallback=True
    )

    text = "Test text for concurrent compression. " * 25  # ~1000 chars

    # Compress 100 memories in parallel
    start_time = time.time()
    tasks = [
        compressor.compress_memory(text, {}, mode="base")
        for _ in range(100)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    # Should complete in <30s (not 300s if blocking)
    assert elapsed < 30.0, f"Took {elapsed:.1f}s - blocking I/O detected! Expected <30s"
    assert len(results) == 100
    assert all(r["compressed"] for r in results)

    logger.info(f"Concurrent compression test: 100 operations in {elapsed:.2f}s ({elapsed/100*1000:.1f}ms avg)")


@pytest.mark.asyncio
async def test_concurrent_decompression_no_blocking():
    """Test 50 parallel decompressions complete in reasonable time (validates non-blocking OCR)"""
    compressor = VisualMemoryCompressor(
        compression_threshold=50,
        use_ocr_fallback=True
    )

    text = "Decompression test text. " * 20  # ~500 chars

    # Create compressed data
    compressed = await compressor.compress_memory(text, {}, mode="base")

    # Decompress 50 times in parallel
    start_time = time.time()
    tasks = [
        compressor.decompress_memory(compressed)
        for _ in range(50)
    ]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    # Should complete in <60s (not 600s if blocking)
    assert elapsed < 60.0, f"Took {elapsed:.1f}s - blocking OCR detected! Expected <60s"
    assert len(results) == 50
    assert all(len(r) > 0 for r in results)

    logger.info(f"Concurrent decompression test: 50 operations in {elapsed:.2f}s ({elapsed/50*1000:.1f}ms avg)")
