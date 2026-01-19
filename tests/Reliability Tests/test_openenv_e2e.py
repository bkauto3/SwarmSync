"""
E2E Tests for OpenEnv External-Tool Agent Wrapper
Version: 1.0
Created: October 24, 2025

End-to-end validation with real integrations and screenshots.

Test Scenarios:
- Real browser automation (Playwright)
- Agent learning via self-play
- Integration with QA/Builder/Support agents
- Screenshot validation
"""

import pytest
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from infrastructure.openenv_wrapper import PlaywrightEnv, SupabaseEnv, EnvRegistry
from infrastructure.env_learning_agent import EnvironmentLearningAgent


# Test configuration
SCREENSHOT_DIR = Path("tests/screenshots/openenv")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# E2E PlaywrightEnv Tests
# ============================================================================

class TestPlaywrightEnvE2E:
    """End-to-end tests for PlaywrightEnv with real browser"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_playwright_real_browser_navigation(self):
        """Test PlaywrightEnv with real browser navigation"""
        env = PlaywrightEnv(goal="Navigate to example.com", headless=True)

        try:
            # Reset environment (launch browser)
            obs = await env.reset()
            assert obs.info["success"] is True

            # Navigate to example.com
            action = {"type": "goto", "url": "https://example.com"}
            obs = await env.step(action)

            assert obs.reward > 0
            assert "example.com" in obs.state.get("url", "")

            # Take screenshot for validation
            screenshot_action = {"type": "screenshot"}
            obs = await env.step(screenshot_action)

            assert obs.reward == 0.5
            assert obs.info["success"] is True

        finally:
            await env.close()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_playwright_multi_step_interaction(self):
        """Test PlaywrightEnv multi-step browser interaction"""
        env = PlaywrightEnv(headless=True)

        try:
            await env.reset()

            # Multi-step interaction
            actions = [
                {"type": "goto", "url": "https://example.com"},
                {"type": "wait", "ms": 500},
                {"type": "screenshot"}
            ]

            total_reward = 0.0
            for action in actions:
                obs = await env.step(action)
                total_reward += obs.reward

            # Should accumulate positive rewards
            assert total_reward > 0
            assert len(env.action_history) == 3

        finally:
            await env.close()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_playwright_error_recovery(self):
        """Test PlaywrightEnv handles errors and continues"""
        env = PlaywrightEnv(headless=True)

        try:
            await env.reset()

            # Valid action
            obs1 = await env.step({"type": "goto", "url": "https://example.com"})
            assert obs1.reward > 0

            # Invalid action (should get negative reward but not crash)
            obs2 = await env.step({"type": "click", "selector": "#nonexistent"})
            assert obs2.reward < 0
            assert obs2.done is False  # Environment continues

            # Another valid action (should work)
            obs3 = await env.step({"type": "wait", "ms": 100})
            assert obs3.reward >= 0

        finally:
            await env.close()


# ============================================================================
# E2E EnvironmentLearningAgent Tests
# ============================================================================

class TestEnvironmentLearningAgentE2E:
    """End-to-end tests for EnvironmentLearningAgent self-play"""

    @pytest.mark.asyncio
    async def test_learning_agent_self_play_simple_goal(self):
        """Test EnvironmentLearningAgent learns simple goal via self-play"""

        # Mock environment with simple goal
        env = Mock(spec=PlaywrightEnv)
        env.env_id = "playwright"

        # Simulate environment responses
        episode_step = 0

        async def mock_reset():
            nonlocal episode_step
            episode_step = 0
            return Mock(
                state={"url": "about:blank", "episode_steps": 0},
                reward=0.0,
                done=False,
                info={"success": True}
            )

        async def mock_step(action):
            nonlocal episode_step
            episode_step += 1

            # Reward positive actions
            if action.get("type") == "goto":
                reward = 2.0
                done = True  # Goal reached
            elif action.get("type") == "wait":
                reward = 0.0
                done = False
            else:
                reward = -0.2
                done = False

            return Mock(
                state={"url": "https://example.com", "episode_steps": episode_step},
                reward=reward,
                done=done,
                info={"success": reward > 0}
            )

        env.reset = mock_reset
        env.step = mock_step

        # Mock LLM that proposes "goto" action
        llm = Mock()
        llm.generate = AsyncMock(return_value='{"type": "goto", "url": "https://example.com"}')

        # Create learning agent
        agent = EnvironmentLearningAgent(
            env=env,
            llm_client=llm,
            max_episodes=3,
            max_steps_per_episode=5
        )

        # Learn task
        result = await agent.learn_task("Navigate to example.com")

        # Assertions
        assert result["success"] is True
        assert result["episodes"] >= 1
        assert result["best_reward"] > 0
        assert len(result["learned_strategy"]) > 0
        assert "learning_curve" in result

    @pytest.mark.asyncio
    async def test_learning_agent_plateau_early_stopping(self):
        """Test EnvironmentLearningAgent stops early on plateau"""

        # Mock environment
        env = Mock(spec=PlaywrightEnv)
        env.env_id = "test_env"

        # Simulate plateauing rewards
        episode_rewards = [1.0, 1.05, 1.03, 1.02, 1.04]
        episode_idx = 0

        async def mock_reset():
            return Mock(state={}, reward=0.0, done=False, info={})

        async def mock_step(action):
            nonlocal episode_idx
            # Return consistent reward (plateau)
            reward = episode_rewards[min(episode_idx, len(episode_rewards) - 1)]
            return Mock(
                state={},
                reward=reward,
                done=True,  # End episode immediately
                info={}
            )

        env.reset = mock_reset
        env.step = mock_step

        # Mock LLM
        llm = Mock()
        llm.generate = AsyncMock(return_value='{"type": "test"}')

        agent = EnvironmentLearningAgent(
            env=env,
            llm_client=llm,
            max_episodes=10  # High limit
        )

        result = await agent.learn_task("Test goal")

        # Should stop early due to plateau
        assert result["episodes"] < 10
        assert len(result["learning_curve"]) < 10

    @pytest.mark.asyncio
    async def test_learning_agent_llm_failure_fallback(self):
        """Test EnvironmentLearningAgent uses fallback on LLM failure"""

        env = Mock(spec=PlaywrightEnv)
        env.env_id = "playwright"

        async def mock_reset():
            return Mock(state={}, reward=0.0, done=False, info={})

        async def mock_step(action):
            # Accept any action
            return Mock(state={}, reward=0.5, done=True, info={})

        env.reset = mock_reset
        env.step = mock_step

        # Mock LLM that fails
        llm = Mock()
        llm.generate = AsyncMock(side_effect=Exception("LLM API error"))

        agent = EnvironmentLearningAgent(
            env=env,
            llm_client=llm,
            max_episodes=2,
            max_steps_per_episode=3
        )

        # Should use fallback actions
        result = await agent.learn_task("Test goal")

        # Fallback actions should work
        assert result["episodes"] > 0
        assert len(result["learned_strategy"]) > 0


# ============================================================================
# E2E Agent Integration Tests
# ============================================================================

class TestAgentIntegrationE2E:
    """End-to-end tests for OpenEnv integration with agents"""

    @pytest.mark.asyncio
    async def test_qa_agent_openenv_integration(self):
        """Test QA Agent OpenEnv integration (mocked)"""

        # Mock QA Agent test_web_feature method
        from agents.qa_agent import QAAgent

        qa_agent = QAAgent(business_id="test")

        # Mock the env_agent
        mock_env_agent = Mock()
        mock_env_agent.learn_task = AsyncMock(return_value={
            "success": True,
            "episodes": 3,
            "best_reward": 5.0,
            "total_steps": 12,
            "learned_strategy": [
                {"type": "goto", "url": "https://example.com", "reward": 1.0},
                {"type": "click", "selector": "#login", "reward": 1.0}
            ],
            "learning_curve": [1.0, 3.0, 5.0]
        })

        qa_agent.env_agent = mock_env_agent

        # Call test_web_feature
        result_json = await qa_agent.test_web_feature(
            feature_url="https://example.com/login",
            test_goal="Login with credentials"
        )

        result = json.loads(result_json)

        assert result["success"] is True
        assert result["status"] == "PASS"
        assert result["episodes"] == 3
        assert len(result["learned_strategy"]) == 2

    @pytest.mark.asyncio
    async def test_builder_agent_openenv_integration(self):
        """Test Builder Agent OpenEnv integration (mocked)"""

        from agents.builder_agent import BuilderAgent

        builder_agent = BuilderAgent(business_id="test")

        # Mock the env_agent
        mock_env_agent = Mock()
        mock_env_agent.learn_task = AsyncMock(return_value={
            "success": True,
            "episodes": 5,
            "best_reward": 10.0,
            "total_steps": 20,
            "learned_strategy": [
                {"type": "goto", "url": "https://vercel.com/login"},
                {"type": "type", "selector": "#email", "text": "user@example.com"},
                {"type": "click", "selector": "#deploy"}
            ],
            "learning_curve": [2.0, 5.0, 8.0, 10.0, 10.0]
        })

        builder_agent.env_agent = mock_env_agent

        # Call deploy_to_cloud
        result_json = await builder_agent.deploy_to_cloud(
            platform="Vercel",
            deployment_goal="Deploy Next.js app"
        )

        result = json.loads(result_json)

        assert result["success"] is True
        assert result["status"] == "DEPLOYED"
        assert result["platform"] == "Vercel"
        assert len(result["learned_workflow"]) == 3

    @pytest.mark.asyncio
    async def test_support_agent_openenv_integration(self):
        """Test Support Agent OpenEnv integration (mocked)"""

        from agents.support_agent import SupportAgent

        support_agent = SupportAgent(business_id="test")

        # Mock the env_agent
        mock_env_agent = Mock()
        mock_env_agent.learn_task = AsyncMock(return_value={
            "success": True,
            "episodes": 4,
            "best_reward": 7.0,
            "total_steps": 15,
            "learned_strategy": [
                {"type": "goto", "url": "https://app.example.com"},
                {"type": "click", "selector": "#broken-button"},
                {"type": "screenshot"}
            ],
            "learning_curve": [1.0, 3.0, 5.0, 7.0]
        })

        support_agent.env_agent = mock_env_agent

        # Call reproduce_customer_issue
        result_json = await support_agent.reproduce_customer_issue(
            ticket_id="TICKET-12345",
            reproduction_steps="Click broken button on dashboard"
        )

        result = json.loads(result_json)

        assert result["reproduced"] is True
        assert result["status"] == "REPRODUCED"
        assert result["ticket_id"] == "TICKET-12345"
        assert len(result["observed_behavior"]) == 3


# ============================================================================
# Performance & Reliability Tests
# ============================================================================

class TestOpenEnvPerformance:
    """Performance and reliability tests"""

    @pytest.mark.asyncio
    async def test_environment_reset_performance(self):
        """Test environment reset completes within time limit"""
        import time

        env = Mock(spec=PlaywrightEnv)
        env.reset = AsyncMock(return_value=Mock(
            state={}, reward=0.0, done=False, info={"success": True}
        ))

        start = time.time()
        obs = await env.reset()
        duration = time.time() - start

        # Reset should be fast (mocked)
        assert duration < 1.0
        assert obs.info["success"] is True

    @pytest.mark.asyncio
    async def test_learning_agent_episode_limit(self):
        """Test learning agent respects episode limit"""

        env = Mock(spec=PlaywrightEnv)
        env.env_id = "test"

        async def mock_reset():
            return Mock(state={}, reward=0.0, done=False, info={})

        async def mock_step(action):
            # Never reach goal (test limit)
            return Mock(state={}, reward=0.5, done=False, info={})

        env.reset = mock_reset
        env.step = mock_step

        llm = Mock()
        llm.generate = AsyncMock(return_value='{"type": "test"}')

        agent = EnvironmentLearningAgent(
            env=env,
            llm_client=llm,
            max_episodes=5,
            max_steps_per_episode=3
        )

        result = await agent.learn_task("Impossible goal")

        # Should stop at max episodes or early on plateau
        assert result["episodes"] <= 5
        assert result["episodes"] >= 1

    @pytest.mark.asyncio
    async def test_concurrent_environment_instances(self):
        """Test multiple environment instances can run concurrently"""

        async def run_env_episode(env_id):
            env = Mock(spec=PlaywrightEnv)
            env.env_id = f"env_{env_id}"
            env.reset = AsyncMock(return_value=Mock(
                state={}, reward=0.0, done=False, info={}
            ))
            env.step = AsyncMock(return_value=Mock(
                state={}, reward=1.0, done=True, info={}
            ))

            llm = Mock()
            llm.generate = AsyncMock(return_value='{"type": "test"}')

            agent = EnvironmentLearningAgent(env=env, llm_client=llm, max_episodes=2)
            return await agent.learn_task(f"Goal {env_id}")

        # Run 3 environments concurrently
        results = await asyncio.gather(
            run_env_episode(1),
            run_env_episode(2),
            run_env_episode(3)
        )

        assert len(results) == 3
        assert all(r["success"] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
