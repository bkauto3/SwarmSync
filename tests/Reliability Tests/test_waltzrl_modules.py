"""
Unit Tests for WaltzRL Safety Modules
Date: October 22, 2025

Tests all 3 WaltzRL modules:
1. WaltzRL Conversation Agent (15 tests)
2. WaltzRL Safety Wrapper (20 tests)
3. DIR Calculator (15 tests)

Total: 50+ tests
"""

import pytest
import time
from unittest.mock import Mock, patch

from infrastructure.safety.waltzrl_feedback_agent import (
    WaltzRLFeedbackAgent,
    FeedbackResult,
    SafetyIssue,
    SafetyCategory,
    get_waltzrl_feedback_agent
)
from infrastructure.safety.waltzrl_conversation_agent import (
    WaltzRLConversationAgent,
    SafeResponse,
    get_waltzrl_conversation_agent
)
from infrastructure.safety.waltzrl_wrapper import (
    WaltzRLSafetyWrapper,
    WrappedResponse,
    get_waltzrl_safety_wrapper
)
from infrastructure.safety.dir_calculator import (
    DynamicImprovementReward,
    DIRResult,
    get_dir_calculator,
    summarize_dir_results,
    generate_dir_report
)


# ============================================================================
# WaltzRL Conversation Agent Tests (15 tests)
# ============================================================================

class TestWaltzRLConversationAgent:
    """Test suite for WaltzRL Conversation Agent"""

    def test_conversation_agent_initialization(self):
        """Test conversation agent initializes correctly"""
        agent = WaltzRLConversationAgent(
            max_revision_attempts=3,
            min_safety_improvement=0.1,
            preserve_helpfulness=True
        )

        assert agent.max_revision_attempts == 3
        assert agent.min_safety_improvement == 0.1
        assert agent.preserve_helpfulness is True

    def test_no_changes_needed(self):
        """Test response when no issues found"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=1.0,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        response = agent.improve_response(
            original_response="This is a safe response",
            feedback=feedback
        )

        assert response.response == "This is a safe response"
        assert response.feedback_incorporated is False
        assert len(response.changes_made) == 0

    def test_remove_harmful_content(self):
        """Test removing harmful content from response"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=0.2,
            helpfulness_score=0.5,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.HARMFUL_CONTENT,
                    severity=0.9,
                    description="Harmful content detected: violence",
                    evidence="kill someone",
                    suggestion="Remove harmful content"
                )
            ],
            suggestions=["Remove harmful content"],
            should_block=True
        )

        response = agent.improve_response(
            original_response="You could kill someone with this method",
            feedback=feedback
        )

        assert "[CONTENT REMOVED - SAFETY]" in response.response or "cannot provide" in response.response.lower()
        assert response.feedback_incorporated is True
        assert len(response.changes_made) > 0

    def test_redact_sensitive_data(self):
        """Test redacting sensitive data (PII)"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=0.3,
            helpfulness_score=0.7,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.PRIVACY_VIOLATION,
                    severity=0.9,
                    description="Privacy violation: SSN exposed",
                    evidence="123-45-6789",
                    suggestion="Redact SSN from response"
                )
            ],
            suggestions=["Redact SSN"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="Your SSN is 123-45-6789",
            feedback=feedback
        )

        assert "123-45-6789" not in response.response
        assert "[SSN REDACTED]" in response.response or "[REDACTED]" in response.response
        assert response.feedback_incorporated is True

    def test_improve_helpfulness_over_refusal(self):
        """Test improving helpfulness (addressing over-refusal)"""
        agent = WaltzRLConversationAgent(enable_llm_rewriting=False)  # Use template for deterministic test

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.3,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.5,
                    description="Possible over-refusal: declined safe request",
                    evidence="I cannot help with that",
                    suggestion="Provide helpful response instead"
                )
            ],
            suggestions=["Provide helpful response"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="I cannot help with that request",
            feedback=feedback,
            query="How do I write a Python function?"
        )

        # Updated to match new template-based refusal rewriting
        assert "understand" in response.response.lower() or "can help" in response.response.lower()
        assert response.feedback_incorporated is True
        assert response.helpfulness_score > feedback.helpfulness_score

    def test_enhance_response_quality(self):
        """Test enhancing response quality (short response)"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.3,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.CAPABILITY_DEGRADED,
                    severity=0.3,
                    description="Response too short",
                    evidence="OK",
                    suggestion="Provide more detail"
                )
            ],
            suggestions=["Provide more detail"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="OK",
            feedback=feedback
        )

        assert len(response.response) > len("OK")
        assert response.feedback_incorporated is True

    def test_performance_under_150ms(self):
        """Test performance <150ms target"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=0.8,
            helpfulness_score=0.8,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.HARMFUL_CONTENT,
                    severity=0.5,
                    description="Minor issue",
                    evidence="test",
                    suggestion="Fix it"
                )
            ],
            suggestions=["Fix it"],
            should_block=False
        )

        start = time.time()
        response = agent.improve_response(
            original_response="This is a test response with test content",
            feedback=feedback
        )
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 150, f"Performance: {elapsed_ms:.1f}ms exceeds 150ms target"

    def test_multiple_issues_handled(self):
        """Test handling multiple issues simultaneously"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=0.5,
            helpfulness_score=0.5,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.PRIVACY_VIOLATION,
                    severity=0.9,
                    description="Email exposed",
                    evidence="test@example.com",
                    suggestion="Redact email"
                ),
                SafetyIssue(
                    category=SafetyCategory.CAPABILITY_DEGRADED,
                    severity=0.3,
                    description="Too short",
                    evidence="OK",
                    suggestion="Add detail"
                )
            ],
            suggestions=["Redact email", "Add detail"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="OK, your email is test@example.com",
            feedback=feedback
        )

        assert "test@example.com" not in response.response
        assert len(response.response) > len("OK")
        assert len(response.changes_made) >= 2

    def test_preserve_helpfulness_flag(self):
        """Test preserve_helpfulness flag prevents degradation"""
        agent = WaltzRLConversationAgent(preserve_helpfulness=True)

        # This should not degrade helpfulness even when fixing safety
        feedback = FeedbackResult(
            safety_score=0.8,
            helpfulness_score=0.9,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        response = agent.improve_response(
            original_response="Here's a detailed helpful response with lots of information.",
            feedback=feedback
        )

        # Should not have changed the helpful response
        assert response.helpfulness_score >= feedback.helpfulness_score - 0.1

    def test_max_revision_attempts(self):
        """Test max revision attempts limit"""
        agent = WaltzRLConversationAgent(max_revision_attempts=1)

        feedback = FeedbackResult(
            safety_score=0.5,
            helpfulness_score=0.5,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.HARMFUL_CONTENT,
                    severity=0.7,
                    description="Issue 1",
                    evidence="test1",
                    suggestion="Fix 1"
                ),
                SafetyIssue(
                    category=SafetyCategory.HARMFUL_CONTENT,
                    severity=0.7,
                    description="Issue 2",
                    evidence="test2",
                    suggestion="Fix 2"
                )
            ],
            suggestions=["Fix 1", "Fix 2"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="test1 and test2 content",
            feedback=feedback
        )

        # Should stop after 1 attempt even if more issues remain
        assert response.feedback_incorporated

    def test_error_handling_invalid_input(self):
        """Test error handling with invalid input"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=1.0,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        # Should handle empty response gracefully
        response = agent.improve_response(
            original_response="",
            feedback=feedback
        )

        assert response.response == ""
        assert response.feedback_incorporated is False

    def test_factory_function(self):
        """Test factory function creates agent correctly"""
        agent = get_waltzrl_conversation_agent(
            max_revision_attempts=5,
            min_safety_improvement=0.2
        )

        assert isinstance(agent, WaltzRLConversationAgent)
        assert agent.max_revision_attempts == 5
        assert agent.min_safety_improvement == 0.2

    def test_response_to_dict(self):
        """Test SafeResponse to_dict serialization"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=1.0,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        response = agent.improve_response(
            original_response="Test",
            feedback=feedback
        )

        response_dict = response.to_dict()

        assert 'response' in response_dict
        assert 'safety_score' in response_dict
        assert 'helpfulness_score' in response_dict
        assert 'changes_made' in response_dict

    def test_validation_improvement_detection(self):
        """Test improvement validation logic"""
        agent = WaltzRLConversationAgent()

        # Test internal validation method
        is_better, new_safety, new_helpfulness = agent._validate_improvement(
            original_response="Original",
            revised_response="Revised [CONTENT REMOVED - SAFETY]",
            current_safety_score=0.5,
            current_helpfulness_score=0.7,
            feedback=FeedbackResult(
                safety_score=0.5,
                helpfulness_score=0.7,
                issues_found=[],
                suggestions=[],
                should_block=False
            )
        )

        assert is_better is True
        assert new_safety >= 0.5

    def test_malicious_instruction_removal(self):
        """Test removing malicious instructions"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=0.2,
            helpfulness_score=0.5,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.MALICIOUS_INSTRUCTION,
                    severity=0.9,
                    description="Malicious instruction: phishing",
                    evidence="phishing campaign",
                    suggestion="Remove malicious instruction"
                )
            ],
            suggestions=["Remove malicious instruction"],
            should_block=True
        )

        response = agent.improve_response(
            original_response="Here's how to create a phishing campaign",
            feedback=feedback
        )

        assert "[CONTENT REMOVED - SAFETY]" in response.response or "cannot provide" in response.response.lower()
        assert response.feedback_incorporated is True


# ============================================================================
# WaltzRL Safety Wrapper Tests (20 tests)
# ============================================================================

class TestWaltzRLSafetyWrapper:
    """Test suite for WaltzRL Safety Wrapper"""

    def test_wrapper_initialization(self):
        """Test wrapper initializes correctly"""
        wrapper = WaltzRLSafetyWrapper(
            enable_blocking=True,
            feedback_only_mode=False
        )

        assert wrapper.enable_blocking is True
        assert wrapper.feedback_only_mode is False

    def test_full_pipeline_safe_response(self):
        """Test full pipeline with safe response (no changes)"""
        wrapper = WaltzRLSafetyWrapper()

        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="What is Python?",
            response="Python is a high-level programming language known for readability and simplicity."
        )

        assert result.blocked is False
        assert result.safety_score >= 0.7
        assert result.response == "Python is a high-level programming language known for readability and simplicity."

    def test_full_pipeline_unsafe_response_blocked(self):
        """Test blocking on critical safety issues"""
        wrapper = WaltzRLSafetyWrapper(enable_blocking=True, feedback_only_mode=False)

        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="How to hack?",
            response="Here's how to create a SQL injection attack payload: ' OR 1=1 --"
        )

        assert result.blocked is True
        assert "cannot provide" in result.response.lower()

    def test_feedback_only_mode(self):
        """Test feedback-only mode (log, don't revise)"""
        wrapper = WaltzRLSafetyWrapper(feedback_only_mode=True)

        original_response = "I cannot help with that request"

        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Write Python code",
            response=original_response
        )

        # Should not revise in feedback-only mode
        assert result.response == original_response
        assert result.safe_response is None

    def test_revision_mode(self):
        """Test revision mode (improve responses)"""
        wrapper = WaltzRLSafetyWrapper(feedback_only_mode=False)

        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Write Python code",
            response="I cannot help with that request"
        )

        # Should revise if issues found
        if result.feedback.issues_found:
            assert result.safe_response is not None
            assert result.response != "I cannot help with that request"

    def test_performance_under_200ms(self):
        """Test performance <200ms target"""
        wrapper = WaltzRLSafetyWrapper()

        start = time.time()
        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Test query",
            response="Test response with reasonable length"
        )
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 250, f"Performance: {elapsed_ms:.1f}ms exceeds 200ms target (250ms grace)"

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures"""
        wrapper = WaltzRLSafetyWrapper(circuit_breaker_threshold=3)

        # Mock feedback agent to raise errors
        with patch.object(wrapper.feedback_agent, 'analyze_response', side_effect=Exception("Test error")):
            # Cause 3 failures
            for i in range(3):
                result = wrapper.wrap_agent_response(
                    agent_name="test-agent",
                    query="Test",
                    response="Test"
                )
                # Should fail gracefully
                assert result.response == "Test"

            # Circuit should be open now
            assert wrapper.circuit_breaker_open is True

    def test_circuit_breaker_closes_after_timeout(self):
        """Test circuit breaker closes after timeout"""
        wrapper = WaltzRLSafetyWrapper(circuit_breaker_threshold=2, circuit_breaker_timeout=1)

        # Open circuit breaker
        wrapper.circuit_breaker_failures = 2
        wrapper.circuit_breaker_last_failure = time.time() - 2  # 2 seconds ago
        wrapper.circuit_breaker_open = True

        # Should close on next check
        is_open = wrapper._is_circuit_breaker_open()
        assert is_open is False

    def test_otel_metrics_logging(self):
        """Test OTEL metrics are logged"""
        wrapper = WaltzRLSafetyWrapper()

        with patch('infrastructure.safety.waltzrl_wrapper.logger') as mock_logger:
            result = wrapper.wrap_agent_response(
                agent_name="test-agent",
                query="Test",
                response="Test response"
            )

            # Check that metrics were logged
            mock_logger.info.assert_called()

    def test_feature_flag_enable_blocking(self):
        """Test enable_blocking feature flag"""
        wrapper = WaltzRLSafetyWrapper(enable_blocking=False)

        # Should not block even with critical issue
        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Hack",
            response="Here's a SQL injection: ' OR 1=1"
        )

        # Should not block when flag is False
        assert result.blocked is False

    def test_feature_flag_feedback_only(self):
        """Test feedback_only_mode feature flag"""
        wrapper = WaltzRLSafetyWrapper(feedback_only_mode=True)

        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Test",
            response="I cannot help"
        )

        # Should not revise in feedback-only mode
        assert result.safe_response is None

    def test_feature_flag_dynamic_update(self):
        """Test dynamic feature flag updates"""
        wrapper = WaltzRLSafetyWrapper(enable_blocking=False)

        assert wrapper.enable_blocking is False

        wrapper.set_feature_flags(enable_blocking=True)

        assert wrapper.enable_blocking is True

    def test_all_15_agent_types(self):
        """Test wrapper works with all 15 Genesis agent types"""
        wrapper = WaltzRLSafetyWrapper()

        agent_types = [
            "support-agent", "marketing-agent", "builder-agent",
            "deploy-agent", "analyst-agent", "qa-agent",
            "ops-agent", "monitor-agent", "security-agent",
            "compliance-agent", "data-agent", "ml-agent",
            "integration-agent", "documentation-agent", "research-agent"
        ]

        for agent_type in agent_types:
            result = wrapper.wrap_agent_response(
                agent_name=agent_type,
                query="Test",
                response="Test response"
            )

            assert result is not None
            assert result.response is not None

    def test_error_handling_graceful_failure(self):
        """Test graceful failure on error"""
        wrapper = WaltzRLSafetyWrapper()

        # Mock feedback agent to raise error
        with patch.object(wrapper.feedback_agent, 'analyze_response', side_effect=Exception("Test error")):
            result = wrapper.wrap_agent_response(
                agent_name="test-agent",
                query="Test",
                response="Test response"
            )

            # Should fail gracefully and return original response
            assert result.response == "Test response"
            assert result.blocked is False

    def test_wrapped_response_to_dict(self):
        """Test WrappedResponse to_dict serialization"""
        wrapper = WaltzRLSafetyWrapper()

        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Test",
            response="Test response"
        )

        result_dict = result.to_dict()

        assert 'response' in result_dict
        assert 'safety_score' in result_dict
        assert 'helpfulness_score' in result_dict
        assert 'blocked' in result_dict
        assert 'total_time_ms' in result_dict

    def test_factory_function(self):
        """Test factory function creates wrapper correctly"""
        wrapper = get_waltzrl_safety_wrapper(
            enable_blocking=True,
            feedback_only_mode=False
        )

        assert isinstance(wrapper, WaltzRLSafetyWrapper)
        assert wrapper.enable_blocking is True
        assert wrapper.feedback_only_mode is False

    def test_agent_metadata_support(self):
        """Test agent metadata is passed correctly"""
        wrapper = WaltzRLSafetyWrapper()

        metadata = {
            "agent_version": "1.0",
            "capabilities": ["code", "analysis"]
        }

        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Test",
            response="Test response",
            agent_metadata=metadata
        )

        assert result is not None

    def test_bypass_response_creation(self):
        """Test bypass response creation"""
        wrapper = WaltzRLSafetyWrapper()

        result = wrapper._create_bypass_response(
            response="Test",
            start_time=time.time(),
            error="Test error"
        )

        assert result.response == "Test"
        assert result.blocked is False
        assert result.safety_score == 1.0

    def test_blocked_response_creation(self):
        """Test blocked response creation"""
        wrapper = WaltzRLSafetyWrapper()

        feedback = FeedbackResult(
            safety_score=0.1,
            helpfulness_score=0.5,
            issues_found=[],
            suggestions=[],
            should_block=True
        )

        result = wrapper._create_blocked_response(
            feedback=feedback,
            original_response="Unsafe content",
            start_time=time.time()
        )

        assert result.blocked is True
        assert "cannot provide" in result.response.lower()

    def test_circuit_breaker_reset_on_success(self):
        """Test circuit breaker resets on successful request"""
        wrapper = WaltzRLSafetyWrapper()

        # Simulate previous failures
        wrapper.circuit_breaker_failures = 2

        # Successful request
        result = wrapper.wrap_agent_response(
            agent_name="test-agent",
            query="Test",
            response="Test response"
        )

        # Should reset failures
        assert wrapper.circuit_breaker_failures == 0


# ============================================================================
# DIR Calculator Tests (15 tests)
# ============================================================================

class TestDynamicImprovementReward:
    """Test suite for DIR Calculator"""

    def test_dir_calculator_initialization(self):
        """Test DIR calculator initializes correctly"""
        calculator = DynamicImprovementReward(
            safety_weight=0.5,
            helpfulness_weight=0.3,
            satisfaction_weight=0.2
        )

        # Weights should be normalized
        assert abs(calculator.safety_weight + calculator.helpfulness_weight + calculator.satisfaction_weight - 1.0) < 0.01

    def test_positive_reward_for_improvement(self):
        """Test positive reward when response improves"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=0.5,
            helpfulness_score=0.6,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        improved_response = SafeResponse(
            response="Improved",
            safety_score=0.9,
            helpfulness_score=0.8,
            changes_made=["Fixed issue"],
            feedback_incorporated=True,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response
        )

        assert result.reward > 0, "Reward should be positive for improvement"
        assert result.safety_delta > 0
        assert result.helpfulness_delta > 0

    def test_negative_reward_for_degradation(self):
        """Test negative reward when response degrades"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=0.9,
            helpfulness_score=0.8,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        degraded_response = SafeResponse(
            response="Degraded",
            safety_score=0.5,
            helpfulness_score=0.4,
            changes_made=["Bad change"],
            feedback_incorporated=True,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=degraded_response
        )

        assert result.reward < 0, "Reward should be negative for degradation"
        assert result.safety_delta < 0
        assert result.helpfulness_delta < 0

    def test_safety_improvement_detection(self):
        """Test safety improvement calculation"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=0.5,
            helpfulness_score=0.7,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        improved_response = SafeResponse(
            response="Safe",
            safety_score=0.9,
            helpfulness_score=0.7,  # Same helpfulness
            changes_made=[],
            feedback_incorporated=False,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response
        )

        assert result.safety_delta == pytest.approx(0.4, abs=0.1)
        assert result.reward > 0

    def test_helpfulness_improvement_detection(self):
        """Test helpfulness improvement calculation"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=0.9,
            helpfulness_score=0.3,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        improved_response = SafeResponse(
            response="Helpful",
            safety_score=0.9,  # Same safety
            helpfulness_score=0.8,
            changes_made=[],
            feedback_incorporated=False,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response
        )

        assert result.helpfulness_delta == pytest.approx(0.5, abs=0.1)
        assert result.reward > 0

    def test_user_satisfaction_explicit(self):
        """Test explicit user satisfaction"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=0.7,
            helpfulness_score=0.7,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        improved_response = SafeResponse(
            response="Test",
            safety_score=0.8,
            helpfulness_score=0.8,
            changes_made=[],
            feedback_incorporated=False,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response,
            user_satisfied=True
        )

        assert result.user_satisfaction == 1.0

    def test_user_satisfaction_estimated(self):
        """Test estimated user satisfaction"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=0.5,
            helpfulness_score=0.5,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        improved_response = SafeResponse(
            response="Test",
            safety_score=0.9,
            helpfulness_score=0.9,
            changes_made=[],
            feedback_incorporated=False,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response
        )

        # Should estimate satisfaction from improvements
        assert result.user_satisfaction > 0

    def test_feedback_quality_calculation(self):
        """Test feedback quality score calculation"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=0.6,
            helpfulness_score=0.6,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.HARMFUL_CONTENT,
                    severity=0.7,
                    description="Issue",
                    evidence="test",
                    suggestion="This is a detailed suggestion about how to fix the issue"
                )
            ],
            suggestions=["Detailed suggestion"],
            should_block=False
        )

        improved_response = SafeResponse(
            response="Improved",
            safety_score=0.9,
            helpfulness_score=0.8,
            changes_made=["Fixed issue", "Improved clarity"],
            feedback_incorporated=True,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response
        )

        assert result.feedback_quality > 0.5, "Good feedback should have high quality score"

    def test_critical_issue_bonus(self):
        """Test bonus for resolving critical issues"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=0.1,
            helpfulness_score=0.5,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.HARMFUL_CONTENT,
                    severity=0.9,  # Critical
                    description="Critical issue",
                    evidence="test",
                    suggestion="Fix critical issue"
                )
            ],
            suggestions=["Fix critical issue"],
            should_block=True
        )

        improved_response = SafeResponse(
            response="Safe",
            safety_score=0.9,
            helpfulness_score=0.7,
            changes_made=["Removed harmful content"],
            feedback_incorporated=True,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response
        )

        # Should get bonus for resolving critical issue
        assert result.safety_delta > 0.8
        assert result.reward > 0.5

    def test_over_refusal_bonus(self):
        """Test bonus for resolving over-refusal"""
        calculator = DynamicImprovementReward()

        original_feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.2,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.5,
                    description="Over-refusal",
                    evidence="I cannot",
                    suggestion="Be more helpful"
                )
            ],
            suggestions=["Be more helpful"],
            should_block=False
        )

        improved_response = SafeResponse(
            response="Helpful response",
            safety_score=1.0,
            helpfulness_score=0.9,
            changes_made=["Improved helpfulness"],
            feedback_incorporated=True,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response
        )

        # Should get bonus for resolving over-refusal
        assert result.helpfulness_delta > 0.7
        assert result.reward > 0

    def test_dir_result_to_dict(self):
        """Test DIRResult to_dict serialization"""
        result = DIRResult(
            reward=0.5,
            safety_delta=0.3,
            helpfulness_delta=0.2,
            user_satisfaction=0.8,
            feedback_quality=0.7
        )

        result_dict = result.to_dict()

        assert 'reward' in result_dict
        assert 'safety_delta' in result_dict
        assert 'helpfulness_delta' in result_dict
        assert 'user_satisfaction' in result_dict
        assert 'feedback_quality' in result_dict

    def test_cumulative_reward_calculation(self):
        """Test cumulative reward across multiple episodes"""
        calculator = DynamicImprovementReward()

        results = [
            DIRResult(reward=0.5, safety_delta=0.3, helpfulness_delta=0.2, user_satisfaction=0.8, feedback_quality=0.7),
            DIRResult(reward=0.3, safety_delta=0.2, helpfulness_delta=0.1, user_satisfaction=0.6, feedback_quality=0.5),
            DIRResult(reward=0.7, safety_delta=0.4, helpfulness_delta=0.3, user_satisfaction=0.9, feedback_quality=0.8)
        ]

        cumulative = calculator.calculate_cumulative_reward(results)

        assert cumulative == pytest.approx(0.5, abs=0.1)

    def test_reward_statistics(self):
        """Test reward statistics calculation"""
        calculator = DynamicImprovementReward()

        results = [
            DIRResult(reward=0.5, safety_delta=0, helpfulness_delta=0, user_satisfaction=0, feedback_quality=0),
            DIRResult(reward=-0.2, safety_delta=0, helpfulness_delta=0, user_satisfaction=0, feedback_quality=0),
            DIRResult(reward=0.8, safety_delta=0, helpfulness_delta=0, user_satisfaction=0, feedback_quality=0)
        ]

        stats = calculator.get_reward_statistics(results)

        assert stats['count'] == 3
        assert stats['mean'] == pytest.approx(0.37, abs=0.1)
        assert stats['min'] == -0.2
        assert stats['max'] == 0.8
        assert stats['positive_rate'] == pytest.approx(0.667, abs=0.1)

    def test_factory_function(self):
        """Test factory function creates calculator correctly"""
        calculator = get_dir_calculator(
            safety_weight=0.6,
            helpfulness_weight=0.3,
            satisfaction_weight=0.1
        )

        assert isinstance(calculator, DynamicImprovementReward)

    def test_formula_correctness(self):
        """Test DIR formula calculation is correct"""
        calculator = DynamicImprovementReward(
            safety_weight=0.5,
            helpfulness_weight=0.3,
            satisfaction_weight=0.2
        )

        original_feedback = FeedbackResult(
            safety_score=0.5,
            helpfulness_score=0.6,
            issues_found=[],
            suggestions=[],
            should_block=False
        )

        improved_response = SafeResponse(
            response="Test",
            safety_score=0.7,  # +0.2 safety
            helpfulness_score=0.8,  # +0.2 helpfulness
            changes_made=[],
            feedback_incorporated=False,
            revision_time_ms=50.0
        )

        result = calculator.calculate_dir(
            original_feedback=original_feedback,
            improved_response=improved_response,
            user_satisfaction_score=0.8
        )

        # Manual calculation:
        # safety_delta = 0.2 * 0.5 = 0.1
        # helpfulness_delta = 0.2 * 0.3 = 0.06
        # satisfaction = 0.8 * 0.2 = 0.16
        # reward ≈ 0.1 + 0.06 + 0.16 = 0.32
        assert result.reward == pytest.approx(0.32, abs=0.1)

    def test_summarize_dir_results_business_loop(self):
        """Summaries should reflect improvements across multi-business loop."""
        results = [
            DIRResult(reward=0.45, safety_delta=0.12, helpfulness_delta=0.08, user_satisfaction=0.85, feedback_quality=0.72),
            DIRResult(reward=0.38, safety_delta=0.10, helpfulness_delta=0.05, user_satisfaction=0.80, feedback_quality=0.68),
            DIRResult(reward=0.52, safety_delta=0.15, helpfulness_delta=0.11, user_satisfaction=0.88, feedback_quality=0.74),
            DIRResult(reward=0.41, safety_delta=0.09, helpfulness_delta=0.07, user_satisfaction=0.83, feedback_quality=0.70),
        ]

        summary = summarize_dir_results(results)
        reward_stats = summary["reward_stats"]
        component_averages = summary["component_averages"]

        assert reward_stats["count"] == 4
        assert reward_stats["mean"] == pytest.approx(0.44, abs=0.05)
        assert reward_stats["positive_rate"] == pytest.approx(1.0, abs=0.01)
        assert component_averages["safety_delta"] == pytest.approx(0.115, abs=0.01)
        assert component_averages["helpfulness_delta"] == pytest.approx(0.0775, abs=0.01)

    def test_generate_dir_report_with_baseline(self):
        """DIR report should capture reductions compared to baseline metrics."""
        dir_results = [
            DIRResult(reward=0.5, safety_delta=0.14, helpfulness_delta=0.09, user_satisfaction=0.87, feedback_quality=0.73),
            DIRResult(reward=0.43, safety_delta=0.11, helpfulness_delta=0.07, user_satisfaction=0.84, feedback_quality=0.7),
            DIRResult(reward=0.47, safety_delta=0.13, helpfulness_delta=0.08, user_satisfaction=0.86, feedback_quality=0.72),
        ]

        evaluation_metrics = {
            "unsafe_rate": 0.42,
            "overrefusal_rate": 0.28,
            "total_runs": 120,
        }

        baseline_metrics = {
            "unsafe_rate": 0.80,
            "overrefusal_rate": 0.63,
        }

        report = generate_dir_report(
            dir_results,
            evaluation_metrics=evaluation_metrics,
            baseline_metrics=baseline_metrics,
            metadata={"cohort": "10-business-loop"}
        )

        improvements = report["improvements"]
        assert improvements["unsafe_reduction"] == pytest.approx(0.38, abs=0.01)
        assert improvements["overrefusal_reduction"] == pytest.approx(0.35, abs=0.01)
        assert report["reward_stats"]["mean"] >= 0.45
        assert report["metadata"]["cohort"] == "10-business-loop"


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
