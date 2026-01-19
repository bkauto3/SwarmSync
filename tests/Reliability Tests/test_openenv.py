"""
Unit Tests for OpenEnv External-Tool Agent Wrapper
Version: 1.0
Created: October 24, 2025

Tests for:
- PlaywrightEnv (browser automation)
- SupabaseEnv (database operations)
- EnvironmentLearningAgent (self-play learning)
- EnvRegistry (environment registry)

Coverage Target: 30 tests
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from infrastructure.openenv_wrapper import (
    OpenEnv,
    PlaywrightEnv,
    SupabaseEnv,
    EnvRegistry,
    EnvObservation,
    EnvironmentState
)
from infrastructure.env_learning_agent import EnvironmentLearningAgent


# ============================================================================
# PlaywrightEnv Tests (10 tests)
# ============================================================================

class TestPlaywrightEnv:
    """Test PlaywrightEnv browser automation environment"""

    @pytest.mark.asyncio
    async def test_playwright_env_initialization(self):
        """Test PlaywrightEnv initializes correctly"""
        env = PlaywrightEnv(goal="Navigate to Google", headless=True)

        assert env.env_id == "playwright"
        assert env.goal == "Navigate to Google"
        assert env.headless is True
        assert env.browser is None
        assert env.page is None
        assert env.action_history == []

    @pytest.mark.asyncio
    async def test_playwright_env_reset_success(self):
        """Test PlaywrightEnv reset launches browser (mocked without playwright dependency)"""
        env = PlaywrightEnv(goal="Test goal")

        # Skip test if playwright not installed (avoid import errors)
        pytest.importorskip("playwright.async_api")

        with patch('playwright.async_api.async_playwright') as mock_playwright:
            # Mock Playwright context
            mock_context = AsyncMock()
            mock_playwright.return_value = mock_context

            # Mock browser and page
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.url = "about:blank"
            mock_page.title = AsyncMock(return_value="Test Page")
            mock_page.content = AsyncMock(return_value="<html>Test</html>")

            mock_context.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_context.__aenter__.return_value.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_page = AsyncMock(return_value=mock_page)

            obs = await env.reset()

            assert obs.reward == 0.0
            assert obs.done is False
            assert obs.info["success"] is True
            assert obs.info["action"] == "reset"
            assert env.episode_steps == 0
            assert env.episode_reward == 0.0

        # Cleanup
        if env.browser:
            await env.close()

    @pytest.mark.asyncio
    async def test_playwright_env_reset_failure(self):
        """Test PlaywrightEnv reset handles errors gracefully (mocked)"""
        env = PlaywrightEnv()

        # Skip if playwright not available
        pytest.importorskip("playwright.async_api")

        with patch('playwright.async_api.async_playwright') as mock_playwright:
            # Simulate initialization failure
            mock_playwright.side_effect = Exception("Playwright not installed")

            obs = await env.reset()

            assert obs.reward == -1.0
            assert obs.done is True
            assert obs.info["success"] is False
            assert "error" in obs.info

    @pytest.mark.asyncio
    async def test_playwright_goto_action_success(self):
        """Test PlaywrightEnv goto action"""
        env = PlaywrightEnv()
        env.page = AsyncMock()
        env.page.goto = AsyncMock()
        env.page.url = "https://example.com"
        env.page.title = AsyncMock(return_value="Example Domain")
        env.page.content = AsyncMock(return_value="<html>Example</html>")

        action = {"type": "goto", "url": "https://example.com"}
        obs = await env.step(action)

        assert obs.reward == 1.0
        assert obs.info["success"] is True
        assert obs.info["action"] == "goto"
        assert env.episode_steps == 1
        env.page.goto.assert_called_once_with("https://example.com", timeout=10000)

    @pytest.mark.asyncio
    async def test_playwright_click_action_success(self):
        """Test PlaywrightEnv click action"""
        env = PlaywrightEnv()
        env.page = AsyncMock()
        env.page.click = AsyncMock()
        env.page.url = "https://example.com"
        env.page.title = AsyncMock(return_value="Example")
        env.page.content = AsyncMock(return_value="<html></html>")

        action = {"type": "click", "selector": "#button"}
        obs = await env.step(action)

        assert obs.reward == 1.0
        assert obs.info["success"] is True
        env.page.click.assert_called_once_with("#button", timeout=5000)

    @pytest.mark.asyncio
    async def test_playwright_type_action_success(self):
        """Test PlaywrightEnv type action"""
        env = PlaywrightEnv()
        env.page = AsyncMock()
        env.page.fill = AsyncMock()
        env.page.url = "https://example.com"
        env.page.title = AsyncMock(return_value="Example")
        env.page.content = AsyncMock(return_value="<html></html>")

        action = {"type": "type", "selector": "#input", "text": "test text"}
        obs = await env.step(action)

        assert obs.reward == 1.0
        assert obs.info["success"] is True
        env.page.fill.assert_called_once_with("#input", "test text", timeout=5000)

    @pytest.mark.asyncio
    async def test_playwright_screenshot_action(self):
        """Test PlaywrightEnv screenshot action"""
        env = PlaywrightEnv()
        env.page = AsyncMock()
        env.page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
        env.page.url = "https://example.com"
        env.page.title = AsyncMock(return_value="Example")
        env.page.content = AsyncMock(return_value="<html></html>")

        action = {"type": "screenshot"}
        obs = await env.step(action)

        assert obs.reward == 0.5
        assert obs.info["success"] is True
        env.page.screenshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_playwright_wait_action(self):
        """Test PlaywrightEnv wait action"""
        env = PlaywrightEnv()
        env.page = AsyncMock()
        env.page.url = "https://example.com"
        env.page.title = AsyncMock(return_value="Example")
        env.page.content = AsyncMock(return_value="<html></html>")

        action = {"type": "wait", "ms": 100}
        obs = await env.step(action)

        assert obs.reward == 0.0
        assert obs.info["success"] is True

    @pytest.mark.asyncio
    async def test_playwright_action_failure(self):
        """Test PlaywrightEnv handles action failures"""
        env = PlaywrightEnv()
        env.page = AsyncMock()
        env.page.click = AsyncMock(side_effect=Exception("Element not found"))
        env.page.url = "https://example.com"
        env.page.title = AsyncMock(return_value="Example")
        env.page.content = AsyncMock(return_value="<html></html>")

        action = {"type": "click", "selector": "#missing"}
        obs = await env.step(action)

        assert obs.reward == -0.5  # Negative reward for learning
        assert obs.info["success"] is False
        assert "error" in obs.info

    @pytest.mark.asyncio
    async def test_playwright_unknown_action(self):
        """Test PlaywrightEnv handles unknown actions"""
        env = PlaywrightEnv()
        env.page = AsyncMock()
        env.page.url = "https://example.com"
        env.page.title = AsyncMock(return_value="Example")
        env.page.content = AsyncMock(return_value="<html></html>")

        action = {"type": "invalid_action"}
        obs = await env.step(action)

        assert obs.reward == -0.5
        assert obs.info["success"] is False


# ============================================================================
# SupabaseEnv Tests (10 tests)
# ============================================================================

class TestSupabaseEnv:
    """Test SupabaseEnv database operations environment"""

    @pytest.mark.asyncio
    async def test_supabase_env_initialization(self):
        """Test SupabaseEnv initializes correctly"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        assert env.env_id == "supabase"
        assert env.url == "https://test.supabase.co"
        assert env.key == "test_key"
        assert env.client is None
        assert env.operation_history == []

    @pytest.mark.asyncio
    async def test_supabase_env_reset_success(self):
        """Test SupabaseEnv reset initializes client (mocked without supabase dependency)"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        # Skip if supabase not available
        pytest.importorskip("supabase")

        with patch('supabase.create_client') as mock_create:
            mock_client = Mock()
            mock_create.return_value = mock_client

            obs = await env.reset()

            assert obs.reward == 0.0
            assert obs.done is False
            assert obs.info["success"] is True
            assert obs.state["connected"] is True
            assert env.client == mock_client

    @pytest.mark.asyncio
    async def test_supabase_env_reset_failure(self):
        """Test SupabaseEnv reset handles errors (mocked)"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="invalid_key"
        )

        # Skip if supabase not available
        pytest.importorskip("supabase")

        with patch('supabase.create_client') as mock_create:
            mock_create.side_effect = Exception("Invalid credentials")

            obs = await env.reset()

            assert obs.reward == -1.0
            assert obs.done is True
            assert obs.info["success"] is False

    @pytest.mark.asyncio
    async def test_supabase_insert_action_success(self):
        """Test SupabaseEnv insert action"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        # Mock Supabase client
        mock_table = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "Test"}]
        mock_table.insert.return_value.execute.return_value = mock_result

        env.client = Mock()
        env.client.table.return_value = mock_table

        action = {"type": "insert", "table": "users", "data": {"name": "Test"}}
        obs = await env.step(action)

        assert obs.reward == 1.0
        assert obs.info["success"] is True
        env.client.table.assert_called_once_with("users")

    @pytest.mark.asyncio
    async def test_supabase_select_action_success(self):
        """Test SupabaseEnv select action"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        # Mock Supabase client
        mock_query = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1}, {"id": 2}]
        mock_query.execute.return_value = mock_result

        mock_table = Mock()
        mock_table.select.return_value.eq.return_value = mock_query

        env.client = Mock()
        env.client.table.return_value = mock_table

        action = {"type": "select", "table": "users", "filters": {"active": True}}
        obs = await env.step(action)

        assert obs.reward == 0.5
        assert obs.info["success"] is True

    @pytest.mark.asyncio
    async def test_supabase_update_action_success(self):
        """Test SupabaseEnv update action"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        # Mock Supabase client
        mock_query = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1, "name": "Updated"}]
        mock_query.execute.return_value = mock_result

        mock_table = Mock()
        mock_table.update.return_value.eq.return_value = mock_query

        env.client = Mock()
        env.client.table.return_value = mock_table

        action = {"type": "update", "table": "users", "id": "1", "data": {"name": "Updated"}}
        obs = await env.step(action)

        assert obs.reward == 1.0
        assert obs.info["success"] is True

    @pytest.mark.asyncio
    async def test_supabase_delete_action_success(self):
        """Test SupabaseEnv delete action"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        # Mock Supabase client
        mock_query = Mock()
        mock_result = Mock()
        mock_result.data = []
        mock_query.execute.return_value = mock_result

        mock_table = Mock()
        mock_table.delete.return_value.eq.return_value = mock_query

        env.client = Mock()
        env.client.table.return_value = mock_table

        action = {"type": "delete", "table": "users", "id": "1"}
        obs = await env.step(action)

        assert obs.reward == 1.0
        assert obs.info["success"] is True

    @pytest.mark.asyncio
    async def test_supabase_action_failure(self):
        """Test SupabaseEnv handles action failures"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        # Mock Supabase client to raise error
        mock_table = Mock()
        mock_table.insert.side_effect = Exception("Database error")

        env.client = Mock()
        env.client.table.return_value = mock_table

        action = {"type": "insert", "table": "users", "data": {"invalid": "data"}}
        obs = await env.step(action)

        assert obs.reward == -0.5  # Negative reward for learning
        assert obs.info["success"] is False
        assert "error" in obs.info

    @pytest.mark.asyncio
    async def test_supabase_unknown_action(self):
        """Test SupabaseEnv handles unknown actions"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )
        env.client = Mock()

        action = {"type": "invalid_action", "table": "users"}
        obs = await env.step(action)

        assert obs.reward == -0.5
        assert obs.info["success"] is False

    @pytest.mark.asyncio
    async def test_supabase_operation_history_tracking(self):
        """Test SupabaseEnv tracks operation history"""
        env = SupabaseEnv(
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        # Mock Supabase client
        mock_table = Mock()
        mock_result = Mock()
        mock_result.data = [{"id": 1}]
        mock_table.insert.return_value.execute.return_value = mock_result

        env.client = Mock()
        env.client.table.return_value = mock_table

        # Execute multiple actions
        await env.step({"type": "insert", "table": "users", "data": {"name": "User1"}})
        await env.step({"type": "insert", "table": "users", "data": {"name": "User2"}})

        assert len(env.operation_history) == 2
        assert env.episode_steps == 2


# ============================================================================
# EnvRegistry Tests (5 tests)
# ============================================================================

class TestEnvRegistry:
    """Test EnvRegistry environment registry"""

    def test_env_registry_default_envs(self):
        """Test EnvRegistry has default environments"""
        envs = EnvRegistry.list_envs()

        assert "playwright" in envs
        assert "supabase" in envs

    def test_env_registry_make_playwright(self):
        """Test EnvRegistry.make creates PlaywrightEnv"""
        env = EnvRegistry.make("playwright", goal="Test goal")

        assert isinstance(env, PlaywrightEnv)
        assert env.goal == "Test goal"

    def test_env_registry_make_supabase(self):
        """Test EnvRegistry.make creates SupabaseEnv"""
        env = EnvRegistry.make(
            "supabase",
            supabase_url="https://test.supabase.co",
            supabase_key="test_key"
        )

        assert isinstance(env, SupabaseEnv)
        assert env.url == "https://test.supabase.co"

    def test_env_registry_make_unknown_env(self):
        """Test EnvRegistry.make raises error for unknown environment"""
        with pytest.raises(ValueError, match="Unknown environment"):
            EnvRegistry.make("unknown_env")

    def test_env_registry_register_custom_env(self):
        """Test EnvRegistry.register adds custom environment"""

        class CustomEnv(OpenEnv):
            def __init__(self):
                super().__init__(env_id="custom")

            async def reset(self):
                return EnvObservation(state={}, reward=0.0, done=False, info={})

            async def step(self, action):
                return EnvObservation(state={}, reward=1.0, done=False, info={})

        EnvRegistry.register("custom", CustomEnv)

        assert "custom" in EnvRegistry.list_envs()
        env = EnvRegistry.make("custom")
        assert isinstance(env, CustomEnv)


# ============================================================================
# EnvironmentLearningAgent Tests (5 tests)
# ============================================================================

class TestEnvironmentLearningAgent:
    """Test EnvironmentLearningAgent self-play learning"""

    @pytest.mark.asyncio
    async def test_learning_agent_initialization(self):
        """Test EnvironmentLearningAgent initializes correctly"""
        env = PlaywrightEnv()
        llm = Mock()

        agent = EnvironmentLearningAgent(
            env=env,
            llm_client=llm,
            max_episodes=5
        )

        assert agent.env == env
        assert agent.llm == llm
        assert agent.max_episodes == 5
        assert agent.episode_history == []

    @pytest.mark.asyncio
    async def test_learning_agent_learns_task(self):
        """Test EnvironmentLearningAgent learns task via self-play"""
        # Mock environment
        env = Mock(spec=OpenEnv)
        env.env_id = "mock_env"
        env.reset = AsyncMock(return_value=EnvObservation(
            state={"initial": True},
            reward=0.0,
            done=False,
            info={}
        ))
        env.step = AsyncMock(return_value=EnvObservation(
            state={"step": 1},
            reward=1.0,
            done=True,
            info={}
        ))

        # Mock LLM
        llm = Mock()
        llm.generate = AsyncMock(return_value='{"type": "test_action"}')

        agent = EnvironmentLearningAgent(
            env=env,
            llm_client=llm,
            max_episodes=2,
            max_steps_per_episode=3
        )

        result = await agent.learn_task("Test goal")

        assert result["success"] is True
        assert result["episodes"] >= 1
        assert "learned_strategy" in result
        assert "learning_curve" in result

    @pytest.mark.asyncio
    async def test_learning_agent_plateau_detection(self):
        """Test EnvironmentLearningAgent detects learning plateau"""
        agent = EnvironmentLearningAgent(
            env=Mock(),
            llm_client=Mock(),
            max_episodes=10
        )

        # Similar rewards (plateau)
        learning_curve = [1.0, 1.05, 1.03, 1.02]
        is_plateau = agent._is_plateau(learning_curve, window=3, threshold=0.1)

        assert is_plateau is True

        # Improving rewards (no plateau)
        learning_curve = [1.0, 2.0, 3.0, 4.0]
        is_plateau = agent._is_plateau(learning_curve, window=3, threshold=0.1)

        assert is_plateau is False

    @pytest.mark.asyncio
    async def test_learning_agent_fallback_action(self):
        """Test EnvironmentLearningAgent fallback action"""
        env = PlaywrightEnv()
        llm = Mock()

        agent = EnvironmentLearningAgent(
            env=env,
            llm_client=llm
        )

        # Fallback action when LLM fails
        action = agent._fallback_action(state={}, history=[])

        assert "type" in action
        assert action["type"] in ["wait", "screenshot"]

    @pytest.mark.asyncio
    async def test_learning_agent_parse_action(self):
        """Test EnvironmentLearningAgent parses LLM response"""
        agent = EnvironmentLearningAgent(
            env=Mock(),
            llm_client=Mock()
        )

        # Valid JSON response
        response = '{"type": "goto", "url": "https://example.com"}'
        action = agent._parse_action(response)

        assert action["type"] == "goto"
        assert action["url"] == "https://example.com"

        # Markdown-wrapped JSON
        response = '```json\n{"type": "click", "selector": "#btn"}\n```'
        action = agent._parse_action(response)

        assert action["type"] == "click"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
