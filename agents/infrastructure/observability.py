"""
OpenTelemetry Observability for Genesis Orchestration

Provides production-grade observability with:
- Distributed tracing across HTDAG, HALO, AOP layers
- Structured metrics collection (latency, success rates, costs)
- Correlation IDs for end-to-end request tracking
- Context propagation for parent-child span relationships
- Human-readable console output + machine-readable JSON logs

Integration:
- HTDAG: Decomposition time, task counts, dynamic updates
- HALO: Routing decisions, agent selections, load balancing
- AOP: Validation scores, failure reasons, quality metrics

Based on Microsoft Agent Framework observability patterns + OTEL best practices
"""

import json
import logging
import os
import random
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Set, Literal, Union

import yaml
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, Span
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    BatchSpanProcessor,
    SpanExportResult,
)
try:
    from opentelemetry.sdk._logs._internal.export import (
        ConsoleLogExporter as OtelConsoleLogExporter,
        LogExportResult,
    )
except ImportError:  # pragma: no cover - OTEL versions without log exporters
    OtelConsoleLogExporter = None
    LogExportResult = None
from opentelemetry.trace import Status, StatusCode
from infrastructure.security_utils import redact_credentials

# Initialize tracer
class SafeConsoleSpanExporter(ConsoleSpanExporter):
    """
    Console exporter that swallows teardown write errors.

    During pytest shutdown stdout/stderr may be closed before OpenTelemetry
    flushes queued spans. The default exporter then raises ValueError
    ("I/O operation on closed file"), which is harmless but noisy.  This wrapper
    catches the condition and treats the export as successful so our test logs
    stay clean without impacting production behaviour.
    """

    def export(self, spans) -> SpanExportResult:
        try:
            return super().export(spans)
        except ValueError:
            logger.debug("Console span exporter suppressed closed-IO warning")
            return SpanExportResult.SUCCESS


trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add console exporter for development visibility
console_exporter = SafeConsoleSpanExporter()
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(console_exporter)
)

logger = logging.getLogger(__name__)


if OtelConsoleLogExporter and LogExportResult:

    original_log_export = OtelConsoleLogExporter.export

    def _safe_log_export(self, data):
        try:
            return original_log_export(self, data)
        except ValueError:
            logger.debug("Console log exporter suppressed closed-IO warning")
            return LogExportResult.SUCCESS

    if not getattr(OtelConsoleLogExporter, "_genesis_patched", False):
        OtelConsoleLogExporter.export = _safe_log_export
        OtelConsoleLogExporter._genesis_patched = True  # type: ignore[attr-defined]


# Model-specific metrics (extended for fine-tuned models)
try:
    from opentelemetry import metrics
    meter = metrics.get_meter(__name__)
    
    # Model performance metrics
    model_latency = meter.create_histogram(
        "model.latency_ms",
        description="Model inference latency in milliseconds"
    )
    model_cost = meter.create_counter(
        "model.cost_usd",
        description="Model inference cost in USD"
    )
    model_errors = meter.create_counter(
        "model.errors",
        description="Model inference errors"
    )
    model_fallbacks = meter.create_counter(
        "model.fallbacks",
        description="Model fallback count (fine-tuned → baseline)"
    )
    model_requests = meter.create_counter(
        "model.requests",
        description="Total model requests"
    )
    
    MODEL_METRICS_AVAILABLE = True
except ImportError:
    MODEL_METRICS_AVAILABLE = False
    model_latency = None
    model_cost = None
    model_errors = None
    model_fallbacks = None
    model_requests = None
    logger.warning("OpenTelemetry metrics not available")


def track_model_call(
    agent_name: str,
    model_id: str,
    latency_ms: float,
    cost_usd: float = 0.0,
    error: bool = False,
    is_fallback: bool = False
):
    """
    Track model call metrics
    
    Args:
        agent_name: Name of the agent
        model_id: Model ID used
        latency_ms: Request latency in milliseconds
        cost_usd: Request cost in USD
        error: Whether request failed
        is_fallback: Whether fallback model was used
    """
    if not MODEL_METRICS_AVAILABLE:
        return
    
    labels = {
        "agent": agent_name,
        "model": model_id,
        "variant": "finetuned" if "ft:" in model_id else "baseline"
    }
    
    if model_latency:
        model_latency.record(latency_ms, labels)
    
    if model_cost:
        model_cost.add(cost_usd, labels)
    
    if model_requests:
        model_requests.add(1, labels)
    
    if error and model_errors:
        model_errors.add(1, labels)
    
    if is_fallback and model_fallbacks:
        model_fallbacks.add(1, labels)


class SpanType(Enum):
    """Span type classification for filtering"""
    ORCHESTRATION = "orchestration"  # Top-level orchestration flow
    HTDAG = "htdag"                   # Task decomposition
    HALO = "halo"                     # Agent routing
    AOP = "aop"                       # Validation
    EXECUTION = "execution"           # Agent execution
    INFRASTRUCTURE = "infrastructure" # Shared services (OCR, caching, IO)


@dataclass
class ObservabilityConfig:
    """
    Configuration for observability instrumentation (VoltAgent pattern)

    Supports span filtering, sampling, and default metric labels.
    """

    sampling_ratio: float = 1.0
    allowed_span_types: Optional[Set[SpanType]] = None
    default_metric_labels: Dict[str, str] = field(default_factory=dict)
    random_seed: Optional[int] = None

    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.allowed_span_types:
            normalized: Set[SpanType] = set()
            for span in self.allowed_span_types:
                if isinstance(span, SpanType):
                    normalized.add(span)
                elif isinstance(span, str):
                    normalized.add(SpanType(span))
                else:
                    raise ValueError(f"Unsupported span type: {span!r}")
            self.allowed_span_types = normalized
        self._rng = random.Random(self.random_seed)

    def should_trace(self, span_type: SpanType) -> bool:
        """Determine whether to record a span."""
        if self.allowed_span_types and span_type not in self.allowed_span_types:
            return False
        if self.sampling_ratio >= 1.0:
            return True
        if self.sampling_ratio <= 0:
            return False
        return self._rng.random() < self.sampling_ratio

    def merge_metric_labels(self, labels: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Merge default labels with request-specific labels."""
        merged = dict(self.default_metric_labels)
        if labels:
            merged.update(labels)
        return merged


def _parse_span_type(value: str) -> Optional[SpanType]:
    """Convert string to SpanType, accepting either enum name or value."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return SpanType(normalized.lower())
    except ValueError:
        try:
            return SpanType[normalized.upper()]
        except KeyError:
            logger.warning("Unknown span type in observability config: %s", value)
            return None


class _NullSpan:
    """No-op span used when sampling filters out instrumentation."""

    def set_attribute(self, *args, **kwargs) -> None:  # pragma: no cover - simple no-op
        return None

    def add_event(self, *args, **kwargs) -> None:  # pragma: no cover - simple no-op
        return None

    def record_exception(self, *args, **kwargs) -> None:  # pragma: no cover - simple no-op
        return None


@dataclass
class CorrelationContext:
    """
    Correlation context for end-to-end request tracking

    Propagated across all orchestration layers to trace requests from
    user input → HTDAG → HALO → AOP → execution
    """
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_request: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    parent_span_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for span attributes"""
        return asdict(self)


@dataclass
class MetricSnapshot:
    """
    Point-in-time metric snapshot for dashboards

    Captures key performance indicators for monitoring and alerting
    """
    metric_name: str
    value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    labels: Dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON for logging"""
        return json.dumps(asdict(self), indent=None)


class ObservabilityManager:
    """
    Central observability manager for Genesis orchestration

    Provides span creation, metric collection, and correlation tracking
    """

    def __init__(self, config: Optional[ObservabilityConfig] = None):
        self.tracer = tracer
        self.active_spans: Dict[str, Span] = {}
        self.metrics: List[MetricSnapshot] = []
        self.config = config or ObservabilityConfig()

    def create_correlation_context(self, user_request: str) -> CorrelationContext:
        """
        Create new correlation context for request

        Args:
            user_request: User's input request

        Returns:
            CorrelationContext with unique ID
        """
        ctx = CorrelationContext(user_request=user_request)
        # Redact credentials before logging
        safe_request = redact_credentials(user_request)
        logger.info(
            f"Created correlation context: {ctx.correlation_id}",
            extra={"correlation_id": ctx.correlation_id, "user_request": safe_request}
        )
        return ctx

    @contextmanager
    def span(
        self,
        name: str,
        span_type: SpanType,
        context: Optional[CorrelationContext] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Create traced span with context propagation

        Args:
            name: Span name (e.g., "htdag.decompose_task")
            span_type: SpanType classification
            context: Correlation context for tracking
            attributes: Additional span attributes

        Yields:
            Span object for adding events/attributes

        Example:
            ```python
            with obs_manager.span("htdag.decompose", SpanType.HTDAG, context) as span:
                span.set_attribute("task_count", len(tasks))
                result = decompose_task(request)
                span.set_attribute("subtask_count", len(result))
            ```
        """
        if not self.config.should_trace(span_type):
            yield _NullSpan()
            return

        span_attrs = {
            "span.type": span_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Add correlation context
        if context:
            span_attrs.update(context.to_dict())

        # Add custom attributes
        if attributes:
            span_attrs.update(attributes)

        # Create span
        with self.tracer.start_as_current_span(name, attributes=span_attrs) as span:
            span_id = format(span.get_span_context().span_id, '016x')

            # Store active span
            self.active_spans[span_id] = span

            # Log span start
            logger.debug(
                f"Span started: {name}",
                extra={
                    "span_id": span_id,
                    "span_type": span_type.value,
                    "correlation_id": context.correlation_id if context else None
                }
            )

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                # Mark span as error
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(
                    f"Span failed: {name}",
                    exc_info=True,
                    extra={
                        "span_id": span_id,
                        "error": str(e),
                        "correlation_id": context.correlation_id if context else None
                    }
                )
                raise
            finally:
                # Clean up
                self.active_spans.pop(span_id, None)
                logger.debug(
                    f"Span completed: {name}",
                    extra={"span_id": span_id}
                )

    def record_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Record metric snapshot

        Args:
            metric_name: Metric identifier (e.g., "htdag.decomposition.duration")
            value: Metric value
            unit: Unit of measurement (e.g., "seconds", "count", "ratio")
            labels: Optional labels for filtering (e.g., {"agent": "spec_agent"})
        """
        merged_labels = self.config.merge_metric_labels(labels)

        snapshot = MetricSnapshot(
            metric_name=metric_name,
            value=value,
            unit=unit,
            labels=merged_labels
        )

        self.metrics.append(snapshot)

        # Log metric for structured logging
        logger.info(
            f"Metric recorded: {metric_name}={value}{unit}",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                "metric_labels": merged_labels
            }
        )

    @contextmanager
    def timed_operation(
        self,
        operation_name: str,
        span_type: SpanType,
        context: Optional[CorrelationContext] = None
    ):
        """
        Measure operation duration with automatic metric recording

        Args:
            operation_name: Operation identifier (e.g., "htdag_decomposition")
            span_type: SpanType for span creation
            context: Correlation context

        Yields:
            Span object

        Example:
            ```python
            with obs_manager.timed_operation("htdag_decompose", SpanType.HTDAG, ctx):
                result = planner.decompose_task(request)
            # Automatically records "htdag_decompose.duration" metric
            ```
        """
        start_time = time.perf_counter()

        with self.span(operation_name, span_type, context) as span:
            try:
                yield span
            finally:
                # Record duration metric
                duration = time.perf_counter() - start_time
                self.record_metric(
                    metric_name=f"{operation_name}.duration",
                    value=duration,
                    unit="seconds",
                    labels={"operation": operation_name}
                )

                # Add duration to span
                span.set_attribute("duration_seconds", duration)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of recorded metrics

        Returns:
            Dictionary with metric statistics
        """
        if not self.metrics:
            return {"total_metrics": 0}

        # Group by metric name
        by_name: Dict[str, List[float]] = {}
        for metric in self.metrics:
            by_name.setdefault(metric.metric_name, []).append(metric.value)

        # Calculate stats
        summary = {
            "total_metrics": len(self.metrics),
            "unique_metrics": len(by_name),
            "by_metric": {}
        }

        for name, values in by_name.items():
            summary["by_metric"][name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "sum": sum(values)
            }

        return summary


# Global observability manager instance
_obs_manager: Optional[ObservabilityManager] = None
_obs_config: ObservabilityConfig = ObservabilityConfig()
_observability_config_loaded: bool = False

OBSERVABILITY_CONFIG_ENV = "OBSERVABILITY_CONFIG_FILE"
ENVIRONMENT_ENV = "ENVIRONMENT"
DEFAULT_CONFIG_MAP = {
    "production": "config/production.yml",
    "staging": "config/staging.yml",
}


def get_observability_manager() -> ObservabilityManager:
    """
    Get global observability manager singleton

    Returns:
        ObservabilityManager instance
    """
    global _obs_manager
    _ensure_observability_config()
    if _obs_manager is None:
        _obs_manager = ObservabilityManager(config=_obs_config)
    return _obs_manager


def configure_observability(config: ObservabilityConfig) -> None:
    """
    Configure the global observability manager.

    Replaces the current manager to ensure new configuration takes effect.
    """
    global _obs_manager, _obs_config, _observability_config_loaded
    _obs_config = config
    _obs_manager = ObservabilityManager(config=config)
    _observability_config_loaded = True


def configure_observability_from_dict(
    config: Dict[str, Any],
    *,
    environment: Optional[str] = None
) -> ObservabilityConfig:
    """Configure observability using a dictionary extracted from YAML/JSON."""
    tracing_cfg = config.get("tracing", {})
    sample = tracing_cfg.get("sample_rate", tracing_cfg.get("sampling_rate"))
    try:
        sampling_ratio = float(sample)
    except (TypeError, ValueError):
        sampling_ratio = 1.0

    allowed_types_cfg = tracing_cfg.get("allowed_span_types") or config.get("span_filters", {}).get("allowed_span_types")
    allowed_span_types: Optional[Set[SpanType]] = None
    if allowed_types_cfg:
        parsed = {
            span_type
            for item in allowed_types_cfg
            if (span_type := _parse_span_type(item)) is not None
        }
        if parsed:
            allowed_span_types = parsed

    metrics_cfg = config.get("metrics", {})
    default_labels_cfg = metrics_cfg.get("default_labels", {})
    default_labels = {str(k): str(v) for k, v in default_labels_cfg.items()}

    span_attrs = tracing_cfg.get("span_attributes", {})
    service_name = span_attrs.get("service_name") or tracing_cfg.get("service_name")
    if service_name and "service" not in default_labels:
        default_labels["service"] = str(service_name)

    if environment and "environment" not in default_labels:
        default_labels["environment"] = environment

    config_obj = ObservabilityConfig(
        sampling_ratio=sampling_ratio,
        allowed_span_types=allowed_span_types,
        default_metric_labels=default_labels,
        random_seed=config.get("random_seed"),
    )
    configure_observability(config_obj)
    return config_obj


def configure_observability_from_file(path: Union[str, Path]) -> Optional[ObservabilityConfig]:
    """Configure observability using a configuration file."""
    config_path = Path(path)
    if not config_path.exists():
        logger.debug("Observability config not found at %s", config_path)
        return None

    try:
        with open(config_path, "r") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to load observability config from %s: %s", config_path, exc)
        return None

    environment = data.get("environment")
    observability_section = data.get("observability", {})
    if not observability_section:
        logger.debug("No observability section found in %s", config_path)
        return None

    config_obj = configure_observability_from_dict(
        observability_section,
        environment=environment,
    )
    logger.info(
        "Configured observability from %s (sampling=%.3f, labels=%s)",
        config_path,
        config_obj.sampling_ratio,
        config_obj.default_metric_labels,
    )
    return config_obj


def _determine_config_path() -> Optional[Path]:
    """Determine which configuration file to use for observability."""
    explicit = os.getenv(OBSERVABILITY_CONFIG_ENV)
    if explicit:
        return Path(explicit)

    environment = os.getenv(ENVIRONMENT_ENV, "").lower()
    path = DEFAULT_CONFIG_MAP.get(environment)
    if path:
        return Path(Path(__file__).resolve().parent.parent, path)

    # Fallback: use staging config if available
    fallback = Path(Path(__file__).resolve().parent.parent, "config/staging.yml")
    return fallback if fallback.exists() else None


def _ensure_observability_config() -> None:
    """Load observability configuration from environment if not already done."""
    global _observability_config_loaded

    if _observability_config_loaded:
        return

    config_path = _determine_config_path()
    if config_path and config_path.exists():
        configure_observability_from_file(config_path)
    else:
        _observability_config_loaded = True  # prevent repeated attempts


# Convenience decorators for common patterns

def traced_operation(operation_name: str, span_type: SpanType):
    """
    Decorator to automatically trace function execution

    Args:
        operation_name: Operation identifier
        span_type: SpanType classification

    Example:
        ```python
        @traced_operation("htdag_decompose", SpanType.HTDAG)
        async def decompose_task(self, request: str, context: CorrelationContext):
            # Function automatically traced
            pass
        ```
    """
    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            obs_manager = get_observability_manager()

            # Extract context if provided
            context = kwargs.get('context') or (args[1] if len(args) > 1 and isinstance(args[1], CorrelationContext) else None)

            with obs_manager.span(operation_name, span_type, context):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            obs_manager = get_observability_manager()

            # Extract context if provided
            context = kwargs.get('context') or (args[1] if len(args) > 1 and isinstance(args[1], CorrelationContext) else None)

            with obs_manager.span(operation_name, span_type, context):
                return func(*args, **kwargs)

        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_structured(message: str, **kwargs):
    """
    Log structured message with automatic JSON formatting

    Args:
        message: Log message
        **kwargs: Additional structured fields

    Example:
        ```python
        log_structured(
            "Task decomposed successfully",
            task_count=5,
            correlation_id=ctx.correlation_id,
            agent="htdag_planner"
        )
        ```
    """
    logger.info(message, extra=kwargs)


# ====================================================================================
# VOLTAGENT-INSPIRED ENHANCEMENTS (October 28, 2025)
# ====================================================================================
# Based on VoltAgent observability patterns:
# - Declarative metric definitions
# - Dashboard configuration helpers
# - Structured logging with context propagation
# - Span filtering for reduced overhead

from enum import Enum as StandardEnum
from typing import Literal


class MetricType(StandardEnum):
    """Prometheus metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    """
    Declarative metric definition (VoltAgent pattern)

    Enables automatic Prometheus config generation and dashboard creation

    Example:
        metric = MetricDefinition(
            name="genesis_agent_duration_seconds",
            type=MetricType.HISTOGRAM,
            description="Agent execution duration",
            unit="seconds",
            labels=["agent", "status"]
        )
    """
    name: str
    type: MetricType
    description: str
    unit: str
    labels: List[str] = field(default_factory=list)

    def to_prometheus_help(self) -> str:
        """Generate Prometheus HELP comment"""
        return f"# HELP {self.name} {self.description}"

    def to_prometheus_type(self) -> str:
        """Generate Prometheus TYPE comment"""
        return f"# TYPE {self.name} {self.type.value}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "unit": self.unit,
            "labels": self.labels
        }


class MetricRegistry:
    """
    Registry for declarative metric definitions (VoltAgent pattern)

    Provides centralized metric management and dashboard generation
    """

    def __init__(self):
        self.metrics: Dict[str, MetricDefinition] = {}
        self.logger = logging.getLogger(__name__)

    def define_metric(
        self,
        name: str,
        type: MetricType,
        labels: List[str],
        description: str,
        unit: str = ""
    ) -> MetricDefinition:
        """
        Define a metric declaratively

        Args:
            name: Metric name (e.g., "genesis_agent_duration_seconds")
            type: Metric type (COUNTER, GAUGE, HISTOGRAM, SUMMARY)
            labels: Label names (e.g., ["agent", "status"])
            description: Human-readable description
            unit: Unit of measurement (e.g., "seconds", "bytes")

        Returns:
            MetricDefinition instance

        Example:
            registry = MetricRegistry()
            registry.define_metric(
                name="genesis_cost_usd_total",
                type=MetricType.COUNTER,
                labels=["agent", "model"],
                description="Total cost in USD",
                unit="usd"
            )
        """
        if name in self.metrics:
            self.logger.warning(f"Metric {name} already defined, overwriting")

        metric = MetricDefinition(
            name=name,
            type=type,
            description=description,
            unit=unit,
            labels=labels
        )

        self.metrics[name] = metric
        self.logger.debug(f"Defined metric: {name} ({type.value})")

        return metric

    def get_metric(self, name: str) -> Optional[MetricDefinition]:
        """Get metric definition by name"""
        return self.metrics.get(name)

    def list_metrics(self) -> List[MetricDefinition]:
        """List all defined metrics"""
        return list(self.metrics.values())

    def create_dashboard(
        self,
        name: str,
        metrics: List[str],
        layout: Optional[Dict[str, Dict[str, int]]] = None
    ) -> Dict[str, Any]:
        """
        Generate Grafana dashboard JSON (VoltAgent pattern)

        Args:
            name: Dashboard name
            metrics: List of metric names to include
            layout: Optional layout configuration (metric_name -> {x, y, w, h})

        Returns:
            Grafana dashboard JSON

        Example:
            dashboard = registry.create_dashboard(
                name="Genesis Overview",
                metrics=["genesis_agents_total", "genesis_cost_usd_total"],
                layout={
                    "genesis_agents_total": {"x": 0, "y": 0, "w": 12, "h": 4},
                    "genesis_cost_usd_total": {"x": 0, "y": 4, "w": 12, "h": 4}
                }
            )
        """
        layout = layout or {}
        panels = []

        for i, metric_name in enumerate(metrics):
            metric = self.metrics.get(metric_name)
            if not metric:
                self.logger.warning(f"Metric {metric_name} not found, skipping panel")
                continue

            # Default layout if not specified
            default_layout = {
                "x": 0,
                "y": i * 4,
                "w": 12,
                "h": 4
            }
            panel_layout = layout.get(metric_name, default_layout)

            # Panel type based on metric type
            panel_type = "graph" if metric.type == MetricType.HISTOGRAM else "stat"

            # Legend format from labels
            legend_format = "{{" + "}}{{".join(metric.labels) + "}}" if metric.labels else ""

            panels.append({
                "id": i + 1,
                "title": metric.description,
                "type": panel_type,
                "datasource": "Prometheus",
                "targets": [
                    {
                        "expr": metric.name,
                        "legendFormat": legend_format,
                        "refId": "A"
                    }
                ],
                "gridPos": panel_layout,
                "fieldConfig": {
                    "defaults": {
                        "unit": metric.unit,
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"value": None, "color": "green"}
                            ]
                        }
                    }
                }
            })

        dashboard = {
            "dashboard": {
                "title": name,
                "panels": panels,
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "10s",
                "schemaVersion": 36,
                "version": 1,
                "uid": f"genesis-{name.lower().replace(' ', '-')}",
                "tags": ["genesis", "auto-generated"]
            }
        }

        self.logger.info(f"Generated dashboard '{name}' with {len(panels)} panels")
        return dashboard


# Global metric registry
_metric_registry: Optional[MetricRegistry] = None


def get_metric_registry() -> MetricRegistry:
    """Get global metric registry singleton"""
    global _metric_registry
    if _metric_registry is None:
        _metric_registry = MetricRegistry()
    return _metric_registry


def structured_log(
    level: Literal["debug", "info", "warning", "error"],
    message: str,
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    **kwargs
):
    """
    Enhanced structured logging with context propagation (VoltAgent pattern)

    Args:
        level: Log level
        message: Log message
        context: Structured context (e.g., {"agent": "spec_agent", "task_id": "123"})
        tags: Tags for filtering (e.g., ["performance", "cost"])
        **kwargs: Additional key-value pairs

    Example:
        structured_log(
            "info",
            "Agent execution complete",
            context={"agent": "spec_agent", "duration": 1.23},
            tags=["performance"],
            correlation_id="abc123"
        )
    """
    # Merge context and kwargs
    extra = context or {}
    extra.update(kwargs)

    # Add tags
    if tags:
        extra["tags"] = tags

    # Log with appropriate level
    log_fn = getattr(logger, level, logger.info)
    log_fn(message, extra=extra)


# ====================================================================================
# OSWORLD & LANGMEM METRICS DEFINITIONS (October 28, 2025)
# ====================================================================================
# Comprehensive metrics for OSWorld benchmarking and LangMem memory management
# to support Phase 4 deployment monitoring requirements.

def register_osworld_metrics():
    """
    Register OSWorld benchmark metrics

    Tracks Computer Use agent performance against OSWorld GUI benchmark.
    Monitors success rates, task duration, failure patterns, and mock vs real execution.
    """
    registry = get_metric_registry()

    # 1. OSWorld benchmark success rate (0-100%)
    registry.define_metric(
        name="osworld_benchmark_success_rate",
        type=MetricType.GAUGE,
        labels=["category"],
        description="OSWorld benchmark success rate by task category",
        unit="percent"
    )

    # 2. Task duration
    registry.define_metric(
        name="osworld_task_duration_seconds",
        type=MetricType.HISTOGRAM,
        labels=["category", "status"],
        description="OSWorld task execution duration",
        unit="seconds"
    )

    # 3. Total tasks executed
    registry.define_metric(
        name="osworld_tasks_total",
        type=MetricType.COUNTER,
        labels=["category"],
        description="Total OSWorld tasks executed by category",
        unit="count"
    )

    # 4. Failed tasks
    registry.define_metric(
        name="osworld_tasks_failed",
        type=MetricType.COUNTER,
        labels=["category", "failure_reason"],
        description="Failed OSWorld tasks by category and failure reason",
        unit="count"
    )

    # 5. Steps per task (efficiency metric)
    registry.define_metric(
        name="osworld_steps_per_task",
        type=MetricType.HISTOGRAM,
        labels=["category"],
        description="Number of steps taken per task completion",
        unit="count"
    )

    # 6. Mock vs real execution ratio
    registry.define_metric(
        name="osworld_mock_vs_real",
        type=MetricType.GAUGE,
        labels=["backend_type"],
        description="Percentage using mock vs real Computer Use client",
        unit="percent"
    )

    logger.info("Registered 6 OSWorld metrics")


def register_langmem_metrics():
    """
    Register LangMem memory management metrics

    Tracks TTL cleanup, deduplication efficiency, cache performance,
    and memory usage for Genesis Memory Store.
    """
    registry = get_metric_registry()

    # 1. TTL deleted entries
    registry.define_metric(
        name="langmem_ttl_deleted_total",
        type=MetricType.COUNTER,
        labels=["namespace", "memory_type"],
        description="Total memory entries deleted by TTL cleanup",
        unit="count"
    )

    # 2. TTL cleanup duration
    registry.define_metric(
        name="langmem_ttl_cleanup_duration_seconds",
        type=MetricType.HISTOGRAM,
        labels=["namespace"],
        description="Duration of TTL cleanup operations",
        unit="seconds"
    )

    # 3. Deduplication rate
    registry.define_metric(
        name="langmem_dedup_rate",
        type=MetricType.GAUGE,
        labels=["namespace", "dedup_type"],
        description="Memory deduplication rate (0-100%)",
        unit="percent"
    )

    # 4. Exact duplicates found
    registry.define_metric(
        name="langmem_dedup_exact_duplicates",
        type=MetricType.COUNTER,
        labels=["namespace"],
        description="Exact duplicates detected via MD5 hash",
        unit="count"
    )

    # 5. Semantic duplicates found
    registry.define_metric(
        name="langmem_dedup_semantic_duplicates",
        type=MetricType.COUNTER,
        labels=["namespace", "similarity_threshold"],
        description="Semantic duplicates detected via cosine similarity",
        unit="count"
    )

    # 6. Cache evictions
    registry.define_metric(
        name="langmem_cache_evictions_total",
        type=MetricType.COUNTER,
        labels=["namespace", "cache_type"],
        description="LRU cache evictions for memory management",
        unit="count"
    )

    # 7. Memory usage
    registry.define_metric(
        name="langmem_memory_usage_bytes",
        type=MetricType.GAUGE,
        labels=["namespace", "memory_type"],
        description="Memory usage in bytes by namespace and type",
        unit="bytes"
    )

    logger.info("Registered 7 LangMem metrics")


def register_all_metrics():
    """
    Register all Genesis metrics including OSWorld and LangMem

    Call this during application startup to ensure all metrics
    are defined before use.
    """
    register_osworld_metrics()
    register_langmem_metrics()
    logger.info("All Genesis metrics registered successfully")


# Export public API
__all__ = [
    "ObservabilityManager",
    "ObservabilityConfig",
    "CorrelationContext",
    "MetricSnapshot",
    "SpanType",
    "get_observability_manager",
    "configure_observability",
    "traced_operation",
    "log_structured",
    # VoltAgent-inspired additions
    "MetricType",
    "MetricDefinition",
    "MetricRegistry",
    "get_metric_registry",
    "structured_log",
    "configure_observability_from_dict",
    "configure_observability_from_file",
    # OSWorld & LangMem metrics
    "register_osworld_metrics",
    "register_langmem_metrics",
    "register_all_metrics",
]
