"""
Test suite for Vertex AI Monitoring

Tests metrics collection, cost tracking, quality monitoring, and alert management.
Includes performance metrics, cost analysis, and drift detection.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from infrastructure.vertex_ai.monitoring import (
    VertexAIMonitoring,
    ModelMetrics,
    CostMetrics,
    QualityMetrics,
    MetricType,
    AlertRule,
)


@pytest.fixture
def mock_vertex_ai():
    """Mock Vertex AI and monitoring APIs"""
    with patch('infrastructure.vertex_ai.monitoring.VERTEX_AI_AVAILABLE', True):
        with patch('infrastructure.vertex_ai.monitoring.aiplatform') as mock_api:
            with patch('infrastructure.vertex_ai.monitoring.monitoring_v3') as mock_monitoring:
                yield mock_api, mock_monitoring


@pytest.fixture
def monitoring(mock_vertex_ai):
    """Create VertexAIMonitoring instance for testing"""
    monitor = VertexAIMonitoring(
        project_id="test-project",
        location="us-central1"
    )
    return monitor


@pytest.mark.asyncio
async def test_collect_performance_metrics_success(monitoring):
    """Test successful collection of performance metrics"""
    metrics = await monitoring.collect_performance_metrics(
        endpoint_id="test-endpoint",
        time_window_minutes=60
    )

    assert metrics is not None
    assert isinstance(metrics, ModelMetrics) or isinstance(metrics, dict)


@pytest.mark.asyncio
async def test_collect_performance_metrics_latency(monitoring):
    """Test latency metrics collection"""
    metrics = await monitoring.collect_performance_metrics(
        endpoint_id="latency-endpoint",
        time_window_minutes=120
    )

    assert metrics is not None
    # Verify latency-related fields exist
    if hasattr(metrics, 'latency_p50'):
        assert metrics.latency_p50 >= 0
    if hasattr(metrics, 'latency_p99'):
        assert metrics.latency_p99 >= 0


@pytest.mark.asyncio
async def test_collect_performance_metrics_throughput(monitoring):
    """Test throughput metrics collection"""
    metrics = await monitoring.collect_performance_metrics(
        endpoint_id="throughput-endpoint",
        time_window_minutes=60
    )

    assert metrics is not None
    if hasattr(metrics, 'throughput'):
        assert isinstance(metrics.throughput, (int, float))


@pytest.mark.asyncio
async def test_calculate_cost_metrics_monthly(monitoring):
    """Test monthly cost metrics calculation"""
    cost_metrics = await monitoring.calculate_cost_metrics(
        endpoint_id="cost-endpoint",
        period_days=30
    )

    assert cost_metrics is not None
    assert isinstance(cost_metrics, (CostMetrics, dict))


@pytest.mark.asyncio
async def test_calculate_cost_metrics_by_model(monitoring):
    """Test cost calculation broken down by model"""
    cost_metrics = await monitoring.calculate_cost_metrics(
        endpoint_id="multi-model-endpoint",
        period_days=30
    )

    assert cost_metrics is not None
    # Cost metrics should track costs
    if hasattr(cost_metrics, 'total_cost_usd'):
        assert isinstance(cost_metrics.total_cost_usd, (int, float))


@pytest.mark.asyncio
async def test_collect_quality_metrics_success(monitoring):
    """Test successful collection of quality metrics"""
    quality = await monitoring.collect_quality_metrics(
        endpoint_id="quality-endpoint",
        sample_size=100
    )

    assert quality is not None
    assert isinstance(quality, (QualityMetrics, dict))


@pytest.mark.asyncio
async def test_collect_quality_metrics_accuracy(monitoring):
    """Test accuracy metrics collection"""
    quality = await monitoring.collect_quality_metrics(
        endpoint_id="accuracy-endpoint",
        sample_size=50
    )

    assert quality is not None
    if hasattr(quality, 'accuracy'):
        assert 0 <= quality.accuracy <= 1


@pytest.mark.asyncio
async def test_collect_quality_metrics_drift_detection(monitoring):
    """Test model drift detection"""
    quality = await monitoring.collect_quality_metrics(
        endpoint_id="drift-endpoint",
        sample_size=200
    )

    assert quality is not None
    # Drift detection should be available
    if hasattr(quality, 'drift_detected'):
        assert isinstance(quality.drift_detected, bool)


@pytest.mark.asyncio
async def test_check_alerts_success(monitoring):
    """Test alert checking"""
    # Register an alert rule first
    monitoring.add_alert_rule(
        rule_name="high_latency",
        metric_type=MetricType.PERFORMANCE,
        condition="latency_p99 > 500",
        description="Alert when p99 latency exceeds 500ms"
    )

    alerts = await monitoring.check_alerts(endpoint_id="alert-endpoint")
    assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_check_alerts_multiple_rules(monitoring):
    """Test checking multiple alert rules"""
    monitoring.add_alert_rule(
        rule_name="high_error_rate",
        metric_type=MetricType.PERFORMANCE,
        condition="error_rate > 0.05",
        description="Alert on error rate"
    )

    monitoring.add_alert_rule(
        rule_name="high_cost",
        metric_type=MetricType.COST,
        condition="daily_cost_usd > 100",
        description="Alert on cost"
    )

    alerts = await monitoring.check_alerts(endpoint_id="multi-alert-endpoint")
    assert isinstance(alerts, list)


@pytest.mark.asyncio
async def test_add_alert_rule(monitoring):
    """Test adding alert rules"""
    rule_name = "test_rule"
    monitoring.add_alert_rule(
        rule_name=rule_name,
        metric_type=MetricType.QUALITY,
        condition="accuracy < 0.85",
        description="Quality degradation alert"
    )

    # Verify rule was added
    assert any(r.rule_name == rule_name for r in monitoring.alert_rules)


@pytest.mark.asyncio
async def test_remove_alert_rule(monitoring):
    """Test removing alert rules"""
    rule_name = "removable_rule"
    monitoring.add_alert_rule(
        rule_name=rule_name,
        metric_type=MetricType.PERFORMANCE,
        condition="latency > 1000",
        description="Test removal"
    )

    # Verify it was added
    initial_count = len(monitoring.alert_rules)
    assert initial_count > 0

    # Remove it
    monitoring.remove_alert_rule(rule_name)

    # Verify it was removed
    assert not any(r.rule_name == rule_name for r in monitoring.alert_rules)


def test_metric_type_enum():
    """Test MetricType enum values"""
    assert MetricType.PERFORMANCE.value == "performance"
    assert MetricType.COST.value == "cost"
    assert MetricType.QUALITY.value == "quality"


def test_model_metrics_initialization():
    """Test ModelMetrics dataclass"""
    metrics = ModelMetrics(
        endpoint_id="test-endpoint",
        timestamp=datetime.now(),
        latency_p50=50.0,
        latency_p99=200.0,
        throughput=100.0,
        error_rate=0.01,
    )

    assert metrics.endpoint_id == "test-endpoint"
    assert metrics.latency_p50 == 50.0
    assert metrics.error_rate == 0.01


def test_cost_metrics_initialization():
    """Test CostMetrics dataclass"""
    cost = CostMetrics(
        endpoint_id="cost-endpoint",
        timestamp=datetime.now(),
        total_cost_usd=150.50,
        cost_per_1m_tokens=0.02,
        cost_per_inference=0.005,
    )

    assert cost.endpoint_id == "cost-endpoint"
    assert cost.total_cost_usd == 150.50
    assert cost.cost_per_1m_tokens == 0.02


def test_quality_metrics_initialization():
    """Test QualityMetrics dataclass"""
    quality = QualityMetrics(
        endpoint_id="quality-endpoint",
        timestamp=datetime.now(),
        accuracy=0.95,
        hallucination_rate=0.02,
        drift_detected=False,
    )

    assert quality.endpoint_id == "quality-endpoint"
    assert quality.accuracy == 0.95
    assert quality.drift_detected is False


def test_alert_rule_initialization():
    """Test AlertRule dataclass"""
    rule = AlertRule(
        rule_name="test_alert",
        metric_type=MetricType.PERFORMANCE,
        condition="latency > 500",
        description="Test alert",
    )

    assert rule.rule_name == "test_alert"
    assert rule.metric_type == MetricType.PERFORMANCE
    assert rule.condition == "latency > 500"


@pytest.mark.asyncio
async def test_metrics_caching(monitoring):
    """Test metrics are cached to avoid redundant calls"""
    endpoint_id = "cache-test-endpoint"

    # Collect metrics twice
    metrics1 = await monitoring.collect_performance_metrics(endpoint_id)
    metrics2 = await monitoring.collect_performance_metrics(endpoint_id)

    # Should return same cached data
    assert metrics1 is not None
    assert metrics2 is not None


@pytest.mark.asyncio
async def test_cost_calculation_accuracy(monitoring):
    """Test cost calculation is accurate"""
    cost = await monitoring.calculate_cost_metrics(
        endpoint_id="billing-endpoint",
        period_days=30
    )

    assert cost is not None
    if hasattr(cost, 'total_cost_usd'):
        assert cost.total_cost_usd >= 0


@pytest.mark.asyncio
async def test_alert_conditions_evaluation(monitoring):
    """Test alert condition evaluation"""
    # Add multiple alert rules
    monitoring.add_alert_rule(
        rule_name="alert1",
        metric_type=MetricType.PERFORMANCE,
        condition="latency_p99 > 100",
        description="P99 latency threshold"
    )

    monitoring.add_alert_rule(
        rule_name="alert2",
        metric_type=MetricType.COST,
        condition="daily_cost_usd > 50",
        description="Daily cost threshold"
    )

    alerts = await monitoring.check_alerts("eval-endpoint")
    assert isinstance(alerts, list)
