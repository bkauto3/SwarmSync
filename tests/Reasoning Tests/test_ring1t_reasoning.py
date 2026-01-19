"""
Tests for Ring-1T Multi-Turn Reasoning System

Validates:
- Problem decomposition
- Reasoning loop convergence
- Self-critique and refinement
- Dependency resolution (topological sort)
- Quality assessment
- Solution synthesis
- Integration with observability
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from agents.ring1t_reasoning import Ring1TReasoning, SubProblem, ReasoningAttempt
from infrastructure.observability import ObservabilityManager, CorrelationContext


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    class MockLLM:
        def __init__(self):
            self.call_count = 0

        async def generate_text(
            self,
            system_prompt: str,
            user_prompt: str,
            temperature: float = 0.7,
            max_tokens: int = 4096
        ) -> str:
            self.call_count += 1

            # Decomposition response
            if "Decompose" in user_prompt:
                return '''```json
{
    "sub_problems": [
        {
            "id": "sp1",
            "description": "First sub-problem",
            "dependencies": [],
            "complexity": 0.5
        },
        {
            "id": "sp2",
            "description": "Second sub-problem",
            "dependencies": ["sp1"],
            "complexity": 0.6
        }
    ]
}
```'''

            # Validation response (check first before quality assessment)
            elif "Validate" in user_prompt:
                return '''```json
{
    "quality_score": 0.9,
    "validation_passed": true,
    "issues": []
}
```'''

            # Quality assessment response
            elif "Rate this solution" in user_prompt or "quality" in user_prompt.lower():
                return "0.9"

            # Critique response
            elif "Critically evaluate" in user_prompt:
                return "The solution is mostly correct. Consider edge cases."

            # Default response (reasoning, refinement, synthesis)
            else:
                return "Mock solution with detailed reasoning."

    return MockLLM()


@pytest.fixture
def obs_manager():
    """Observability manager for testing"""
    return ObservabilityManager()


@pytest.mark.asyncio
async def test_ring1t_initialization(mock_llm_client, obs_manager):
    """Test Ring-1T initialization"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client,
        obs_manager=obs_manager
    )

    assert reasoning.max_reasoning_rounds == 3
    assert reasoning.quality_threshold == 0.85
    assert reasoning.llm_client is not None
    assert reasoning.obs_manager is not None


@pytest.mark.asyncio
async def test_ring1t_custom_parameters(mock_llm_client):
    """Test Ring-1T with custom parameters"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client,
        max_reasoning_rounds=5,
        quality_threshold=0.95
    )

    assert reasoning.max_reasoning_rounds == 5
    assert reasoning.quality_threshold == 0.95


@pytest.mark.asyncio
async def test_problem_decomposition(mock_llm_client, obs_manager):
    """Test problem decomposition into sub-problems"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client,
        obs_manager=obs_manager
    )

    ctx = CorrelationContext(user_request="Test problem")

    sub_problems = await reasoning._decompose_problem(
        problem="Test problem",
        context={},
        correlation_context=ctx
    )

    assert len(sub_problems) == 2
    assert all(isinstance(sp, SubProblem) for sp in sub_problems)
    assert sub_problems[0].id == "sp1"
    assert sub_problems[1].id == "sp2"
    assert sub_problems[0].dependencies == []
    assert sub_problems[1].dependencies == ["sp1"]


@pytest.mark.asyncio
async def test_problem_decomposition_fallback(obs_manager):
    """Test problem decomposition fallback on parse error"""
    class FailingLLM:
        async def generate_text(self, **kwargs):
            return "Invalid JSON response"

    reasoning = Ring1TReasoning(
        llm_client=FailingLLM(),
        obs_manager=obs_manager
    )

    ctx = CorrelationContext(user_request="Test")

    sub_problems = await reasoning._decompose_problem(
        problem="Test problem",
        context={},
        correlation_context=ctx
    )

    # Should return single fallback sub-problem
    assert len(sub_problems) == 1
    assert sub_problems[0].id == "sp1"
    assert sub_problems[0].description == "Test problem"


@pytest.mark.asyncio
async def test_topological_sort_simple(mock_llm_client):
    """Test dependency sorting (simple case)"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client
    )

    sub_problems = [
        SubProblem("sp1", "Problem 1", dependencies=["sp2"], complexity=0.5, status="pending"),
        SubProblem("sp2", "Problem 2", dependencies=[], complexity=0.3, status="pending"),
        SubProblem("sp3", "Problem 3", dependencies=["sp1"], complexity=0.7, status="pending"),
    ]

    sorted_problems = reasoning._topological_sort(sub_problems)

    # sp2 should come before sp1, sp1 before sp3
    assert sorted_problems[0].id == "sp2"
    assert sorted_problems[1].id == "sp1"
    assert sorted_problems[2].id == "sp3"


@pytest.mark.asyncio
async def test_topological_sort_complex(mock_llm_client):
    """Test dependency sorting (complex case)"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client
    )

    sub_problems = [
        SubProblem("sp1", "P1", dependencies=[], complexity=0.5, status="pending"),
        SubProblem("sp2", "P2", dependencies=[], complexity=0.3, status="pending"),
        SubProblem("sp3", "P3", dependencies=["sp1", "sp2"], complexity=0.7, status="pending"),
        SubProblem("sp4", "P4", dependencies=["sp3"], complexity=0.8, status="pending"),
    ]

    sorted_problems = reasoning._topological_sort(sub_problems)

    # sp1, sp2 first (any order), then sp3, then sp4
    sp1_idx = next(i for i, sp in enumerate(sorted_problems) if sp.id == "sp1")
    sp2_idx = next(i for i, sp in enumerate(sorted_problems) if sp.id == "sp2")
    sp3_idx = next(i for i, sp in enumerate(sorted_problems) if sp.id == "sp3")
    sp4_idx = next(i for i, sp in enumerate(sorted_problems) if sp.id == "sp4")

    assert sp3_idx > sp1_idx
    assert sp3_idx > sp2_idx
    assert sp4_idx > sp3_idx


@pytest.mark.asyncio
async def test_reasoning_loop_convergence(mock_llm_client, obs_manager):
    """Test reasoning loop converges before max rounds"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client,
        obs_manager=obs_manager,
        quality_threshold=0.85
    )

    sub_problem = SubProblem(
        id="sp1",
        description="Test sub-problem",
        dependencies=[],
        complexity=0.5,
        status="pending"
    )

    ctx = CorrelationContext(user_request="Test")

    result = await reasoning._reasoning_loop(sub_problem, {}, ctx)

    # Should converge in 1 round (quality 0.9 > 0.85)
    assert result["rounds"] == 1
    assert "final_solution" in result
    assert len(result["reasoning_attempts"]) == 1


@pytest.mark.asyncio
async def test_reasoning_loop_max_rounds(obs_manager):
    """Test reasoning loop reaches max rounds"""
    class LowQualityLLM:
        async def generate_text(self, **kwargs):
            if "Rate this solution" in kwargs.get("user_prompt", ""):
                return "0.5"  # Below threshold
            elif "Validate" in kwargs.get("user_prompt", ""):
                return '{"quality_score": 0.5, "validation_passed": false, "issues": []}'
            else:
                return "Mock solution"

    reasoning = Ring1TReasoning(
        llm_client=LowQualityLLM(),
        obs_manager=obs_manager,
        quality_threshold=0.85,
        max_reasoning_rounds=3
    )

    sub_problem = SubProblem(
        id="sp1",
        description="Test",
        dependencies=[],
        complexity=0.5,
        status="pending"
    )

    ctx = CorrelationContext(user_request="Test")

    result = await reasoning._reasoning_loop(sub_problem, {}, ctx)

    # Should reach max rounds (3)
    assert result["rounds"] == 3
    assert len(result["reasoning_attempts"]) == 3


@pytest.mark.asyncio
async def test_quality_assessment(mock_llm_client, obs_manager):
    """Test solution quality assessment"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client,
        obs_manager=obs_manager
    )

    sub_problem = SubProblem(
        id="sp1",
        description="Test",
        dependencies=[],
        complexity=0.5,
        status="pending"
    )

    quality = await reasoning._assess_quality(sub_problem, "Test solution")

    assert 0.0 <= quality <= 1.0
    assert quality == 0.9  # Mock returns 0.9


@pytest.mark.asyncio
async def test_quality_assessment_fallback(obs_manager):
    """Test quality assessment fallback on parse error"""
    class InvalidLLM:
        async def generate_text(self, **kwargs):
            return "Not a number"

    reasoning = Ring1TReasoning(
        llm_client=InvalidLLM(),
        obs_manager=obs_manager
    )

    sub_problem = SubProblem(
        id="sp1",
        description="Test",
        dependencies=[],
        complexity=0.5,
        status="pending"
    )

    quality = await reasoning._assess_quality(sub_problem, "Test solution")

    # Should return default 0.5
    assert quality == 0.5


@pytest.mark.asyncio
async def test_full_solve_workflow(mock_llm_client, obs_manager):
    """Test full solve workflow (decompose → solve → synthesize → validate)"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client,
        obs_manager=obs_manager
    )

    result = await reasoning.solve(
        problem="Test complex problem",
        context={"constraints": "test"}
    )

    assert "solution" in result
    assert "sub_problems" in result
    assert "total_rounds" in result
    assert "quality_score" in result
    assert "validation" in result

    assert len(result["sub_problems"]) == 2
    assert result["total_rounds"] >= 2  # At least 1 round per sub-problem
    assert 0.0 <= result["quality_score"] <= 1.0


@pytest.mark.asyncio
async def test_dependency_resolution(mock_llm_client, obs_manager):
    """Test sub-problems are solved in correct dependency order"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client,
        obs_manager=obs_manager
    )

    ctx = CorrelationContext(user_request="Test")

    # Create sub-problems with dependencies
    sub_problems = [
        SubProblem("sp3", "P3", ["sp1", "sp2"], 0.7, "pending"),
        SubProblem("sp1", "P1", [], 0.5, "pending"),
        SubProblem("sp2", "P2", [], 0.6, "pending"),
    ]

    solved = await reasoning._solve_sub_problems(sub_problems, ctx)

    # Check all solved
    assert all(sp.status == "completed" for sp in solved)
    assert all(sp.solution is not None for sp in solved)

    # Check order: sp1, sp2 before sp3
    sp1_idx = next(i for i, sp in enumerate(solved) if sp.id == "sp1")
    sp2_idx = next(i for i, sp in enumerate(solved) if sp.id == "sp2")
    sp3_idx = next(i for i, sp in enumerate(solved) if sp.id == "sp3")

    assert sp3_idx > sp1_idx
    assert sp3_idx > sp2_idx


@pytest.mark.asyncio
async def test_observability_integration(mock_llm_client, obs_manager):
    """Test observability metrics are recorded"""
    reasoning = Ring1TReasoning(
        llm_client=mock_llm_client,
        obs_manager=obs_manager
    )

    # Mock record_metric
    obs_manager.record_metric = Mock()

    result = await reasoning.solve(problem="Test problem")

    # Check metrics were recorded
    assert obs_manager.record_metric.called
    metric_names = [call[0][0] for call in obs_manager.record_metric.call_args_list]

    assert "ring1t.sub_problems_count" in metric_names
    assert "ring1t.total_reasoning_rounds" in metric_names
    assert "ring1t.quality_score" in metric_names


@pytest.mark.asyncio
async def test_llm_call_count(obs_manager):
    """Test LLM is called expected number of times"""
    class CountingLLM:
        def __init__(self):
            self.call_count = 0

        async def generate_text(self, **kwargs):
            self.call_count += 1
            user_prompt = kwargs.get("user_prompt", "")

            if "Decompose" in user_prompt:
                return '''```json
{
    "sub_problems": [
        {"id": "sp1", "description": "P1", "dependencies": [], "complexity": 0.5}
    ]
}
```'''
            elif "Rate this solution" in user_prompt:
                return "0.9"
            elif "Validate" in user_prompt:
                return '''```json
{
    "quality_score": 0.9,
    "validation_passed": true,
    "issues": []
}
```'''
            else:
                return "Mock solution"

    mock_llm = CountingLLM()

    reasoning = Ring1TReasoning(
        llm_client=mock_llm,
        obs_manager=obs_manager,
        max_reasoning_rounds=2
    )

    await reasoning.solve(problem="Test")

    # Expected calls:
    # 1. Decomposition
    # 2. Reasoning (sp1 round 1)
    # 3. Critique (sp1 round 1)
    # 4. Refinement (sp1 round 1)
    # 5. Quality assessment (sp1 round 1)
    # 6. Synthesis
    # 7. Validation

    assert mock_llm.call_count >= 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
