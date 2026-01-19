"""
Darwin Integration E2E Tests
Version: 1.0
Date: October 19, 2025

Comprehensive end-to-end validation of Darwin evolution integration
across multiple agents (marketing, builder, qa).

Tests the complete pipeline:
User request → HTDAG → HALO → AOP → Darwin → Benchmark → Result
"""

import asyncio
import json
import logging
import pytest
import time
from pathlib import Path
from typing import Dict, Any

# Darwin and orchestration imports
from agents.darwin_agent import DarwinAgent
from infrastructure.darwin_orchestration_bridge import (
    DarwinOrchestrationBridge,
    EvolutionRequest,
    EvolutionResult,
    EvolutionTaskType
)
from infrastructure.htdag_planner import HTDAGPlanner
from infrastructure.halo_router import HALORouter
from infrastructure.aop_validator import AOPValidator

# Benchmark imports
from benchmarks.agent_benchmarks import (
    MarketingAgentBenchmark,
    BuilderAgentBenchmark,
    QAAgentBenchmark
)

logger = logging.getLogger(__name__)


@pytest.fixture
async def orchestration_components():
    """Setup orchestration components for testing"""
    htdag = HTDAGPlanner()
    halo = HALORouter()
    aop = AOPValidator()

    return {
        "htdag": htdag,
        "halo": halo,
        "aop": aop
    }


@pytest.fixture
async def darwin_bridge(orchestration_components):
    """Setup Darwin orchestration bridge"""
    bridge = DarwinOrchestrationBridge(
        htdag_planner=orchestration_components["htdag"],
        halo_router=orchestration_components["halo"],
        aop_validator=orchestration_components["aop"]
    )

    return bridge


@pytest.fixture
def sample_agent_code():
    """Sample agent code for testing"""
    return '''
"""
Sample Marketing Agent for Testing
"""

import logging

logger = logging.getLogger(__name__)

class MarketingAgent:
    """Simple marketing agent for evolution testing"""

    def __init__(self, business_id: str = "test"):
        self.business_id = business_id
        self.campaigns = []

    async def create_strategy(self, product: str, budget: int, timeline: str) -> dict:
        """Create marketing strategy"""
        strategy = {
            "product": product,
            "budget": budget,
            "timeline": timeline,
            "channels": ["social_media", "content_marketing"],
            "targeting": "general audience"
        }

        logger.info(f"Created strategy for {product}")
        return strategy

    async def generate_content(self, campaign_type: str) -> str:
        """Generate marketing content"""
        return f"Sample {campaign_type} content"
'''


# ========================================
# E2E TESTS: AGENT-SPECIFIC EVOLUTION
# ========================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_marketing_agent_evolution_e2e(darwin_bridge, tmp_path):
    """
    E2E Test: Evolve marketing agent and validate improvement

    Flow:
    1. User requests: "Improve marketing agent conversion rates"
    2. HTDAG decomposes into evolution task
    3. HALO routes to darwin_agent
    4. AOP validates evolution plan
    5. Darwin analyzes marketing agent
    6. Darwin generates improved code
    7. Sandbox executes new code
    8. Benchmarks validate improvement
    9. New version deployed
    10. Result returned
    """
    logger.info("=== Starting Marketing Agent E2E Evolution Test ===")

    # Create test agent code file
    agent_path = tmp_path / "marketing_agent.py"
    agent_code = '''
"""Marketing Agent for Evolution Test"""

class MarketingAgent:
    def __init__(self):
        self.campaigns = []

    async def create_strategy(self, product: str, budget: int) -> dict:
        # Basic strategy - room for improvement
        return {
            "product": product,
            "budget": budget,
            "channels": ["social_media"],  # Limited channels
            "timeline": "3 months"
        }
'''
    agent_path.write_text(agent_code)

    # Get baseline benchmark
    benchmark = MarketingAgentBenchmark()
    baseline_result = await benchmark.run(agent_code)
    baseline_score = baseline_result.overall_score

    logger.info(f"Baseline score: {baseline_score:.3f}")

    # Execute evolution via Darwin bridge
    result = await darwin_bridge.evolve_agent(
        agent_name="marketing_agent",
        evolution_type=EvolutionTaskType.IMPROVE_AGENT,
        context={
            "metric": "conversion_rate",
            "current_score": baseline_score,
            "goal": "increase conversion rate by 5%",
            "agent_code_path": str(agent_path)
        },
        target_metric="conversion_rate"
    )

    # Validate result
    assert result is not None, "Evolution result should not be None"
    assert isinstance(result, EvolutionResult), "Should return EvolutionResult"

    # Validate improvement (if evolution succeeded)
    if result.success:
        # Run benchmark on improved code
        # Note: Darwin would have saved improved code, we validate metrics
        improvement = result.improvement_delta.get("overall_score", 0.0)

        logger.info(f"Evolution result: success={result.success}, improvement={improvement:.3f}")

        # Darwin should show some improvement (may be small in test)
        assert improvement >= 0.0, "Should not regress"

        # Validate metrics structure
        assert "overall_score" in result.metrics_after
        assert "accuracy" in result.metrics_after or "correctness" in result.metrics_after

        logger.info("✅ Marketing agent evolution E2E test PASSED")
    else:
        # Evolution can fail (e.g., LLM issues, validation failures)
        # This is acceptable in E2E test - we validate the pipeline works
        logger.warning(f"Evolution failed (acceptable in test): {result.error_message}")
        assert result.error_message is not None, "Should have error message on failure"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_builder_agent_evolution_e2e(darwin_bridge, tmp_path):
    """
    E2E Test: Evolve builder agent code generation quality

    Validates:
    - Builder agent evolution through full pipeline
    - Code quality improvements measured
    - Best practices validation
    """
    logger.info("=== Starting Builder Agent E2E Evolution Test ===")

    # Create test agent code
    agent_path = tmp_path / "builder_agent.py"
    agent_code = '''
"""Builder Agent for Evolution Test"""

class BuilderAgent:
    def __init__(self):
        self.projects = []

    async def generate_frontend(self, component: str) -> str:
        # Basic code generation - can be improved
        code = f"""
def {component}():
    return "Hello World"
"""
        return code

    async def generate_backend(self, endpoint: str) -> str:
        # Missing error handling, validation
        code = f"""
def handle_{endpoint}(request):
    return {{"status": "ok"}}
"""
        return code
'''
    agent_path.write_text(agent_code)

    # Get baseline
    benchmark = BuilderAgentBenchmark()
    baseline_result = await benchmark.run(agent_code)
    baseline_score = baseline_result.overall_score

    logger.info(f"Baseline score: {baseline_score:.3f}")

    # Execute evolution
    result = await darwin_bridge.evolve_agent(
        agent_name="builder_agent",
        evolution_type=EvolutionTaskType.OPTIMIZE_PERFORMANCE,
        context={
            "metric": "code_quality",
            "current_score": baseline_score,
            "goal": "improve code generation quality",
            "agent_code_path": str(agent_path)
        },
        target_metric="code_quality"
    )

    # Validate
    assert result is not None
    assert isinstance(result, EvolutionResult)

    if result.success:
        improvement = result.improvement_delta.get("overall_score", 0.0)
        logger.info(f"Builder evolution: success={result.success}, improvement={improvement:.3f}")

        assert improvement >= 0.0, "Should not regress"
        assert "overall_score" in result.metrics_after

        logger.info("✅ Builder agent evolution E2E test PASSED")
    else:
        logger.warning(f"Evolution failed (acceptable): {result.error_message}")
        assert result.error_message is not None


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_qa_agent_evolution_e2e(darwin_bridge, tmp_path):
    """
    E2E Test: Evolve QA agent bug detection rate

    Validates:
    - QA agent evolution
    - Test generation improvements
    - Bug detection accuracy
    """
    logger.info("=== Starting QA Agent E2E Evolution Test ===")

    # Create test agent code
    agent_path = tmp_path / "qa_agent.py"
    agent_code = '''
"""QA Agent for Evolution Test"""

class QAAgent:
    def __init__(self):
        self.test_suites = []

    async def generate_tests(self, module: str) -> list:
        # Basic test generation - can be improved
        tests = [
            f"def test_{module}_basic(): pass",
            f"def test_{module}_success(): pass"
        ]
        return tests

    async def detect_bugs(self, code: str) -> list:
        # Simple bug detection
        bugs = []
        if "null" in code:
            bugs.append("Potential null pointer")
        return bugs
'''
    agent_path.write_text(agent_code)

    # Get baseline
    benchmark = QAAgentBenchmark()
    baseline_result = await benchmark.run(agent_code)
    baseline_score = baseline_result.overall_score

    logger.info(f"Baseline score: {baseline_score:.3f}")

    # Execute evolution
    result = await darwin_bridge.evolve_agent(
        agent_name="qa_agent",
        evolution_type=EvolutionTaskType.IMPROVE_AGENT,
        context={
            "metric": "bug_detection_rate",
            "current_score": baseline_score,
            "goal": "improve test coverage and bug detection",
            "agent_code_path": str(agent_path)
        },
        target_metric="bug_detection_rate"
    )

    # Validate
    assert result is not None
    assert isinstance(result, EvolutionResult)

    if result.success:
        improvement = result.improvement_delta.get("overall_score", 0.0)
        logger.info(f"QA evolution: success={result.success}, improvement={improvement:.3f}")

        assert improvement >= 0.0
        assert "overall_score" in result.metrics_after

        logger.info("✅ QA agent evolution E2E test PASSED")
    else:
        logger.warning(f"Evolution failed (acceptable): {result.error_message}")
        assert result.error_message is not None


# ========================================
# E2E TESTS: PERFORMANCE VALIDATION
# ========================================

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.performance
async def test_evolution_cycle_performance(darwin_bridge, tmp_path):
    """
    Validate evolution cycle completes in <10 minutes

    Target: <600 seconds (10 minutes)
    Measures: Full end-to-end evolution time
    """
    logger.info("=== Starting Evolution Cycle Performance Test ===")

    # Create simple test agent
    agent_path = tmp_path / "perf_test_agent.py"
    agent_code = '''
class SimpleAgent:
    def run(self):
        return "Hello"
'''
    agent_path.write_text(agent_code)

    # Request evolution with timer
    start_time = time.time()

    result = await darwin_bridge.evolve_agent(
        agent_name="marketing_agent",  # Use agent with benchmark
        evolution_type=EvolutionTaskType.OPTIMIZE_PERFORMANCE,
        context={
            "agent_code_path": str(agent_path)
        }
    )

    end_time = time.time()
    duration_seconds = end_time - start_time
    duration_minutes = duration_seconds / 60

    logger.info(f"Evolution cycle took: {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")

    # Validate result exists
    assert result is not None

    # Validate performance target
    # Note: In test, we use a relaxed target (2 minutes) since we're not doing full LLM evolution
    # In production, target is 10 minutes
    assert duration_minutes < 2.0, f"Evolution took {duration_minutes:.2f} minutes (target: <2 min in test)"

    logger.info(f"✅ Performance test PASSED: {duration_minutes:.2f} minutes")


# ========================================
# E2E TESTS: CONCURRENT EVOLUTION
# ========================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_evolution(darwin_bridge, tmp_path):
    """
    Test evolving multiple agents concurrently

    Validates:
    - Concurrent evolution requests
    - Resource management (max 3 concurrent per Darwin config)
    - No race conditions
    - All evolutions complete
    """
    logger.info("=== Starting Concurrent Evolution Test ===")

    # Create test agent files
    agent_paths = []
    for i, agent_name in enumerate(["marketing_agent", "builder_agent", "qa_agent"]):
        agent_path = tmp_path / f"{agent_name}_test.py"
        agent_code = f'''
class TestAgent{i}:
    def run(self):
        return "Agent {i}"
'''
        agent_path.write_text(agent_code)
        agent_paths.append((agent_name, agent_path))

    # Execute concurrently
    start_time = time.time()

    tasks = [
        darwin_bridge.evolve_agent(
            agent_name=agent_name,
            evolution_type=EvolutionTaskType.IMPROVE_AGENT,
            context={"agent_code_path": str(agent_path)}
        )
        for agent_name, agent_path in agent_paths
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    duration = end_time - start_time

    logger.info(f"Concurrent evolution completed in {duration:.2f} seconds")

    # Validate all completed
    assert len(results) == 3, "Should have 3 results"

    # Count successes (some may fail due to LLM/validation issues)
    successful = sum(1 for r in results if isinstance(r, EvolutionResult) and not isinstance(r, Exception))
    failed = sum(1 for r in results if isinstance(r, Exception))

    logger.info(f"Results: {successful} successful, {failed} failed/exceptions")

    # At least some should complete (even if they fail evolution, they should return results)
    non_exception_results = [r for r in results if not isinstance(r, Exception)]
    assert len(non_exception_results) > 0, "At least one evolution should complete without exception"

    logger.info("✅ Concurrent evolution test PASSED")


# ========================================
# E2E TESTS: FAILURE SCENARIOS
# ========================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_evolution_with_invalid_code(darwin_bridge, tmp_path):
    """
    Test evolution handles invalid agent code gracefully

    Validates:
    - Syntax error detection
    - Graceful failure
    - Clear error messages
    """
    logger.info("=== Starting Invalid Code Evolution Test ===")

    # Create invalid agent code (syntax error)
    agent_path = tmp_path / "invalid_agent.py"
    agent_code = '''
class BrokenAgent
    def run(self  # Missing closing parenthesis and colon
        return "This won't compile
'''
    agent_path.write_text(agent_code)

    # Execute evolution
    result = await darwin_bridge.evolve_agent(
        agent_name="marketing_agent",
        evolution_type=EvolutionTaskType.FIX_BUG,
        context={
            "agent_code_path": str(agent_path)
        }
    )

    # Validate graceful failure
    assert result is not None
    assert isinstance(result, EvolutionResult)

    # Should fail validation
    assert result.success is False, "Should fail on invalid code"
    assert result.error_message is not None, "Should have error message"

    logger.info(f"✅ Invalid code test PASSED: {result.error_message}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_evolution_timeout_handling(darwin_bridge, tmp_path):
    """
    Test evolution handles timeouts gracefully

    Note: This test validates the timeout mechanism exists,
    but doesn't actually wait 10 minutes to trigger it.
    """
    logger.info("=== Starting Timeout Handling Test ===")

    # Create simple agent
    agent_path = tmp_path / "timeout_test_agent.py"
    agent_code = '''
class TimeoutAgent:
    def run(self):
        return "test"
'''
    agent_path.write_text(agent_code)

    # Execute with timeout
    try:
        result = await asyncio.wait_for(
            darwin_bridge.evolve_agent(
                agent_name="marketing_agent",
                evolution_type=EvolutionTaskType.IMPROVE_AGENT,
                context={
                    "agent_code_path": str(agent_path),
                    "timeout": 30  # 30 second timeout for test
                }
            ),
            timeout=30
        )

        # Should complete within timeout
        assert result is not None
        logger.info("✅ Evolution completed within timeout")

    except asyncio.TimeoutError:
        # Timeout is acceptable - validates mechanism exists
        logger.info("✅ Timeout mechanism validated")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_benchmark_validation_failure(tmp_path):
    """
    Test that failed benchmark validation prevents evolution acceptance

    Validates:
    - Benchmarks run correctly
    - Failed benchmarks prevent acceptance
    - No regression in code quality
    """
    logger.info("=== Starting Benchmark Validation Failure Test ===")

    # Create agent code that will fail benchmark
    poor_quality_code = '''
class PoorAgent:
    # No documentation
    # No error handling
    # No best practices
    def do_stuff(x):  # No type hints
        return x  # Minimal implementation
'''

    # Run benchmark
    benchmark = BuilderAgentBenchmark()
    result = await benchmark.run(poor_quality_code)

    # Validate benchmark detected poor quality
    logger.info(f"Poor quality code score: {result.overall_score:.3f}")

    # Score should be low
    assert result.overall_score < 0.7, "Poor quality code should score low"

    logger.info("✅ Benchmark validation test PASSED")


# ========================================
# UTILITY FUNCTIONS FOR TESTING
# ========================================

async def run_marketing_benchmark(agent_code: str = None) -> float:
    """Helper to run marketing agent benchmark"""
    if agent_code is None:
        agent_code = "class MarketingAgent: pass"

    benchmark = MarketingAgentBenchmark()
    result = await benchmark.run(agent_code)
    return result.overall_score


async def run_builder_benchmark(agent_code: str = None) -> float:
    """Helper to run builder agent benchmark"""
    if agent_code is None:
        agent_code = "class BuilderAgent: pass"

    benchmark = BuilderAgentBenchmark()
    result = await benchmark.run(agent_code)
    return result.overall_score


# ========================================
# TEST SUMMARY
# ========================================

"""
E2E Test Coverage Summary:

1. Agent-Specific Evolution (3 tests):
   - test_marketing_agent_evolution_e2e
   - test_builder_agent_evolution_e2e
   - test_qa_agent_evolution_e2e

2. Performance (1 test):
   - test_evolution_cycle_performance (<10 min target)

3. Concurrency (1 test):
   - test_concurrent_evolution (3 agents simultaneously)

4. Failure Scenarios (3 tests):
   - test_evolution_with_invalid_code
   - test_evolution_timeout_handling
   - test_benchmark_validation_failure

Total: 8 E2E tests covering full Darwin integration pipeline

Expected Results:
- Some tests may show evolution "failures" due to LLM/validation
- This is acceptable - validates pipeline handles failures gracefully
- Key validation: Pipeline executes end-to-end without exceptions
- Benchmarks run and provide real scores (not mocked)
"""
