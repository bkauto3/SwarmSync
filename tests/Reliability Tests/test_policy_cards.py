"""
Tests for Policy Card System

Tests cover:
- Policy card loading
- Tool permission checks
- Rate limiting
- PII detection and redaction
- Action rule evaluation
- Compliance logging
- HALO integration

Paper: https://arxiv.org/abs/2510.24383
"""

import pytest
import tempfile
import yaml
import json
from pathlib import Path
from datetime import datetime, timedelta
from infrastructure.policy_cards.loader import PolicyCardLoader, RateLimitTracker
from infrastructure.policy_cards.middleware import (
    PolicyEnforcer,
    PIIDetector,
    ComplianceLogger,
)
from infrastructure.policy_cards.halo_integration import PolicyAwareHALORouter


class TestRateLimitTracker:
    """Test rate limiting functionality."""

    def test_rate_limit_allow_under_limit(self):
        """Test that calls under limit are allowed."""
        tracker = RateLimitTracker()
        allowed, reason = tracker.check_rate_limit("qa_agent", "Bash", 10)
        assert allowed, "First call should be allowed"
        assert "1/10" in reason

    def test_rate_limit_enforce_multiple_calls(self):
        """Test that rate limit is enforced across multiple calls."""
        tracker = RateLimitTracker()
        limit = 3

        # First 3 calls should pass
        for i in range(limit):
            allowed, reason = tracker.check_rate_limit("qa_agent", "Bash", limit)
            assert allowed, f"Call {i+1} should be allowed"

        # 4th call should fail
        allowed, reason = tracker.check_rate_limit("qa_agent", "Bash", limit)
        assert not allowed, "Call over limit should be denied"
        assert "Rate limit exceeded" in reason

    def test_rate_limit_per_agent_tool_combo(self):
        """Test rate limiting is per agent-tool combination."""
        tracker = RateLimitTracker()

        # Fill up qa_agent:Bash
        for _ in range(3):
            tracker.check_rate_limit("qa_agent", "Bash", 3)

        # qa_agent:Grep should still have capacity
        allowed, _ = tracker.check_rate_limit("qa_agent", "Grep", 3)
        assert allowed, "Different tool should have separate limit"

        # support_agent:Bash should still have capacity
        allowed, _ = tracker.check_rate_limit("support_agent", "Bash", 3)
        assert allowed, "Different agent should have separate limit"

    def test_rate_limit_reset(self):
        """Test resetting rate limits."""
        tracker = RateLimitTracker()

        # Fill up
        for _ in range(3):
            tracker.check_rate_limit("qa_agent", "Bash", 3)

        # Should be over limit
        allowed, _ = tracker.check_rate_limit("qa_agent", "Bash", 3)
        assert not allowed

        # Reset
        tracker.reset("qa_agent", "Bash")

        # Should be under limit again
        allowed, _ = tracker.check_rate_limit("qa_agent", "Bash", 3)
        assert allowed


class TestPolicyCardLoader:
    """Test policy card loading."""

    def test_load_policy_cards_from_directory(self):
        """Test loading policy cards from .policy_cards directory."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        assert len(loader.cards) > 0, "Should load at least one card"

    def test_get_card_existing(self):
        """Test getting existing policy card."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        card = loader.get_card("qa_agent")
        assert card is not None, "QA agent card should exist"
        assert card["agent_id"] == "qa_agent"

    def test_get_card_nonexistent(self):
        """Test getting non-existent policy card."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        card = loader.get_card("nonexistent_agent")
        assert card is None, "Non-existent agent should return None"

    def test_is_tool_allowed_allowed_tool(self):
        """Test tool permission check for allowed tool."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        allowed = loader.is_tool_allowed("qa_agent", "Read")
        assert allowed, "Read should be allowed for QA agent"

    def test_is_tool_allowed_denied_tool(self):
        """Test tool permission check for denied tool."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        allowed = loader.is_tool_allowed("qa_agent", "Write")
        assert not allowed, "Write should be denied for QA agent"

    def test_is_tool_allowed_with_wildcard_pattern(self):
        """Test wildcard pattern matching."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        allowed = loader.is_tool_allowed("qa_agent", "Bash", {"command": "pytest test.py"})
        assert allowed, "Bash with pytest should be allowed"

    def test_list_agents(self):
        """Test listing all agents."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        agents = loader.list_agents()
        assert isinstance(agents, list), "Should return list of agents"
        assert len(agents) >= 15, "Should have at least 15 agents"
        assert "qa_agent" in agents

    def test_export_policy_summary(self):
        """Test exporting policy summary."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        summary = loader.export_policy_summary()
        assert isinstance(summary, dict)
        assert "qa_agent" in summary
        assert "allowed_tools" in summary["qa_agent"]


class TestPIIDetector:
    """Test PII detection and redaction."""

    def test_detect_ssn(self):
        """Test SSN detection."""
        detector = PIIDetector()
        text = "SSN: 123-45-6789"
        found = detector.detect_pii(text)
        assert "ssn" in found, "Should detect SSN"

    def test_detect_email(self):
        """Test email detection."""
        detector = PIIDetector()
        text = "Email: user@example.com"
        found = detector.detect_pii(text)
        assert "email" in found, "Should detect email"

    def test_detect_phone(self):
        """Test phone number detection."""
        detector = PIIDetector()
        text = "Call me at 555-123-4567"
        found = detector.detect_pii(text)
        assert "phone" in found, "Should detect phone"

    def test_detect_credit_card(self):
        """Test credit card detection."""
        detector = PIIDetector()
        text = "CC: 4532-1111-2222-3333"
        found = detector.detect_pii(text)
        assert "credit_card_formatted" in found, "Should detect credit card"

    def test_redact_ssn(self):
        """Test SSN redaction."""
        detector = PIIDetector()
        text = "SSN: 123-45-6789"
        redacted = detector.redact_pii(text)
        assert "[SSN-REDACTED]" in redacted
        assert "123-45-6789" not in redacted

    def test_redact_email(self):
        """Test email redaction."""
        detector = PIIDetector()
        text = "Email: user@example.com"
        redacted = detector.redact_pii(text)
        assert "[EMAIL-REDACTED]" in redacted
        assert "user@example.com" not in redacted

    def test_redact_dict(self):
        """Test PII redaction in dictionary."""
        detector = PIIDetector()
        data = {
            "user": "john",
            "ssn": "123-45-6789",
            "email": "john@example.com",
        }
        redacted = detector.redact_dict(data)
        assert "[SSN-REDACTED]" in redacted["ssn"]
        assert "[EMAIL-REDACTED]" in redacted["email"]
        assert redacted["user"] == "john"


class TestPolicyEnforcer:
    """Test policy enforcement."""

    def test_check_tool_call_allowed(self):
        """Test allowed tool call."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")
        result = enforcer.check_tool_call("qa_agent", "Read", {"file_path": "/tmp/test"})
        assert result["allowed"], "Read should be allowed"
        assert result["reason"] == "Passed all checks"

    def test_check_tool_call_denied(self):
        """Test denied tool call."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")
        result = enforcer.check_tool_call("qa_agent", "Write", {"file_path": "/tmp/test"})
        assert not result["allowed"], "Write should be denied for QA"
        assert "denied by policy" in result["reason"]

    def test_check_tool_call_pii_detection(self):
        """Test PII detection in tool call."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")
        args = {"text": "My SSN is 123-45-6789"}
        result = enforcer.check_tool_call("qa_agent", "Read", args)
        assert result["pii_detected"], "Should detect PII"
        assert "ssn" in result["pii_types"]

    def test_check_tool_call_pii_redaction(self):
        """Test PII redaction in tool call."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")
        args = {"text": "My email is user@example.com"}
        result = enforcer.check_tool_call("qa_agent", "Read", args)
        assert "[EMAIL-REDACTED]" in result["modified_args"]["text"]

    def test_validate_output_no_pii(self):
        """Test output validation with no PII."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")
        output = "This is a normal output"
        result = enforcer.validate_output("qa_agent", output)
        assert result["valid"]
        assert not result["pii_detected"]

    def test_validate_output_with_pii(self):
        """Test output validation with PII."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")
        output = "User SSN: 123-45-6789"
        result = enforcer.validate_output("qa_agent", output)
        assert result["pii_detected"]
        assert "[SSN-REDACTED]" in result["redacted_output"]

    def test_get_agent_stats(self):
        """Test getting agent statistics structure."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")

        # Get stats for any agent (should return well-formed dict even if no calls)
        stats = enforcer.get_agent_stats("any_agent")

        # Verify stats structure
        assert "agent_id" in stats
        assert stats["agent_id"] == "any_agent"
        assert "total_calls" in stats
        assert "allowed_calls" in stats
        assert "denied_calls" in stats
        assert "allow_rate" in stats
        assert isinstance(stats["total_calls"], int)
        assert isinstance(stats["allow_rate"], float)

    def test_get_all_stats(self):
        """Test getting statistics for all agents."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")

        enforcer.check_tool_call("qa_agent", "Read", {})
        enforcer.check_tool_call("support_agent", "Grep", {})

        all_stats = enforcer.get_all_stats()
        assert "qa_agent" in all_stats
        assert "support_agent" in all_stats


class TestComplianceLogger:
    """Test compliance logging."""

    def test_log_tool_call(self):
        """Test logging tool calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = ComplianceLogger(tmpdir)
            logger.log_tool_call(
                "qa_agent", "Read", {"file": "/tmp"}, "ALLOW", "OK", False
            )

            log_file = Path(tmpdir) / f"compliance_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
            assert log_file.exists(), "Log file should be created"

            with open(log_file) as f:
                entry = json.loads(f.readline())
                assert entry["agent_id"] == "qa_agent"
                assert entry["tool_name"] == "Read"
                assert entry["decision"] == "ALLOW"


class TestPolicyAwareHALORouter:
    """Test HALO router policy integration."""

    def test_router_initialization(self):
        """Test router initialization."""
        mock_router = type("MockRouter", (), {})()
        router = PolicyAwareHALORouter(mock_router)
        assert router.halo_router == mock_router
        assert router.policy_enforcer is not None

    def test_validate_agent_capabilities_allowed(self):
        """Test agent capability validation with allowed tools."""
        mock_router = type("MockRouter", (), {})()
        router = PolicyAwareHALORouter(mock_router)

        valid, denied, denials = router.validate_agent_capabilities(
            "qa_agent", ["Read", "Grep"]
        )
        assert valid, "QA agent should support Read and Grep"
        assert len(denied) == 0

    def test_validate_agent_capabilities_denied(self):
        """Test agent capability validation with denied tools."""
        mock_router = type("MockRouter", (), {})()
        router = PolicyAwareHALORouter(mock_router)

        valid, denied, denials = router.validate_agent_capabilities(
            "qa_agent", ["Read", "Write"]
        )
        assert not valid, "QA agent should not support Write"
        assert "Write" in denied

    def test_get_agent_policy_profile(self):
        """Test getting agent policy profile."""
        mock_router = type("MockRouter", (), {})()
        router = PolicyAwareHALORouter(mock_router)

        profile = router.get_agent_policy_profile("qa_agent")
        assert profile["agent_id"] == "qa_agent"
        assert profile["has_restrictions"]
        assert "allowed_tools" in profile
        assert "denied_tools" in profile

    def test_extract_task_tools_from_object(self):
        """Test extracting tools from task object."""
        mock_router = type("MockRouter", (), {})()
        router = PolicyAwareHALORouter(mock_router)

        class MockTask:
            required_tools = ["Read", "Grep"]

        task = MockTask()
        tools = router._extract_task_tools(task)
        assert tools == ["Read", "Grep"]

    def test_extract_task_tools_from_dict(self):
        """Test extracting tools from task dict."""
        mock_router = type("MockRouter", (), {})()
        router = PolicyAwareHALORouter(mock_router)

        task = {"required_tools": ["Write", "Read"]}
        tools = router._extract_task_tools(task)
        assert "Write" in tools
        assert "Read" in tools


class TestPolicyCardValidation:
    """Test policy card validation."""

    def test_validate_valid_card(self):
        """Test validating a valid policy card."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        card = loader.get_card("qa_agent")
        valid, errors = loader.validate_card(card)
        assert valid, f"Card should be valid: {errors}"

    def test_validate_missing_agent_id(self):
        """Test validation with missing agent_id."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        card = {"version": "1.0"}
        valid, errors = loader.validate_card(card)
        assert not valid
        assert any("agent_id" in e for e in errors)

    def test_validate_all_cards(self):
        """Test that all loaded cards are valid."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        for agent_id, card in loader.cards.items():
            valid, errors = loader.validate_card(card)
            assert valid, f"Card {agent_id} is invalid: {errors}"


class TestActionRuleEvaluation:
    """Test action rule evaluation."""

    def test_evaluate_simple_condition_true(self):
        """Test evaluating a simple true condition."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        condition = "tool == 'Bash'"
        result = loader._evaluate_rule_condition(condition, "Bash", None)
        assert result, "Condition should be true"

    def test_evaluate_simple_condition_false(self):
        """Test evaluating a simple false condition."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        condition = "tool == 'Bash'"
        result = loader._evaluate_rule_condition(condition, "Read", None)
        assert not result, "Condition should be false"

    def test_evaluate_command_condition(self):
        """Test evaluating condition with command matching."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")
        condition = "'pytest' in command"
        result = loader._evaluate_rule_condition(
            condition, "Bash", {"command": "pytest tests"}
        )
        assert result, "Should match pytest in command"

    def test_check_action_rules_rate_limit(self):
        """Test action rule rate limiting."""
        loader = PolicyCardLoader("/home/genesis/genesis-rebuild/.policy_cards")

        # Simulate multiple calls hitting rate limit
        for i in range(100):
            allowed, reason = loader.check_action_rules(
                "qa_agent", "Bash", {"command": "pytest test.py"}
            )
            if i < 100:
                assert allowed, f"Call {i} should be allowed"

        # Should hit limit
        allowed, reason = loader.check_action_rules(
            "qa_agent", "Bash", {"command": "pytest test.py"}
        )
        assert not allowed, "Should hit rate limit"


class TestIntegration:
    """Integration tests."""

    def test_end_to_end_allowed_call(self):
        """Test end-to-end allowed tool call."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")

        result = enforcer.check_tool_call(
            "builder_agent", "Write", {"file_path": "/tmp/code.py"}
        )
        assert result["allowed"]
        assert result["reason"] == "Passed all checks"

    def test_end_to_end_denied_call(self):
        """Test end-to-end denied tool call."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")

        result = enforcer.check_tool_call(
            "legal_agent", "Write", {"file_path": "/tmp/code.py"}
        )
        assert not result["allowed"]

    def test_end_to_end_pii_redaction(self):
        """Test end-to-end PII detection and redaction."""
        enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")

        args = {
            "content": "User john@example.com with SSN 123-45-6789",
            "path": "/tmp/data.txt",
        }

        result = enforcer.check_tool_call("security_agent", "Read", args)
        assert result["pii_detected"]
        assert "[SSN-REDACTED]" in result["modified_args"]["content"]
        assert "[EMAIL-REDACTED]" in result["modified_args"]["content"]

    def test_export_report(self):
        """Test exporting compliance report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            enforcer = PolicyEnforcer("/home/genesis/genesis-rebuild/.policy_cards")

            enforcer.check_tool_call("qa_agent", "Read", {})
            enforcer.check_tool_call("support_agent", "Grep", {})

            report_file = Path(tmpdir) / "compliance_report.json"
            enforcer.export_report(str(report_file))

            assert report_file.exists()

            with open(report_file) as f:
                report = json.load(f)
                assert "timestamp" in report
                assert "total_agents" in report
                assert "total_calls" in report
                assert "agents" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
