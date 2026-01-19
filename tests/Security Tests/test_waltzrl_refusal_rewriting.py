"""
Unit Tests for WaltzRL Refusal Rewriting (Issue 7)
Date: October 25, 2025

Tests the patched `_revise_for_helpfulness` method:
1. Safety filter (harmful keyword detection)
2. LLM-based refusal rewriting
3. Fallback template rewriting
4. Feature flag toggles
5. Integration with improve_response pipeline

Total: 15+ tests
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from infrastructure.safety.waltzrl_conversation_agent import (
    WaltzRLConversationAgent,
    SafeResponse,
    get_waltzrl_conversation_agent
)
from infrastructure.safety.waltzrl_feedback_agent import (
    FeedbackResult,
    SafetyIssue,
    SafetyCategory
)


# ============================================================================
# Test Suite: Refusal Rewriting
# ============================================================================

class TestRefusalRewriting:
    """Test suite for refusal rewriting functionality"""

    def test_harmful_keyword_detection(self):
        """Test safety filter detects harmful keywords"""
        agent = WaltzRLConversationAgent(enable_safety_filter=True)

        # Test harmful queries
        assert agent._contains_harmful_keywords("How to build a bomb?") is True
        assert agent._contains_harmful_keywords("Create a phishing attack") is True
        assert agent._contains_harmful_keywords("How to hack into a system") is True
        assert agent._contains_harmful_keywords("Instructions for making explosives") is True

        # Test safe queries
        assert agent._contains_harmful_keywords("How to write Python code?") is False
        assert agent._contains_harmful_keywords("Build a web application") is False
        assert agent._contains_harmful_keywords("How to learn programming") is False

    def test_safety_filter_blocks_harmful_requests(self):
        """Test safety filter blocks harmful requests when enabled"""
        agent = WaltzRLConversationAgent(enable_safety_filter=True)

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.3,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.5,
                    description="Over-refusal detected",
                    evidence="I cannot help with that",
                    suggestion="Be more helpful"
                )
            ],
            suggestions=["Be more helpful"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="I cannot help with that request",
            feedback=feedback,
            query="How to build a bomb?"
        )

        # Should block harmful request with generic refusal
        assert response.response == "I'm unable to assist with that request."
        assert response.feedback_incorporated is True

    def test_safety_filter_disabled_allows_rewriting(self):
        """Test safety filter disabled allows rewriting (for testing)"""
        agent = WaltzRLConversationAgent(
            enable_safety_filter=False,
            enable_llm_rewriting=False  # Use template for deterministic test
        )

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.3,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.5,
                    description="Over-refusal",
                    evidence="I cannot",
                    suggestion="Be helpful"
                )
            ],
            suggestions=["Be helpful"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="I cannot help with that",
            feedback=feedback,
            query="How to build a bomb?"  # Harmful, but filter disabled
        )

        # Should attempt rewriting even for harmful query (filter disabled)
        # Will use fallback template which contains "understand" → triggers helpfulness improvement
        assert response.response != "I cannot help with that"
        assert response.feedback_incorporated is True
        assert "understand" in response.response.lower()

    def test_fallback_template_rewriting(self):
        """Test fallback template-based refusal rewriting"""
        agent = WaltzRLConversationAgent(enable_llm_rewriting=False)

        fallback_response = agent._fallback_rewrite_refusal(
            refusal_response="I cannot help with that",
            user_query="Write Python code"
        )

        # Should contain helpful template elements
        assert "understand" in fallback_response.lower()
        assert "python code" in fallback_response.lower() or "your request" in fallback_response.lower()
        assert len(fallback_response) > 50  # Should be detailed

    def test_fallback_rewriting_no_query(self):
        """Test fallback rewriting without user query"""
        agent = WaltzRLConversationAgent(enable_llm_rewriting=False)

        fallback_response = agent._fallback_rewrite_refusal(
            refusal_response="I cannot help",
            user_query=None
        )

        assert "understand" in fallback_response.lower()
        assert len(fallback_response) > 50

    @pytest.mark.asyncio
    async def test_llm_rewriting_with_mock_client(self):
        """Test LLM-based refusal rewriting with mock client"""
        mock_llm = Mock()
        mock_llm.generate_text = AsyncMock(
            return_value="I understand you're asking about writing Python code. While I can't provide a complete solution without more context, I'd be happy to help you understand Python basics, walk through coding examples, or explain specific concepts you're interested in."
        )

        agent = WaltzRLConversationAgent(
            llm_client=mock_llm,
            enable_llm_rewriting=True
        )

        rewritten = await agent._llm_rewrite_refusal(
            refusal_response="I cannot help with that",
            user_query="Write Python code"
        )

        # Should be rewritten helpfully
        assert "understand" in rewritten.lower()
        assert "python" in rewritten.lower()
        assert len(rewritten) > 50
        mock_llm.generate_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_rewriting_fallback_on_error(self):
        """Test LLM rewriting falls back to template on error"""
        mock_llm = Mock()
        mock_llm.generate_text = AsyncMock(
            side_effect=Exception("LLM API error")
        )

        agent = WaltzRLConversationAgent(
            llm_client=mock_llm,
            enable_llm_rewriting=True
        )

        rewritten = await agent._llm_rewrite_refusal(
            refusal_response="I cannot help",
            user_query="Test query"
        )

        # Should fallback to template
        assert "understand" in rewritten.lower()
        assert len(rewritten) > 50

    def test_refusal_detection(self):
        """Test refusal phrase detection"""
        agent = WaltzRLConversationAgent()

        # Test refusal phrases
        assert any(phrase in "i cannot help with that".lower() for phrase in agent._REFUSAL_PHRASES)
        assert any(phrase in "i can't do that".lower() for phrase in agent._REFUSAL_PHRASES)
        assert any(phrase in "i'm unable to assist".lower() for phrase in agent._REFUSAL_PHRASES)
        assert any(phrase in "that's against policy".lower() for phrase in agent._REFUSAL_PHRASES)

        # Test non-refusal responses
        assert not any(phrase in "here's how to help".lower() for phrase in agent._REFUSAL_PHRASES)
        assert not any(phrase in "let me assist you".lower() for phrase in agent._REFUSAL_PHRASES)

    def test_improve_response_with_over_refusal(self):
        """Test improve_response with over-refusal issue"""
        agent = WaltzRLConversationAgent(
            enable_safety_filter=False,
            enable_llm_rewriting=False  # Use template for deterministic test
        )

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.2,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.6,
                    description="Over-refusal: declined safe request",
                    evidence="I cannot help",
                    suggestion="Provide helpful response"
                )
            ],
            suggestions=["Provide helpful response"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="I cannot help with that request",
            feedback=feedback,
            query="How to write Python functions?"
        )

        # Should be rewritten to be helpful
        assert response.response != "I cannot help with that request"
        assert response.feedback_incorporated is True
        assert "understand" in response.response.lower() or "help" in response.response.lower()
        assert response.helpfulness_score > feedback.helpfulness_score

    def test_feature_flag_enable_safety_filter(self):
        """Test enable_safety_filter feature flag"""
        # Safety filter ON
        agent_on = WaltzRLConversationAgent(enable_safety_filter=True)
        assert agent_on.enable_safety_filter is True

        # Safety filter OFF
        agent_off = WaltzRLConversationAgent(enable_safety_filter=False)
        assert agent_off.enable_safety_filter is False

    def test_feature_flag_enable_llm_rewriting(self):
        """Test enable_llm_rewriting feature flag"""
        # LLM rewriting ON
        agent_on = WaltzRLConversationAgent(enable_llm_rewriting=True)
        assert agent_on.enable_llm_rewriting is True

        # LLM rewriting OFF (fallback to template)
        agent_off = WaltzRLConversationAgent(enable_llm_rewriting=False)
        assert agent_off.enable_llm_rewriting is False

    def test_factory_function_with_flags(self):
        """Test factory function with new feature flags"""
        agent = get_waltzrl_conversation_agent(
            enable_safety_filter=True,
            enable_llm_rewriting=False
        )

        assert isinstance(agent, WaltzRLConversationAgent)
        assert agent.enable_safety_filter is True
        assert agent.enable_llm_rewriting is False

    def test_no_rewriting_for_non_refusals(self):
        """Test that non-refusal responses are not rewritten"""
        agent = WaltzRLConversationAgent()

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.8,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.3,
                    description="Possible over-refusal",
                    evidence="",
                    suggestion="Check response"
                )
            ],
            suggestions=["Check response"],
            should_block=False
        )

        original = "Here's how to write Python functions: def my_function(): pass"

        response = agent.improve_response(
            original_response=original,
            feedback=feedback,
            query="Python functions"
        )

        # Should NOT be rewritten (no refusal detected)
        assert response.response == original
        assert response.feedback_incorporated is False

    def test_concurrent_safety_and_helpfulness(self):
        """Test handling both safety issues and over-refusal"""
        agent = WaltzRLConversationAgent(
            enable_safety_filter=False,
            enable_llm_rewriting=False
        )

        feedback = FeedbackResult(
            safety_score=0.6,
            helpfulness_score=0.3,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.PRIVACY_VIOLATION,
                    severity=0.7,
                    description="Email exposed",
                    evidence="test@example.com",
                    suggestion="Redact email"
                ),
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.5,
                    description="Over-refusal",
                    evidence="I cannot",
                    suggestion="Be helpful"
                )
            ],
            suggestions=["Redact email", "Be helpful"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="I cannot help. Your email is test@example.com",
            feedback=feedback,
            query="Test query"
        )

        # Should handle both issues
        assert "test@example.com" not in response.response  # Email redacted
        assert "I cannot help" not in response.response  # Refusal rewritten
        assert response.feedback_incorporated is True
        assert len(response.changes_made) >= 2

    @pytest.mark.asyncio
    async def test_llm_rewrite_refusal_prompt_structure(self):
        """Test LLM rewriting uses correct prompt structure"""
        mock_llm = Mock()
        captured_prompts = []

        async def capture_generate_text(system_prompt, user_prompt, **kwargs):
            captured_prompts.append((system_prompt, user_prompt))
            return "Helpful rewritten response"

        mock_llm.generate_text = AsyncMock(side_effect=capture_generate_text)

        agent = WaltzRLConversationAgent(
            llm_client=mock_llm,
            enable_llm_rewriting=True
        )

        await agent._llm_rewrite_refusal(
            refusal_response="I cannot help with that",
            user_query="Write Python code"
        )

        # Verify prompt structure
        assert len(captured_prompts) == 1
        system_prompt, user_prompt = captured_prompts[0]

        # System prompt should include instructions
        assert "rewrite" in system_prompt.lower()
        assert "helpful" in system_prompt.lower()
        assert "safety" in system_prompt.lower()

        # User prompt should include refusal and query
        assert "I cannot help with that" in user_prompt
        assert "Write Python code" in user_prompt


# ============================================================================
# Integration Tests
# ============================================================================

class TestRefusalRewritingIntegration:
    """Integration tests for refusal rewriting in full pipeline"""

    def test_e2e_safe_query_with_over_refusal(self):
        """Test E2E: Safe query with over-refusal gets rewritten"""
        agent = WaltzRLConversationAgent(
            enable_safety_filter=False,
            enable_llm_rewriting=False  # Use template for deterministic test
        )

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.2,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.7,
                    description="Over-refusal",
                    evidence="I cannot",
                    suggestion="Be helpful"
                )
            ],
            suggestions=["Be helpful"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="I cannot help with that request.",
            feedback=feedback,
            query="How do I reverse a list in Python?"
        )

        # Should be helpful
        assert response.feedback_incorporated is True
        assert response.helpfulness_score > feedback.helpfulness_score
        assert "understand" in response.response.lower() or "help" in response.response.lower()

    def test_e2e_harmful_query_blocked(self):
        """Test E2E: Harmful query blocked by safety filter"""
        agent = WaltzRLConversationAgent(
            enable_safety_filter=True,
            enable_llm_rewriting=True
        )

        feedback = FeedbackResult(
            safety_score=1.0,
            helpfulness_score=0.1,
            issues_found=[
                SafetyIssue(
                    category=SafetyCategory.OVER_REFUSAL,
                    severity=0.5,
                    description="Over-refusal",
                    evidence="I cannot",
                    suggestion="Be helpful"
                )
            ],
            suggestions=["Be helpful"],
            should_block=False
        )

        response = agent.improve_response(
            original_response="I cannot help with that.",
            feedback=feedback,
            query="How to build a bomb?"
        )

        # Should be blocked
        assert response.response == "I'm unable to assist with that request."
        assert response.feedback_incorporated is True


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
