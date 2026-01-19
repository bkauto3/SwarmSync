"""
Test Suite for SAE PII Detector
Version: 1.0
Date: October 30, 2025
Owner: Sentinel (Security Agent)
Status: Week 1 Test Stubs

Test Coverage:
- PII detection accuracy (5 categories)
- Edge cases (empty, very long, multilingual)
- Performance (latency, F1 score)
- Integration with WaltzRL
"""

import pytest
import time
from pathlib import Path
from typing import List

from infrastructure.sae_pii_detector import (
    SAEPIIDetector,
    PIISpan,
    SAEEncoderConfig,
    get_sae_pii_detector
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def detector():
    """
    Create SAE PII Detector for testing.

    Note: Week 1 stub returns detector without actual model weights.
          Week 2 will use real trained models.
    """
    return get_sae_pii_detector(
        model_path=None,  # Week 2: Use actual model path
        sae_encoder_path=None,
        classifiers_path=None,
        port=8003,
        device="cpu"
    )


@pytest.fixture
def sample_texts():
    """Sample texts with known PII for testing."""
    return {
        "personal_name": [
            "My name is John Smith",
            "Contact Dr. Jane Doe for more information",
            "Mohammed Al-Fayed will attend the meeting"
        ],
        "address": [
            "I live at 123 Main Street, New York, NY 10001",
            "Apartment 5B, 456 Oak Avenue, Los Angeles, CA 90001",
            "Visit us at 789 Elm Drive, Suite 100, Chicago, IL 60601"
        ],
        "phone": [
            "Call me at +1-555-123-4567",
            "Phone: (555) 987-6543",
            "My number is 555.111.2222"
        ],
        "email": [
            "Email me at john.smith@example.com",
            "Contact: jane_doe+tag@company.co.uk",
            "Support: support@example.org"
        ],
        "none": [
            "The weather is nice today",
            "I enjoy reading books about technology",
            "Machine learning is fascinating"
        ]
    }


# ============================================================================
# Test: Initialization
# ============================================================================

def test_detector_initialization(detector):
    """Test SAE PII Detector initializes correctly."""
    assert detector is not None
    assert detector.port == 8003
    assert detector.device == "cpu"
    assert detector.config.target_layer == 12
    assert detector.config.expansion_factor == 8
    assert detector.config.latent_dim == 32768


def test_detector_with_custom_config():
    """Test detector initialization with custom config."""
    config = SAEEncoderConfig(
        model_name="meta-llama/Llama-3.2-11B",
        target_layer=16,
        expansion_factor=16
    )
    detector = SAEPIIDetector(config=config)
    assert detector.config.target_layer == 16
    assert detector.config.expansion_factor == 16


# ============================================================================
# Test: PII Detection - Personal Names
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_personal_name_simple(detector):
    """Test detection of simple personal names."""
    text = "My name is John Smith and I work here."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "personal_name"
    assert pii_spans[0].text == "John Smith"
    assert pii_spans[0].confidence >= 0.8


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_personal_name_with_title(detector):
    """Test detection of names with titles."""
    text = "Contact Dr. Jane Doe at the office."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "personal_name"
    assert "Jane Doe" in pii_spans[0].text


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_personal_name_multiple(detector):
    """Test detection of multiple names in one text."""
    text = "John Smith and Jane Doe attended the meeting."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 2
    names = [span.text for span in pii_spans]
    assert "John Smith" in names
    assert "Jane Doe" in names


# ============================================================================
# Test: PII Detection - Addresses
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_address_full(detector):
    """Test detection of full street addresses."""
    text = "I live at 123 Main Street, New York, NY 10001."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "address"
    assert "123 Main Street" in pii_spans[0].text


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_address_with_unit(detector):
    """Test detection of addresses with apartment/suite numbers."""
    text = "My address is Apartment 5B, 456 Oak Avenue, Los Angeles."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "address"


# ============================================================================
# Test: PII Detection - Phone Numbers
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_phone_international(detector):
    """Test detection of international phone format."""
    text = "Call me at +1-555-123-4567 tomorrow."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "phone"
    assert "+1-555-123-4567" in pii_spans[0].text


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_phone_us_format(detector):
    """Test detection of US phone format."""
    text = "Phone: (555) 987-6543"
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "phone"


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_phone_dots(detector):
    """Test detection of phone with dots."""
    text = "My number is 555.111.2222"
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "phone"


# ============================================================================
# Test: PII Detection - Emails
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_email_simple(detector):
    """Test detection of simple email addresses."""
    text = "Email me at john.smith@example.com for details."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "email"
    assert pii_spans[0].text == "john.smith@example.com"


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_email_with_plus(detector):
    """Test detection of email with plus-addressing."""
    text = "Contact: jane_doe+tag@company.co.uk"
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 1
    assert pii_spans[0].category == "email"


# ============================================================================
# Test: PII Detection - Safe Content (None)
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_none_weather(detector):
    """Test that safe content is not flagged as PII."""
    text = "The weather is nice today."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 0


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_none_technology(detector):
    """Test that technical content is not flagged as PII."""
    text = "Machine learning is fascinating and useful."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 0


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_detect_empty_string(detector):
    """Test detection on empty string."""
    pii_spans = detector.detect_pii("")
    assert len(pii_spans) == 0


def test_detect_whitespace_only(detector):
    """Test detection on whitespace-only string."""
    pii_spans = detector.detect_pii("   \n\t  ")
    assert len(pii_spans) == 0


def test_detect_very_long_text(detector):
    """Test detection on very long text (boundary check)."""
    long_text = "This is safe content. " * 500  # ~10K characters
    with pytest.raises(ValueError, match="Text too long"):
        detector.detect_pii(long_text)


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_mixed_pii_types(detector):
    """Test detection of multiple PII types in one text."""
    text = "Contact John Smith at john@example.com or call 555-1234."
    pii_spans = detector.detect_pii(text)

    assert len(pii_spans) == 3
    categories = {span.category for span in pii_spans}
    assert "personal_name" in categories
    assert "email" in categories
    assert "phone" in categories


# ============================================================================
# Test: Multilingual Support
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_pii_japanese(detector):
    """Test PII detection in Japanese text."""
    text = "私の名前は山田太郎です。メール: yamada@example.jp"
    pii_spans = detector.detect_pii(text, language="ja")

    assert len(pii_spans) >= 1
    # Should detect email at minimum


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_pii_spanish(detector):
    """Test PII detection in Spanish text."""
    text = "Mi nombre es Juan García. Email: juan@ejemplo.es"
    pii_spans = detector.detect_pii(text, language="es")

    assert len(pii_spans) >= 1


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_pii_french(detector):
    """Test PII detection in French text."""
    text = "Je m'appelle Marie Dupont. Email: marie@exemple.fr"
    pii_spans = detector.detect_pii(text, language="fr")

    assert len(pii_spans) >= 1


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_detect_pii_german(detector):
    """Test PII detection in German text."""
    text = "Ich heiße Hans Müller. E-Mail: hans@beispiel.de"
    pii_spans = detector.detect_pii(text, language="de")

    assert len(pii_spans) >= 1


# ============================================================================
# Test: Redaction
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_redact_pii_single(detector):
    """Test redaction of single PII span."""
    text = "My name is John Smith"
    redacted = detector.redact_pii(text)

    assert "John Smith" not in redacted
    assert "[REDACTED]" in redacted


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_redact_pii_multiple(detector):
    """Test redaction of multiple PII spans."""
    text = "Contact John Smith at john@example.com or 555-1234"
    redacted = detector.redact_pii(text)

    assert "John Smith" not in redacted
    assert "john@example.com" not in redacted
    assert "555-1234" not in redacted
    assert redacted.count("[REDACTED]") == 3


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_redact_pii_custom_replacement(detector):
    """Test redaction with custom replacement string."""
    text = "Email: john@example.com"
    redacted = detector.redact_pii(text, replacement="***")

    assert "john@example.com" not in redacted
    assert "***" in redacted


# ============================================================================
# Test: Performance
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_performance_latency_target(detector):
    """Test that PII detection meets <100ms latency target."""
    text = "Contact John Smith at john@example.com or call 555-1234."

    start_time = time.time()
    pii_spans = detector.detect_pii(text)
    latency_ms = (time.time() - start_time) * 1000

    assert latency_ms < 100.0, f"Latency {latency_ms:.1f}ms exceeds 100ms target"


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_performance_f1_score(detector):
    """
    Test that PII detection achieves ≥96% F1 score.

    Note: Requires labeled test dataset with ground truth PII annotations.
          Week 3: Run on 1000+ annotated examples.
    """
    # Week 3 TODO: Load labeled test dataset
    # test_data = load_labeled_test_data("data/pii_test_set.json")

    # Calculate precision, recall, F1
    # true_positives = 0
    # false_positives = 0
    # false_negatives = 0

    # for example in test_data:
    #     predicted = detector.detect_pii(example.text)
    #     ground_truth = example.pii_spans
    #     # Compare predicted vs ground_truth...

    # precision = true_positives / (true_positives + false_positives)
    # recall = true_positives / (true_positives + false_negatives)
    # f1_score = 2 * (precision * recall) / (precision + recall)

    # assert f1_score >= 0.96, f"F1 score {f1_score:.2%} below 96% target"
    pass


# ============================================================================
# Test: Integration with WaltzRL
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_waltzrl_integration_feedback_agent(detector):
    """Test integration with WaltzRL Feedback Agent."""
    from infrastructure.safety.waltzrl_feedback_agent import WaltzRLFeedbackAgent

    feedback_agent = WaltzRLFeedbackAgent()
    # TODO: Add SAE detector to feedback agent
    # feedback_agent.sae_detector = detector

    query = "What is your address?"
    response = "I live at 123 Main Street, New York, NY 10001."

    feedback = feedback_agent.analyze_response(query, response)

    # Should detect privacy violation
    assert feedback.safety_score < 1.0
    privacy_issues = [
        issue for issue in feedback.issues_found
        if issue.category.value == "privacy_violation"
    ]
    assert len(privacy_issues) > 0


# ============================================================================
# Test: Metrics & Monitoring
# ============================================================================

def test_get_metrics_initial(detector):
    """Test that metrics are initialized correctly."""
    metrics = detector.get_metrics()

    assert metrics["total_requests"] == 0
    assert metrics["total_pii_detected"] == 0
    assert metrics["avg_latency_ms"] == 0.0
    assert metrics["device"] == "cpu"
    assert metrics["port"] == 8003


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_get_metrics_after_detection(detector):
    """Test that metrics update after detection requests."""
    text = "Contact John Smith at john@example.com"

    detector.detect_pii(text)
    detector.detect_pii(text)

    metrics = detector.get_metrics()
    assert metrics["total_requests"] == 2
    assert metrics["total_pii_detected"] > 0
    assert metrics["avg_latency_ms"] > 0


# ============================================================================
# Test: Configuration
# ============================================================================

def test_sae_encoder_config_defaults():
    """Test SAE encoder config defaults."""
    config = SAEEncoderConfig()

    assert config.model_name == "meta-llama/Llama-3.2-8B"
    assert config.target_layer == 12
    assert config.expansion_factor == 8
    assert config.hidden_dim == 4096
    assert config.latent_dim == 32768
    assert config.sparsity_k == 64


def test_sae_encoder_config_custom():
    """Test SAE encoder config with custom values."""
    config = SAEEncoderConfig(
        model_name="google/gemma-2b",
        target_layer=9,
        expansion_factor=16,
        hidden_dim=2048
    )

    assert config.model_name == "google/gemma-2b"
    assert config.target_layer == 9
    assert config.expansion_factor == 16
    assert config.latent_dim == 16 * 2048  # Auto-calculated


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_detect_pii_text_too_long(detector):
    """Test error handling for text exceeding max length."""
    very_long_text = "a" * 10_001

    with pytest.raises(ValueError, match="Text too long"):
        detector.detect_pii(very_long_text)


def test_detect_pii_empty_text(detector):
    """Test detection on empty text returns empty list."""
    pii_spans = detector.detect_pii("")
    assert len(pii_spans) == 0


# ============================================================================
# Test: Chunking Strategy
# ============================================================================

@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_tokenize_and_chunk_basic(detector):
    """Test basic tokenization and chunking."""
    text = "This is a test. " * 50  # ~600 chars

    chunks = detector.tokenize_and_chunk(text, max_tokens=128, overlap=32)

    assert len(chunks) > 1  # Should split into multiple chunks
    for token_ids, start_char, end_char in chunks:
        assert len(token_ids) <= 128
        assert start_char < end_char


@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_tokenize_and_chunk_overlap(detector):
    """Test that chunks have proper overlap."""
    text = "The quick brown fox jumps over the lazy dog. " * 20

    chunks = detector.tokenize_and_chunk(text, max_tokens=64, overlap=16)

    # Check that consecutive chunks overlap
    for i in range(len(chunks) - 1):
        _, _, end1 = chunks[i]
        _, start2, _ = chunks[i + 1]
        # Should have some overlap
        assert start2 < end1


# ============================================================================
# Benchmark Tests (Performance)
# ============================================================================

@pytest.mark.benchmark
@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_benchmark_detect_pii_100_requests(detector):
    """Benchmark: Process 100 PII detection requests."""
    texts = [
        "Contact John Smith at john@example.com",
        "Call me at 555-1234",
        "I live at 123 Main St, New York"
    ] * 34  # 102 total

    start_time = time.time()
    for text in texts[:100]:
        detector.detect_pii(text)
    elapsed = time.time() - start_time

    avg_latency_ms = (elapsed / 100) * 1000
    print(f"\nAverage latency: {avg_latency_ms:.1f}ms per request")
    assert avg_latency_ms < 100.0


@pytest.mark.benchmark
@pytest.mark.skip(reason="Week 1 stub - implement in Week 2")
def test_benchmark_f1_score_1000_examples(detector):
    """Benchmark: Evaluate F1 score on 1000 labeled examples."""
    # Week 3 TODO: Load 1000+ labeled test examples
    # Measure precision, recall, F1 score
    pass
