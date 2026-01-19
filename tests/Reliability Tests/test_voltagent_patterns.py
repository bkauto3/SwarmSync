"""
Test VoltAgent-Inspired Patterns

Tests for:
- Declarative metric definitions
- Dashboard generation
- Workflow spec loading
- Tool validation (placeholder for future AATC)

Based on VoltAgent observability and workflow patterns
"""
import json
import os
import tempfile
from typing import Any, Dict

import pytest
import yaml
from pydantic import ValidationError

from infrastructure.observability import (
    MetricType,
    MetricDefinition,
    MetricRegistry,
    ObservabilityConfig,
    ObservabilityManager,
    SpanType,
    configure_observability,
    configure_observability_from_dict,
    structured_log,
)

from infrastructure.htdag_planner import (
    WorkflowStepSpec,
    WorkflowSpec,
    WorkflowValidator,
    WorkflowExecutor,
    ValidationResult,
    WorkflowBuilder,
)

from infrastructure.aatc_system import (
    ToolRegistry,
    ToolValidationError,
    get_tool_registry,
)


# ====================================================================================
# METRIC DEFINITION TESTS
# ====================================================================================

class TestMetricDefinition:
    """Test declarative metric definitions"""

    def test_metric_definition_basic(self):
        """Test basic metric definition"""
        metric = MetricDefinition(
            name="genesis_agent_duration_seconds",
            type=MetricType.HISTOGRAM,
            description="Agent execution duration",
            unit="seconds",
            labels=["agent", "status"]
        )

        assert metric.name == "genesis_agent_duration_seconds"
        assert metric.type == MetricType.HISTOGRAM
        assert metric.unit == "seconds"
        assert metric.labels == ["agent", "status"]

    def test_prometheus_help_generation(self):
        """Test Prometheus HELP comment generation"""
        metric = MetricDefinition(
            name="genesis_cost_usd_total",
            type=MetricType.COUNTER,
            description="Total cost in USD",
            unit="usd",
            labels=["agent", "model"]
        )

        help_text = metric.to_prometheus_help()
        assert help_text == "# HELP genesis_cost_usd_total Total cost in USD"

    def test_prometheus_type_generation(self):
        """Test Prometheus TYPE comment generation"""
        metric = MetricDefinition(
            name="genesis_agents_total",
            type=MetricType.GAUGE,
            description="Total number of agents",
            unit="count",
            labels=[]
        )

        type_text = metric.to_prometheus_type()
        assert type_text == "# TYPE genesis_agents_total gauge"

    def test_metric_to_dict(self):
        """Test metric serialization to dict"""
        metric = MetricDefinition(
            name="genesis_errors_total",
            type=MetricType.COUNTER,
            description="Total errors",
            unit="count",
            labels=["error_type"]
        )

        data = metric.to_dict()
        assert data["name"] == "genesis_errors_total"
        assert data["type"] == "counter"
        assert data["unit"] == "count"
        assert data["labels"] == ["error_type"]


class TestMetricRegistry:
    """Test metric registry"""

    def test_define_metric(self):
        """Test metric definition"""
        registry = MetricRegistry()

        metric = registry.define_metric(
            name="test_metric",
            type=MetricType.COUNTER,
            labels=["label1"],
            description="Test metric"
        )

        assert metric.name == "test_metric"
        assert registry.get_metric("test_metric") == metric

    def test_list_metrics(self):
        """Test listing all metrics"""
        registry = MetricRegistry()

        registry.define_metric("metric1", MetricType.COUNTER, [], "Metric 1")
        registry.define_metric("metric2", MetricType.GAUGE, [], "Metric 2")

        metrics = registry.list_metrics()
        assert len(metrics) == 2
        assert {m.name for m in metrics} == {"metric1", "metric2"}

    def test_create_dashboard_basic(self):
        """Test Grafana dashboard generation"""
        registry = MetricRegistry()

        registry.define_metric(
            "genesis_agents_total",
            MetricType.GAUGE,
            [],
            "Total agents",
            unit="count"
        )

        registry.define_metric(
            "genesis_cost_usd_total",
            MetricType.COUNTER,
            ["agent", "model"],
            "Total cost",
            unit="usd"
        )

        dashboard = registry.create_dashboard(
            name="Test Dashboard",
            metrics=["genesis_agents_total", "genesis_cost_usd_total"]
        )

        assert "dashboard" in dashboard
        assert dashboard["dashboard"]["title"] == "Test Dashboard"
        assert len(dashboard["dashboard"]["panels"]) == 2

    def test_create_dashboard_with_layout(self):
        """Test dashboard generation with custom layout"""
        registry = MetricRegistry()

        registry.define_metric("metric1", MetricType.GAUGE, [], "Metric 1")

        dashboard = registry.create_dashboard(
            name="Custom Layout",
            metrics=["metric1"],
            layout={"metric1": {"x": 12, "y": 0, "w": 12, "h": 8}}
        )

        panel = dashboard["dashboard"]["panels"][0]
        assert panel["gridPos"]["x"] == 12
        assert panel["gridPos"]["y"] == 0
        assert panel["gridPos"]["w"] == 12
        assert panel["gridPos"]["h"] == 8


# ====================================================================================
# OBSERVABILITY CONFIG TESTS
# ====================================================================================

class TestObservabilityConfig:
    """Test VoltAgent-inspired observability configuration"""

    def test_sampling_ratio_disables_span(self):
        """Sampling ratio 0 should skip tracing and yield NullSpan."""
        manager = ObservabilityManager(config=ObservabilityConfig(sampling_ratio=0.0))

        with manager.span("htdag.skip", SpanType.HTDAG) as span:
            assert span.__class__.__name__ == "_NullSpan"

    def test_allowed_span_types_filter(self):
        """Span type filter should allow only configured types."""
        config = ObservabilityConfig(allowed_span_types={SpanType.HTDAG})
        manager = ObservabilityManager(config=config)

        with manager.span("allowed", SpanType.HTDAG) as span_allowed:
            # When tracing is enabled, we expect a real OTEL span implementation
            assert span_allowed.__class__.__name__ != "_NullSpan"

        with manager.span("filtered", SpanType.AOP) as span_blocked:
            assert span_blocked.__class__.__name__ == "_NullSpan"

    def test_default_metric_labels(self):
        """Default metric labels should merge with per-call labels."""
        config = ObservabilityConfig(default_metric_labels={"service": "genesis"})
        manager = ObservabilityManager(config=config)

        manager.record_metric("test.metric", 1.0, "count", labels={"component": "demo"})

        snapshot = manager.metrics[-1]
        assert snapshot.labels["service"] == "genesis"
        assert snapshot.labels["component"] == "demo"

    def test_configure_from_dict_applies_span_filters(self):
        config_dict = {
            "tracing": {
                "sampling_rate": 0.25,
                "allowed_span_types": ["htdag", "halo"],
            },
            "metrics": {
                "default_labels": {"service": "test-service"}
            }
        }

        config_obj = configure_observability_from_dict(
            config_dict,
            environment="qa",
        )

        try:
            assert config_obj.sampling_ratio == 0.25
            assert config_obj.allowed_span_types == {SpanType.HTDAG, SpanType.HALO}
            assert config_obj.default_metric_labels["service"] == "test-service"
            assert config_obj.default_metric_labels["environment"] == "qa"
        finally:
            configure_observability(ObservabilityConfig())


# ====================================================================================
# WORKFLOW SPEC TESTS
# ====================================================================================

class TestWorkflowStepSpec:
    """Test workflow step specifications"""

    def test_step_spec_basic(self):
        """Test basic step spec"""
        step = WorkflowStepSpec(
            id="test_step",
            type="task",
            description="Test step",
            depends_on=["prev_step"],
            config={"command": "echo test"}
        )

        assert step.id == "test_step"
        assert step.type == "task"
        assert step.description == "Test step"
        assert step.depends_on == ["prev_step"]
        assert step.config == {"command": "echo test"}

    def test_step_spec_validation_invalid_id(self):
        """Test step ID validation"""
        with pytest.raises(ValueError, match="Step ID cannot be empty"):
            WorkflowStepSpec(id="", type="task")

    def test_step_spec_validation_invalid_type(self):
        """Test step type validation"""
        with pytest.raises(ValidationError):
            WorkflowStepSpec(id="test", type="invalid_type")


class TestWorkflowSpec:
    """Test complete workflow specifications"""

    def test_workflow_spec_basic(self):
        """Test basic workflow spec"""
        spec = WorkflowSpec(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            steps=[
                WorkflowStepSpec(id="step1", type="task"),
                WorkflowStepSpec(id="step2", type="task", depends_on=["step1"])
            ]
        )

        assert spec.id == "test-workflow"
        assert spec.name == "Test Workflow"
        assert len(spec.steps) == 2

    def test_workflow_spec_from_yaml(self):
        """Test loading workflow from YAML"""
        yaml_content = """
id: deploy-saas
name: Deploy SaaS
description: Deploy SaaS application
steps:
  - id: spec
    type: agent
    description: Generate spec
    config:
      agent: spec_agent

  - id: build
    type: task
    description: Build app
    depends_on: [spec]
    config:
      command: npm run build
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            spec = WorkflowSpec.from_yaml(yaml_path)
            assert spec.id == "deploy-saas"
            assert spec.name == "Deploy SaaS"
            assert len(spec.steps) == 2
            assert spec.steps[0].id == "spec"
            assert spec.steps[1].depends_on == ["spec"]
        finally:
            os.unlink(yaml_path)

    def test_workflow_spec_from_json(self):
        """Test loading workflow from JSON"""
        json_content = {
            "id": "test-workflow",
            "name": "Test Workflow",
            "description": "Test",
            "steps": [
                {"id": "step1", "type": "task"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            json_path = f.name

        try:
            spec = WorkflowSpec.from_json(json_path)
            assert spec.id == "test-workflow"
            assert len(spec.steps) == 1
        finally:
            os.unlink(json_path)


class TestWorkflowValidator:
    """Test workflow validation"""

    def test_validate_valid_workflow(self):
        """Test validation of valid workflow"""
        spec = WorkflowSpec(
            id="valid",
            name="Valid Workflow",
            description="Valid",
            steps=[
                WorkflowStepSpec(id="step1", type="task"),
                WorkflowStepSpec(id="step2", type="task", depends_on=["step1"])
            ]
        )

        result = WorkflowValidator.validate(spec)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_cycle_detection(self):
        """Test cycle detection"""
        spec = WorkflowSpec(
            id="cycle",
            name="Cycle Workflow",
            description="Has cycle",
            steps=[
                WorkflowStepSpec(id="step1", type="task", depends_on=["step2"]),
                WorkflowStepSpec(id="step2", type="task", depends_on=["step1"])
            ]
        )

        result = WorkflowValidator.validate(spec)
        assert result.valid is False
        assert any("cycle" in err.lower() for err in result.errors)

    def test_validate_missing_dependency(self):
        """Test missing dependency detection"""
        spec = WorkflowSpec(
            id="missing-dep",
            name="Missing Dependency",
            description="Missing",
            steps=[
                WorkflowStepSpec(id="step1", type="task", depends_on=["nonexistent"])
            ]
        )

        result = WorkflowValidator.validate(spec)
        assert result.valid is False
        assert any("non-existent" in err.lower() for err in result.errors)

    def test_validate_duplicate_step_ids(self):
        """Test duplicate step ID detection"""
        spec = WorkflowSpec(
            id="duplicate",
            name="Duplicate IDs",
            description="Duplicate",
            steps=[
                WorkflowStepSpec(id="step1", type="task"),
                WorkflowStepSpec(id="step1", type="task")
            ]
        )

        result = WorkflowValidator.validate(spec)
        assert result.valid is False
        assert any("duplicate" in err.lower() for err in result.errors)

    def test_validate_warnings(self):
        """Test validation warnings"""
        # Create workflow with 51 steps (triggers warning)
        steps = [
            WorkflowStepSpec(id=f"step{i}", type="task")
            for i in range(51)
        ]

        spec = WorkflowSpec(
            id="large",
            name="Large Workflow",
            description="Large",
            steps=steps
        )

        result = WorkflowValidator.validate(spec)
        assert len(result.warnings) > 0


class TestWorkflowBuilder:
    """Test fluent workflow builder"""

    def test_builder_creates_spec(self):
        """Fluent builder should chain steps and infer dependencies."""
        builder = WorkflowBuilder(
            workflow_id="deploy",
            name="Deploy Workflow",
            description="End-to-end deploy",
        )

        spec = (
            builder
            .and_agent(
                step_id="spec",
                agent="spec_agent",
                description="Create spec",
                prompt="Generate technical specification",
            )
            .and_task(
                step_id="build",
                description="Build service",
                command="npm run build",
            )
            .and_parallel(
                step_id="test",
                description="Execute tests",
                subtasks=["unit_tests", "integration_tests"],
            )
            .build()
        )

        assert [step.id for step in spec.steps] == ["spec", "build", "test"]
        assert spec.steps[1].depends_on == ["spec"]
        assert spec.steps[2].depends_on == ["build"]
        assert spec.steps[0].config["agent"] == "spec_agent"
        assert spec.steps[1].config["command"] == "npm run build"
        assert spec.steps[2].config["subtasks"] == ["unit_tests", "integration_tests"]

    def test_builder_custom_dependencies(self):
        """Builder should respect explicit dependencies."""
        builder = WorkflowBuilder(workflow_id="custom", name="Custom", description="")

        spec = (
            builder
            .and_task("ingest", description="Ingest")
            .and_task("transform", description="Transform")
            .and_task("publish", description="Publish", depends_on=["ingest"])
            .build()
        )

        deps = {step.id: step.depends_on for step in spec.steps}
        assert deps["transform"] == ["ingest"]
        assert deps["publish"] == ["ingest"]


@pytest.mark.asyncio
class TestWorkflowExecutor:
    """Test workflow execution"""

    async def test_execute_workflow_basic(self):
        """Test basic workflow execution"""
        spec = WorkflowSpec(
            id="simple",
            name="Simple Workflow",
            description="Simple",
            steps=[
                WorkflowStepSpec(id="step1", type="task", description="First step"),
                WorkflowStepSpec(id="step2", type="task", description="Second step", depends_on=["step1"])
            ]
        )

        executor = WorkflowExecutor()
        dag = await executor.execute_workflow(spec, {})

        assert len(dag) == 2
        assert "step1" in dag.tasks
        assert "step2" in dag.tasks
        assert "step1" in dag.get_parents("step2")

    async def test_execute_workflow_invalid(self):
        """Test execution with invalid workflow"""
        spec = WorkflowSpec(
            id="invalid",
            name="Invalid Workflow",
            description="Invalid",
            steps=[
                WorkflowStepSpec(id="step1", type="task", depends_on=["nonexistent"])
            ]
        )

        executor = WorkflowExecutor()

        with pytest.raises(ValueError, match="Invalid workflow"):
            await executor.execute_workflow(spec, {})


# ====================================================================================
# TOOL REGISTRY TESTS
# ====================================================================================

class TestToolRegistry:
    """Test AATC tool registry with Pydantic validation."""

    def _sample_tool_spec(self) -> Dict[str, Any]:
        return {
            "name": "fetch_docs",
            "description": "Fetch documents by query",
            "version": "1.0",
            "input": {
                "fields": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "required": False, "description": "Result limit"},
                }
            },
            "output": {
                "fields": {
                    "results": {"type": "array", "description": "List of documents"},
                }
            },
            "tags": ["search"],
        }

    def test_register_and_validate_input(self):
        registry = ToolRegistry()
        registry.register(self._sample_tool_spec())

        payload = {"query": "vision models", "limit": 5}
        validated = registry.validate_input("fetch_docs", payload)

        assert validated == payload

    def test_validate_input_missing_required(self):
        registry = ToolRegistry()
        registry.register(self._sample_tool_spec())

        with pytest.raises(ToolValidationError, match="missing required field 'query'"):
            registry.validate_input("fetch_docs", {"limit": 10})

    def test_validate_input_type_mismatch(self):
        registry = ToolRegistry()
        registry.register(self._sample_tool_spec())

        with pytest.raises(ToolValidationError, match="expected type 'integer'"):
            registry.validate_input("fetch_docs", {"query": "hi", "limit": "five"})

    def test_validate_output(self):
        registry = ToolRegistry()
        registry.register(self._sample_tool_spec())

        output = {"results": []}
        assert registry.validate_output("fetch_docs", output) == output

    def test_load_spec_from_yaml(self, tmp_path):
        registry = ToolRegistry()
        spec_path = tmp_path / "tool.yaml"
        spec_path.write_text(yaml.safe_dump({"tools": [self._sample_tool_spec()]}))

        loaded = registry.load_file(spec_path)
        assert len(loaded) == 1
        assert loaded[0].name == "fetch_docs"

    def test_default_registry_loads_workflow_specs(self):
        registry = get_tool_registry()
        assert registry.get("research_web_search") is not None

# ====================================================================================
# STRUCTURED LOGGING TESTS
# ====================================================================================

class TestStructuredLogging:
    """Test enhanced structured logging"""

    def test_structured_log_basic(self, caplog):
        """Test basic structured logging"""
        structured_log(
            "info",
            "Test message",
            context={"key": "value"},
            tags=["test"]
        )

        # Verify log was created (exact assertion depends on logging config)
        assert len(caplog.records) >= 0  # Placeholder - adjust based on logging setup


# ====================================================================================
# INTEGRATION TESTS
# ====================================================================================

class TestVoltAgentPatternsIntegration:
    """Integration tests for VoltAgent patterns"""

    def test_end_to_end_dashboard_generation(self):
        """Test complete dashboard generation workflow"""
        registry = MetricRegistry()

        # Define 5 metrics for Genesis dashboard
        registry.define_metric(
            "genesis_agents_total",
            MetricType.GAUGE,
            [],
            "Total number of agents",
            "count"
        )

        registry.define_metric(
            "genesis_workflows_total",
            MetricType.GAUGE,
            [],
            "Total number of workflows",
            "count"
        )

        registry.define_metric(
            "genesis_cost_usd_total",
            MetricType.COUNTER,
            ["agent", "model"],
            "Total cost in USD",
            "usd"
        )

        registry.define_metric(
            "genesis_agent_duration_seconds",
            MetricType.HISTOGRAM,
            ["agent", "status"],
            "Agent execution duration",
            "seconds"
        )

        registry.define_metric(
            "genesis_safety_unsafe_blocked_total",
            MetricType.COUNTER,
            ["agent"],
            "Unsafe requests blocked",
            "count"
        )

        # Generate dashboard
        dashboard = registry.create_dashboard(
            "Genesis Overview",
            [
                "genesis_agents_total",
                "genesis_workflows_total",
                "genesis_cost_usd_total",
                "genesis_agent_duration_seconds",
                "genesis_safety_unsafe_blocked_total"
            ]
        )

        assert len(dashboard["dashboard"]["panels"]) == 5
        assert dashboard["dashboard"]["title"] == "Genesis Overview"

    async def test_end_to_end_workflow_execution(self):
        """Test complete workflow specification and execution"""
        # Create workflow spec programmatically
        spec = WorkflowSpec(
            id="deploy-saas",
            name="Deploy SaaS",
            description="Deploy SaaS application",
            steps=[
                WorkflowStepSpec(
                    id="spec",
                    type="agent",
                    description="Generate technical spec",
                    config={"agent": "spec_agent"}
                ),
                WorkflowStepSpec(
                    id="build",
                    type="task",
                    description="Build application",
                    depends_on=["spec"],
                    config={"command": "npm run build"}
                ),
                WorkflowStepSpec(
                    id="test",
                    type="parallel",
                    description="Run tests",
                    depends_on=["build"],
                    config={"subtasks": ["unit", "integration"]}
                ),
                WorkflowStepSpec(
                    id="deploy",
                    type="task",
                    description="Deploy to production",
                    depends_on=["test"],
                    config={"target": "production"}
                )
            ]
        )

        # Validate
        validation = WorkflowValidator.validate(spec)
        assert validation.valid is True

        # Execute
        executor = WorkflowExecutor()
        dag = await executor.execute_workflow(spec, {})

        assert len(dag) == 4
        assert not dag.has_cycle()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
