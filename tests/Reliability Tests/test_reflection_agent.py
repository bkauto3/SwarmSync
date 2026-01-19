"""
Unit Tests for ReflectionAgent
Version: 1.0
Last Updated: October 15, 2025

Comprehensive test suite for ReflectionAgent functionality.
Tests all quality dimensions, scoring, pattern learning, and edge cases.
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Import reflection agent
import sys
sys.path.insert(0, '/home/genesis/genesis-rebuild')

from agents.reflection_agent import (
    ReflectionAgent,
    QualityDimension,
    DimensionScore,
    ReflectionResult,
    get_reflection_agent
)


class TestReflectionAgent:
    """Test suite for ReflectionAgent"""

    @pytest.fixture
    def agent(self):
        """Create reflection agent for testing"""
        return ReflectionAgent(
            agent_id="test_agent",
            quality_threshold=0.70,
            use_llm=False  # Use rule-based for testing
        )

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.agent_id == "test_agent"
        assert agent.quality_threshold == 0.70
        assert agent.use_llm == False
        assert agent.total_reflections == 0
        assert agent.total_passes == 0
        assert agent.total_failures == 0

    @pytest.mark.asyncio
    async def test_reflect_code_correctness(self, agent):
        """Test reflection on code correctness"""
        code = """
def calculate(x, y):
    return x + y
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        assert isinstance(result, ReflectionResult)
        assert 0.0 <= result.overall_score <= 1.0
        assert QualityDimension.CORRECTNESS.value in result.dimension_scores

    @pytest.mark.asyncio
    async def test_reflect_code_with_todos(self, agent):
        """Test reflection detects TODO markers"""
        code = """
def process_data():
    # TODO: Implement this
    pass
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        correctness = result.dimension_scores[QualityDimension.CORRECTNESS.value]
        assert any("TODO" in issue for issue in correctness.issues)
        assert correctness.score < 1.0

    @pytest.mark.asyncio
    async def test_reflect_code_security_eval(self, agent):
        """Test security dimension detects eval()"""
        code = """
def unsafe_function(user_input):
    return eval(user_input)  # Dangerous!
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        security = result.dimension_scores[QualityDimension.SECURITY.value]
        assert any("eval" in issue.lower() for issue in security.issues)
        assert security.score < 0.9

    @pytest.mark.asyncio
    async def test_reflect_code_quality_console_log(self, agent):
        """Test quality dimension detects console.log"""
        code = """
function processData(data) {
    console.log('Debug:', data);
    return data;
}
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        quality = result.dimension_scores[QualityDimension.QUALITY.value]
        # The issue text is "Debug statements left in code", not "console.log"
        assert any("Debug statements" in issue for issue in quality.issues)

    @pytest.mark.asyncio
    async def test_reflect_code_performance_select_star(self, agent):
        """Test performance dimension detects SELECT *"""
        code = """
SELECT * FROM users WHERE active = true;
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        performance = result.dimension_scores[QualityDimension.PERFORMANCE.value]
        assert any("SELECT *" in issue for issue in performance.issues)

    @pytest.mark.asyncio
    async def test_reflect_code_completeness_required_features(self, agent):
        """Test completeness dimension checks required features"""
        code = """
function login(username) {
    return authenticate(username);
}
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={
                "required_features": ["login", "logout", "register"]
            }
        )

        completeness = result.dimension_scores[QualityDimension.COMPLETENESS.value]
        # Should detect missing "logout" and "register"
        assert len(completeness.issues) > 0

    @pytest.mark.asyncio
    async def test_reflect_high_quality_code(self, agent):
        """Test reflection on high-quality code"""
        code = """
/**
 * Calculate sum of two numbers
 * @param x First number
 * @param y Second number
 * @returns Sum of x and y
 */
function calculateSum(x: number, y: number): number {
    if (typeof x !== 'number' || typeof y !== 'number') {
        throw new Error('Invalid input: numbers required');
    }
    return x + y;
}
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # High-quality code should score well
        assert result.overall_score >= 0.70
        assert result.passes_threshold == True

    @pytest.mark.asyncio
    async def test_reflect_low_quality_code(self, agent):
        """Test reflection on low-quality code"""
        # Use code with multiple serious issues that will definitely fail
        code = """
x
"""
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # Low-quality code should score poorly
        assert result.overall_score < 0.70
        assert result.passes_threshold == False
        assert len(result.critical_issues) > 0

    @pytest.mark.asyncio
    async def test_overall_score_calculation(self, agent):
        """Test overall score is weighted average"""
        code = "function test() { return true; }"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # Manually calculate weighted average
        total_score = 0.0
        total_weight = 0.0

        for dimension, weight in agent.dimension_weights.items():
            dim_score = result.dimension_scores.get(dimension.value)
            if dim_score:
                total_score += dim_score.score * weight
                total_weight += weight

        expected_overall = total_score / total_weight

        assert abs(result.overall_score - expected_overall) < 0.01

    @pytest.mark.asyncio
    async def test_reflection_updates_statistics(self, agent):
        """Test statistics are updated correctly"""
        initial_total = agent.total_reflections

        code = "def test(): pass"
        await agent.reflect(content=code, content_type="code", context={})

        assert agent.total_reflections == initial_total + 1
        assert (agent.total_passes + agent.total_failures) == agent.total_reflections

    @pytest.mark.asyncio
    async def test_get_statistics(self, agent):
        """Test get_statistics returns correct data"""
        # Perform some reflections
        for i in range(5):
            code = f"function test{i}() {{ return {i}; }}"
            await agent.reflect(content=code, content_type="code", context={})

        stats = agent.get_statistics()

        assert stats["agent_id"] == "test_agent"
        assert stats["total_reflections"] == 5
        assert stats["success_rate"] >= 0.0
        assert stats["success_rate"] <= 1.0
        assert "reasoning_bank_connected" in stats
        assert "replay_buffer_connected" in stats

    @pytest.mark.asyncio
    async def test_reflection_result_structure(self, agent):
        """Test ReflectionResult has all required fields"""
        code = "def example(): return 42"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # Check all fields exist
        assert hasattr(result, 'overall_score')
        assert hasattr(result, 'passes_threshold')
        assert hasattr(result, 'dimension_scores')
        assert hasattr(result, 'summary_feedback')
        assert hasattr(result, 'critical_issues')
        assert hasattr(result, 'suggestions')
        assert hasattr(result, 'reflection_time_seconds')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'metadata')

        # Validate types
        assert isinstance(result.overall_score, float)
        assert isinstance(result.passes_threshold, bool)
        assert isinstance(result.dimension_scores, dict)
        assert isinstance(result.summary_feedback, str)
        assert isinstance(result.critical_issues, list)
        assert isinstance(result.suggestions, list)
        assert isinstance(result.reflection_time_seconds, float)
        assert isinstance(result.timestamp, str)
        assert isinstance(result.metadata, dict)

    @pytest.mark.asyncio
    async def test_dimension_score_structure(self, agent):
        """Test DimensionScore has correct structure"""
        code = "def test(): return True"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        for dim_name, dim_score in result.dimension_scores.items():
            assert isinstance(dim_score, DimensionScore)
            assert dim_score.dimension == dim_name
            assert 0.0 <= dim_score.score <= 1.0
            assert isinstance(dim_score.feedback, str)
            assert isinstance(dim_score.issues, list)
            assert isinstance(dim_score.suggestions, list)

    @pytest.mark.asyncio
    async def test_threshold_boundary_exactly_at_threshold(self, agent):
        """Test behavior when score exactly equals threshold"""
        # This is tricky - we need code that scores exactly 0.70
        # For this test, we'll mock the scoring
        with patch.object(agent, '_calculate_overall_score', return_value=0.70):
            code = "def test(): pass"
            result = await agent.reflect(
                content=code,
                content_type="code",
                context={}
            )

            assert result.overall_score == 0.70
            assert result.passes_threshold == True  # >= threshold

    @pytest.mark.asyncio
    async def test_threshold_boundary_just_below(self, agent):
        """Test behavior when score just below threshold"""
        with patch.object(agent, '_calculate_overall_score', return_value=0.69):
            code = "def test(): pass"
            result = await agent.reflect(
                content=code,
                content_type="code",
                context={}
            )

            assert result.overall_score == 0.69
            assert result.passes_threshold == False  # < threshold

    @pytest.mark.asyncio
    async def test_reflection_time_tracking(self, agent):
        """Test reflection time is tracked"""
        code = "def test(): return 42"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        assert result.reflection_time_seconds >= 0.0
        assert result.reflection_time_seconds < 10.0  # Should be fast

    @pytest.mark.asyncio
    async def test_timestamp_format(self, agent):
        """Test timestamp is ISO format"""
        code = "def test(): pass"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # Should be parseable as ISO datetime
        timestamp = datetime.fromisoformat(result.timestamp.replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)

    @pytest.mark.asyncio
    async def test_metadata_contains_context(self, agent):
        """Test metadata contains relevant context"""
        code = "def test(): pass"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={"custom": "value"}
        )

        assert "content_type" in result.metadata
        assert result.metadata["content_type"] == "code"
        assert "content_length" in result.metadata
        assert "threshold" in result.metadata
        assert "agent_id" in result.metadata

    @pytest.mark.asyncio
    async def test_critical_issues_only_low_scores(self, agent):
        """Test critical issues only added for low scores"""
        # High quality code with comments to avoid penalties
        good_code = """
// Calculate sum of two numbers
function calculate(x: number, y: number): number {
    return x + y;
}
"""
        good_result = await agent.reflect(
            content=good_code,
            content_type="code",
            context={}
        )

        # Very low quality code - minimal length triggers critical correctness score
        bad_code = "x"
        bad_result = await agent.reflect(
            content=bad_code,
            content_type="code",
            context={}
        )

        # Good code should have fewer critical issues (dimensions with score < 0.5)
        assert len(bad_result.critical_issues) > len(good_result.critical_issues)

    @pytest.mark.asyncio
    async def test_suggestions_limited_to_top_10(self, agent):
        """Test suggestions are limited to 10"""
        code = "function test() { console.log('debug'); eval(x); }"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # Even if many suggestions generated, max 10 returned
        assert len(result.suggestions) <= 10

    @pytest.mark.asyncio
    async def test_factory_function(self):
        """Test get_reflection_agent factory function"""
        agent = get_reflection_agent(
            agent_id="factory_test",
            quality_threshold=0.80
        )

        assert isinstance(agent, ReflectionAgent)
        assert agent.agent_id == "factory_test"
        assert agent.quality_threshold == 0.80

    @pytest.mark.asyncio
    async def test_custom_dimension_weights(self):
        """Test custom dimension weights"""
        from agents.reflection_agent import QualityDimension

        custom_weights = {
            QualityDimension.CORRECTNESS: 0.5,
            QualityDimension.SECURITY: 0.5,
            QualityDimension.COMPLETENESS: 0.0,
            QualityDimension.QUALITY: 0.0,
            QualityDimension.PERFORMANCE: 0.0,
            QualityDimension.MAINTAINABILITY: 0.0
        }

        agent = ReflectionAgent(
            agent_id="custom_weights",
            dimension_weights=custom_weights
        )

        assert agent.dimension_weights == custom_weights

    @pytest.mark.asyncio
    async def test_concurrent_reflections(self, agent):
        """Test thread-safe concurrent reflections"""
        codes = [
            "def test1(): pass",
            "def test2(): return 42",
            "function test3() { return true; }",
            "const test4 = () => false;",
            "class Test5 { constructor() {} }"
        ]

        # Run concurrent reflections
        tasks = [
            agent.reflect(content=code, content_type="code", context={})
            for code in codes
        ]

        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == len(codes)
        for result in results:
            assert isinstance(result, ReflectionResult)

        # Statistics should be accurate
        assert agent.total_reflections == len(codes)

    @pytest.mark.asyncio
    async def test_empty_content_handling(self, agent):
        """Test handling of empty content"""
        result = await agent.reflect(
            content="",
            content_type="code",
            context={}
        )

        # Should complete without crashing
        assert isinstance(result, ReflectionResult)
        # Empty content likely scores poorly
        assert result.overall_score < 1.0

    @pytest.mark.asyncio
    async def test_very_long_content(self, agent):
        """Test handling of very long content"""
        long_code = "def function():\n    pass\n" * 1000

        result = await agent.reflect(
            content=long_code,
            content_type="code",
            context={}
        )

        assert isinstance(result, ReflectionResult)
        assert result.metadata["content_length"] == len(long_code)

    @pytest.mark.asyncio
    async def test_all_quality_dimensions_assessed(self, agent):
        """Test all 6 quality dimensions are assessed"""
        code = "function test() { return true; }"
        result = await agent.reflect(
            content=code,
            content_type="code",
            context={}
        )

        # All 6 dimensions should be present
        expected_dimensions = [
            QualityDimension.CORRECTNESS,
            QualityDimension.COMPLETENESS,
            QualityDimension.QUALITY,
            QualityDimension.SECURITY,
            QualityDimension.PERFORMANCE,
            QualityDimension.MAINTAINABILITY
        ]

        for dimension in expected_dimensions:
            assert dimension.value in result.dimension_scores


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
