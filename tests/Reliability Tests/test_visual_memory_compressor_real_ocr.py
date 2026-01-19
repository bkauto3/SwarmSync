"""
Real OCR End-to-End Tests - Visual Memory Compression

Tests real Tesseract OCR without mocking to validate production viability.
All tests use real PIL image generation and real Tesseract OCR extraction.

Critical Validation:
- OCR accuracy >80% across all test scenarios
- Performance within acceptable bounds
- Production readiness confirmation

Author: Thon (Python expert)
Date: October 23, 2025 - Issue #3 Fix
"""

import asyncio
import pytest
import time
from difflib import SequenceMatcher

from infrastructure.visual_memory_compressor import VisualMemoryCompressor, VisualCompressionMode
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


# ==================== HELPER FUNCTIONS ====================

def _calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts using SequenceMatcher (0.0-1.0)

    Args:
        text1: Original text
        text2: OCR-extracted text

    Returns:
        Similarity ratio (1.0 = perfect match, 0.0 = no match)
    """
    # Normalize whitespace for fairer comparison
    text1_normalized = " ".join(text1.split())
    text2_normalized = " ".join(text2.split())

    return SequenceMatcher(None, text1_normalized, text2_normalized).ratio()


# ==================== REAL OCR TESTS (NO MOCKING) ====================

@pytest.mark.asyncio
async def test_real_ocr_simple_text():
    """Test real Tesseract OCR with simple clean text"""
    compressor = VisualMemoryCompressor(
        compression_threshold=50,
        use_ocr_fallback=True
    )

    original_text = "Hello World! This is a simple test with clean text."

    # Compress (text → image)
    compressed = await compressor.compress_memory(original_text, {})
    assert compressed["compressed"] is True
    assert "visual_encoding" in compressed

    # Decompress (image → text via REAL Tesseract)
    decompressed_text = await compressor.decompress_memory(compressed)

    # Calculate accuracy
    accuracy = _calculate_text_similarity(original_text, decompressed_text)

    logger.info(f"Simple text OCR accuracy: {accuracy:.2%}")
    logger.info(f"Original:     '{original_text}'")
    logger.info(f"Decompressed: '{decompressed_text}'")

    assert accuracy > 0.95, f"OCR accuracy {accuracy:.2%} too low (expected >95% for simple text)"


@pytest.mark.asyncio
async def test_real_ocr_complex_text():
    """Test real Tesseract OCR with numbers, symbols, punctuation"""
    compressor = VisualMemoryCompressor(
        compression_threshold=50,
        use_ocr_fallback=True
    )

    original_text = """
    Customer ID: 12345
    Order Total: $99.99
    Items: Product A (qty: 2), Product B (qty: 1)
    Status: SHIPPED
    Tracking: ABC-123-XYZ
    """.strip()

    compressed = await compressor.compress_memory(original_text, {})
    decompressed_text = await compressor.decompress_memory(compressed)

    # Check critical values are preserved
    assert "12345" in decompressed_text, "Customer ID lost in OCR"
    assert "99" in decompressed_text or "99.99" in decompressed_text, "Price lost in OCR"
    assert "SHIPPED" in decompressed_text, "Status lost in OCR"

    accuracy = _calculate_text_similarity(original_text, decompressed_text)

    logger.info(f"Complex text OCR accuracy: {accuracy:.2%}")

    assert accuracy > 0.90, f"OCR accuracy {accuracy:.2%} too low for complex text (expected >90%)"


@pytest.mark.asyncio
async def test_real_ocr_long_text():
    """Test real Tesseract OCR with long text (1000+ chars)"""
    compressor = VisualMemoryCompressor(
        compression_threshold=100,
        use_ocr_fallback=True
    )

    # Generate realistic long text
    original_text = """
    Memory Store Architecture Summary:

    The Genesis memory system uses a three-tier architecture:
    1. GenesisMemoryStore (unified API)
    2. MongoDB (persistent storage)
    3. Redis (fast caching layer)

    Each memory entry contains:
    - Namespace: (agent_type, agent_id)
    - Key: unique identifier
    - Value: JSON data
    - Metadata: timestamps, tags, access_count

    Performance characteristics:
    - Redis cache hit: <10ms
    - MongoDB query: 50-100ms
    - Compression ratio: 10-20x
    """.strip() * 3  # ~1500 chars

    compressed = await compressor.compress_memory(original_text, {})
    decompressed_text = await compressor.decompress_memory(compressed)

    accuracy = _calculate_text_similarity(original_text, decompressed_text)

    logger.info(f"Long text OCR accuracy: {accuracy:.2%} ({len(original_text)} chars)")

    assert accuracy > 0.85, f"OCR accuracy {accuracy:.2%} too low for long text (expected >85%)"


@pytest.mark.asyncio
async def test_real_ocr_all_compression_modes():
    """Test real OCR across all compression modes (TEXT/BASE/SMALL/TINY)"""
    text = "Test text for compression mode comparison. " * 10  # 400+ chars

    results = {}
    for mode in [VisualCompressionMode.TEXT, VisualCompressionMode.BASE,
                 VisualCompressionMode.SMALL, VisualCompressionMode.TINY]:
        compressor = VisualMemoryCompressor(
            compression_threshold=50,
            default_mode=mode,
            use_ocr_fallback=True
        )

        compressed = await compressor.compress_memory(text, {}, mode=mode)

        # Skip TEXT mode (no compression, no OCR needed)
        if mode == VisualCompressionMode.TEXT:
            results[mode] = {
                "accuracy": 1.0,  # No OCR, perfect preservation
                "compression_ratio": compressed["compression_ratio"]
            }
            continue

        decompressed = await compressor.decompress_memory(compressed)
        accuracy = _calculate_text_similarity(text, decompressed)

        results[mode] = {
            "accuracy": accuracy,
            "compression_ratio": compressed["compression_ratio"]
        }

        logger.info(f"Mode {mode}: accuracy={accuracy:.2%}, ratio={compressed['compression_ratio']:.1f}x")

    # All modes should have >80% accuracy
    for mode, metrics in results.items():
        if mode == VisualCompressionMode.TEXT:
            continue  # TEXT mode has no OCR

        assert metrics["accuracy"] > 0.80, \
            f"Mode {mode} accuracy {metrics['accuracy']:.2%} too low (expected >80%)"

    # Higher compression = potentially lower accuracy (acceptable tradeoff)
    # TINY mode might have 80-85% accuracy, BASE mode should have 90%+
    assert results[VisualCompressionMode.BASE]["accuracy"] > 0.90, \
        "BASE mode should have >90% accuracy"


@pytest.mark.asyncio
async def test_real_ocr_performance_benchmark():
    """Benchmark real OCR performance (not mocked) to validate latency targets"""
    compressor = VisualMemoryCompressor(
        compression_threshold=50,
        use_ocr_fallback=True
    )

    text = "Performance test text. " * 50  # ~1000 chars

    # Measure compression time (with real PIL)
    start = time.time()
    compressed = await compressor.compress_memory(text, {})
    compression_time = (time.time() - start) * 1000

    # Measure decompression time (with real Tesseract)
    start = time.time()
    decompressed = await compressor.decompress_memory(compressed)
    decompression_time = (time.time() - start) * 1000

    # Calculate accuracy
    accuracy = _calculate_text_similarity(text, decompressed)

    logger.info(f"Real OCR Performance:")
    logger.info(f"  Compression:   {compression_time:.1f}ms")
    logger.info(f"  Decompression: {decompression_time:.1f}ms (real Tesseract)")
    logger.info(f"  OCR Accuracy:  {accuracy:.2%}")

    # Validate targets (realistic with real OCR)
    # Tesseract is slower than the original 300ms target, so we adjust
    assert compression_time < 1000, f"Compression {compression_time:.0f}ms too slow (expected <1000ms)"
    assert decompression_time < 2000, f"Decompression {decompression_time:.0f}ms too slow (expected <2000ms with real OCR)"
    assert accuracy > 0.85, f"OCR accuracy {accuracy:.2%} too low"


@pytest.mark.asyncio
async def test_real_ocr_whitespace_preservation():
    """Test how well Tesseract preserves formatting and whitespace"""
    compressor = VisualMemoryCompressor(
        compression_threshold=50,
        use_ocr_fallback=True
    )

    original_text = """
    Line 1: First line
    Line 2: Second line
    Line 3: Third line

    Paragraph 2 after blank line.
    """.strip()

    compressed = await compressor.compress_memory(original_text, {})
    decompressed_text = await compressor.decompress_memory(compressed)

    # Check key content is preserved (exact whitespace may vary)
    assert "Line 1" in decompressed_text
    assert "Line 2" in decompressed_text
    assert "Line 3" in decompressed_text
    assert "Paragraph 2" in decompressed_text

    accuracy = _calculate_text_similarity(original_text, decompressed_text)

    logger.info(f"Whitespace preservation accuracy: {accuracy:.2%}")

    # Whitespace preservation is challenging for OCR, accept lower threshold
    assert accuracy > 0.75, f"Whitespace preservation {accuracy:.2%} too low (expected >75%)"


# ==================== SUMMARY ====================

@pytest.mark.asyncio
async def test_real_ocr_summary_report():
    """Generate summary report of real OCR performance across all test types"""

    test_scenarios = [
        ("Simple text", "Hello World! This is simple text.", 0.95),
        ("Numbers & symbols", "Order #12345 Total: $99.99", 0.90),
        ("Long text (1000+ chars)", "Architecture summary... " * 50, 0.85),
    ]

    compressor = VisualMemoryCompressor(
        compression_threshold=50,
        use_ocr_fallback=True
    )

    results = []

    for scenario_name, text, expected_accuracy in test_scenarios:
        compressed = await compressor.compress_memory(text, {})
        decompressed = await compressor.decompress_memory(compressed)
        accuracy = _calculate_text_similarity(text, decompressed)

        results.append({
            "scenario": scenario_name,
            "accuracy": accuracy,
            "expected": expected_accuracy,
            "passed": accuracy >= expected_accuracy
        })

    logger.info("\n" + "="*60)
    logger.info("REAL OCR VALIDATION SUMMARY")
    logger.info("="*60)

    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        logger.info(f"{status} {result['scenario']:30s} {result['accuracy']:.2%} (expected ≥{result['expected']:.2%})")

    logger.info("="*60)

    # All scenarios should pass
    assert all(r["passed"] for r in results), "Some OCR scenarios failed accuracy thresholds"
