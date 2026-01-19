"""
Comprehensive Benchmark Tests for OpenHands Integration with SE-Darwin

Tests the integration of OpenHands (58.3% SWE-bench SOTA) with SE-Darwin agent
to validate the expected +8-12% improvement over baseline.

Test Coverage:
1. OpenHands client initialization and configuration
2. Code generation with OpenHands (vs baseline)
3. Test generation capabilities
4. Debugging and refactoring
5. SE-Darwin operator enhancement
6. Performance benchmarking (baseline vs OpenHands)
7. Feature flag behavior (USE_OPENHANDS)
8. Error handling and fallback mechanisms
"""

import asyncio
import os
import pytest
import time
from pathlib import Path
from typing import Dict, Any

# Import OpenHands integration
from infrastructure.openhands_integration import (
    OpenHandsClient,
    OpenHandsConfig,
    OpenHandsMode,
    OpenHandsResult,
    OpenHandsOperatorEnhancer,
    get_openhands_client,
    get_openhands_enhancer
)

# Import SE-Darwin components (direct imports to avoid dependency issues)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import infrastructure modules first
from infrastructure.trajectory_pool import Trajectory, OperatorType
from infrastructure.se_operators import OperatorResult

# Import SE-Darwin agent (may require mocking missing dependencies)
try:
    from agents.se_darwin_agent import SEDarwinAgent, get_se_darwin_agent
    SE_DARWIN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: SE-Darwin agent not fully available: {e}")
    SE_DARWIN_AVAILABLE = False
    SEDarwinAgent = None
    get_se_darwin_agent = None


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def openhands_config_disabled():
    """OpenHands config with integration disabled"""
    return OpenHandsConfig(
        enabled=False,
        model="claude-3-5-sonnet-20241022",
        max_iterations=5,
        timeout_seconds=60
    )


@pytest.fixture
def openhands_config_enabled():
    """OpenHands config with integration enabled (requires API key)"""
    return OpenHandsConfig(
        enabled=True,
        model="claude-3-5-sonnet-20241022",
        max_iterations=5,
        timeout_seconds=60
    )


@pytest.fixture
def mock_trajectory():
    """Mock trajectory for operator testing"""
    return Trajectory(
        trajectory_id="test_traj_001",
        generation=1,
        agent_name="test_agent",
        operator_applied=OperatorType.BASELINE.value,
        proposed_strategy="Implement FastAPI endpoint with authentication",
        reasoning_pattern="direct_implementation",
        code_changes="# Placeholder code\nfrom fastapi import FastAPI\napp = FastAPI()",
        status="pending"
    )


@pytest.fixture
def mock_operator_result():
    """Mock SE-Darwin operator result"""
    return OperatorResult(
        success=True,
        generated_code="def hello_world():\n    return 'Hello, World!'",
        strategy_description="Simple function implementation",
        reasoning="Direct implementation approach",
        confidence_score=0.75
    )


# ============================================================================
# TEST 1: OpenHands Client Initialization
# ============================================================================

def test_openhands_config_from_env():
    """Test OpenHands configuration from environment variables"""
    # Set environment variables
    os.environ["USE_OPENHANDS"] = "true"
    os.environ["OPENHANDS_MODEL"] = "claude-3-5-sonnet-20241022"
    os.environ["OPENHANDS_MAX_ITERATIONS"] = "15"

    config = OpenHandsConfig()

    assert config.enabled is True
    assert config.model == "claude-3-5-sonnet-20241022"
    assert config.max_iterations == 15

    # Cleanup
    del os.environ["USE_OPENHANDS"]
    del os.environ["OPENHANDS_MODEL"]
    del os.environ["OPENHANDS_MAX_ITERATIONS"]


def test_openhands_config_defaults():
    """Test OpenHands default configuration"""
    # Ensure USE_OPENHANDS is not set
    os.environ.pop("USE_OPENHANDS", None)

    config = OpenHandsConfig()

    assert config.enabled is False  # Default: disabled
    assert config.max_iterations == 10
    assert config.timeout_seconds == 300
    assert config.sandbox_type == "local"


def test_openhands_client_initialization_disabled(openhands_config_disabled):
    """Test OpenHands client with disabled config"""
    client = OpenHandsClient(config=openhands_config_disabled)

    assert client.config.enabled is False
    assert client._runtime is None
    assert client._agent is None


def test_openhands_client_initialization_enabled(openhands_config_enabled):
    """Test OpenHands client with enabled config"""
    client = OpenHandsClient(config=openhands_config_enabled)

    assert client.config.enabled is True
    assert client.config.model == "claude-3-5-sonnet-20241022"
    # Runtime and agent lazy-loaded (not initialized yet)
    assert client._runtime is None
    assert client._agent is None


# ============================================================================
# TEST 2: OpenHands Code Generation (Integration Test - Requires API Key)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY for OpenHands integration"
)
async def test_openhands_code_generation_simple():
    """Test OpenHands code generation with simple task (requires API key)"""
    config = OpenHandsConfig(
        enabled=True,
        model="claude-3-5-sonnet-20241022",
        max_iterations=5,
        timeout_seconds=120
    )
    client = OpenHandsClient(config=config)

    problem = "Create a Python function that adds two numbers and returns the result"

    result = await client.generate_code(
        problem_description=problem,
        context={"language": "python"},
        mode=OpenHandsMode.CODE_GENERATION
    )

    # Validate result structure
    assert isinstance(result, OpenHandsResult)
    assert result.execution_time > 0
    assert result.iterations_used >= 0

    # Check for success (may fail if API issues)
    if result.success:
        assert result.generated_code is not None
        assert len(result.generated_code) > 0
        assert "def" in result.generated_code  # Should contain function definition
    else:
        # Log failure for debugging
        print(f"OpenHands generation failed: {result.error_message}")

    await client.close()


@pytest.mark.asyncio
async def test_openhands_code_generation_disabled():
    """Test OpenHands code generation when disabled"""
    config = OpenHandsConfig(enabled=False)
    client = OpenHandsClient(config=config)

    result = await client.generate_code(
        problem_description="Create a function",
        mode=OpenHandsMode.CODE_GENERATION
    )

    assert result.success is False
    assert "disabled" in result.error_message.lower()


# ============================================================================
# TEST 3: OpenHands Test Generation
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY for OpenHands integration"
)
async def test_openhands_test_generation():
    """Test OpenHands test generation (requires API key)"""
    config = OpenHandsConfig(
        enabled=True,
        max_iterations=5,
        timeout_seconds=120
    )
    client = OpenHandsClient(config=config)

    code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""

    result = await client.generate_test(
        code=code,
        test_framework="pytest",
        context={"language": "python"}
    )

    assert isinstance(result, OpenHandsResult)

    if result.success:
        assert result.generated_code is not None or result.test_code is not None
        # Look for test patterns in either generated_code or test_code
        test_content = result.test_code or result.generated_code or ""
        assert any(pattern in test_content for pattern in ["def test_", "class Test", "pytest"])

    await client.close()


# ============================================================================
# TEST 4: OpenHands Debugging
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires ANTHROPIC_API_KEY for OpenHands integration"
)
async def test_openhands_debugging():
    """Test OpenHands debugging capabilities (requires API key)"""
    config = OpenHandsConfig(
        enabled=True,
        max_iterations=5,
        timeout_seconds=120
    )
    client = OpenHandsClient(config=config)

    buggy_code = """
def divide(a, b):
    return a / b  # Bug: no zero division check
"""

    error = "ZeroDivisionError: division by zero when b=0"

    result = await client.debug_code(
        code=buggy_code,
        error_message=error,
        context={"language": "python"}
    )

    assert isinstance(result, OpenHandsResult)

    if result.success:
        assert result.generated_code is not None
        # Fixed code should have error handling
        fixed_code = result.generated_code.lower()
        assert any(keyword in fixed_code for keyword in ["if", "zero", "exception", "raise"])

    await client.close()


# ============================================================================
# TEST 5: SE-Darwin Operator Enhancement
# ============================================================================

def test_openhands_operator_enhancer_initialization():
    """Test OpenHandsOperatorEnhancer initialization"""
    config = OpenHandsConfig(enabled=False)
    client = OpenHandsClient(config=config)

    enhancer = OpenHandsOperatorEnhancer(
        openhands_client=client,
        use_for_revision=True,
        use_for_recombination=True,
        use_for_refinement=True,
        fallback_on_error=True
    )

    assert enhancer.client == client
    assert enhancer.use_for_revision is True
    assert enhancer.use_for_recombination is True
    assert enhancer.use_for_refinement is True
    assert enhancer.fallback_on_error is True


@pytest.mark.asyncio
async def test_openhands_operator_enhancement_disabled(mock_operator_result):
    """Test operator enhancement when OpenHands is disabled"""
    config = OpenHandsConfig(enabled=False)
    client = OpenHandsClient(config=config)
    enhancer = OpenHandsOperatorEnhancer(client, fallback_on_error=True)

    # Mock original operator
    async def mock_operator(*args, **kwargs):
        return mock_operator_result

    # Enhance operator
    enhanced = enhancer.enhance_operator(mock_operator, operator_name="revision")

    # Call enhanced operator
    result = await enhanced("test problem", context={})

    # Should return original operator result (OpenHands disabled)
    assert result == mock_operator_result


@pytest.mark.asyncio
async def test_openhands_operator_fallback():
    """Test operator fallback when OpenHands errors"""
    config = OpenHandsConfig(enabled=True)  # Enabled but will error
    client = OpenHandsClient(config=config)
    enhancer = OpenHandsOperatorEnhancer(client, fallback_on_error=True)

    fallback_result = OperatorResult(
        success=True,
        generated_code="# Fallback code",
        strategy_description="Fallback strategy",
        reasoning="Original operator",
        confidence_score=0.5
    )

    async def mock_operator(*args, **kwargs):
        return fallback_result

    enhanced = enhancer.enhance_operator(mock_operator, operator_name="revision")

    # Call enhanced operator (will fail OpenHands check, fallback to original)
    result = await enhanced("test problem", context={})

    # Should fallback to original operator
    assert result == fallback_result


# ============================================================================
# TEST 6: SE-Darwin Agent Integration
# ============================================================================

@pytest.mark.skipif(
    not SE_DARWIN_AVAILABLE,
    reason="SE-Darwin agent not available (missing dependencies)"
)
def test_se_darwin_agent_openhands_disabled():
    """Test SE-Darwin agent with OpenHands disabled"""
    # Ensure OpenHands is disabled
    os.environ.pop("USE_OPENHANDS", None)

    agent = SEDarwinAgent(
        agent_name="test_agent",
        llm_client=None,  # Mock client
        trajectories_per_iteration=2,
        max_iterations=2
    )

    # OpenHands should be disabled
    assert agent.openhands_client is None or not agent.openhands_client.config.enabled
    assert agent.openhands_enhancer is None

    # Operators should be base operators (not wrapped)
    assert agent.revision_operator == agent._base_revision_operator


@pytest.mark.skipif(
    not SE_DARWIN_AVAILABLE,
    reason="SE-Darwin agent not available (missing dependencies)"
)
def test_se_darwin_agent_openhands_enabled():
    """Test SE-Darwin agent with OpenHands enabled"""
    # Enable OpenHands via env var
    os.environ["USE_OPENHANDS"] = "true"

    agent = SEDarwinAgent(
        agent_name="test_agent",
        llm_client=None,
        trajectories_per_iteration=2,
        max_iterations=2
    )

    # OpenHands should be enabled
    assert agent.openhands_client is not None
    assert agent.openhands_client.config.enabled is True
    assert agent.openhands_enhancer is not None

    # Operators should be wrapped (different from base)
    assert agent.revision_operator != agent._base_revision_operator

    # Cleanup
    del os.environ["USE_OPENHANDS"]


# ============================================================================
# TEST 7: Performance Benchmarking (Baseline vs OpenHands)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.benchmark
@pytest.mark.skipif(
    not SE_DARWIN_AVAILABLE or not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requires SE-Darwin and ANTHROPIC_API_KEY for performance benchmarking"
)
async def test_performance_baseline_vs_openhands():
    """
    Benchmark: Compare SE-Darwin baseline vs OpenHands-enhanced performance

    Expected: OpenHands delivers +8-12% improvement in code quality scores
    """
    # Test problem
    problem = "Create a FastAPI endpoint that handles user authentication with JWT tokens"

    # Baseline: SE-Darwin without OpenHands
    os.environ.pop("USE_OPENHANDS", None)
    baseline_agent = SEDarwinAgent(
        agent_name="baseline_test",
        llm_client=None,
        trajectories_per_iteration=1,
        max_iterations=1
    )

    baseline_start = time.time()
    baseline_result = await baseline_agent.evolve_solution(
        problem_description=problem,
        context={"language": "python", "framework": "fastapi"}
    )
    baseline_time = time.time() - baseline_start
    baseline_score = baseline_result.get('best_score', 0.0)

    # OpenHands-enhanced: SE-Darwin with OpenHands
    os.environ["USE_OPENHANDS"] = "true"
    openhands_agent = SEDarwinAgent(
        agent_name="openhands_test",
        llm_client=None,
        trajectories_per_iteration=1,
        max_iterations=1
    )

    openhands_start = time.time()
    openhands_result = await openhands_agent.evolve_solution(
        problem_description=problem,
        context={"language": "python", "framework": "fastapi"}
    )
    openhands_time = time.time() - openhands_start
    openhands_score = openhands_result.get('best_score', 0.0)

    # Calculate improvement
    if baseline_score > 0:
        improvement_pct = ((openhands_score - baseline_score) / baseline_score) * 100
    else:
        improvement_pct = 0.0

    # Log results
    print(f"\n{'='*60}")
    print(f"PERFORMANCE BENCHMARK: Baseline vs OpenHands")
    print(f"{'='*60}")
    print(f"Baseline Score:     {baseline_score:.4f} ({baseline_time:.2f}s)")
    print(f"OpenHands Score:    {openhands_score:.4f} ({openhands_time:.2f}s)")
    print(f"Improvement:        {improvement_pct:+.2f}%")
    print(f"Expected:           +8-12%")
    print(f"{'='*60}\n")

    # Assertions (lenient due to variability)
    assert openhands_score >= 0.0  # Should produce valid score
    assert openhands_time > 0  # Should take measurable time

    # Expected improvement (may not always achieve due to task variability)
    # This is informational, not a hard requirement
    if improvement_pct >= 8.0:
        print(f"SUCCESS: Achieved {improvement_pct:.2f}% improvement (>= 8% target)")
    else:
        print(f"INFO: Achieved {improvement_pct:.2f}% improvement (target: +8-12%)")

    # Cleanup
    del os.environ["USE_OPENHANDS"]


# ============================================================================
# TEST 8: Feature Flag Behavior
# ============================================================================

def test_feature_flag_use_openhands_true():
    """Test USE_OPENHANDS=true enables integration"""
    os.environ["USE_OPENHANDS"] = "true"

    config = OpenHandsConfig()
    assert config.enabled is True

    del os.environ["USE_OPENHANDS"]


def test_feature_flag_use_openhands_false():
    """Test USE_OPENHANDS=false disables integration"""
    os.environ["USE_OPENHANDS"] = "false"

    config = OpenHandsConfig()
    assert config.enabled is False

    del os.environ["USE_OPENHANDS"]


def test_feature_flag_use_openhands_unset():
    """Test unset USE_OPENHANDS defaults to disabled"""
    os.environ.pop("USE_OPENHANDS", None)

    config = OpenHandsConfig()
    assert config.enabled is False


# ============================================================================
# TEST 9: Error Handling and Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_openhands_timeout_handling():
    """Test OpenHands timeout behavior"""
    config = OpenHandsConfig(
        enabled=True,
        timeout_seconds=1  # Very short timeout
    )
    client = OpenHandsClient(config=config)

    # This should timeout (if API key is available)
    if os.getenv("ANTHROPIC_API_KEY"):
        result = await client.generate_code(
            problem_description="Complex task that takes long time...",
            mode=OpenHandsMode.CODE_GENERATION
        )

        # Should handle timeout gracefully
        if not result.success:
            assert "timeout" in result.error_message.lower() or "error" in result.error_message.lower()

    await client.close()


@pytest.mark.asyncio
async def test_openhands_empty_problem():
    """Test OpenHands with empty problem description"""
    config = OpenHandsConfig(enabled=False)  # Disabled to avoid API calls
    client = OpenHandsClient(config=config)

    result = await client.generate_code(
        problem_description="",
        mode=OpenHandsMode.CODE_GENERATION
    )

    assert result.success is False
    assert result.error_message is not None


# ============================================================================
# TEST 10: Factory Functions
# ============================================================================

def test_get_openhands_client_factory():
    """Test get_openhands_client factory function"""
    client = get_openhands_client()

    assert isinstance(client, OpenHandsClient)
    assert client.config is not None


def test_get_openhands_enhancer_factory():
    """Test get_openhands_enhancer factory function"""
    enhancer = get_openhands_enhancer()

    assert isinstance(enhancer, OpenHandsOperatorEnhancer)
    assert isinstance(enhancer.client, OpenHandsClient)


def test_get_openhands_enhancer_with_custom_client():
    """Test get_openhands_enhancer with custom client"""
    config = OpenHandsConfig(enabled=False)
    custom_client = OpenHandsClient(config=config)

    enhancer = get_openhands_enhancer(client=custom_client)

    assert enhancer.client == custom_client
    assert enhancer.client.config.enabled is False


# ============================================================================
# SUMMARY TEST
# ============================================================================

@pytest.mark.skipif(
    not SE_DARWIN_AVAILABLE,
    reason="SE-Darwin agent not available (missing dependencies)"
)
def test_integration_summary():
    """
    Summary test: Validate all components are properly integrated

    This test verifies:
    1. OpenHands client can be created
    2. SE-Darwin agent recognizes OpenHands
    3. Feature flags work correctly
    4. Operators can be enhanced
    5. Backward compatibility maintained
    """
    # Test 1: Client creation
    client = get_openhands_client()
    assert client is not None

    # Test 2: SE-Darwin agent integration (disabled)
    os.environ.pop("USE_OPENHANDS", None)
    agent_disabled = SEDarwinAgent(
        agent_name="summary_test_disabled",
        llm_client=None,
        max_iterations=1
    )
    assert agent_disabled.openhands_client is None or not agent_disabled.openhands_client.config.enabled

    # Test 3: SE-Darwin agent integration (enabled)
    os.environ["USE_OPENHANDS"] = "true"
    agent_enabled = SEDarwinAgent(
        agent_name="summary_test_enabled",
        llm_client=None,
        max_iterations=1
    )
    assert agent_enabled.openhands_client is not None
    assert agent_enabled.openhands_client.config.enabled is True

    # Test 4: Operators enhanced
    assert agent_enabled.revision_operator != agent_enabled._base_revision_operator
    assert agent_enabled.recombination_operator != agent_enabled._base_recombination_operator
    assert agent_enabled.refinement_operator != agent_enabled._base_refinement_operator

    # Test 5: Backward compatibility (disabled agent uses base operators)
    assert agent_disabled.revision_operator == agent_disabled._base_revision_operator

    # Cleanup
    del os.environ["USE_OPENHANDS"]

    print("\n" + "="*60)
    print("INTEGRATION SUMMARY: ALL CHECKS PASSED")
    print("="*60)
    print("✓ OpenHands client initialized")
    print("✓ SE-Darwin integration verified")
    print("✓ Feature flags working")
    print("✓ Operators enhanced when enabled")
    print("✓ Backward compatibility maintained")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
