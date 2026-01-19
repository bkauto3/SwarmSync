"""
Test Suite for Context Profile Optimization System
Tests MQA/GQA-based long-context optimization for 40-60% memory cost reduction

Test Coverage:
- Profile selection (auto + manual)
- Cost savings calculation
- Configuration validation
- Agent integration (Analyst, Builder)
- Edge cases and error handling
"""

import pytest
import json
from infrastructure.context_profiles import (
    ContextProfile,
    ContextProfileManager,
    ProfileConfig,
    PROFILE_CONFIGS,
    get_profile_manager,
    reset_profile_manager,
    estimate_tokens_from_chars,
    get_profile_recommendation
)


class TestContextProfileEnums:
    """Test profile enumeration and constants"""

    def test_profile_enum_values(self):
        """All expected profiles exist"""
        assert ContextProfile.DEFAULT.value == "default"
        assert ContextProfile.LONGDOC.value == "longdoc"
        assert ContextProfile.VIDEO.value == "video"
        assert ContextProfile.CODE.value == "code"

    def test_all_profiles_have_configs(self):
        """Every profile has a configuration"""
        for profile in ContextProfile:
            assert profile in PROFILE_CONFIGS
            config = PROFILE_CONFIGS[profile]
            assert isinstance(config, ProfileConfig)


class TestProfileConfigurations:
    """Test profile configuration values"""

    def test_default_profile_config(self):
        """DEFAULT profile has full attention, no cost reduction"""
        config = PROFILE_CONFIGS[ContextProfile.DEFAULT]

        assert config.max_context == 8000
        assert config.attention_type == "full"
        assert config.num_key_value_heads is None
        assert config.window_size is None
        assert config.global_tokens is None
        assert config.cost_multiplier == 1.0  # No savings

    def test_longdoc_profile_config(self):
        """LONGDOC profile has GQA, 60% cost reduction"""
        config = PROFILE_CONFIGS[ContextProfile.LONGDOC]

        assert config.max_context == 128000  # 128k tokens
        assert config.attention_type == "grouped_query"
        assert config.num_key_value_heads == 8  # Reduced KV heads
        assert config.cost_multiplier == 0.4  # 60% savings

    def test_video_profile_config(self):
        """VIDEO profile has sparse attention, 50% cost reduction"""
        config = PROFILE_CONFIGS[ContextProfile.VIDEO]

        assert config.max_context == 100000  # 100k tokens for frames
        assert config.attention_type == "sparse"
        assert config.window_size == 512  # Local attention
        assert config.global_tokens == 64  # Global summary
        assert config.cost_multiplier == 0.5  # 50% savings

    def test_code_profile_config(self):
        """CODE profile has GQA, 40% cost reduction"""
        config = PROFILE_CONFIGS[ContextProfile.CODE]

        assert config.max_context == 64000  # 64k tokens for code
        assert config.attention_type == "grouped_query"
        assert config.num_key_value_heads == 16  # More than LONGDOC
        assert config.cost_multiplier == 0.6  # 40% savings


class TestProfileManager:
    """Test ContextProfileManager functionality"""

    def setup_method(self):
        """Reset profile manager before each test"""
        reset_profile_manager()
        self.manager = get_profile_manager()

    def test_singleton_pattern(self):
        """Profile manager uses singleton pattern"""
        manager1 = get_profile_manager()
        manager2 = get_profile_manager()

        assert manager1 is manager2  # Same instance

    def test_auto_select_longdoc(self):
        """Long documents (>8k chars) → LONGDOC profile"""
        profile = self.manager.select_profile(
            task_type="document analysis",
            context_length=50000,  # 50k chars
            has_video=False,
            has_code=False
        )

        assert profile == ContextProfile.LONGDOC
        assert self.manager.profile_usage[ContextProfile.LONGDOC] == 1

    def test_auto_select_video(self):
        """Video content → VIDEO profile"""
        profile = self.manager.select_profile(
            task_type="video analysis",
            context_length=100000,
            has_video=True
        )

        assert profile == ContextProfile.VIDEO
        assert self.manager.profile_usage[ContextProfile.VIDEO] == 1

    def test_auto_select_code_long_context(self):
        """Code with >8k context → CODE profile"""
        profile = self.manager.select_profile(
            task_type="code repository analysis",
            context_length=40000,
            has_code=True
        )

        assert profile == ContextProfile.CODE
        assert self.manager.profile_usage[ContextProfile.CODE] == 1

    def test_auto_select_code_short_context(self):
        """Code with <8k context → DEFAULT profile"""
        profile = self.manager.select_profile(
            task_type="code snippet",
            context_length=5000,
            has_code=True
        )

        assert profile == ContextProfile.DEFAULT

    def test_auto_select_default_short(self):
        """Short contexts → DEFAULT profile"""
        profile = self.manager.select_profile(
            task_type="simple query",
            context_length=1000,
            has_video=False,
            has_code=False
        )

        assert profile == ContextProfile.DEFAULT

    def test_force_profile_override(self):
        """force_profile overrides auto-selection"""
        profile = self.manager.select_profile(
            task_type="short text",
            context_length=1000,
            force_profile=ContextProfile.LONGDOC
        )

        assert profile == ContextProfile.LONGDOC


class TestCostSavings:
    """Test cost savings calculations"""

    def setup_method(self):
        reset_profile_manager()
        self.manager = get_profile_manager()

    def test_longdoc_cost_savings(self):
        """LONGDOC profile provides 60% cost reduction"""
        savings = self.manager.estimate_cost_savings(
            profile=ContextProfile.LONGDOC,
            tokens=50000,  # 50k tokens
            baseline_cost_per_1m=3.0  # $3/1M tokens
        )

        assert savings["savings_pct"] == 60.0
        assert abs(savings["baseline_cost"] - 0.15) < 0.001  # $0.15 for 50k tokens
        assert abs(savings["profile_cost"] - 0.06) < 0.001  # 40% of baseline
        assert abs(savings["savings"] - 0.09) < 0.001  # $0.09 saved

    def test_video_cost_savings(self):
        """VIDEO profile provides 50% cost reduction"""
        savings = self.manager.estimate_cost_savings(
            profile=ContextProfile.VIDEO,
            tokens=100000,  # 100k tokens
            baseline_cost_per_1m=3.0
        )

        assert savings["savings_pct"] == 50.0
        assert abs(savings["baseline_cost"] - 0.30) < 0.001
        assert abs(savings["profile_cost"] - 0.15) < 0.001
        assert abs(savings["savings"] - 0.15) < 0.001

    def test_code_cost_savings(self):
        """CODE profile provides 40% cost reduction"""
        savings = self.manager.estimate_cost_savings(
            profile=ContextProfile.CODE,
            tokens=25000,
            baseline_cost_per_1m=3.0
        )

        assert savings["savings_pct"] == 40.0
        assert abs(savings["baseline_cost"] - 0.075) < 0.001
        assert abs(savings["profile_cost"] - 0.045) < 0.001
        assert abs(savings["savings"] - 0.030) < 0.001

    def test_default_no_savings(self):
        """DEFAULT profile has no cost reduction"""
        savings = self.manager.estimate_cost_savings(
            profile=ContextProfile.DEFAULT,
            tokens=8000,
            baseline_cost_per_1m=3.0
        )

        assert savings["savings_pct"] == 0.0
        assert savings["baseline_cost"] == savings["profile_cost"]
        assert savings["savings"] == 0.0

    def test_cumulative_savings_tracking(self):
        """Manager tracks cumulative cost savings"""
        # First request
        self.manager.estimate_cost_savings(
            ContextProfile.LONGDOC, 50000, 3.0
        )

        # Second request
        self.manager.estimate_cost_savings(
            ContextProfile.VIDEO, 100000, 3.0
        )

        # Should accumulate
        assert self.manager.cost_savings > 0.2  # At least $0.20 saved
        assert self.manager.total_tokens_processed == 150000


class TestUsageStatistics:
    """Test profile usage statistics"""

    def setup_method(self):
        reset_profile_manager()
        self.manager = get_profile_manager()

    def test_empty_stats(self):
        """Stats are empty initially"""
        stats = self.manager.get_usage_stats()

        assert stats["total_requests"] == 0
        assert "message" in stats

    def test_profile_distribution(self):
        """Stats show profile distribution"""
        # Make requests
        self.manager.select_profile("doc analysis", 50000)  # LONGDOC
        self.manager.select_profile("video", 100000, has_video=True)  # VIDEO
        self.manager.select_profile("short", 1000)  # DEFAULT

        stats = self.manager.get_usage_stats()

        assert stats["total_requests"] == 3
        assert "longdoc" in stats["profile_distribution"]
        assert "video" in stats["profile_distribution"]
        assert "default" in stats["profile_distribution"]

    def test_cost_savings_in_stats(self):
        """Stats include total cost savings"""
        self.manager.select_profile("doc", 50000)
        self.manager.estimate_cost_savings(
            ContextProfile.LONGDOC, 50000, 3.0
        )

        stats = self.manager.get_usage_stats()

        assert stats["total_cost_savings"] > 0


class TestContextValidation:
    """Test context length validation"""

    def setup_method(self):
        reset_profile_manager()
        self.manager = get_profile_manager()

    def test_validate_within_limit(self):
        """Context within limit passes validation"""
        is_valid, error = self.manager.validate_context_length(
            profile=ContextProfile.LONGDOC,
            context_length=50000  # Within 128k limit
        )

        assert is_valid is True
        assert error is None

    def test_validate_exceeds_limit(self):
        """Context exceeding limit fails validation"""
        is_valid, error = self.manager.validate_context_length(
            profile=ContextProfile.DEFAULT,
            context_length=10000  # Exceeds 8k limit
        )

        assert is_valid is False
        assert "exceeds" in error.lower()

    def test_validate_edge_case(self):
        """Exactly at limit passes validation"""
        is_valid, error = self.manager.validate_context_length(
            profile=ContextProfile.DEFAULT,
            context_length=8000  # Exactly at limit
        )

        assert is_valid is True


class TestUtilityFunctions:
    """Test utility functions"""

    def test_estimate_tokens_from_chars(self):
        """Token estimation from character count"""
        # 1 token ≈ 4 chars
        assert estimate_tokens_from_chars("a" * 400) == 100
        assert estimate_tokens_from_chars("a" * 4000) == 1000
        assert estimate_tokens_from_chars("") == 1  # Minimum 1 token

    def test_get_profile_recommendation_video(self):
        """Recommendation for video content"""
        profile, explanation = get_profile_recommendation(
            "video analysis",
            100000
        )

        assert profile == ContextProfile.VIDEO
        assert "video" in explanation.lower()
        assert "50%" in explanation

    def test_get_profile_recommendation_code(self):
        """Recommendation for code content"""
        profile, explanation = get_profile_recommendation(
            "code repository",
            40000
        )

        assert profile == ContextProfile.CODE
        assert "code" in explanation.lower()
        assert "40%" in explanation

    def test_get_profile_recommendation_longdoc(self):
        """Recommendation for long documents"""
        profile, explanation = get_profile_recommendation(
            "document analysis",
            50000
        )

        assert profile == ContextProfile.LONGDOC
        assert "longdoc" in explanation.lower() or "document" in explanation.lower()
        assert "60%" in explanation

    def test_get_profile_recommendation_default(self):
        """Recommendation for short content"""
        profile, explanation = get_profile_recommendation(
            "simple query",
            1000
        )

        assert profile == ContextProfile.DEFAULT
        assert "default" in explanation.lower()


class TestAgentIntegration:
    """Test integration with agents"""

    def test_analyst_agent_integration(self):
        """Analyst agent can use LONGDOC profile"""
        # This test verifies the analyst agent has the profile manager
        # In production, would test actual agent method calls
        from agents.analyst_agent import AnalystAgent

        agent = AnalystAgent()

        # Verify profile manager is initialized
        assert hasattr(agent, 'profile_manager')
        assert agent.profile_manager is not None

        # Verify analyze_long_document method exists
        assert hasattr(agent, 'analyze_long_document')

    def test_analyst_longdoc_method(self):
        """Analyst analyze_long_document returns proper structure"""
        from agents.analyst_agent import AnalystAgent

        agent = AnalystAgent()

        # Create long document
        long_doc = "x" * 100000  # 100k chars

        # Analyze with LONGDOC profile
        result_str = agent.analyze_long_document(long_doc, "test query")
        result = json.loads(result_str)

        # Verify structure
        assert result["context_profile"] == "longdoc"
        assert result["estimated_tokens"] == 25000  # 100k / 4
        assert result["cost_savings"]["savings_pct"] == 60.0
        assert "profile_config" in result
        assert result["profile_config"]["attention_type"] == "grouped_query"


class TestRegressionAndEdgeCases:
    """Test edge cases and regression scenarios"""

    def setup_method(self):
        reset_profile_manager()
        self.manager = get_profile_manager()

    def test_zero_tokens(self):
        """Handle zero token request"""
        savings = self.manager.estimate_cost_savings(
            profile=ContextProfile.LONGDOC,
            tokens=0,
            baseline_cost_per_1m=3.0
        )

        assert savings["baseline_cost"] == 0.0
        assert savings["profile_cost"] == 0.0
        assert savings["savings"] == 0.0

    def test_very_large_token_count(self):
        """Handle very large token counts"""
        savings = self.manager.estimate_cost_savings(
            profile=ContextProfile.LONGDOC,
            tokens=10_000_000,  # 10M tokens
            baseline_cost_per_1m=3.0
        )

        assert savings["baseline_cost"] == 30.0  # $30
        assert savings["profile_cost"] == 12.0  # $12 (40% of baseline)
        assert savings["savings"] == 18.0  # $18 saved

    def test_multiple_profile_selections(self):
        """Handle multiple rapid profile selections"""
        for _ in range(100):
            self.manager.select_profile("doc", 50000)

        assert self.manager.profile_usage[ContextProfile.LONGDOC] == 100

    def test_reset_stats(self):
        """Stats reset properly"""
        # Generate some stats
        self.manager.select_profile("doc", 50000)
        self.manager.estimate_cost_savings(
            ContextProfile.LONGDOC, 50000, 3.0
        )

        # Reset
        self.manager.reset_stats()

        # Verify reset
        stats = self.manager.get_usage_stats()
        assert stats["total_requests"] == 0
        assert self.manager.cost_savings == 0.0

    def test_keyword_detection_case_insensitive(self):
        """Profile selection is case-insensitive"""
        profile1 = self.manager.select_profile("VIDEO analysis", 100000)
        profile2 = self.manager.select_profile("video ANALYSIS", 100000)

        assert profile1 == profile2 == ContextProfile.VIDEO


# Performance validation test
class TestPerformanceValidation:
    """Validate 40-60% cost reduction targets"""

    def test_cost_reduction_targets(self):
        """Validate advertised cost reduction percentages"""
        manager = get_profile_manager()

        # LONGDOC: 60% reduction
        longdoc_savings = manager.estimate_cost_savings(
            ContextProfile.LONGDOC, 50000, 3.0
        )
        assert longdoc_savings["savings_pct"] == 60.0

        # VIDEO: 50% reduction
        video_savings = manager.estimate_cost_savings(
            ContextProfile.VIDEO, 100000, 3.0
        )
        assert video_savings["savings_pct"] == 50.0

        # CODE: 40% reduction
        code_savings = manager.estimate_cost_savings(
            ContextProfile.CODE, 25000, 3.0
        )
        assert code_savings["savings_pct"] == 40.0

    def test_real_world_workload_simulation(self):
        """Simulate real-world mixed workload"""
        manager = get_profile_manager()

        # Simulate 1000 requests
        # - 40% short (DEFAULT)
        # - 40% long docs (LONGDOC)
        # - 20% video (VIDEO)

        total_baseline_cost = 0.0
        total_profile_cost = 0.0

        for _ in range(400):
            # Short requests (8k tokens avg)
            s = manager.estimate_cost_savings(
                ContextProfile.DEFAULT, 8000, 3.0
            )
            total_baseline_cost += s["baseline_cost"]
            total_profile_cost += s["profile_cost"]

        for _ in range(400):
            # Long doc requests (50k tokens avg)
            s = manager.estimate_cost_savings(
                ContextProfile.LONGDOC, 50000, 3.0
            )
            total_baseline_cost += s["baseline_cost"]
            total_profile_cost += s["profile_cost"]

        for _ in range(200):
            # Video requests (100k tokens avg)
            s = manager.estimate_cost_savings(
                ContextProfile.VIDEO, 100000, 3.0
            )
            total_baseline_cost += s["baseline_cost"]
            total_profile_cost += s["profile_cost"]

        # Calculate overall savings
        total_savings = total_baseline_cost - total_profile_cost
        total_savings_pct = (total_savings / total_baseline_cost) * 100

        # With this distribution, we expect ~24% overall savings
        # (40% no savings + 40% * 60% + 20% * 50% = 24% + 10% = 34%)
        assert total_savings_pct > 30.0  # At least 30% overall

        print(f"\n=== Real-World Workload Simulation ===")
        print(f"Total baseline cost: ${total_baseline_cost:.2f}")
        print(f"Total profile cost: ${total_profile_cost:.2f}")
        print(f"Total savings: ${total_savings:.2f} ({total_savings_pct:.1f}%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
