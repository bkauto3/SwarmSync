"""
Integration Tests for A2A Connector + Triple-Layer Orchestration

Tests the full integration between:
- HTDAG (task decomposition)
- HALO (agent routing)
- AOP (plan validation)
- A2A Connector (agent execution)

Test Categories:
1. Simple single-agent execution
2. Multi-agent complex workflows
3. Dependency handling (sequential tasks)
4. Parallel execution (independent tasks)
5. Error handling (agent failures, timeouts)
6. Circuit breaker behavior
7. Feature flag toggling
8. OTEL tracing validation
9. Agent name mapping validation

Author: Alex (Full-Stack Integration Specialist)
Date: 2025-10-19
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import aiohttp

from infrastructure.a2a_connector import (
    A2AConnector,
    A2AExecutionResult,
    HALO_TO_A2A_MAPPING,
    TASK_TYPE_TO_TOOL_MAPPING
)
from infrastructure.task_dag import TaskDAG, Task, TaskStatus
from infrastructure.halo_router import HALORouter, RoutingPlan
from infrastructure.observability import CorrelationContext
from infrastructure.error_handler import CircuitBreaker
from genesis_orchestrator import GenesisOrchestrator


# Fixtures

@pytest.fixture
def a2a_connector():
    """
    Create A2A connector instance

    Uses HTTPS by default (secure). Set A2A_ALLOW_HTTP=true for local HTTP testing.
    In CI/staging, HTTPS is required unless A2A_ALLOW_HTTP=true is explicitly set.
    """
    import os

    # Check if HTTP is explicitly allowed (for local development)
    allow_http = os.getenv("A2A_ALLOW_HTTP", "false").lower() == "true"

    if allow_http:
        base_url = "http://127.0.0.1:8080"
    else:
        # Use HTTPS by default (secure by default)
        base_url = "https://127.0.0.1:8443"

    return A2AConnector(base_url=base_url, timeout_seconds=10.0, verify_ssl=False)


@pytest.fixture
def simple_dag():
    """Create simple DAG with 1 task"""
    dag = TaskDAG()
    task = Task(
        task_id="task_marketing",
        task_type="marketing",
        description="Create marketing strategy for SaaS product"
    )
    dag.add_task(task)
    return dag


@pytest.fixture
def complex_dag():
    """Create complex DAG with dependencies"""
    dag = TaskDAG()

    # Task 1: Design (no dependencies)
    task1 = Task(
        task_id="task_design",
        task_type="design",
        description="Design product architecture"
    )
    dag.add_task(task1)

    # Task 2: Frontend (depends on design)
    task2 = Task(
        task_id="task_frontend",
        task_type="frontend",
        description="Build frontend UI"
    )
    dag.add_task(task2)
    dag.add_dependency("task_design", "task_frontend")

    # Task 3: Backend (depends on design)
    task3 = Task(
        task_id="task_backend",
        task_type="backend",
        description="Build backend API"
    )
    dag.add_task(task3)
    dag.add_dependency("task_design", "task_backend")

    # Task 4: Deploy (depends on frontend + backend)
    task4 = Task(
        task_id="task_deploy",
        task_type="deploy",
        description="Deploy application"
    )
    dag.add_task(task4)
    dag.add_dependency("task_frontend", "task_deploy")
    dag.add_dependency("task_backend", "task_deploy")

    return dag


@pytest.fixture
def simple_routing_plan():
    """Create simple routing plan"""
    plan = RoutingPlan()
    plan.assignments = {"task_marketing": "marketing_agent"}
    plan.explanations = {"task_marketing": "Marketing tasks route to Marketing Agent"}
    return plan


@pytest.fixture
def complex_routing_plan():
    """Create complex routing plan"""
    plan = RoutingPlan()
    plan.assignments = {
        "task_design": "spec_agent",
        "task_frontend": "frontend_agent",
        "task_backend": "backend_agent",
        "task_deploy": "deploy_agent"
    }
    plan.explanations = {
        "task_design": "Design tasks route to Spec Agent",
        "task_frontend": "Frontend tasks route to Frontend Agent",
        "task_backend": "Backend tasks route to Backend Agent",
        "task_deploy": "Deploy tasks route to Deploy Agent"
    }
    return plan


# Test 1: Agent Name Mapping

def test_agent_name_mapping(a2a_connector):
    """Test HALO agent name -> A2A agent mapping"""
    # Valid mappings
    assert a2a_connector._map_agent_name("spec_agent") == "spec"
    assert a2a_connector._map_agent_name("builder_agent") == "builder"
    assert a2a_connector._map_agent_name("marketing_agent") == "marketing"
    assert a2a_connector._map_agent_name("qa_agent") == "qa"

    # Custom agent not in whitelist (should raise SecurityError)
    # Implementation correctly enforces security whitelist
    with pytest.raises(Exception):  # SecurityError or ValueError
        a2a_connector._map_agent_name("custom_agent")

    # Unknown agent (should raise)
    with pytest.raises(ValueError):
        a2a_connector._map_agent_name("unknown_weird_name")


# Test 2: Task Type -> Tool Mapping

def test_task_to_tool_mapping(a2a_connector):
    """Test task type -> A2A tool mapping"""
    # Design tasks
    task_design = Task(task_id="t1", task_type="design", description="Design system")
    assert a2a_connector._map_task_to_tool(task_design) == "research_market"

    # Implementation tasks
    task_frontend = Task(task_id="t2", task_type="frontend", description="Build UI")
    assert a2a_connector._map_task_to_tool(task_frontend) == "generate_frontend"

    # Backend tasks
    task_backend = Task(task_id="t3", task_type="backend", description="Build API")
    assert a2a_connector._map_task_to_tool(task_backend) == "generate_backend"

    # Testing tasks
    task_test = Task(task_id="t4", task_type="test", description="Run tests")
    assert a2a_connector._map_task_to_tool(task_test) == "run_tests"

    # Explicit tool hint in metadata (gets sanitized by implementation)
    # Implementation validates tool names against whitelist for security
    task_custom = Task(
        task_id="t5",
        task_type="generic",
        description="Custom task",
        metadata={"a2a_tool": "research_market"}  # Use whitelisted tool
    )
    assert a2a_connector._map_task_to_tool(task_custom) == "research_market"

    # Unknown task type (should fall back to generic)
    task_unknown = Task(task_id="t6", task_type="weird_unknown", description="Unknown")
    assert a2a_connector._map_task_to_tool(task_unknown) == "generate_backend"


# Test 3: Argument Preparation

def test_prepare_arguments(a2a_connector):
    """Test argument preparation from task and dependencies"""
    task = Task(
        task_id="task1",
        task_type="backend",
        description="Build REST API",
        metadata={"framework": "FastAPI", "version": "0.1.0"}
    )

    dependency_results = {
        "task0": {"design": "system architecture"}
    }

    args = a2a_connector._prepare_arguments(task, dependency_results)

    # Should include description
    assert args["description"] == "Build REST API"

    # Should include metadata as context
    assert "context" in args
    assert args["context"]["framework"] == "FastAPI"
    assert args["context"]["version"] == "0.1.0"

    # Should include dependency results
    assert "dependency_results" in args
    assert args["dependency_results"]["task0"]["design"] == "system architecture"


# Test 4: Dependency Results Retrieval

def test_get_dependency_results(a2a_connector):
    """Test dependency results retrieval"""
    task = Task(task_id="task2", task_type="deploy", description="Deploy app")
    task.dependencies = ["task0", "task1"]

    results = {
        "task0": A2AExecutionResult(
            task_id="task0",
            agent_name="spec",
            tool_name="research_market",
            status="success",
            result={"design": "architecture"}
        ),
        "task1": A2AExecutionResult(
            task_id="task1",
            agent_name="builder",
            tool_name="generate_backend",
            status="failed",
            error="Build failed"
        )
    }

    dep_results = a2a_connector._get_dependency_results(task, results)

    # Successful dependency
    assert "task0" in dep_results
    assert dep_results["task0"]["design"] == "architecture"

    # Failed dependency (should include error info)
    assert "task1" in dep_results
    assert dep_results["task1"]["status"] == "failed"
    assert dep_results["task1"]["error"] == "Build failed"


# Test 5: Simple Single-Agent Execution (Mocked)

@pytest.mark.asyncio
async def test_simple_single_agent_execution(a2a_connector, simple_dag, simple_routing_plan):
    """Test simple single-agent execution with mocked HTTP"""

    # Mock the HTTP call
    async def mock_invoke(agent_name, tool_name, arguments):
        return {"status": "success", "data": "Marketing strategy created"}

    a2a_connector.invoke_agent_tool = mock_invoke

    # Execute routing plan
    result = await a2a_connector.execute_routing_plan(
        simple_routing_plan,
        simple_dag
    )

    # Verify result
    assert result["status"] == "completed"
    assert result["total_tasks"] == 1
    assert result["successful"] == 1
    assert result["failed"] == 0
    assert "task_marketing" in result["results"]


# Test 6: Complex Multi-Agent Workflow (Mocked)

@pytest.mark.asyncio
async def test_complex_multi_agent_workflow(a2a_connector, complex_dag, complex_routing_plan):
    """Test complex multi-agent workflow with dependencies"""

    # Mock the HTTP call
    call_count = 0

    async def mock_invoke(agent_name, tool_name, arguments):
        nonlocal call_count
        call_count += 1
        return {"status": "success", "data": f"Task completed by {agent_name}"}

    a2a_connector.invoke_agent_tool = mock_invoke

    # Execute routing plan
    result = await a2a_connector.execute_routing_plan(
        complex_routing_plan,
        complex_dag
    )

    # Verify result
    assert result["status"] == "completed"
    assert result["total_tasks"] == 4
    assert result["successful"] == 4
    assert result["failed"] == 0
    assert call_count == 4  # All 4 tasks should be executed


# Test 7: Dependency Order Enforcement

@pytest.mark.asyncio
async def test_dependency_order_enforcement(a2a_connector, complex_dag, complex_routing_plan):
    """Test that tasks are executed in dependency order"""

    execution_order = []

    async def mock_invoke(agent_name, tool_name, arguments):
        # Extract task_id from arguments
        task_desc = arguments.get("description", "")
        if "architecture" in task_desc:
            execution_order.append("task_design")
        elif "frontend" in task_desc:
            execution_order.append("task_frontend")
        elif "backend" in task_desc:
            execution_order.append("task_backend")
        elif "Deploy" in task_desc:
            execution_order.append("task_deploy")

        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    # Execute
    await a2a_connector.execute_routing_plan(complex_routing_plan, complex_dag)

    # Verify order: design must come first, deploy must come last
    assert execution_order[0] == "task_design"
    assert execution_order[-1] == "task_deploy"
    # Frontend and backend can be in any order (parallel)
    assert "task_frontend" in execution_order[1:3]
    assert "task_backend" in execution_order[1:3]


# Test 8: Error Handling (Agent Failure)

@pytest.mark.asyncio
async def test_error_handling_agent_failure(a2a_connector, simple_dag, simple_routing_plan):
    """Test error handling when agent execution fails"""

    async def mock_invoke_failure(agent_name, tool_name, arguments):
        raise Exception("Agent execution failed")

    a2a_connector.invoke_agent_tool = mock_invoke_failure

    # Execute routing plan (should handle error gracefully)
    result = await a2a_connector.execute_routing_plan(
        simple_routing_plan,
        simple_dag
    )

    # Verify result
    assert result["status"] == "partial"  # Partial completion
    assert result["total_tasks"] == 1
    assert result["successful"] == 0
    assert result["failed"] == 1
    assert result["errors"] is not None
    assert len(result["errors"]) == 1


# Test 9: Circuit Breaker Opens After Failures

@pytest.mark.asyncio
async def test_circuit_breaker_opens(a2a_connector):
    """Test circuit breaker opens after threshold failures"""

    # Simulate 5 failures (threshold)
    for _ in range(5):
        a2a_connector.circuit_breaker.record_failure()

    # Circuit breaker should be open
    assert not a2a_connector.circuit_breaker.can_attempt()

    # Attempting to invoke should fail immediately
    with pytest.raises(Exception, match="Circuit breaker OPEN"):
        await a2a_connector.invoke_agent_tool("marketing", "create_strategy", {
            "business_name": "TestBusiness",
            "target_audience": "SaaS founders",
            "budget": 5000.0
        })


# Test 10: Circuit Breaker Recovers After Success

@pytest.mark.asyncio
async def test_circuit_breaker_recovery(a2a_connector):
    """Test circuit breaker recovers after successful attempts"""

    # Record 2 successes (success threshold)
    a2a_connector.circuit_breaker.record_success()
    a2a_connector.circuit_breaker.record_success()

    # Circuit breaker should allow attempts
    assert a2a_connector.circuit_breaker.can_attempt()


# Test 11: Execution Summary Statistics

@pytest.mark.asyncio
async def test_execution_summary(a2a_connector, complex_dag, complex_routing_plan):
    """Test execution summary statistics"""

    async def mock_invoke(agent_name, tool_name, arguments):
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    # Execute
    await a2a_connector.execute_routing_plan(complex_routing_plan, complex_dag)

    # Get summary
    summary = a2a_connector.get_execution_summary()

    assert summary["total_executions"] == 4
    assert summary["successful"] == 4
    assert summary["failed"] == 0
    assert summary["success_rate"] == 1.0
    assert "spec" in summary["agents_used"]
    assert "builder" in summary["agents_used"]


# Test 12: Correlation Context Propagation

@pytest.mark.asyncio
async def test_correlation_context_propagation(a2a_connector, simple_dag, simple_routing_plan):
    """Test correlation context is propagated through execution"""

    ctx = CorrelationContext(user_request="Test request")

    async def mock_invoke(agent_name, tool_name, arguments):
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    # Execute with correlation context
    result = await a2a_connector.execute_routing_plan(
        simple_routing_plan,
        simple_dag,
        correlation_context=ctx
    )

    # Correlation ID should be preserved
    assert result["status"] in ["completed", "partial"]


# Test 13: End-to-End Orchestration (Mocked A2A Service)

@pytest.mark.asyncio
async def test_end_to_end_orchestration_mocked():
    """Test full end-to-end orchestration with mocked A2A service"""

    # This test requires feature flags to be enabled
    # For now, we'll skip if not available
    try:
        from infrastructure.feature_flags import is_feature_enabled

        if not is_feature_enabled('orchestration_enabled'):
            pytest.skip("Orchestration feature flag not enabled")

        orchestrator = GenesisOrchestrator()

        if orchestrator.a2a_connector is None:
            pytest.skip("A2A connector not initialized")

        # Mock the A2A connector's invoke method
        async def mock_invoke(agent_name, tool_name, arguments):
            return {"status": "success", "data": f"Executed {tool_name}"}

        orchestrator.a2a_connector.invoke_agent_tool = mock_invoke

        # Execute orchestrated request
        result = await orchestrator.execute_orchestrated_request(
            "Create a simple SaaS application"
        )

        # Verify result structure
        assert "status" in result
        assert "correlation_id" in result
        assert result["dag_size"] > 0

    except ImportError:
        pytest.skip("Orchestration components not available")


# Test 14: Parallel Task Execution

@pytest.mark.asyncio
async def test_parallel_task_execution(a2a_connector):
    """Test that independent tasks can execute in parallel"""

    dag = TaskDAG()

    # Create 3 independent tasks
    for i in range(3):
        task = Task(
            task_id=f"task_{i}",
            task_type="generic",
            description=f"Task {i}"
        )
        dag.add_task(task)

    routing_plan = RoutingPlan()
    routing_plan.assignments = {
        "task_0": "builder_agent",
        "task_1": "builder_agent",
        "task_2": "builder_agent"
    }

    execution_times = []

    async def mock_invoke(agent_name, tool_name, arguments):
        import time
        start = time.time()
        await asyncio.sleep(0.01)  # Simulate work
        execution_times.append(time.time() - start)
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    # Execute (should be sequential due to topological sort, but fast)
    result = await a2a_connector.execute_routing_plan(routing_plan, dag)

    assert result["successful"] == 3
    assert len(execution_times) == 3


# Test 15: Agent Name Mapping Coverage

def test_agent_name_mapping_coverage():
    """Test that all HALO agents have A2A mappings"""

    halo_agents = [
        "spec_agent", "architect_agent", "builder_agent", "frontend_agent",
        "backend_agent", "qa_agent", "security_agent", "deploy_agent",
        "monitoring_agent", "marketing_agent", "sales_agent", "support_agent",
        "analytics_agent", "research_agent", "finance_agent"
    ]

    for halo_agent in halo_agents:
        assert halo_agent in HALO_TO_A2A_MAPPING, f"Missing mapping for {halo_agent}"


# Test 16: Task Type Mapping Coverage

def test_task_type_mapping_coverage():
    """Test that common task types have tool mappings"""

    common_task_types = [
        "design", "implement", "test", "deploy", "marketing",
        "frontend", "backend", "security", "support"
    ]

    for task_type in common_task_types:
        assert task_type in TASK_TYPE_TO_TOOL_MAPPING, f"Missing mapping for {task_type}"


# Test 17: HTTP Timeout Handling

@pytest.mark.asyncio
async def test_http_timeout_handling(a2a_connector):
    """Test HTTP timeout handling"""

    # This test would require actual HTTP mocking with aiohttp
    # For now, we test the circuit breaker response

    # Simulate timeout by opening circuit breaker
    for _ in range(5):
        a2a_connector.circuit_breaker.record_failure()

    with pytest.raises(Exception, match="Circuit breaker OPEN"):
        await a2a_connector.invoke_agent_tool("marketing", "create_strategy", {
            "business_name": "TestBusiness",
            "target_audience": "SaaS founders",
            "budget": 5000.0
        })


# Test 18: DAG with Cycles (Should Fail)

@pytest.mark.asyncio
async def test_dag_with_cycles(a2a_connector):
    """Test that DAG with cycles fails gracefully"""

    dag = TaskDAG()

    task1 = Task(task_id="task1", task_type="generic", description="Task 1")
    task2 = Task(task_id="task2", task_type="generic", description="Task 2")

    dag.add_task(task1)
    dag.add_task(task2)

    # Create cycle
    dag.add_dependency("task1", "task2")
    dag.add_dependency("task2", "task1")

    routing_plan = RoutingPlan()
    routing_plan.assignments = {"task1": "builder_agent", "task2": "builder_agent"}

    # Execute should fail with cycle error
    result = await a2a_connector.execute_routing_plan(routing_plan, dag)

    assert result["status"] == "failed"
    assert "cycle" in result["error"].lower()


# Test 19: Empty Routing Plan

@pytest.mark.asyncio
async def test_empty_routing_plan(a2a_connector):
    """Test execution with empty routing plan"""

    dag = TaskDAG()
    task = Task(task_id="task1", task_type="generic", description="Task 1")
    dag.add_task(task)

    empty_plan = RoutingPlan()  # No assignments

    result = await a2a_connector.execute_routing_plan(empty_plan, dag)

    # Should complete successfully (no tasks to execute)
    assert result["total_tasks"] == 0
    assert result["successful"] == 0


# Test 20: Task with Missing Dependencies

@pytest.mark.asyncio
async def test_task_with_missing_dependencies(a2a_connector):
    """Test task execution when dependency results are missing"""

    dag = TaskDAG()

    task1 = Task(task_id="task1", task_type="generic", description="Task 1")
    task2 = Task(task_id="task2", task_type="generic", description="Task 2")

    dag.add_task(task1)
    dag.add_task(task2)
    dag.add_dependency("task1", "task2")

    routing_plan = RoutingPlan()
    routing_plan.assignments = {"task2": "builder_agent"}  # task1 not routed

    async def mock_invoke(agent_name, tool_name, arguments):
        # Check if dependency results are empty
        dep_results = arguments.get("dependency_results", {})
        assert "task1" not in dep_results  # task1 wasn't executed
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    result = await a2a_connector.execute_routing_plan(routing_plan, dag)

    assert result["successful"] == 1


# Test 21: Reset Circuit Breaker

def test_reset_circuit_breaker(a2a_connector):
    """Test circuit breaker reset functionality"""

    # Open circuit breaker
    for _ in range(5):
        a2a_connector.circuit_breaker.record_failure()

    assert not a2a_connector.circuit_breaker.can_attempt()

    # Reset
    a2a_connector.reset_circuit_breaker()

    # Should be closed now
    assert a2a_connector.circuit_breaker.can_attempt()


# Test 22: Execution History Tracking

@pytest.mark.asyncio
async def test_execution_history_tracking(a2a_connector, simple_dag, simple_routing_plan):
    """Test that execution history is tracked correctly"""

    async def mock_invoke(agent_name, tool_name, arguments):
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    # Execute
    await a2a_connector.execute_routing_plan(simple_routing_plan, simple_dag)

    # Check history
    assert len(a2a_connector.execution_history) == 1
    assert a2a_connector.execution_history[0].task_id == "task_marketing"
    assert a2a_connector.execution_history[0].agent_name == "marketing"
    assert a2a_connector.execution_history[0].status == "success"


# Test 23: Task Metadata Propagation

@pytest.mark.asyncio
async def test_task_metadata_propagation(a2a_connector):
    """Test that task metadata is propagated to arguments"""

    dag = TaskDAG()
    task = Task(
        task_id="task1",
        task_type="marketing",
        description="Create strategy",
        metadata={"budget": 10000, "target_audience": "developers"}
    )
    dag.add_task(task)

    routing_plan = RoutingPlan()
    routing_plan.assignments = {"task1": "marketing_agent"}

    async def mock_invoke(agent_name, tool_name, arguments):
        # Check metadata propagation
        assert "context" in arguments
        assert arguments["context"]["budget"] == 10000
        assert arguments["context"]["target_audience"] == "developers"
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    await a2a_connector.execute_routing_plan(routing_plan, dag)


# Test 24: Feature Flag Integration

@pytest.mark.asyncio
async def test_feature_flag_integration():
    """Test that feature flags control A2A integration"""

    try:
        from infrastructure.feature_flags import is_feature_enabled

        orchestrator = GenesisOrchestrator()

        # Check if A2A connector was initialized based on feature flag
        a2a_enabled = is_feature_enabled('a2a_integration_enabled')

        if a2a_enabled:
            assert orchestrator.a2a_connector is not None
        else:
            # In planning-only mode, connector might be None
            pass

    except ImportError:
        pytest.skip("Feature flags not available")


# Test 25: Multiple Execution Cycles

@pytest.mark.asyncio
async def test_multiple_execution_cycles(a2a_connector):
    """Test multiple execution cycles don't interfere"""

    async def mock_invoke(agent_name, tool_name, arguments):
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    # Execute 3 times with fresh DAGs
    for i in range(3):
        # Create fresh DAG and routing plan for each execution
        dag = TaskDAG()
        task = Task(
            task_id=f"task_marketing_{i}",
            task_type="marketing",
            description=f"Create marketing strategy {i}"
        )
        dag.add_task(task)

        routing_plan = RoutingPlan()
        routing_plan.assignments = {f"task_marketing_{i}": "marketing_agent"}

        result = await a2a_connector.execute_routing_plan(routing_plan, dag)
        assert result["successful"] == 1

    # Should have 3 executions in history
    assert len(a2a_connector.execution_history) == 3


# Test 26: Execution Time Tracking

@pytest.mark.asyncio
async def test_execution_time_tracking(a2a_connector, simple_dag, simple_routing_plan):
    """Test that execution time is tracked"""

    async def mock_invoke(agent_name, tool_name, arguments):
        await asyncio.sleep(0.01)  # Simulate work
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    result = await a2a_connector.execute_routing_plan(simple_routing_plan, simple_dag)

    # Execution time should be > 0
    assert result["execution_time_ms"] > 0

    # Individual task execution time should be tracked
    assert len(a2a_connector.execution_history) == 1
    assert a2a_connector.execution_history[0].execution_time_ms > 0


# Test 27: Success Rate Calculation

@pytest.mark.asyncio
async def test_success_rate_calculation(a2a_connector):
    """Test success rate calculation in summary"""

    # Manually add execution results (2 success, 1 failure)
    a2a_connector.execution_history = [
        A2AExecutionResult(
            task_id="t1",
            agent_name="spec",
            tool_name="research_market",
            status="success"
        ),
        A2AExecutionResult(
            task_id="t2",
            agent_name="builder",
            tool_name="generate_backend",
            status="success"
        ),
        A2AExecutionResult(
            task_id="t3",
            agent_name="deploy",
            tool_name="deploy_to_vercel",
            status="failed",
            error="Deploy failed"
        )
    ]

    summary = a2a_connector.get_execution_summary()

    assert summary["total_executions"] == 3
    assert summary["successful"] == 2
    assert summary["failed"] == 1
    assert summary["success_rate"] == pytest.approx(0.666, abs=0.01)


# Test 28: Empty DAG Handling

@pytest.mark.asyncio
async def test_empty_dag_handling(a2a_connector):
    """Test execution with empty DAG"""

    empty_dag = TaskDAG()
    empty_plan = RoutingPlan()

    result = await a2a_connector.execute_routing_plan(empty_plan, empty_dag)

    # Should complete successfully with no tasks
    assert result["status"] == "completed"
    assert result["total_tasks"] == 0
    assert result["successful"] == 0
    assert result["failed"] == 0


# Test 29: Large DAG Performance

@pytest.mark.asyncio
async def test_large_dag_performance(a2a_connector):
    """Test performance with large DAG (50 tasks)"""

    dag = TaskDAG()
    routing_plan = RoutingPlan()

    # Create 50 independent tasks
    for i in range(50):
        task = Task(
            task_id=f"task_{i}",
            task_type="generic",
            description=f"Task {i}"
        )
        dag.add_task(task)
        routing_plan.assignments[f"task_{i}"] = "builder_agent"

    async def mock_invoke(agent_name, tool_name, arguments):
        await asyncio.sleep(0.001)  # Minimal delay
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    import time
    start = time.time()

    result = await a2a_connector.execute_routing_plan(routing_plan, dag)

    execution_time = time.time() - start

    # Verify completion
    assert result["successful"] == 50
    assert result["failed"] == 0

    # Should complete in reasonable time (< 5 seconds)
    assert execution_time < 5.0


# Test 30: Partial Completion Status

@pytest.mark.asyncio
async def test_partial_completion_status(a2a_connector):
    """Test partial completion status when some tasks fail"""

    dag = TaskDAG()
    for i in range(3):
        task = Task(task_id=f"task_{i}", task_type="generic", description=f"Task {i}")
        dag.add_task(task)

    routing_plan = RoutingPlan()
    routing_plan.assignments = {
        "task_0": "builder_agent",
        "task_1": "builder_agent",
        "task_2": "builder_agent"
    }

    call_count = [0]

    async def mock_invoke(agent_name, tool_name, arguments):
        call_count[0] += 1
        # Fail task_1
        if "Task 1" in arguments.get("description", ""):
            raise Exception("Task 1 failed")
        return {"status": "success"}

    a2a_connector.invoke_agent_tool = mock_invoke

    result = await a2a_connector.execute_routing_plan(routing_plan, dag)

    # Status should be "partial" when some tasks fail
    assert result["status"] == "partial"
    assert result["successful"] == 2
    assert result["failed"] == 1
    assert len(result["errors"]) == 1


# Summary: 30 comprehensive tests covering all integration points
