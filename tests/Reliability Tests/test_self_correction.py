"""
Unit tests for Self-Correction Infrastructure
Version: 1.0
Created: October 24, 2025

Tests the state-based self-correction loop with QA validation.

Test Coverage:
- First attempt valid scenarios (5 tests)
- Correction success scenarios (5 tests)
- Max attempts failure scenarios (5 tests)
- QA feedback parsing (5 tests)
- Integration with agents (5 tests)

Total: 25 tests
"""

import asyncio
import json
import pytest
from datetime import datetime
from typing import Any, Dict, Optional

from infrastructure.self_correction import (
    SelfCorrectingAgent,
    ValidationCategory,
    ValidationIssue,
    QAFeedback,
    CorrectionStats,
    get_self_correcting_agent
)


# ============================================================================
# MOCK AGENTS FOR TESTING
# ============================================================================


class MockValidAgent:
    """Mock agent that always returns valid solutions"""

    def __init__(self, solution: str = "VALID SOLUTION"):
        self.solution = solution
        self.call_count = 0

    async def execute(self, task: str) -> str:
        self.call_count += 1
        await asyncio.sleep(0.001)  # Simulate async work
        return self.solution


class MockInvalidAgent:
    """Mock agent that always returns invalid solutions"""

    def __init__(self):
        self.call_count = 0

    async def execute(self, task: str) -> str:
        self.call_count += 1
        await asyncio.sleep(0.001)
        return f"INVALID SOLUTION {self.call_count}"


class MockProgressiveAgent:
    """Mock agent that improves over attempts"""

    def __init__(self, valid_after: int = 3):
        self.call_count = 0
        self.valid_after = valid_after

    async def execute(self, task: str) -> str:
        self.call_count += 1
        await asyncio.sleep(0.001)

        if self.call_count >= self.valid_after:
            return "VALID SOLUTION"
        return f"INVALID SOLUTION {self.call_count}"


class MockValidatingQA:
    """Mock QA that always validates successfully"""

    def __init__(self):
        self.call_count = 0

    async def execute(self, prompt: str) -> str:
        self.call_count += 1
        await asyncio.sleep(0.001)

        return json.dumps({
            "valid": True,
            "issues": [],
            "suggestions": [],
            "confidence": 0.95,
            "categories_checked": ["correctness", "completeness", "quality", "safety"]
        })


class MockInvalidatingQA:
    """Mock QA that always finds issues"""

    def __init__(self):
        self.call_count = 0

    async def execute(self, prompt: str) -> str:
        self.call_count += 1
        await asyncio.sleep(0.001)

        return json.dumps({
            "valid": False,
            "issues": [
                {
                    "category": "correctness",
                    "severity": "high",
                    "description": f"Bug found in attempt {self.call_count}",
                    "line": 42,
                    "suggestion": "Fix the bug"
                }
            ],
            "suggestions": ["Add error handling", "Improve validation"],
            "confidence": 0.85,
            "categories_checked": ["correctness", "quality"]
        })


class MockProgressiveQA:
    """Mock QA that validates after N attempts"""

    def __init__(self, valid_after: int = 2):
        self.call_count = 0
        self.valid_after = valid_after

    async def execute(self, prompt: str) -> str:
        self.call_count += 1
        await asyncio.sleep(0.001)

        if self.call_count >= self.valid_after:
            return json.dumps({
                "valid": True,
                "issues": [],
                "suggestions": [],
                "confidence": 0.9,
                "categories_checked": ["correctness", "completeness", "quality"]
            })

        return json.dumps({
            "valid": False,
            "issues": [
                {
                    "category": "quality",
                    "severity": "medium",
                    "description": f"Quality issue in attempt {self.call_count}",
                    "suggestion": "Improve code quality"
                }
            ],
            "suggestions": ["Refactor", "Add comments"],
            "confidence": 0.75,
            "categories_checked": ["quality"]
        })


# ============================================================================
# TEST SUITE 1: First Attempt Valid (5 tests)
# ============================================================================


class TestFirstAttemptValid:
    """Test scenarios where solution is valid on first attempt"""

    @pytest.mark.asyncio
    async def test_first_attempt_valid_simple(self):
        """Valid solution on first attempt → return immediately"""
        agent = MockValidAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Test task")

        assert result["valid"] == True
        assert result["attempts"] == 1
        assert result["solution"] == "VALID SOLUTION"
        assert agent.call_count == 1
        assert qa.call_count == 1

    @pytest.mark.asyncio
    async def test_first_attempt_valid_with_expectations(self):
        """Valid solution with expectations on first attempt"""
        agent = MockValidAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)

        expectations = {
            "has_tests": True,
            "handles_errors": True,
            "follows_style": True
        }

        result = await correcting.execute_with_validation(
            "Build REST API",
            expectations=expectations
        )

        assert result["valid"] == True
        assert result["attempts"] == 1
        assert "qa_feedback" in result
        assert result["qa_feedback"].confidence >= 0.9

    @pytest.mark.asyncio
    async def test_first_attempt_stats_tracking(self):
        """Stats correctly track first-attempt success"""
        agent = MockValidAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)

        # Execute 3 tasks
        for _ in range(3):
            await correcting.execute_with_validation("Task")

        stats = correcting.get_correction_stats()

        assert stats["first_attempt_success_rate"] == 1.0
        assert stats["total_executions"] == 3
        assert stats["correction_success_rate"] == 0.0
        assert stats["failure_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_first_attempt_with_context(self):
        """Valid solution with additional context"""
        agent = MockValidAgent("CONTEXT-AWARE SOLUTION")
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)

        context = {
            "agent": "BuilderAgent",
            "business_id": "test-123"
        }

        result = await correcting.execute_with_validation(
            "Generate code",
            context=context
        )

        assert result["valid"] == True
        assert result["solution"] == "CONTEXT-AWARE SOLUTION"

    @pytest.mark.asyncio
    async def test_first_attempt_attempt_history(self):
        """Attempt history correctly recorded for first attempt"""
        agent = MockValidAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        history = correcting.get_attempt_history()

        assert len(history) == 1  # One execution
        assert len(history[0]) == 1  # One attempt
        assert history[0][0].attempt_number == 1
        assert history[0][0].solution == "VALID SOLUTION"
        assert history[0][0].qa_feedback.valid == True


# ============================================================================
# TEST SUITE 2: Correction Success (5 tests)
# ============================================================================


class TestCorrectionSuccess:
    """Test scenarios where correction succeeds after failures"""

    @pytest.mark.asyncio
    async def test_correction_after_one_failure(self):
        """Invalid → Valid (2 attempts)"""
        agent = MockProgressiveAgent(valid_after=2)
        qa = MockProgressiveQA(valid_after=2)

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert result["valid"] == True
        assert result["attempts"] == 2
        assert agent.call_count == 2
        assert qa.call_count == 2

    @pytest.mark.asyncio
    async def test_correction_after_two_failures(self):
        """Invalid → Invalid → Valid (3 attempts)"""
        agent = MockProgressiveAgent(valid_after=3)
        qa = MockProgressiveQA(valid_after=3)

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert result["valid"] == True
        assert result["attempts"] == 3
        assert result["solution"] == "VALID SOLUTION"

    @pytest.mark.asyncio
    async def test_correction_stats_tracking(self):
        """Stats correctly track correction success"""
        # Create fresh instances for each execution to ensure consistent behavior
        correcting = SelfCorrectingAgent(
            MockProgressiveAgent(valid_after=2),
            MockProgressiveQA(valid_after=2),
            max_attempts=3
        )

        # Execute 3 tasks (all need correction)
        # Note: Progressive agents increment globally, so need fresh instances
        for i in range(3):
            # Create new progressive agents for each task to ensure they fail first, then succeed
            correcting.agent = MockProgressiveAgent(valid_after=2)
            correcting.qa_agent = MockProgressiveQA(valid_after=2)
            await correcting.execute_with_validation(f"Task {i}")

        stats = correcting.get_correction_stats()

        assert stats["correction_success_rate"] == 1.0
        assert stats["first_attempt_success_rate"] == 0.0
        assert stats["total_executions"] == 3

    @pytest.mark.asyncio
    async def test_correction_history_multiple_attempts(self):
        """Correction history tracks all attempts"""
        agent = MockProgressiveAgent(valid_after=3)
        qa = MockProgressiveQA(valid_after=3)

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert len(result["correction_history"]) == 3

        # First two attempts should be invalid
        assert result["correction_history"][0].qa_feedback.valid == False
        assert result["correction_history"][1].qa_feedback.valid == False

        # Third attempt should be valid
        assert result["correction_history"][2].qa_feedback.valid == True

    @pytest.mark.asyncio
    async def test_correction_with_qa_feedback(self):
        """QA feedback is incorporated in fix prompts"""
        agent = MockProgressiveAgent(valid_after=2)
        qa = MockProgressiveQA(valid_after=2)

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        # Check QA feedback structure
        feedback = result["qa_feedback"]
        assert feedback.valid == True
        assert feedback.confidence > 0.0
        assert len(feedback.categories_checked) > 0


# ============================================================================
# TEST SUITE 3: Max Attempts Failure (5 tests)
# ============================================================================


class TestMaxAttemptsFailure:
    """Test scenarios where max attempts are reached"""

    @pytest.mark.asyncio
    async def test_max_attempts_failure_basic(self):
        """Invalid after max attempts → return invalid"""
        agent = MockInvalidAgent()
        qa = MockInvalidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert result["valid"] == False
        assert result["attempts"] == 3
        assert agent.call_count == 3
        assert qa.call_count == 3

    @pytest.mark.asyncio
    async def test_max_attempts_failure_stats(self):
        """Stats correctly track max attempts failures"""
        agent = MockInvalidAgent()
        qa = MockInvalidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=2)

        # Execute 3 tasks (all fail)
        for _ in range(3):
            await correcting.execute_with_validation("Task")

        stats = correcting.get_correction_stats()

        assert stats["failure_rate"] == 1.0
        assert stats["total_executions"] == 3
        assert stats["first_attempt_success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_max_attempts_returns_best_attempt(self):
        """Max attempts returns last solution (best effort)"""
        agent = MockInvalidAgent()
        qa = MockInvalidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert result["solution"] == "INVALID SOLUTION 3"
        assert len(result["correction_history"]) == 3

    @pytest.mark.asyncio
    async def test_max_attempts_with_custom_limit(self):
        """Max attempts respects custom limit"""
        agent = MockInvalidAgent()
        qa = MockInvalidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=5)
        result = await correcting.execute_with_validation("Task")

        assert result["attempts"] == 5
        assert agent.call_count == 5

    @pytest.mark.asyncio
    async def test_max_attempts_qa_feedback_preserved(self):
        """QA feedback from last attempt is preserved"""
        agent = MockInvalidAgent()
        qa = MockInvalidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=2)
        result = await correcting.execute_with_validation("Task")

        feedback = result["qa_feedback"]
        assert feedback.valid == False
        assert len(feedback.issues) > 0
        assert feedback.issues[0].category == ValidationCategory.CORRECTNESS


# ============================================================================
# TEST SUITE 4: QA Feedback Parsing (5 tests)
# ============================================================================


class TestQAFeedbackParsing:
    """Test QA feedback parsing with various formats"""

    @pytest.mark.asyncio
    async def test_parse_valid_json_feedback(self):
        """Parse valid JSON feedback"""
        agent = MockValidAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        feedback = result["qa_feedback"]
        assert feedback.valid == True
        assert feedback.confidence == 0.95
        assert len(feedback.categories_checked) == 4

    @pytest.mark.asyncio
    async def test_parse_feedback_with_issues(self):
        """Parse feedback with validation issues"""
        agent = MockInvalidAgent()
        qa = MockInvalidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=1)
        result = await correcting.execute_with_validation("Task")

        feedback = result["qa_feedback"]
        assert len(feedback.issues) > 0
        assert feedback.issues[0].severity == "high"
        assert feedback.issues[0].line == 42

    @pytest.mark.asyncio
    async def test_parse_markdown_wrapped_json(self):
        """Parse JSON wrapped in markdown code blocks"""

        class MarkdownQA:
            async def execute(self, prompt: str) -> str:
                return """
```json
{
  "valid": true,
  "issues": [],
  "suggestions": ["Great job!"],
  "confidence": 0.88,
  "categories_checked": ["correctness"]
}
```
"""

        agent = MockValidAgent()
        qa = MarkdownQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert result["valid"] == True
        assert result["qa_feedback"].confidence == 0.88

    @pytest.mark.asyncio
    async def test_parse_fallback_heuristic(self):
        """Fallback to heuristic when JSON parsing fails"""

        class HeuristicQA:
            async def execute(self, prompt: str) -> str:
                return "The solution is valid and looks good."

        agent = MockValidAgent()
        qa = HeuristicQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        # Heuristic should detect "valid" keyword
        assert result["valid"] == True
        assert result["qa_feedback"].confidence == 0.5  # Default confidence

    @pytest.mark.asyncio
    async def test_parse_invalid_heuristic(self):
        """Heuristic detects invalid keywords"""

        class InvalidHeuristicQA:
            async def execute(self, prompt: str) -> str:
                return "Error: The solution is invalid and has failures."

        agent = MockInvalidAgent()
        qa = InvalidHeuristicQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=1)
        result = await correcting.execute_with_validation("Task")

        # Heuristic should detect "invalid", "error", "fail" keywords
        assert result["valid"] == False


# ============================================================================
# TEST SUITE 5: Integration with Agents (5 tests)
# ============================================================================


class TestAgentIntegration:
    """Test integration with different agent interfaces"""

    @pytest.mark.asyncio
    async def test_integration_execute_method(self):
        """Integration with agent.execute() interface"""

        class ExecuteAgent:
            async def execute(self, task: str) -> str:
                return "Solution via execute()"

        agent = ExecuteAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert result["solution"] == "Solution via execute()"

    @pytest.mark.asyncio
    async def test_integration_run_method(self):
        """Integration with agent.run() interface"""

        class RunAgent:
            async def run(self, task: str) -> str:
                return "Solution via run()"

        agent = RunAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert result["solution"] == "Solution via run()"

    @pytest.mark.asyncio
    async def test_integration_callable_agent(self):
        """Integration with callable agent"""

        class CallableAgent:
            async def __call__(self, task: str) -> str:
                return "Solution via __call__()"

        agent = CallableAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)
        result = await correcting.execute_with_validation("Task")

        assert result["solution"] == "Solution via __call__()"

    @pytest.mark.asyncio
    async def test_integration_validation_categories(self):
        """Custom validation categories"""
        agent = MockValidAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(
            agent,
            qa,
            max_attempts=3,
            validation_categories=[
                ValidationCategory.SAFETY,
                ValidationCategory.CORRECTNESS
            ]
        )

        result = await correcting.execute_with_validation("Task")
        assert result["valid"] == True

    @pytest.mark.asyncio
    async def test_integration_factory_function(self):
        """Factory function creates correct instance"""
        agent = MockValidAgent()
        qa = MockValidatingQA()

        correcting = get_self_correcting_agent(
            agent=agent,
            qa_agent=qa,
            max_attempts=5
        )

        assert correcting.max_attempts == 5
        assert correcting.agent == agent
        assert correcting.qa_agent == qa


# ============================================================================
# ADDITIONAL TESTS: Edge Cases & Performance
# ============================================================================


class TestEdgeCases:
    """Edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_stats_reset(self):
        """Stats can be reset"""
        agent = MockValidAgent()
        qa = MockValidatingQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=3)

        await correcting.execute_with_validation("Task 1")
        await correcting.execute_with_validation("Task 2")

        stats_before = correcting.get_correction_stats()
        assert stats_before["total_executions"] == 2

        correcting.reset_stats()

        stats_after = correcting.get_correction_stats()
        assert stats_after["total_executions"] == 0

    @pytest.mark.asyncio
    async def test_qa_execution_error_handling(self):
        """Handle QA agent execution errors gracefully"""

        class ErrorQA:
            async def execute(self, prompt: str) -> str:
                raise RuntimeError("QA agent crashed")

        agent = MockValidAgent()
        qa = ErrorQA()

        correcting = SelfCorrectingAgent(agent, qa, max_attempts=1)
        result = await correcting.execute_with_validation("Task")

        # Should handle error gracefully
        assert result["valid"] == False
        assert "QA validation failed" in result["qa_feedback"].issues[0].description

    @pytest.mark.asyncio
    async def test_mixed_success_failure_stats(self):
        """Stats correctly track mixed success/failure"""

        # First task: success on first attempt
        agent1 = MockValidAgent()
        qa1 = MockValidatingQA()
        correcting = SelfCorrectingAgent(agent1, qa1, max_attempts=3)
        await correcting.execute_with_validation("Task 1")

        # Second task: success after correction
        agent2 = MockProgressiveAgent(valid_after=2)
        qa2 = MockProgressiveQA(valid_after=2)
        correcting.agent = agent2
        correcting.qa_agent = qa2
        await correcting.execute_with_validation("Task 2")

        # Third task: failure after max attempts
        agent3 = MockInvalidAgent()
        qa3 = MockInvalidatingQA()
        correcting.agent = agent3
        correcting.qa_agent = qa3
        await correcting.execute_with_validation("Task 3")

        stats = correcting.get_correction_stats()

        assert stats["total_executions"] == 3
        assert stats["first_attempt_success_rate"] == 1/3
        assert stats["correction_success_rate"] == 1/3
        assert stats["failure_rate"] == 1/3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
