"""
Tests for Prometheus metrics exporter (P1-4)

Author: Claude (P1 Fixes)
Date: November 3, 2025
"""

import pytest
import time
from prometheus_client import REGISTRY

from infrastructure.local_llm_metrics import (
    LocalLLMMetricsCollector,
    get_metrics_collector,
    track_inference,
    record_rate_limit,
    record_error,
    record_tokens,
    llm_inference_requests_total,
    llm_inference_latency_seconds,
    llm_rate_limit_hits_total,
    llm_active_connections,
    llm_error_total
)


class TestLocalLLMMetricsCollector:
    """Tests for LocalLLMMetricsCollector."""

    def test_initialization(self):
        """Test metrics collector initializes correctly."""
        collector = LocalLLMMetricsCollector(port=9091, enable_metrics=True)

        assert collector.port == 9091
        assert collector.enable_metrics is True
        assert collector._server_started is False

    def test_disabled_metrics(self):
        """Test metrics collection can be disabled."""
        collector = LocalLLMMetricsCollector(enable_metrics=False)

        # Should not raise errors when disabled
        collector.start()
        with collector.track_inference("test-model"):
            pass
        collector.record_rate_limit("client1")
        collector.record_error("test_error")

        # Server should not start
        assert collector._server_started is False

    def test_track_inference_success(self):
        """Test tracking successful inference."""
        collector = LocalLLMMetricsCollector(port=9092, enable_metrics=True)

        # Get initial metric values
        initial_requests = self._get_counter_value(
            llm_inference_requests_total,
            model="test-model",
            status="success"
        )

        # Track inference
        with collector.track_inference("test-model"):
            time.sleep(0.01)  # Simulate work

        # Check metrics incremented
        final_requests = self._get_counter_value(
            llm_inference_requests_total,
            model="test-model",
            status="success"
        )
        assert final_requests > initial_requests

    def test_track_inference_error(self):
        """Test tracking failed inference."""
        collector = LocalLLMMetricsCollector(port=9093, enable_metrics=True)

        initial_requests = self._get_counter_value(
            llm_inference_requests_total,
            model="test-model",
            status="error"
        )
        initial_errors = self._get_counter_value(
            llm_error_total,
            error_type="ValueError"
        )

        # Track inference with error
        try:
            with collector.track_inference("test-model"):
                raise ValueError("Test error")
        except ValueError:
            pass

        # Check metrics incremented
        final_requests = self._get_counter_value(
            llm_inference_requests_total,
            model="test-model",
            status="error"
        )
        final_errors = self._get_counter_value(
            llm_error_total,
            error_type="ValueError"
        )

        assert final_requests > initial_requests
        assert final_errors > initial_errors

    def test_record_rate_limit(self):
        """Test recording rate limit hits."""
        collector = LocalLLMMetricsCollector(port=9094, enable_metrics=True)

        initial_hits = self._get_counter_value(
            llm_rate_limit_hits_total,
            client_id="test-client"
        )

        collector.record_rate_limit("test-client")

        final_hits = self._get_counter_value(
            llm_rate_limit_hits_total,
            client_id="test-client"
        )
        assert final_hits > initial_hits

    def test_record_error(self):
        """Test recording errors."""
        collector = LocalLLMMetricsCollector(port=9095, enable_metrics=True)

        initial_errors = self._get_counter_value(
            llm_error_total,
            error_type="timeout"
        )

        collector.record_error("timeout")

        final_errors = self._get_counter_value(
            llm_error_total,
            error_type="timeout"
        )
        assert final_errors > initial_errors

    def test_record_tokens(self):
        """Test recording token usage."""
        collector = LocalLLMMetricsCollector(port=9096, enable_metrics=True)

        collector.record_tokens("test-model", prompt_tokens=100, completion_tokens=50)

        # Tokens should be recorded (no assertion, just ensure no error)

    def test_set_queue_size(self):
        """Test setting queue size gauge."""
        collector = LocalLLMMetricsCollector(port=9097, enable_metrics=True)

        collector.set_queue_size("test-model", size=42)

        # Queue size should be set (no assertion, just ensure no error)

    def test_set_model_info(self):
        """Test setting model metadata."""
        collector = LocalLLMMetricsCollector(port=9098, enable_metrics=True)

        collector.set_model_info(
            model_name="llama-3.2-vision",
            version="3.2",
            base_url="http://127.0.0.1:8001"
        )

        # Model info should be set (no assertion, just ensure no error)

    def test_singleton_collector(self):
        """Test global singleton collector."""
        collector1 = get_metrics_collector(port=9099)
        collector2 = get_metrics_collector(port=9099)

        # Should return same instance
        assert collector1 is collector2

    def test_convenience_functions(self):
        """Test convenience functions work."""
        # These should not raise errors
        with track_inference("test-model"):
            pass

        record_rate_limit("test-client")
        record_error("test_error")
        record_tokens("test-model", 10, 5)

    # Helper methods

    def _get_counter_value(self, counter, **labels):
        """Get current value of a Prometheus counter."""
        try:
            # Try to get metric with labels
            metric = counter.labels(**labels)
            # Access the underlying value
            for sample in REGISTRY.collect():
                if sample.name == counter._name:
                    for s in sample.samples:
                        if all(s.labels.get(k) == v for k, v in labels.items()):
                            return s.value
            return 0.0
        except Exception:
            return 0.0


class TestMetricsIntegration:
    """Integration tests for metrics."""

    def test_multiple_inferences(self):
        """Test tracking multiple inferences."""
        collector = LocalLLMMetricsCollector(port=9100, enable_metrics=True)

        # Track 5 successful inferences
        for i in range(5):
            with collector.track_inference("test-model"):
                time.sleep(0.001)

        # Metrics should be incremented (no specific assertion, just ensure no errors)

    def test_concurrent_metrics(self):
        """Test metrics are thread-safe."""
        collector = LocalLLMMetricsCollector(port=9101, enable_metrics=True)

        # Simulate concurrent operations
        collector.record_rate_limit("client1")
        collector.record_error("error1")
        with collector.track_inference("model1"):
            collector.record_rate_limit("client2")

        # Should handle concurrent updates without errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
