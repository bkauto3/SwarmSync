"""
Tests for Observability Infrastructure (Phase 3.2)

Validates:
- OpenTelemetry span creation and propagation
- Correlation ID tracking across layers
- Metric collection and aggregation
- Structured logging
- Context propagation (parent → child spans)
- Timed operations
- Error span marking
"""

import asyncio
import pytest
import time
from typing import Dict, Any
from infrastructure.observability import (
    ObservabilityManager,
    CorrelationContext,
    MetricSnapshot,
    SpanType,
    get_observability_manager,
    traced_operation,
    log_structured
)


class TestCorrelationContext:
    """Test correlation context creation and propagation"""

    def test_correlation_context_creation(self):
        """Test creating correlation context with auto-generated ID"""
        ctx = CorrelationContext(user_request="Test request")

        assert ctx.correlation_id is not None
        assert len(ctx.correlation_id) > 0
        assert ctx.user_request == "Test request"
        assert ctx.timestamp is not None

    def test_correlation_context_unique_ids(self):
        """Test that each context gets unique correlation ID"""
        ctx1 = CorrelationContext(user_request="Request 1")
        ctx2 = CorrelationContext(user_request="Request 2")

        assert ctx1.correlation_id != ctx2.correlation_id

    def test_correlation_context_to_dict(self):
        """Test serializing context to dictionary"""
        ctx = CorrelationContext(
            user_request="Test request",
            parent_span_id="parent_123"
        )

        ctx_dict = ctx.to_dict()

        assert "correlation_id" in ctx_dict
        assert ctx_dict["user_request"] == "Test request"
        assert ctx_dict["parent_span_id"] == "parent_123"
        assert "timestamp" in ctx_dict


class TestMetricSnapshot:
    """Test metric snapshot creation and serialization"""

    def test_metric_snapshot_creation(self):
        """Test creating metric snapshot"""
        metric = MetricSnapshot(
            metric_name="htdag.decomposition.duration",
            value=1.23,
            unit="seconds",
            labels={"agent": "htdag_planner"}
        )

        assert metric.metric_name == "htdag.decomposition.duration"
        assert metric.value == 1.23
        assert metric.unit == "seconds"
        assert metric.labels["agent"] == "htdag_planner"
        assert metric.timestamp is not None

    def test_metric_snapshot_json_serialization(self):
        """Test JSON serialization of metric snapshot"""
        metric = MetricSnapshot(
            metric_name="test.metric",
            value=42.0,
            unit="count"
        )

        json_str = metric.to_json()

        assert "metric_name" in json_str
        assert "test.metric" in json_str
        assert "42" in json_str
        assert "count" in json_str


class TestObservabilityManager:
    """Test observability manager functionality"""

    def setup_method(self):
        """Create fresh observability manager for each test"""
        self.obs_manager = ObservabilityManager()

    def test_manager_initialization(self):
        """Test manager initializes correctly"""
        assert self.obs_manager.tracer is not None
        assert len(self.obs_manager.active_spans) == 0
        assert len(self.obs_manager.metrics) == 0

    def test_create_correlation_context(self):
        """Test creating correlation context via manager"""
        ctx = self.obs_manager.create_correlation_context("Build SaaS app")

        assert ctx.correlation_id is not None
        assert ctx.user_request == "Build SaaS app"

    def test_span_creation_basic(self):
        """Test basic span creation"""
        ctx = CorrelationContext(user_request="Test")

        with self.obs_manager.span("test.operation", SpanType.HTDAG, ctx) as span:
            assert span is not None
            # Span should be active during context
            pass

        # Span should be cleaned up after context
        # (active_spans dict should be empty)
        assert len(self.obs_manager.active_spans) == 0

    def test_span_with_attributes(self):
        """Test span with custom attributes"""
        ctx = CorrelationContext(user_request="Test")

        with self.obs_manager.span(
            "test.operation",
            SpanType.HTDAG,
            ctx,
            attributes={"task_count": 5, "agent": "test_agent"}
        ) as span:
            # Attributes are set on span (we can't directly assert them,
            # but the span object exists)
            assert span is not None

    def test_span_error_handling(self):
        """Test span marks errors correctly"""
        ctx = CorrelationContext(user_request="Test")

        with pytest.raises(ValueError):
            with self.obs_manager.span("test.error", SpanType.HTDAG, ctx) as span:
                # Span should mark error and re-raise
                raise ValueError("Test error")

        # Span should still be cleaned up
        assert len(self.obs_manager.active_spans) == 0

    def test_record_metric(self):
        """Test recording metrics"""
        self.obs_manager.record_metric(
            metric_name="htdag.task_count",
            value=10.0,
            unit="count",
            labels={"phase": "decomposition"}
        )

        assert len(self.obs_manager.metrics) == 1
        metric = self.obs_manager.metrics[0]
        assert metric.metric_name == "htdag.task_count"
        assert metric.value == 10.0
        assert metric.unit == "count"
        assert metric.labels["phase"] == "decomposition"

    def test_record_multiple_metrics(self):
        """Test recording multiple metrics"""
        for i in range(5):
            self.obs_manager.record_metric(
                metric_name=f"test.metric_{i}",
                value=float(i),
                unit="count"
            )

        assert len(self.obs_manager.metrics) == 5

    def test_get_metrics_summary_empty(self):
        """Test metrics summary with no metrics"""
        summary = self.obs_manager.get_metrics_summary()

        assert summary["total_metrics"] == 0

    def test_get_metrics_summary(self):
        """Test metrics summary with recorded metrics"""
        # Record same metric multiple times
        self.obs_manager.record_metric("test.duration", 1.0, "seconds")
        self.obs_manager.record_metric("test.duration", 2.0, "seconds")
        self.obs_manager.record_metric("test.duration", 3.0, "seconds")

        # Record different metric
        self.obs_manager.record_metric("test.count", 10.0, "count")

        summary = self.obs_manager.get_metrics_summary()

        assert summary["total_metrics"] == 4
        assert summary["unique_metrics"] == 2

        # Check aggregation for test.duration
        duration_stats = summary["by_metric"]["test.duration"]
        assert duration_stats["count"] == 3
        assert duration_stats["min"] == 1.0
        assert duration_stats["max"] == 3.0
        assert duration_stats["avg"] == 2.0
        assert duration_stats["sum"] == 6.0

        # Check aggregation for test.count
        count_stats = summary["by_metric"]["test.count"]
        assert count_stats["count"] == 1
        assert count_stats["min"] == 10.0


class TestTimedOperation:
    """Test timed operation context manager"""

    def setup_method(self):
        """Create fresh observability manager"""
        self.obs_manager = ObservabilityManager()

    def test_timed_operation_records_duration(self):
        """Test that timed operation records duration metric"""
        ctx = CorrelationContext(user_request="Test")

        with self.obs_manager.timed_operation("test.operation", SpanType.HTDAG, ctx):
            time.sleep(0.01)  # Simulate work

        # Check metric was recorded
        assert len(self.obs_manager.metrics) == 1
        metric = self.obs_manager.metrics[0]
        assert metric.metric_name == "test.operation.duration"
        assert metric.value >= 0.01  # At least 10ms
        assert metric.unit == "seconds"

    def test_timed_operation_with_error(self):
        """Test timed operation records duration even on error"""
        ctx = CorrelationContext(user_request="Test")

        with pytest.raises(RuntimeError):
            with self.obs_manager.timed_operation("test.error", SpanType.HTDAG, ctx):
                raise RuntimeError("Test error")

        # Metric should still be recorded
        assert len(self.obs_manager.metrics) == 1
        assert self.obs_manager.metrics[0].metric_name == "test.error.duration"


class TestGlobalObservabilityManager:
    """Test global observability manager singleton"""

    def test_get_observability_manager_singleton(self):
        """Test that get_observability_manager returns same instance"""
        manager1 = get_observability_manager()
        manager2 = get_observability_manager()

        assert manager1 is manager2

    def test_global_manager_isolated_from_local(self):
        """Test global manager is separate from local instances"""
        global_manager = get_observability_manager()
        local_manager = ObservabilityManager()

        # Record metric in global manager
        global_manager.record_metric("global.test", 1.0, "count")

        # Local manager should have no metrics
        assert len(local_manager.metrics) == 0


class TestTracedOperationDecorator:
    """Test @traced_operation decorator"""

    def setup_method(self):
        """Reset global manager for each test"""
        global_manager = get_observability_manager()
        global_manager.metrics = []
        global_manager.active_spans = {}

    @pytest.mark.asyncio
    async def test_traced_async_function(self):
        """Test tracing async functions"""

        @traced_operation("test.async_op", SpanType.HTDAG)
        async def async_task(value: int, context: CorrelationContext):
            await asyncio.sleep(0.01)
            return value * 2

        ctx = CorrelationContext(user_request="Test")
        result = await async_task(5, context=ctx)

        assert result == 10
        # Span should be created and closed (hard to assert directly)

    def test_traced_sync_function(self):
        """Test tracing synchronous functions"""

        @traced_operation("test.sync_op", SpanType.HALO)
        def sync_task(value: int, context: CorrelationContext):
            return value * 3

        ctx = CorrelationContext(user_request="Test")
        result = sync_task(7, context=ctx)

        assert result == 21

    @pytest.mark.asyncio
    async def test_traced_function_with_error(self):
        """Test traced function propagates errors"""

        @traced_operation("test.error_op", SpanType.AOP)
        async def failing_task(context: CorrelationContext):
            raise ValueError("Intentional error")

        ctx = CorrelationContext(user_request="Test")

        with pytest.raises(ValueError, match="Intentional error"):
            await failing_task(context=ctx)


class TestStructuredLogging:
    """Test structured logging utility"""

    def test_log_structured_basic(self):
        """Test basic structured logging (no exceptions expected)"""
        # This just ensures the function doesn't crash
        log_structured("Test message", correlation_id="test_123", task_count=5)

    def test_log_structured_with_nested_data(self):
        """Test structured logging with nested data structures"""
        log_structured(
            "Complex log entry",
            user="test_user",
            metadata={"key": "value", "count": 42}
        )


class TestEndToEndScenario:
    """Test end-to-end observability scenarios"""

    def setup_method(self):
        """Create fresh manager"""
        self.obs_manager = ObservabilityManager()

    @pytest.mark.asyncio
    async def test_multi_layer_tracing(self):
        """Test tracing across multiple orchestration layers"""
        ctx = self.obs_manager.create_correlation_context("Build SaaS app")

        # Simulate HTDAG layer
        with self.obs_manager.timed_operation("htdag.decompose", SpanType.HTDAG, ctx) as span1:
            span1.set_attribute("task_count", 5)
            await asyncio.sleep(0.01)

            # Simulate HALO layer (nested)
            with self.obs_manager.timed_operation("halo.route", SpanType.HALO, ctx) as span2:
                span2.set_attribute("agent_count", 3)
                await asyncio.sleep(0.01)

                # Simulate AOP layer (nested further)
                with self.obs_manager.timed_operation("aop.validate", SpanType.AOP, ctx) as span3:
                    span3.set_attribute("validation_score", 0.95)
                    await asyncio.sleep(0.01)

        # Check metrics recorded
        assert len(self.obs_manager.metrics) == 3

        # Check metric names
        metric_names = [m.metric_name for m in self.obs_manager.metrics]
        assert "htdag.decompose.duration" in metric_names
        assert "halo.route.duration" in metric_names
        assert "aop.validate.duration" in metric_names

    @pytest.mark.asyncio
    async def test_correlation_propagation(self):
        """Test correlation ID propagates through nested operations"""
        ctx = self.obs_manager.create_correlation_context("Test request")

        correlation_ids_seen = []

        # Layer 1
        with self.obs_manager.span("layer1", SpanType.ORCHESTRATION, ctx) as span1:
            correlation_ids_seen.append(ctx.correlation_id)

            # Layer 2
            with self.obs_manager.span("layer2", SpanType.HTDAG, ctx) as span2:
                correlation_ids_seen.append(ctx.correlation_id)

                # Layer 3
                with self.obs_manager.span("layer3", SpanType.HALO, ctx) as span3:
                    correlation_ids_seen.append(ctx.correlation_id)

        # All layers should see same correlation ID
        assert len(set(correlation_ids_seen)) == 1
        assert correlation_ids_seen[0] == ctx.correlation_id

    def test_metrics_aggregation_workflow(self):
        """Test realistic metrics aggregation scenario"""
        # Simulate 10 decomposition operations
        for i in range(10):
            self.obs_manager.record_metric(
                "htdag.decomposition.duration",
                value=0.1 + (i * 0.05),  # Increasing durations
                unit="seconds"
            )

            self.obs_manager.record_metric(
                "htdag.task_count",
                value=float(3 + i),  # Increasing task counts
                unit="count"
            )

        summary = self.obs_manager.get_metrics_summary()

        assert summary["total_metrics"] == 20
        assert summary["unique_metrics"] == 2

        # Check duration stats
        duration_stats = summary["by_metric"]["htdag.decomposition.duration"]
        assert duration_stats["count"] == 10
        assert duration_stats["min"] == 0.1
        assert duration_stats["max"] == 0.55
        assert 0.3 < duration_stats["avg"] < 0.35  # Approximate average

        # Check task count stats
        task_stats = summary["by_metric"]["htdag.task_count"]
        assert task_stats["count"] == 10
        assert task_stats["min"] == 3.0
        assert task_stats["max"] == 12.0


# Integration smoke tests

def test_observability_imports():
    """Test that all observability exports are available"""
    from infrastructure.observability import (
        ObservabilityManager,
        CorrelationContext,
        MetricSnapshot,
        SpanType,
        get_observability_manager,
        traced_operation,
        log_structured
    )

    # All imports should succeed
    assert ObservabilityManager is not None
    assert CorrelationContext is not None
    assert MetricSnapshot is not None
    assert SpanType is not None
    assert get_observability_manager is not None
    assert traced_operation is not None
    assert log_structured is not None


def test_span_types_enum():
    """Test SpanType enum values"""
    assert SpanType.ORCHESTRATION.value == "orchestration"
    assert SpanType.HTDAG.value == "htdag"
    assert SpanType.HALO.value == "halo"
    assert SpanType.AOP.value == "aop"
    assert SpanType.EXECUTION.value == "execution"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
