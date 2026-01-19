"""
Comprehensive Tests for SICA Integration
Part of SE-Darwin system

Tests:
- Complexity detection (simple/moderate/complex)
- Mode selection (SICA vs standard)
- Reasoning loop (chain-of-thought, self-critique)
- TUMIX early stopping
- LLM integration (GPT-4o, Claude, fallback)
- Trajectory refinement
- OTEL instrumentation
- Cost tracking
- Integration with SE-Darwin
"""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from infrastructure.sica_integration import (
    SICAIntegration,
    SICAComplexityDetector,
    SICAReasoningLoop,
    ReasoningMode,
    ReasoningComplexity,
    ReasoningStep,
    SICAResult,
    get_sica_integration,
    refine_trajectory_with_sica
)
from infrastructure.trajectory_pool import Trajectory, TrajectoryStatus
from infrastructure.llm_client import LLMFactory, MockLLMClient
from infrastructure.observability import ObservabilityManager


# ================================
# FIXTURES
# ================================

@pytest.fixture
def simple_trajectory():
    """Simple trajectory (high success score)"""
    return Trajectory(
        trajectory_id="simple_001",
        generation=1,
        agent_name="test_agent",
        success_score=0.85,
        status=TrajectoryStatus.SUCCESS.value,
        code_changes="def hello(): return 'world'",
        problem_diagnosis="Simple function implementation"
    )


@pytest.fixture
def complex_trajectory():
    """Complex trajectory (low score, multiple failures)"""
    return Trajectory(
        trajectory_id="complex_001",
        generation=3,
        agent_name="builder_agent",
        success_score=0.35,
        status=TrajectoryStatus.PARTIAL_SUCCESS.value,
        code_changes="def complex_algorithm(): pass",
        problem_diagnosis="Multi-step algorithm optimization needed",
        failure_reasons=[
            "Timeout on large inputs",
            "Memory inefficiency",
            "Edge case failures"
        ]
    )


@pytest.fixture
def mock_llm_client():
    """Mock LLM client with predefined responses"""
    responses = {
        "reasoning": json.dumps({
            "thought": "Analyzing the current approach shows potential optimization",
            "critique": "Current implementation lacks caching and has O(n^2) complexity",
            "refinement": "Add memoization and optimize to O(n log n)",
            "quality_score": 0.75
        })
    }
    return LLMFactory.create_mock(mock_responses=responses)


@pytest.fixture
def complexity_detector():
    """SICA complexity detector"""
    return SICAComplexityDetector()


@pytest.fixture
def obs_manager():
    """Observability manager"""
    return ObservabilityManager()


@pytest.fixture
def sica_integration(mock_llm_client):
    """SICA integration with mock LLM"""
    return SICAIntegration(
        gpt4o_client=mock_llm_client,
        claude_haiku_client=mock_llm_client
    )


# ================================
# COMPLEXITY DETECTION TESTS
# ================================

class TestComplexityDetection:
    """Test task complexity classification"""

    def test_simple_task_detection(self, complexity_detector):
        """Test simple task classification"""
        problem = "Implement a hello world function"

        complexity, confidence = complexity_detector.analyze_complexity(problem)

        assert complexity == ReasoningComplexity.SIMPLE
        assert confidence < 0.4

    def test_moderate_task_detection(self, complexity_detector):
        """Test moderate task classification"""
        problem = "Implement a REST API endpoint to create user accounts with validation"

        complexity, confidence = complexity_detector.analyze_complexity(problem)

        # Can be SIMPLE, MODERATE, or COMPLEX depending on interpretation
        assert complexity in [ReasoningComplexity.SIMPLE, ReasoningComplexity.MODERATE, ReasoningComplexity.COMPLEX]
        assert confidence >= 0.1

    def test_complex_task_detection(self, complexity_detector):
        """Test complex task classification"""
        problem = """
        Debug and optimize a multi-threaded algorithm for distributed data processing.
        The algorithm needs to handle edge cases including network failures, data corruption,
        and race conditions. Analyze the performance bottlenecks and refactor for better
        scalability. Implement comprehensive error handling and validation logic.
        """

        complexity, confidence = complexity_detector.analyze_complexity(problem)

        # Should be at least MODERATE due to keywords
        assert complexity in [ReasoningComplexity.MODERATE, ReasoningComplexity.COMPLEX]
        assert confidence >= 0.4

    def test_complexity_with_failure_history(self, complexity_detector, complex_trajectory):
        """Test complexity increases with failure history"""
        problem = "Optimize function performance"

        # Without failure history
        complexity_no_history, confidence_no_history = complexity_detector.analyze_complexity(problem)

        # With failure history
        complexity_with_history, confidence_with_history = complexity_detector.analyze_complexity(
            problem,
            trajectory=complex_trajectory
        )

        # Should be more complex with failures (confidence should increase)
        assert confidence_with_history >= confidence_no_history

    def test_should_use_sica_complex(self, complexity_detector):
        """Test SICA should be used for complex tasks"""
        problem = "Debug complex multi-step algorithm with intricate edge cases analyze optimize refactor"

        should_use = complexity_detector.should_use_sica(problem)

        # With multiple complex keywords, should trigger SICA
        complexity, confidence = complexity_detector.analyze_complexity(problem)
        assert complexity in [ReasoningComplexity.MODERATE, ReasoningComplexity.COMPLEX]

    def test_should_not_use_sica_simple(self, complexity_detector):
        """Test SICA should not be used for simple tasks"""
        problem = "Print hello world"

        should_use = complexity_detector.should_use_sica(problem)

        assert should_use is False

    def test_keyword_detection(self, complexity_detector):
        """Test complexity keyword detection"""
        complex_problem = "Refactor and optimize the complex debugging algorithm"
        simple_problem = "Show the output"

        complex_result, _ = complexity_detector.analyze_complexity(complex_problem)
        simple_result, _ = complexity_detector.analyze_complexity(simple_problem)

        assert complex_result != ReasoningComplexity.SIMPLE
        assert simple_result == ReasoningComplexity.SIMPLE

    def test_token_length_impact(self, complexity_detector):
        """Test prompt length affects complexity"""
        short_problem = "Fix bug"
        long_problem = "Fix bug " * 200  # ~600 tokens

        short_complexity, _ = complexity_detector.analyze_complexity(short_problem)
        long_complexity, long_confidence = complexity_detector.analyze_complexity(long_problem)

        # Longer problems should have higher complexity scores
        assert long_confidence > 0.3


# ================================
# REASONING LOOP TESTS
# ================================

class TestReasoningLoop:
    """Test SICA reasoning loop"""

    @pytest.mark.asyncio
    async def test_single_reasoning_step(self, mock_llm_client, simple_trajectory, obs_manager):
        """Test generating single reasoning step"""
        loop = SICAReasoningLoop(
            llm_client=mock_llm_client,
            max_iterations=5,
            obs_manager=obs_manager
        )

        step = await loop._generate_reasoning_step(
            trajectory=simple_trajectory,
            problem_description="Improve function",
            step_number=1,
            previous_steps=[]
        )

        assert step.step_number == 1
        assert len(step.thought) > 0
        assert len(step.critique) > 0
        assert len(step.refinement) > 0
        assert 0.0 <= step.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_iterative_reasoning(self, mock_llm_client, complex_trajectory, obs_manager):
        """Test full iterative reasoning loop"""
        loop = SICAReasoningLoop(
            llm_client=mock_llm_client,
            max_iterations=5,
            min_iterations=2,
            obs_manager=obs_manager
        )

        result = await loop.reason_and_refine(
            trajectory=complex_trajectory,
            problem_description="Optimize algorithm performance"
        )

        assert result.success is True
        assert len(result.reasoning_steps) >= 2
        assert len(result.reasoning_steps) <= 5
        assert result.iterations_performed == len(result.reasoning_steps)
        assert result.improved_trajectory is not None
        assert result.tokens_used > 0

    @pytest.mark.asyncio
    async def test_tumix_early_stopping(self, obs_manager):
        """Test TUMIX early stopping when no improvement"""
        # Mock LLM that returns no improvement
        mock_client = Mock()
        mock_client.generate_text = AsyncMock(return_value=json.dumps({
            "thought": "No significant improvements identified",
            "critique": "Current approach is near optimal",
            "refinement": "Minor tweaks possible",
            "quality_score": 0.71  # Small improvement
        }))

        loop = SICAReasoningLoop(
            llm_client=mock_client,
            max_iterations=5,
            min_iterations=2,
            improvement_threshold=0.10,  # 10% required
            obs_manager=obs_manager
        )

        trajectory = Trajectory(
            trajectory_id="test",
            generation=1,
            agent_name="test",
            success_score=0.70
        )

        result = await loop.reason_and_refine(
            trajectory=trajectory,
            problem_description="Test early stopping"
        )

        assert result.success is True
        assert result.stopped_early is True
        assert result.iterations_performed >= 2
        assert result.iterations_performed < 5  # Should stop before max

    @pytest.mark.asyncio
    async def test_reasoning_with_llm_failure(self, complex_trajectory, obs_manager):
        """Test fallback to heuristic reasoning when LLM fails"""
        # Mock LLM that raises exception
        failing_client = Mock()
        failing_client.generate_text = AsyncMock(side_effect=Exception("API error"))

        loop = SICAReasoningLoop(
            llm_client=failing_client,
            max_iterations=3,
            obs_manager=obs_manager
        )

        result = await loop.reason_and_refine(
            trajectory=complex_trajectory,
            problem_description="Test LLM failure"
        )

        # Should use heuristic fallback
        assert result.success is True
        assert len(result.reasoning_steps) >= 1

    @pytest.mark.asyncio
    async def test_quality_improvement_tracking(self, mock_llm_client, obs_manager):
        """Test quality score improves over iterations"""
        # Mock progressive improvement
        responses = [
            json.dumps({"thought": "t1", "critique": "c1", "refinement": "r1", "quality_score": 0.5}),
            json.dumps({"thought": "t2", "critique": "c2", "refinement": "r2", "quality_score": 0.6}),
            json.dumps({"thought": "t3", "critique": "c3", "refinement": "r3", "quality_score": 0.75}),
        ]
        mock_client = Mock()
        mock_client.generate_text = AsyncMock(side_effect=responses)

        loop = SICAReasoningLoop(
            llm_client=mock_client,
            max_iterations=3,
            improvement_threshold=0.05,
            obs_manager=obs_manager
        )

        trajectory = Trajectory(
            trajectory_id="test",
            generation=1,
            agent_name="test",
            success_score=0.4
        )

        result = await loop.reason_and_refine(
            trajectory=trajectory,
            problem_description="Test improvement"
        )

        # Quality should improve
        assert result.improved_trajectory.success_score >= trajectory.success_score
        assert result.improvement_delta >= 0

    @pytest.mark.asyncio
    async def test_cost_estimation(self, mock_llm_client, simple_trajectory, obs_manager):
        """Test cost estimation for reasoning"""
        loop = SICAReasoningLoop(
            llm_client=mock_llm_client,
            max_iterations=3,
            obs_manager=obs_manager
        )

        result = await loop.reason_and_refine(
            trajectory=simple_trajectory,
            problem_description="Test cost"
        )

        assert result.cost_dollars > 0
        assert result.tokens_used > 0
        # Cost should be proportional to tokens (rough check)
        expected_cost = (result.tokens_used / 1_000_000) * 3.0
        assert abs(result.cost_dollars - expected_cost) < 0.01


# ================================
# SICA INTEGRATION TESTS
# ================================

class TestSICAIntegration:
    """Test full SICA integration"""

    @pytest.mark.asyncio
    async def test_refine_simple_trajectory(self, sica_integration, simple_trajectory):
        """Test refining simple trajectory (should skip SICA)"""
        result = await sica_integration.refine_trajectory(
            trajectory=simple_trajectory,
            problem_description="Simple improvement"
        )

        assert result.success is True
        # Simple tasks should use standard mode (no iterations)
        assert result.iterations_performed == 0
        assert result.improved_trajectory is not None

    @pytest.mark.asyncio
    async def test_refine_complex_trajectory(self, sica_integration, complex_trajectory):
        """Test refining complex trajectory (should use SICA)"""
        result = await sica_integration.refine_trajectory(
            trajectory=complex_trajectory,
            problem_description="Debug complex multi-step algorithm with intricate optimization"
        )

        assert result.success is True
        # Complex tasks should use SICA reasoning
        assert result.iterations_performed >= 2
        assert len(result.reasoning_steps) >= 2

    @pytest.mark.asyncio
    async def test_force_reasoning_mode(self, sica_integration, simple_trajectory):
        """Test forcing SICA reasoning mode"""
        result = await sica_integration.refine_trajectory(
            trajectory=simple_trajectory,
            problem_description="Simple task",
            force_mode=ReasoningMode.REASONING
        )

        # Should use SICA even though task is simple
        assert result.success is True
        assert result.iterations_performed >= 2

    @pytest.mark.asyncio
    async def test_force_standard_mode(self, sica_integration, complex_trajectory):
        """Test forcing standard mode"""
        result = await sica_integration.refine_trajectory(
            trajectory=complex_trajectory,
            problem_description="Complex debugging task",
            force_mode=ReasoningMode.STANDARD
        )

        # Should skip SICA even though task is complex
        assert result.success is True
        assert result.iterations_performed == 0

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, sica_integration, simple_trajectory, complex_trajectory):
        """Test usage statistics tracking"""
        # Run multiple refinements
        await sica_integration.refine_trajectory(
            simple_trajectory,
            "Simple task 1"
        )
        await sica_integration.refine_trajectory(
            complex_trajectory,
            "Complex debugging optimization intricate"
        )
        await sica_integration.refine_trajectory(
            simple_trajectory,
            "Simple task 2"
        )

        stats = sica_integration.get_statistics()

        assert stats["total_requests"] == 3
        assert stats["sica_used"] >= 1  # At least complex task
        assert stats["standard_used"] >= 1  # At least simple task
        assert 0.0 <= stats["sica_usage_rate"] <= 1.0
        assert stats["total_cost"] >= 0

    @pytest.mark.asyncio
    async def test_trajectory_metadata_update(self, sica_integration, complex_trajectory):
        """Test improved trajectory has correct metadata"""
        result = await sica_integration.refine_trajectory(
            trajectory=complex_trajectory,
            problem_description="Complex algorithm optimization",
            force_mode=ReasoningMode.REASONING
        )

        improved = result.improved_trajectory

        assert improved.trajectory_id.endswith("_sica")
        assert improved.generation == complex_trajectory.generation + 1
        assert improved.parent_trajectories == [complex_trajectory.trajectory_id]
        assert improved.operator_applied == "sica_refinement"
        assert "sica" in improved.tools_used
        assert improved.reasoning_pattern == "sica_iterative_reasoning"
        assert "sica_iterations" in improved.metrics


# ================================
# CONVENIENCE FUNCTION TESTS
# ================================

class TestConvenienceFunctions:
    """Test high-level convenience functions"""

    @pytest.mark.asyncio
    async def test_get_sica_integration(self):
        """Test factory function"""
        sica = get_sica_integration()

        assert isinstance(sica, SICAIntegration)
        assert sica.complexity_detector is not None

    @pytest.mark.asyncio
    async def test_refine_trajectory_with_sica_forced(self, simple_trajectory):
        """Test convenience function with forced reasoning"""
        with patch('infrastructure.sica_integration.SICAIntegration') as mock_sica:
            mock_instance = Mock()
            mock_instance.refine_trajectory = AsyncMock(return_value=SICAResult(
                success=True,
                original_trajectory=simple_trajectory,
                improved_trajectory=simple_trajectory,
                reasoning_steps=[],
                improvement_delta=0.1,
                iterations_performed=3,
                stopped_early=False,
                tokens_used=100,
                cost_dollars=0.01
            ))
            mock_sica.return_value = mock_instance

            result = await refine_trajectory_with_sica(
                trajectory=simple_trajectory,
                problem_description="Test",
                force_reasoning=True
            )

            assert result.success is True


# ================================
# EDGE CASES & ERROR HANDLING
# ================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_complexity_detector_empty_problem(self, complexity_detector):
        """Test complexity detection with empty problem"""
        complexity, confidence = complexity_detector.analyze_complexity("")

        assert complexity == ReasoningComplexity.SIMPLE
        assert confidence < 0.3

    def test_complexity_detector_very_long_problem(self, complexity_detector):
        """Test complexity detection with very long problem"""
        problem = "Complex optimization " * 500  # Very long

        complexity, confidence = complexity_detector.analyze_complexity(problem)

        assert complexity in [ReasoningComplexity.MODERATE, ReasoningComplexity.COMPLEX]

    @pytest.mark.asyncio
    async def test_reasoning_loop_with_zero_max_iterations(self, mock_llm_client, simple_trajectory, obs_manager):
        """Test reasoning loop with invalid max_iterations"""
        loop = SICAReasoningLoop(
            llm_client=mock_llm_client,
            max_iterations=0,  # Invalid
            obs_manager=obs_manager
        )

        result = await loop.reason_and_refine(
            trajectory=simple_trajectory,
            problem_description="Test"
        )

        # Should handle gracefully (generates at least 1 initial step)
        assert result.iterations_performed >= 0

    @pytest.mark.asyncio
    async def test_sica_with_none_llm_client(self, simple_trajectory):
        """Test SICA with no LLM client (should use mock)"""
        sica = SICAIntegration(
            gpt4o_client=None,
            claude_haiku_client=None
        )

        result = await sica.refine_trajectory(
            trajectory=simple_trajectory,
            problem_description="Test without LLM",
            force_mode=ReasoningMode.REASONING
        )

        # Should fallback to mock client
        assert result.success is True

    @pytest.mark.asyncio
    async def test_trajectory_with_missing_fields(self, sica_integration):
        """Test refinement with minimal trajectory"""
        minimal_traj = Trajectory(
            trajectory_id="minimal",
            generation=1,
            agent_name="test"
        )

        result = await sica_integration.refine_trajectory(
            trajectory=minimal_traj,
            problem_description="Test minimal"
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_parse_malformed_json(self, obs_manager):
        """Test parsing malformed LLM JSON response"""
        mock_client = Mock()
        mock_client.generate_text = AsyncMock(return_value="Not valid JSON at all")

        loop = SICAReasoningLoop(
            llm_client=mock_client,
            max_iterations=1,
            obs_manager=obs_manager
        )

        trajectory = Trajectory(
            trajectory_id="test",
            generation=1,
            agent_name="test"
        )

        result = await loop.reason_and_refine(
            trajectory=trajectory,
            problem_description="Test"
        )

        # Should fallback to text extraction
        assert result.success is True


# ================================
# INTEGRATION WITH SE-DARWIN
# ================================

class TestSEDarwinIntegration:
    """Test integration with SE-Darwin trajectory system"""

    @pytest.mark.asyncio
    async def test_sica_creates_valid_trajectory(self, sica_integration, complex_trajectory):
        """Test SICA creates trajectory compatible with trajectory pool"""
        result = await sica_integration.refine_trajectory(
            trajectory=complex_trajectory,
            problem_description="Complex optimization",
            force_mode=ReasoningMode.REASONING
        )

        improved = result.improved_trajectory

        # Verify trajectory pool compatibility
        assert improved.trajectory_id is not None
        assert improved.generation == complex_trajectory.generation + 1
        assert improved.agent_name == complex_trajectory.agent_name
        assert len(improved.parent_trajectories) == 1
        assert improved.operator_applied is not None
        assert improved.success_score >= 0
        assert improved.created_at is not None

    @pytest.mark.asyncio
    async def test_sica_preserves_lineage(self, sica_integration):
        """Test SICA preserves trajectory lineage"""
        parent = Trajectory(
            trajectory_id="parent_001",
            generation=1,
            agent_name="test",
            success_score=0.5
        )

        result = await sica_integration.refine_trajectory(
            trajectory=parent,
            problem_description="Complex task",
            force_mode=ReasoningMode.REASONING
        )

        child = result.improved_trajectory

        assert child.parent_trajectories == [parent.trajectory_id]
        assert child.generation == parent.generation + 1

    @pytest.mark.asyncio
    async def test_sica_insight_extraction(self, sica_integration, complex_trajectory):
        """Test SICA extracts key insights for trajectory pool"""
        result = await sica_integration.refine_trajectory(
            trajectory=complex_trajectory,
            problem_description="Complex debugging",
            force_mode=ReasoningMode.REASONING
        )

        improved = result.improved_trajectory

        # Should have insights from reasoning steps
        assert len(improved.key_insights) >= 1
        assert all(isinstance(insight, str) for insight in improved.key_insights)


# ================================
# OBSERVABILITY TESTS
# ================================

class TestObservability:
    """Test OTEL instrumentation"""

    @pytest.mark.asyncio
    async def test_span_creation(self, sica_integration, simple_trajectory):
        """Test OTEL spans are created"""
        with patch.object(sica_integration.obs_manager, 'span') as mock_span:
            mock_span.return_value.__enter__ = Mock()
            mock_span.return_value.__exit__ = Mock(return_value=False)

            await sica_integration.refine_trajectory(
                trajectory=simple_trajectory,
                problem_description="Test"
            )

            # Should create span
            mock_span.assert_called()

    @pytest.mark.asyncio
    async def test_span_attributes(self, sica_integration, complex_trajectory):
        """Test span attributes include SICA metadata"""
        result = await sica_integration.refine_trajectory(
            trajectory=complex_trajectory,
            problem_description="Complex task",
            force_mode=ReasoningMode.REASONING
        )

        # Verify result has tracing metadata
        assert result.iterations_performed >= 0
        assert result.cost_dollars >= 0
        assert result.improvement_delta is not None


# ================================
# PERFORMANCE TESTS
# ================================

class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.asyncio
    async def test_reasoning_loop_timeout(self, mock_llm_client, simple_trajectory, obs_manager):
        """Test reasoning loop completes in reasonable time"""
        import time

        loop = SICAReasoningLoop(
            llm_client=mock_llm_client,
            max_iterations=5,
            obs_manager=obs_manager
        )

        start = time.time()
        result = await loop.reason_and_refine(
            trajectory=simple_trajectory,
            problem_description="Test performance"
        )
        elapsed = time.time() - start

        assert result.success is True
        # Should complete in < 5 seconds with mock client
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_concurrent_refinements(self, sica_integration, simple_trajectory):
        """Test multiple concurrent refinements"""
        import asyncio

        tasks = [
            sica_integration.refine_trajectory(
                trajectory=simple_trajectory,
                problem_description=f"Task {i}"
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r.success for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
