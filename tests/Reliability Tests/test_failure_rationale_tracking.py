"""
Unit Tests for Failure Rationale Tracking
Version: 1.0
Last Updated: October 15, 2025

Comprehensive test suite for failure rationale tracking in Replay Buffer,
ReasoningBank integration, and Builder Agent enhancements.

Tests:
1. Trajectory dataclass with failure fields
2. Anti-pattern storage in ReasoningBank
3. Anti-pattern queries from ReplayBuffer
4. Builder Agent integration
"""

import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import Mock, patch

# Import system under test
import sys
sys.path.insert(0, '/home/genesis/genesis-rebuild')

from infrastructure.replay_buffer import (
    ReplayBuffer,
    Trajectory,
    ActionStep,
    OutcomeTag,
    get_replay_buffer
)
from infrastructure.reasoning_bank import (
    ReasoningBank,
    get_reasoning_bank,
    StrategyNugget
)


class TestTrajectoryFailureFields:
    """Test Trajectory dataclass enhancements"""

    def test_trajectory_with_failure_fields(self):
        """Test creating trajectory with failure rationale fields"""
        trajectory = Trajectory(
            trajectory_id="test_123",
            agent_id="test_agent",
            task_description="Build authentication system",
            initial_state={},
            steps=(),
            final_outcome=OutcomeTag.FAILURE.value,
            reward=0.0,
            metadata={},
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=10.5,
            failure_rationale="Supabase authentication failed due to missing SUPABASE_URL environment variable",
            error_category="configuration",
            fix_applied="Added .env.example template with required variables"
        )

        assert trajectory.failure_rationale is not None
        assert "SUPABASE_URL" in trajectory.failure_rationale
        assert trajectory.error_category == "configuration"
        assert trajectory.fix_applied is not None

    def test_trajectory_backward_compatible(self):
        """Test backward compatibility - old trajectories without failure fields"""
        trajectory = Trajectory(
            trajectory_id="test_456",
            agent_id="test_agent",
            task_description="Build dashboard",
            initial_state={},
            steps=(),
            final_outcome=OutcomeTag.SUCCESS.value,
            reward=1.0,
            metadata={},
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=15.0
        )

        # Should have None for optional fields
        assert trajectory.failure_rationale is None
        assert trajectory.error_category is None
        assert trajectory.fix_applied is None

    def test_trajectory_frozen_immutability(self):
        """Test that Trajectory is immutable (frozen dataclass)"""
        trajectory = Trajectory(
            trajectory_id="test_789",
            agent_id="test_agent",
            task_description="Test task",
            initial_state={},
            steps=(),
            final_outcome=OutcomeTag.SUCCESS.value,
            reward=0.8,
            metadata={},
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=5.0
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            trajectory.failure_rationale = "Should not be allowed"


class TestReplayBufferAntiPatterns:
    """Test ReplayBuffer anti-pattern functionality"""

    @pytest.fixture
    def replay_buffer(self):
        """Create replay buffer for testing (in-memory)"""
        return ReplayBuffer()

    @pytest.fixture
    def mock_reasoning_bank(self):
        """Create mock ReasoningBank"""
        mock_bank = Mock(spec=ReasoningBank)
        mock_bank.store_strategy = Mock(return_value="strategy_123")
        mock_bank.search_strategies = Mock(return_value=[])
        return mock_bank

    def test_store_trajectory_with_failure_rationale(self, replay_buffer):
        """Test storing trajectory with failure rationale"""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            agent_id="builder_agent",
            task_description="Build API endpoints",
            initial_state={"environment": "test"},
            steps=tuple([
                ActionStep(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    tool_name="generate_backend",
                    tool_args={"routes": ["users"]},
                    tool_result="Failed: Missing database connection",
                    agent_reasoning="Attempting to generate backend API"
                )
            ]),
            final_outcome=OutcomeTag.FAILURE.value,
            reward=0.0,
            metadata={"build_type": "backend"},
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=12.5,
            failure_rationale="Database connection string not configured in environment",
            error_category="configuration",
            fix_applied="Added DATABASE_URL to .env.example"
        )

        # Store trajectory
        trajectory_id = replay_buffer.store_trajectory(trajectory)
        assert trajectory_id == trajectory.trajectory_id

        # Retrieve and verify
        retrieved = replay_buffer.get_trajectory(trajectory_id)
        assert retrieved is not None
        assert retrieved.failure_rationale == trajectory.failure_rationale
        assert retrieved.error_category == trajectory.error_category
        assert retrieved.fix_applied == trajectory.fix_applied

    def test_trajectory_serialization_with_failure_fields(self, replay_buffer):
        """Test serialization/deserialization of failure fields"""
        trajectory = Trajectory(
            trajectory_id=str(uuid.uuid4()),
            agent_id="test_agent",
            task_description="Test task",
            initial_state={},
            steps=(),
            final_outcome=OutcomeTag.FAILURE.value,
            reward=0.0,
            metadata={},
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=5.0,
            failure_rationale="Network timeout during API call",
            error_category="network",
            fix_applied="Added retry logic with exponential backoff"
        )

        # Convert to dict
        traj_dict = replay_buffer._trajectory_to_dict(trajectory)
        assert "failure_rationale" in traj_dict
        assert traj_dict["failure_rationale"] == "Network timeout during API call"
        assert traj_dict["error_category"] == "network"

        # Convert back to object
        reconstructed = replay_buffer._dict_to_trajectory(traj_dict)
        assert reconstructed.failure_rationale == trajectory.failure_rationale
        assert reconstructed.error_category == trajectory.error_category
        assert reconstructed.fix_applied == trajectory.fix_applied

    def test_anti_pattern_storage_integration(self, replay_buffer):
        """Test automatic anti-pattern storage when storing failed trajectory"""
        # Mock the ReasoningBank at the source
        with patch('infrastructure.reasoning_bank.get_reasoning_bank') as mock_get_bank:
            mock_bank = Mock(spec=ReasoningBank)
            mock_bank.store_strategy = Mock(return_value="anti_pattern_123")
            mock_get_bank.return_value = mock_bank

            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                agent_id="builder_agent",
                task_description="Build authentication system",
                initial_state={},
                steps=tuple([
                    ActionStep(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        tool_name="generate_config",
                        tool_args={"env_vars": ["SUPABASE_URL"]},
                        tool_result="Config generated",
                        agent_reasoning="Creating environment configuration"
                    )
                ]),
                final_outcome=OutcomeTag.FAILURE.value,
                reward=0.0,
                metadata={},
                created_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=8.0,
                failure_rationale="Missing JWT_SECRET environment variable",
                error_category="configuration"
            )

            # Store trajectory (should trigger anti-pattern storage)
            trajectory_id = replay_buffer.store_trajectory(trajectory)
            assert trajectory_id is not None

            # Verify store_strategy was called
            assert mock_bank.store_strategy.called

    def test_query_anti_patterns(self, replay_buffer):
        """Test querying anti-patterns by task type"""
        # Store some failed trajectories with anti-patterns
        for i in range(3):
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                agent_id="builder_agent",
                task_description=f"Frontend build attempt {i}",
                initial_state={},
                steps=(),
                final_outcome=OutcomeTag.FAILURE.value,
                reward=0.0,
                metadata={},
                created_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=10.0,
                failure_rationale=f"Frontend error: Missing dependency {i}",
                error_category="dependency"
            )
            replay_buffer.store_trajectory(trajectory)

        # Query anti-patterns (in-memory, won't have ReasoningBank)
        # This tests the query method exists and handles gracefully
        anti_patterns = replay_buffer.query_anti_patterns("frontend", top_n=5)
        # Should return empty list when ReasoningBank not available
        assert isinstance(anti_patterns, list)

    def test_store_anti_pattern_method(self, replay_buffer, mock_reasoning_bank):
        """Test _store_anti_pattern helper method"""
        trajectory = Trajectory(
            trajectory_id="traj_999",
            agent_id="builder_agent",
            task_description="Build database schema",
            initial_state={},
            steps=tuple([
                ActionStep(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    tool_name="generate_database",
                    tool_args={"tables": ["users"]},
                    tool_result="Error: Invalid SQL syntax",
                    agent_reasoning="Creating database schema"
                )
            ]),
            final_outcome=OutcomeTag.FAILURE.value,
            reward=0.0,
            metadata={},
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=15.0,
            failure_rationale="SQL injection vulnerability in generated migration",
            error_category="security",
            fix_applied="Added parameterized queries"
        )

        # Call _store_anti_pattern
        strategy_id = replay_buffer._store_anti_pattern(trajectory, mock_reasoning_bank)
        assert strategy_id == "strategy_123"
        assert mock_reasoning_bank.store_strategy.called

        # Verify correct parameters passed
        call_args = mock_reasoning_bank.store_strategy.call_args
        assert "Anti-pattern:" in call_args[1]["description"]
        assert call_args[1]["task_metadata"]["is_anti_pattern"] is True
        assert call_args[1]["task_metadata"]["error_category"] == "security"


class TestBuilderAgentIntegration:
    """Test Builder Agent failure tracking integration"""

    def test_finalize_trajectory_with_failure_rationale(self):
        """Test _finalize_trajectory with failure tracking parameters"""
        from agents.builder_agent_enhanced import EnhancedBuilderAgent, BuildAttempt

        agent = EnhancedBuilderAgent(business_id="test_business")

        # Setup current attempt
        agent.current_attempt = BuildAttempt(
            attempt_id="attempt_123",
            business_id="test_business",
            spec_summary="Build frontend dashboard"
        )
        agent.trajectory_steps = []

        # Finalize with failure
        trajectory_id = agent._finalize_trajectory(
            outcome=OutcomeTag.FAILURE,
            reward=0.0,
            metadata={"test": True},
            failure_rationale="React component failed to compile due to TypeScript error",
            error_category="validation",
            fix_applied="Fixed type definitions in component interface"
        )

        assert trajectory_id == "attempt_123"

        # Verify trajectory was stored
        stored_traj = agent.replay_buffer.get_trajectory(trajectory_id)
        assert stored_traj is not None
        assert stored_traj.failure_rationale is not None
        assert "TypeScript error" in stored_traj.failure_rationale
        assert stored_traj.error_category == "validation"

    def test_check_anti_patterns_method(self):
        """Test _check_anti_patterns method"""
        from agents.builder_agent_enhanced import EnhancedBuilderAgent

        agent = EnhancedBuilderAgent(business_id="test_business")

        # Check anti-patterns for frontend spec
        spec = "Build a React frontend with authentication"
        anti_patterns = agent._check_anti_patterns(spec)

        # Should return list (may be empty if no anti-patterns stored)
        assert isinstance(anti_patterns, list)

    def test_check_anti_patterns_extracts_task_type(self):
        """Test that _check_anti_patterns correctly extracts task type"""
        from agents.builder_agent_enhanced import EnhancedBuilderAgent

        agent = EnhancedBuilderAgent(business_id="test_business")

        # Test different specs
        specs = [
            ("Build a frontend dashboard", "frontend"),
            ("Create backend API endpoints", "backend"),
            ("Design database schema", "database"),
            ("Generate complete application", "build")
        ]

        for spec, expected_type in specs:
            # Mock the query to verify correct task_type is used
            with patch.object(agent.replay_buffer, 'query_anti_patterns') as mock_query:
                mock_query.return_value = []
                agent._check_anti_patterns(spec)
                mock_query.assert_called_once()
                # Verify task_type parameter
                call_args = mock_query.call_args
                assert call_args[1]['task_type'] == expected_type


class TestErrorCategories:
    """Test error category classifications"""

    def test_error_categories(self):
        """Test various error categories"""
        categories = [
            "configuration",
            "validation",
            "network",
            "timeout",
            "security",
            "dependency",
            "syntax"
        ]

        for category in categories:
            trajectory = Trajectory(
                trajectory_id=str(uuid.uuid4()),
                agent_id="test_agent",
                task_description="Test task",
                initial_state={},
                steps=(),
                final_outcome=OutcomeTag.FAILURE.value,
                reward=0.0,
                metadata={},
                created_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=5.0,
                failure_rationale=f"Error in category: {category}",
                error_category=category
            )

            assert trajectory.error_category == category


class TestEndToEndScenario:
    """End-to-end test of failure tracking workflow"""

    def test_complete_failure_tracking_workflow(self):
        """Test complete workflow: fail -> store -> query -> avoid"""
        from agents.builder_agent_enhanced import EnhancedBuilderAgent, BuildAttempt

        agent = EnhancedBuilderAgent(business_id="e2e_test")

        # Step 1: Simulate a build failure
        agent.current_attempt = BuildAttempt(
            attempt_id=str(uuid.uuid4()),
            business_id="e2e_test",
            spec_summary="Build Supabase integration"
        )
        agent.trajectory_steps = [
            ActionStep(
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_name="generate_config",
                tool_args={"env_vars": ["SUPABASE_URL"]},
                tool_result="Config generated",
                agent_reasoning="Creating Supabase configuration"
            )
        ]

        # Step 2: Finalize with failure
        trajectory_id = agent._finalize_trajectory(
            outcome=OutcomeTag.FAILURE,
            reward=0.0,
            failure_rationale="Supabase client initialization failed - missing anon key",
            error_category="configuration",
            fix_applied="Added SUPABASE_ANON_KEY to environment variables"
        )

        assert trajectory_id is not None

        # Step 3: Verify trajectory stored with failure details
        stored = agent.replay_buffer.get_trajectory(trajectory_id)
        assert stored.failure_rationale is not None
        assert "anon key" in stored.failure_rationale.lower()

        # Step 4: Check anti-patterns before next build
        anti_patterns = agent._check_anti_patterns("Build Supabase integration")
        # Should return list (may be populated if ReasoningBank available)
        assert isinstance(anti_patterns, list)

        # Step 5: Verify agent can continue after failure
        agent.current_attempt = BuildAttempt(
            attempt_id=str(uuid.uuid4()),
            business_id="e2e_test",
            spec_summary="Build another feature"
        )
        assert agent.current_attempt is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
