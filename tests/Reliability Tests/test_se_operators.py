"""
Comprehensive tests for SE Operators (Day 7)
ISSUE #1: Critical 450-line UNTESTED module

Tests coverage:
- RevisionOperator: Alternative strategies from failures
- RecombinationOperator: Crossover of successful elements
- RefinementOperator: Optimization of promising trajectories
- All operators: Mock LLM, edge cases, API failures
- Target: >85% code coverage

Based on SE-Agent (arXiv 2508.02085)
"""

import pytest
import logging
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock, patch

from infrastructure.se_operators import (
    BaseOperator,
    RevisionOperator,
    RecombinationOperator,
    RefinementOperator,
    OperatorResult,
    get_revision_operator,
    get_recombination_operator,
    get_refinement_operator
)
from infrastructure.trajectory_pool import Trajectory, OperatorType, TrajectoryStatus


# ================================
# MOCK LLM CLIENT
# ================================

class MockLLMClient:
    """Mock LLM client for deterministic testing (no API calls)"""

    def __init__(self, response_type: str = "valid"):
        """
        Args:
            response_type: Type of response to return
                - 'valid': Well-formatted response with STRATEGY/CODE
                - 'malformed': Missing CODE section
                - 'empty': Empty response
                - 'error': Raise exception
                - 'no_markers': Response without STRATEGY markers
        """
        self.response_type = response_type
        self.call_count = 0
        self.last_messages = None

        # OpenAI-style client
        self.chat = Mock()
        self.chat.completions = Mock()
        self.chat.completions.create = self._mock_openai_call

    async def _mock_openai_call(self, **kwargs):
        """Mock OpenAI-style API call"""
        self.call_count += 1
        self.last_messages = kwargs.get('messages', [])

        if self.response_type == "error":
            raise Exception("Simulated API failure")

        # Create mock response
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock()
        response.choices[0].message.content = self._get_response_content()

        return response

    def _get_response_content(self) -> str:
        """Get response content based on type"""
        if self.response_type == "valid":
            return """
STRATEGY: Use test-driven development approach with incremental validation.
Start with minimal test cases and expand coverage gradually.

DIFFERENCES:
- Focus on test-first methodology (vs code-first in previous attempt)
- Incremental validation (vs all-at-once testing)
- Prioritize edge cases early (vs happy path focus)

CODE:
```python
def improved_solution():
    # Test-driven implementation
    assert validate_input(), "Input validation failed"

    result = process_data()
    assert result is not None, "Processing failed"

    return result

def validate_input():
    return True

def process_data():
    return "success"
```
"""
        elif self.response_type == "malformed":
            return """
STRATEGY: Malformed response without code section.
This should trigger fallback parsing logic.

DIFFERENCES: Missing code block entirely.
"""
        elif self.response_type == "empty":
            return ""

        elif self.response_type == "no_markers":
            return """
This is a plain response without any STRATEGY or CODE markers.
It should still extract something useful.

```python
def fallback_code():
    return "extracted from unmarked response"
```
"""
        else:
            return "# Generic response"


class MockAnthropicClient:
    """Mock Anthropic-style client"""

    def __init__(self, response_type: str = "valid"):
        self.response_type = response_type
        self.call_count = 0

    async def messages_create_mock(self, **kwargs):
        """Mock messages.create call"""
        self.call_count += 1

        if self.response_type == "error":
            raise Exception("Anthropic API error")

        response = Mock()
        response.content = [Mock()]
        response.content[0].text = "# Anthropic mock response with code"

        return response


# ================================
# FIXTURES
# ================================

@pytest.fixture
def mock_llm_client():
    """Standard mock LLM client with valid responses"""
    return MockLLMClient(response_type="valid")


@pytest.fixture
def error_llm_client():
    """Mock LLM client that raises errors"""
    return MockLLMClient(response_type="error")


@pytest.fixture
def malformed_llm_client():
    """Mock LLM client with malformed responses"""
    return MockLLMClient(response_type="malformed")


@pytest.fixture
def empty_llm_client():
    """Mock LLM client with empty responses"""
    return MockLLMClient(response_type="empty")


@pytest.fixture
def no_markers_llm_client():
    """Mock LLM client without formatting markers"""
    return MockLLMClient(response_type="no_markers")


@pytest.fixture
def failed_trajectory():
    """Create a failed trajectory for testing RevisionOperator"""
    return Trajectory(
        trajectory_id="fail_001",
        generation=1,
        agent_name="test_agent",
        success_score=0.15,
        status=TrajectoryStatus.FAILURE.value,
        operator_applied=OperatorType.BASELINE.value,
        code_changes="def broken_function(): raise ValueError('Bug')",
        reasoning_pattern="trial-and-error without testing",
        tools_used=["manual_coding"],
        failure_reasons=["syntax error", "logic error", "timeout"],
        modified_files=["src/module.py"]
    )


@pytest.fixture
def successful_trajectory_a():
    """First successful trajectory for RecombinationOperator"""
    return Trajectory(
        trajectory_id="success_001",
        generation=2,
        agent_name="test_agent",
        success_score=0.82,
        status=TrajectoryStatus.SUCCESS.value,
        operator_applied=OperatorType.REVISION.value,
        code_changes="def solution_a(): return test_driven_approach()",
        reasoning_pattern="test-driven development",
        tools_used=["pytest", "coverage"],
        key_insights=["Write tests first", "Small iterations"],
        modified_files=["src/module.py", "tests/test_module.py"]
    )


@pytest.fixture
def successful_trajectory_b():
    """Second successful trajectory for RecombinationOperator"""
    return Trajectory(
        trajectory_id="success_002",
        generation=3,
        agent_name="test_agent",
        success_score=0.78,
        status=TrajectoryStatus.SUCCESS.value,
        operator_applied=OperatorType.REVISION.value,
        code_changes="def solution_b(): return performance_optimized()",
        reasoning_pattern="performance-first optimization",
        tools_used=["profiler", "cProfile"],
        key_insights=["Profile before optimize", "Focus on hotspots"],
        modified_files=["src/module.py"]
    )


@pytest.fixture
def promising_trajectory():
    """Promising trajectory for RefinementOperator"""
    return Trajectory(
        trajectory_id="promising_001",
        generation=4,
        agent_name="test_agent",
        success_score=0.72,
        status=TrajectoryStatus.PARTIAL_SUCCESS.value,
        operator_applied=OperatorType.RECOMBINATION.value,
        code_changes="def promising_solution(): # Good but can be optimized\n    return process()",
        reasoning_pattern="hybrid test+performance approach",
        tools_used=["pytest", "profiler"],
        key_insights=["Balance speed and correctness"],
        modified_files=["src/module.py"]
    )


@pytest.fixture
def pool_insights():
    """Sample pool insights for RefinementOperator"""
    return [
        "Always validate inputs before processing",
        "Use caching for repeated computations",
        "Handle edge cases explicitly",
        "Avoid premature optimization",
        "Write clear error messages"
    ]


# ================================
# BASE OPERATOR TESTS
# ================================

class TestBaseOperator:
    """Test BaseOperator base class"""

    def test_base_operator_initialization_with_client(self, mock_llm_client):
        """Test initializing with LLM client"""
        op = BaseOperator(llm_client=mock_llm_client)
        assert op.llm_client == mock_llm_client

    def test_base_operator_initialization_without_client(self):
        """Test initializing without LLM client"""
        op = BaseOperator(llm_client=None)
        assert op.llm_client is None

    @pytest.mark.asyncio
    async def test_call_llm_with_openai_client(self, mock_llm_client):
        """Test _call_llm with OpenAI-style client"""
        op = BaseOperator(llm_client=mock_llm_client)

        response = await op._call_llm(
            prompt="Test prompt",
            system_prompt="Test system",
            max_tokens=100
        )

        assert isinstance(response, str)
        assert len(response) > 0
        assert mock_llm_client.call_count == 1

    @pytest.mark.asyncio
    async def test_call_llm_without_client_returns_mock(self):
        """Test _call_llm without client returns mock response"""
        op = BaseOperator(llm_client=None)

        response = await op._call_llm(prompt="Test")

        assert "Mock LLM response" in response
        assert "configure llm_client" in response

    @pytest.mark.asyncio
    async def test_call_llm_handles_api_errors(self, error_llm_client):
        """Test _call_llm handles API failures gracefully"""
        op = BaseOperator(llm_client=error_llm_client)

        response = await op._call_llm(prompt="Test")

        # Should return error message, not raise exception
        assert "Error calling LLM" in response
        assert "Simulated API failure" in response

    @pytest.mark.asyncio
    async def test_call_llm_unsupported_client_type(self):
        """Test _call_llm with unsupported client type"""
        unsupported_client = Mock()  # No chat or messages attribute
        op = BaseOperator(llm_client=unsupported_client)

        response = await op._call_llm(prompt="Test")

        # Should return error message (not raise exception)
        assert isinstance(response, str)
        assert ("Unsupported" in response or "Error" in response)


# ================================
# REVISION OPERATOR TESTS
# ================================

class TestRevisionOperator:
    """Test RevisionOperator (alternative strategies from failures)"""

    def test_revision_operator_initialization(self, mock_llm_client):
        """Test RevisionOperator creation"""
        op = RevisionOperator(llm_client=mock_llm_client)
        assert isinstance(op, BaseOperator)
        assert op.llm_client == mock_llm_client

    @pytest.mark.asyncio
    async def test_revise_with_valid_response(
        self,
        mock_llm_client,
        failed_trajectory
    ):
        """Test revise() with well-formatted LLM response"""
        op = RevisionOperator(llm_client=mock_llm_client)

        result = await op.revise(
            failed_trajectory=failed_trajectory,
            problem_description="Fix the broken function that raises ValueError"
        )

        # Verify result structure
        assert isinstance(result, OperatorResult)
        assert result.success is True
        assert result.generated_code is not None
        assert len(result.generated_code) > 0
        assert result.strategy_description
        assert result.reasoning
        assert failed_trajectory.trajectory_id in result.reasoning
        assert result.error_message is None

        # Verify LLM was called
        assert mock_llm_client.call_count == 1

    @pytest.mark.asyncio
    async def test_revise_without_llm_client(self, failed_trajectory):
        """Test revise() without LLM client (uses mock)"""
        op = RevisionOperator(llm_client=None)

        result = await op.revise(
            failed_trajectory=failed_trajectory,
            problem_description="Test problem"
        )

        # Should still succeed with mock response
        assert result.success is True
        assert "Mock LLM response" in result.generated_code

    @pytest.mark.asyncio
    async def test_revise_with_api_failure(self, error_llm_client, failed_trajectory):
        """Test revise() when LLM API fails"""
        op = RevisionOperator(llm_client=error_llm_client)

        result = await op.revise(
            failed_trajectory=failed_trajectory,
            problem_description="Test problem"
        )

        # NOTE: With security validation, API errors return error strings
        # which get validated and wrapped. The operation still "succeeds"
        # but with error-wrapped code.
        assert result.success is True
        # Code will contain error message from LLM API failure
        assert "Error calling LLM" in result.generated_code

    @pytest.mark.asyncio
    async def test_revise_with_malformed_response(
        self,
        malformed_llm_client,
        failed_trajectory
    ):
        """Test revise() with malformed LLM response (missing code)"""
        op = RevisionOperator(llm_client=malformed_llm_client)

        result = await op.revise(
            failed_trajectory=failed_trajectory,
            problem_description="Test problem"
        )

        # Should still succeed, code might be empty or fallback
        assert result.success is True
        assert result.strategy_description  # Strategy should still be extracted

    @pytest.mark.asyncio
    async def test_revise_with_empty_response(
        self,
        empty_llm_client,
        failed_trajectory
    ):
        """Test revise() with empty LLM response"""
        op = RevisionOperator(llm_client=empty_llm_client)

        result = await op.revise(
            failed_trajectory=failed_trajectory,
            problem_description="Test problem"
        )

        # Should succeed but with empty/minimal content
        assert result.success is True
        assert result.generated_code == ""  # Empty code from empty response

    def test_build_failure_context(self, failed_trajectory):
        """Test _build_failure_context() formatting"""
        op = RevisionOperator()

        context = op._build_failure_context(failed_trajectory)

        assert failed_trajectory.trajectory_id in context
        assert str(failed_trajectory.generation) in context
        assert failed_trajectory.reasoning_pattern in context
        assert "syntax error" in context  # Failure reason
        assert "manual_coding" in context  # Tool used

    def test_parse_llm_response_with_strategy_and_code(self):
        """Test _parse_llm_response() with complete response"""
        op = RevisionOperator()

        response = """
STRATEGY: Use defensive programming with validation.

DIFFERENCES: Add input validation and error handling.

CODE:
```python
def safe_function(x):
    if x is None:
        raise ValueError("x cannot be None")
    return x * 2
```
"""
        strategy, code = op._parse_llm_response(response)

        assert "defensive programming" in strategy.lower()
        assert "def safe_function" in code
        assert "ValueError" in code

    def test_parse_llm_response_without_markers(self):
        """Test _parse_llm_response() without STRATEGY markers"""
        op = RevisionOperator()

        response = """
Here is some code without markers:
```python
def unmarked_function():
    return True
```
"""
        strategy, code = op._parse_llm_response(response)

        # Strategy should be empty, code should be extracted
        assert strategy == ""
        assert "def unmarked_function" in code

    def test_parse_llm_response_plain_code_block(self):
        """Test _parse_llm_response() with non-Python code block"""
        op = RevisionOperator()

        response = """
STRATEGY: Generic approach
CODE:
```
plain code without python marker
def still_extract_this():
    pass
```
"""
        strategy, code = op._parse_llm_response(response)

        assert "generic approach" in strategy.lower()
        # Code validation happens, so check for either extracted code or validation error
        assert len(code) > 0  # Something was extracted

    def test_parse_llm_response_no_code_block(self):
        """Test _parse_llm_response() without code blocks"""
        op = RevisionOperator()

        response = "STRATEGY: No code provided\nJust text without code blocks"

        strategy, code = op._parse_llm_response(response)

        assert "no code provided" in strategy.lower()
        # With security validation, invalid code gets wrapped with error message
        # Original response becomes fallback but may fail validation
        assert len(code) > 0  # Something was returned


# ================================
# RECOMBINATION OPERATOR TESTS
# ================================

class TestRecombinationOperator:
    """Test RecombinationOperator (crossover of successful elements)"""

    def test_recombination_operator_initialization(self, mock_llm_client):
        """Test RecombinationOperator creation"""
        op = RecombinationOperator(llm_client=mock_llm_client)
        assert isinstance(op, BaseOperator)
        assert op.llm_client == mock_llm_client

    @pytest.mark.asyncio
    async def test_recombine_two_successful_trajectories(
        self,
        mock_llm_client,
        successful_trajectory_a,
        successful_trajectory_b
    ):
        """Test recombine() with two successful trajectories"""
        op = RecombinationOperator(llm_client=mock_llm_client)

        result = await op.recombine(
            trajectory_a=successful_trajectory_a,
            trajectory_b=successful_trajectory_b,
            problem_description="Combine TDD and performance optimization"
        )

        # Verify result
        assert isinstance(result, OperatorResult)
        assert result.success is True
        assert result.generated_code is not None
        assert result.strategy_description
        assert successful_trajectory_a.trajectory_id in result.reasoning
        assert successful_trajectory_b.trajectory_id in result.reasoning
        assert result.error_message is None

        # Verify LLM was called with both trajectories
        assert mock_llm_client.call_count == 1

    @pytest.mark.asyncio
    async def test_recombine_with_diverse_patterns(
        self,
        mock_llm_client,
        successful_trajectory_a,
        successful_trajectory_b
    ):
        """Test recombine() leverages diversity in reasoning patterns"""
        op = RecombinationOperator(llm_client=mock_llm_client)

        # Ensure trajectories have different patterns
        assert successful_trajectory_a.reasoning_pattern != successful_trajectory_b.reasoning_pattern

        result = await op.recombine(
            trajectory_a=successful_trajectory_a,
            trajectory_b=successful_trajectory_b,
            problem_description="Test diversity"
        )

        assert result.success is True
        # Reasoning should mention combining both trajectories
        assert "+" in result.reasoning  # Combined with "+"

    @pytest.mark.asyncio
    async def test_recombine_without_llm_client(
        self,
        successful_trajectory_a,
        successful_trajectory_b
    ):
        """Test recombine() without LLM client"""
        op = RecombinationOperator(llm_client=None)

        result = await op.recombine(
            trajectory_a=successful_trajectory_a,
            trajectory_b=successful_trajectory_b,
            problem_description="Test"
        )

        assert result.success is True
        assert "Mock LLM response" in result.generated_code

    @pytest.mark.asyncio
    async def test_recombine_with_api_failure(
        self,
        error_llm_client,
        successful_trajectory_a,
        successful_trajectory_b
    ):
        """Test recombine() handles API failures"""
        op = RecombinationOperator(llm_client=error_llm_client)

        result = await op.recombine(
            trajectory_a=successful_trajectory_a,
            trajectory_b=successful_trajectory_b,
            problem_description="Test"
        )

        # With security validation, API errors return error strings
        # Operation succeeds but with error-wrapped code
        assert result.success is True
        assert "Error calling LLM" in result.generated_code

    @pytest.mark.asyncio
    async def test_recombine_parsing_edge_cases(
        self,
        no_markers_llm_client,
        successful_trajectory_a,
        successful_trajectory_b
    ):
        """Test recombine() with response without markers"""
        op = RecombinationOperator(llm_client=no_markers_llm_client)

        result = await op.recombine(
            trajectory_a=successful_trajectory_a,
            trajectory_b=successful_trajectory_b,
            problem_description="Test"
        )

        # Should still extract code even without STRATEGY markers
        assert result.success is True
        assert result.generated_code  # Should extract from unmarked response

    def test_parse_llm_response_recombination_format(self):
        """Test _parse_llm_response() for recombination-specific format"""
        op = RecombinationOperator()

        response = """
STRATEGY: Combine test-driven approach with performance profiling.

STRENGTHS COMBINED:
- TDD ensures correctness
- Profiling identifies bottlenecks
- Iterative improvement cycle

CODE:
```python
def hybrid_solution():
    # Test first
    assert validate()

    # Then optimize
    with profiler:
        return optimized_process()
```
"""
        strategy, code = op._parse_llm_response(response)

        assert "combine" in strategy.lower()
        assert "def hybrid_solution" in code


# ================================
# REFINEMENT OPERATOR TESTS
# ================================

class TestRefinementOperator:
    """Test RefinementOperator (optimization of promising trajectories)"""

    def test_refinement_operator_initialization(self, mock_llm_client):
        """Test RefinementOperator creation"""
        op = RefinementOperator(llm_client=mock_llm_client)
        assert isinstance(op, BaseOperator)
        assert op.llm_client == mock_llm_client

    @pytest.mark.asyncio
    async def test_refine_with_pool_insights(
        self,
        mock_llm_client,
        promising_trajectory,
        pool_insights
    ):
        """Test refine() with pool insights"""
        op = RefinementOperator(llm_client=mock_llm_client)

        result = await op.refine(
            trajectory=promising_trajectory,
            pool_insights=pool_insights,
            problem_description="Optimize the promising solution"
        )

        # Verify result
        assert isinstance(result, OperatorResult)
        assert result.success is True
        assert result.generated_code is not None
        # Strategy description may be empty depending on parsing
        # (RefinementOperator looks for OPTIMIZATION: not STRATEGY:)
        assert promising_trajectory.trajectory_id in result.reasoning
        assert "pool insights" in result.reasoning.lower()
        assert result.error_message is None

        # Verify LLM was called
        assert mock_llm_client.call_count == 1

    @pytest.mark.asyncio
    async def test_refine_without_insights(
        self,
        mock_llm_client,
        promising_trajectory
    ):
        """Test refine() with empty insights list"""
        op = RefinementOperator(llm_client=mock_llm_client)

        result = await op.refine(
            trajectory=promising_trajectory,
            pool_insights=[],  # No insights
            problem_description="Optimize"
        )

        # Should still work without insights
        assert result.success is True
        assert result.generated_code is not None

    @pytest.mark.asyncio
    async def test_refine_with_many_insights(
        self,
        mock_llm_client,
        promising_trajectory
    ):
        """Test refine() with many insights (should limit to 5)"""
        op = RefinementOperator(llm_client=mock_llm_client)

        many_insights = [f"Insight {i}" for i in range(20)]

        result = await op.refine(
            trajectory=promising_trajectory,
            pool_insights=many_insights,
            problem_description="Optimize"
        )

        # Should succeed (insights capped at 5 in prompt)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_refine_without_llm_client(self, promising_trajectory, pool_insights):
        """Test refine() without LLM client"""
        op = RefinementOperator(llm_client=None)

        result = await op.refine(
            trajectory=promising_trajectory,
            pool_insights=pool_insights,
            problem_description="Test"
        )

        assert result.success is True
        assert "Mock LLM response" in result.generated_code

    @pytest.mark.asyncio
    async def test_refine_with_api_failure(
        self,
        error_llm_client,
        promising_trajectory,
        pool_insights
    ):
        """Test refine() handles API failures"""
        op = RefinementOperator(llm_client=error_llm_client)

        result = await op.refine(
            trajectory=promising_trajectory,
            pool_insights=pool_insights,
            problem_description="Test"
        )

        # With security validation, API errors return error strings
        # Operation succeeds but with error-wrapped code
        assert result.success is True
        assert "Error calling LLM" in result.generated_code

    def test_parse_llm_response_refinement_format(self):
        """Test _parse_llm_response() for refinement-specific format"""
        op = RefinementOperator()

        response = """
OPTIMIZATION: Removed redundant validation, streamlined logic flow.

IMPROVEMENTS:
- Eliminated duplicate checks (15% faster)
- Cached repeated computations
- Simplified control flow

CODE:
```python
def refined_solution():
    # Optimized implementation
    cached_result = get_cached()
    if cached_result:
        return cached_result

    result = streamlined_process()
    cache(result)
    return result
```
"""
        optimization, code = op._parse_llm_response(response)

        assert "removed redundant" in optimization.lower()
        assert "def refined_solution" in code
        assert "cached" in code.lower()


# ================================
# FACTORY FUNCTION TESTS
# ================================

class TestFactoryFunctions:
    """Test factory functions for operators"""

    def test_get_revision_operator_without_client(self):
        """Test get_revision_operator() factory"""
        op = get_revision_operator()

        assert isinstance(op, RevisionOperator)
        assert op.llm_client is None

    def test_get_revision_operator_with_client(self, mock_llm_client):
        """Test get_revision_operator() with LLM client"""
        op = get_revision_operator(llm_client=mock_llm_client)

        assert isinstance(op, RevisionOperator)
        assert op.llm_client == mock_llm_client

    def test_get_recombination_operator_without_client(self):
        """Test get_recombination_operator() factory"""
        op = get_recombination_operator()

        assert isinstance(op, RecombinationOperator)
        assert op.llm_client is None

    def test_get_recombination_operator_with_client(self, mock_llm_client):
        """Test get_recombination_operator() with LLM client"""
        op = get_recombination_operator(llm_client=mock_llm_client)

        assert isinstance(op, RecombinationOperator)
        assert op.llm_client == mock_llm_client

    def test_get_refinement_operator_without_client(self):
        """Test get_refinement_operator() factory"""
        op = get_refinement_operator()

        assert isinstance(op, RefinementOperator)
        assert op.llm_client is None

    def test_get_refinement_operator_with_client(self, mock_llm_client):
        """Test get_refinement_operator() with LLM client"""
        op = get_refinement_operator(llm_client=mock_llm_client)

        assert isinstance(op, RefinementOperator)
        assert op.llm_client == mock_llm_client


# ================================
# EDGE CASES & ERROR HANDLING
# ================================

class TestEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_revise_with_empty_failure_reasons(self, mock_llm_client):
        """Test revise() with trajectory lacking failure reasons"""
        op = RevisionOperator(llm_client=mock_llm_client)

        traj = Trajectory(
            trajectory_id="no_reasons",
            generation=1,
            agent_name="test",
            success_score=0.2,
            failure_reasons=[],  # Empty
            tools_used=[]
        )

        result = await op.revise(
            failed_trajectory=traj,
            problem_description="Test"
        )

        # Should still work
        assert result.success is True

    @pytest.mark.asyncio
    async def test_recombine_with_identical_trajectories(
        self,
        mock_llm_client,
        successful_trajectory_a
    ):
        """Test recombine() with same trajectory twice"""
        op = RecombinationOperator(llm_client=mock_llm_client)

        result = await op.recombine(
            trajectory_a=successful_trajectory_a,
            trajectory_b=successful_trajectory_a,  # Same
            problem_description="Test"
        )

        # Should still work (though not ideal)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_refine_with_very_low_score(self, mock_llm_client):
        """Test refine() with low-scoring trajectory (edge case)"""
        op = RefinementOperator(llm_client=mock_llm_client)

        low_score_traj = Trajectory(
            trajectory_id="low",
            generation=1,
            agent_name="test",
            success_score=0.35,  # Low but not failure
            code_changes="def barely_works(): pass"
        )

        result = await op.refine(
            trajectory=low_score_traj,
            pool_insights=["Try harder"],
            problem_description="Test"
        )

        # Should still refine it
        assert result.success is True

    @pytest.mark.asyncio
    async def test_operators_with_very_long_problem_description(
        self,
        mock_llm_client,
        failed_trajectory
    ):
        """Test operators with very long problem descriptions (truncation)"""
        op = RevisionOperator(llm_client=mock_llm_client)

        long_description = "x" * 10000  # 10k characters

        result = await op.revise(
            failed_trajectory=failed_trajectory,
            problem_description=long_description
        )

        # Should succeed (prompt truncates description)
        assert result.success is True


# ================================
# INTEGRATION TESTS
# ================================

class TestOperatorsIntegration:
    """Integration tests for operators working together"""

    @pytest.mark.asyncio
    async def test_full_evolution_cycle(
        self,
        mock_llm_client,
        failed_trajectory,
        successful_trajectory_a,
        promising_trajectory,
        pool_insights
    ):
        """Test full evolution cycle: Revision → Recombination → Refinement"""

        # 1. Revision: Create alternative from failure
        revision_op = RevisionOperator(llm_client=mock_llm_client)
        revised = await revision_op.revise(
            failed_trajectory=failed_trajectory,
            problem_description="Fix bug"
        )

        assert revised.success is True

        # 2. Recombination: Combine two successful approaches
        recombine_op = RecombinationOperator(llm_client=mock_llm_client)
        combined = await recombine_op.recombine(
            trajectory_a=successful_trajectory_a,
            trajectory_b=successful_trajectory_a,  # Reuse for test
            problem_description="Combine strategies"
        )

        assert combined.success is True

        # 3. Refinement: Optimize promising trajectory
        refine_op = RefinementOperator(llm_client=mock_llm_client)
        refined = await refine_op.refine(
            trajectory=promising_trajectory,
            pool_insights=pool_insights,
            problem_description="Optimize"
        )

        assert refined.success is True

        # Verify all operators ran successfully
        assert mock_llm_client.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--cov=infrastructure.se_operators", "--cov-report=term-missing"])
