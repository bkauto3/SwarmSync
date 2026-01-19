"""
Comprehensive Tests for Deploy Agent
Tests all capabilities including learning infrastructure integration

Run with: pytest tests/test_deploy_agent.py -v
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.deploy_agent import (
    DeployAgent,
    DeploymentConfig,
    DeploymentResult,
    GeminiComputerUseClient,
    get_deploy_agent
)


class TestGeminiComputerUseClient:
    """Test Gemini Computer Use client"""

    @pytest.mark.asyncio
    async def test_browser_lifecycle(self):
        """Test browser start/stop lifecycle"""
        client = GeminiComputerUseClient()
        assert not client.browser_running

        await client.start_browser(headless=True)
        assert client.browser_running

        await client.stop_browser()
        assert not client.browser_running

    @pytest.mark.asyncio
    async def test_navigation(self):
        """Test navigation functionality"""
        client = GeminiComputerUseClient()
        await client.start_browser()

        await client.navigate("https://vercel.com")
        assert "navigate:https://vercel.com" in client.action_history

        await client.stop_browser()

    @pytest.mark.asyncio
    async def test_screenshot(self):
        """Test screenshot capability"""
        client = GeminiComputerUseClient()
        await client.start_browser()

        screenshot = await client.take_screenshot()
        assert screenshot.endswith(".png")
        assert "screenshot" in screenshot

        await client.stop_browser()

    @pytest.mark.asyncio
    async def test_autonomous_task(self):
        """Test autonomous task execution"""
        client = GeminiComputerUseClient()
        await client.start_browser()

        result = await client.autonomous_task(
            "Deploy to Vercel",
            max_steps=10
        )

        assert result["success"]
        assert result["steps"] > 0
        assert isinstance(result["action_log"], list)
        assert result["final_state"] == "task_completed"

        await client.stop_browser()


class TestDeploymentConfig:
    """Test DeploymentConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = DeploymentConfig(repo_name="test-app")

        assert config.repo_name == "test-app"
        assert config.platform == "vercel"
        assert config.framework == "nextjs"
        assert config.environment == "production"
        assert config.headless is True
        assert config.max_steps == 30

    def test_custom_config(self):
        """Test custom configuration"""
        config = DeploymentConfig(
            repo_name="my-app",
            platform="netlify",
            framework="react",
            environment="staging",
            headless=False,
            max_steps=50
        )

        assert config.platform == "netlify"
        assert config.framework == "react"
        assert config.environment == "staging"
        assert config.headless is False
        assert config.max_steps == 50


class TestDeploymentResult:
    """Test DeploymentResult dataclass"""

    def test_successful_result(self):
        """Test successful deployment result"""
        result = DeploymentResult(
            success=True,
            deployment_url="https://test-app.vercel.app",
            github_url="https://github.com/org/test-app",
            platform="vercel",
            duration_seconds=45.2,
            steps_taken=5,
            cost_estimate=0.02
        )

        assert result.success
        assert result.deployment_url
        assert result.duration_seconds == 45.2
        assert result.cost_estimate == 0.02
        assert isinstance(result.action_log, list)
        assert isinstance(result.metadata, dict)

    def test_failed_result(self):
        """Test failed deployment result"""
        result = DeploymentResult(
            success=False,
            error="Deployment failed: timeout"
        )

        assert not result.success
        assert result.error
        assert result.deployment_url is None


class TestDeployAgent:
    """Test Deploy Agent functionality"""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization"""
        # Mock Azure credentials
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'):

            agent = DeployAgent(business_id="test-business")
            await agent.initialize()

            assert agent.business_id == "test-business"
            assert agent.agent_id == "deploy_agent_test-business"
            assert agent.agent is not None
            assert agent.deployments_attempted == 0
            assert agent.deployments_successful == 0

    @pytest.mark.asyncio
    async def test_agent_initialization_with_learning(self):
        """Test agent initialization with learning enabled"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'), \
             patch('agents.deploy_agent.get_reasoning_bank') as mock_rb, \
             patch('agents.deploy_agent.get_replay_buffer') as mock_replay:

            mock_rb.return_value = Mock()
            mock_replay.return_value = Mock()

            agent = DeployAgent(
                business_id="test",
                use_learning=True,
                use_reflection=True
            )
            await agent.initialize()

            assert agent.use_learning
            assert agent.use_reflection

    def test_prepare_deployment_files(self):
        """Test file preparation for deployment"""
        agent = DeployAgent()

        code_files = {
            "pages/index.js": "export default function Home() { return <div>Home</div> }",
            "styles/globals.css": "body { margin: 0; }"
        }

        result_json = agent.prepare_deployment_files(
            business_name="test-app",
            code_files=code_files,
            framework="nextjs"
        )

        result = json.loads(result_json)

        assert result["success"]
        assert result["files_written"] >= 2  # At least the 2 files + package.json
        assert result["framework"] == "nextjs"
        assert "deploy_dir" in result

        # Cleanup
        deploy_dir = Path(result["deploy_dir"])
        if deploy_dir.exists():
            import shutil
            shutil.rmtree(deploy_dir.parent.parent)

    def test_prepare_deployment_files_error_handling(self):
        """Test error handling in file preparation"""
        agent = DeployAgent()

        # Invalid code_files (not a dict)
        result_json = agent.prepare_deployment_files(
            business_name="test-app",
            code_files=None,  # Invalid
            framework="nextjs"
        )

        result = json.loads(result_json)
        assert not result["success"]
        assert "error" in result

    def test_generate_package_json_nextjs(self):
        """Test Next.js package.json generation"""
        agent = DeployAgent()

        package = agent._generate_package_json("test-app", "nextjs")

        assert package["name"] == "test-app"
        assert "next" in package["dependencies"]
        assert "react" in package["dependencies"]
        assert "dev" in package["scripts"]
        assert "build" in package["scripts"]

    def test_generate_package_json_react(self):
        """Test React package.json generation"""
        agent = DeployAgent()

        package = agent._generate_package_json("test-app", "react")

        assert package["name"] == "test-app"
        assert "react" in package["dependencies"]
        assert "vite" in package["devDependencies"]
        assert "dev" in package["scripts"]
        assert "build" in package["scripts"]

    @pytest.mark.asyncio
    async def test_deploy_to_vercel(self):
        """Test Vercel deployment"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'):

            agent = DeployAgent()
            await agent.initialize()

            result_json = await agent.deploy_to_vercel(
                repo_name="test-app",
                github_url="https://github.com/org/test-app",
                environment="production"
            )

            result = json.loads(result_json)

            assert result["success"]
            assert "vercel.app" in result["deployment_url"]
            assert result["platform"] == "vercel"
            assert result["duration_seconds"] > 0
            assert result["cost_estimate"] > 0

    @pytest.mark.asyncio
    async def test_deploy_to_netlify(self):
        """Test Netlify deployment"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'):

            agent = DeployAgent()
            await agent.initialize()

            result_json = await agent.deploy_to_netlify(
                repo_name="test-app",
                github_url="https://github.com/org/test-app",
                environment="production"
            )

            result = json.loads(result_json)

            assert result["success"]
            assert "netlify.app" in result["deployment_url"]
            assert result["platform"] == "netlify"

    def test_verify_deployment_success(self):
        """Test deployment verification (mocked)"""
        agent = DeployAgent()

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_get.return_value = mock_response

            result_json = agent.verify_deployment("https://test-app.vercel.app")
            result = json.loads(result_json)

            assert result["success"]
            assert result["status_code"] == 200
            assert result["healthy"]
            assert result["response_time_ms"] == 500

    def test_verify_deployment_failure(self):
        """Test deployment verification failure"""
        agent = DeployAgent()

        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_get.return_value = mock_response

            result_json = agent.verify_deployment("https://test-app.vercel.app")
            result = json.loads(result_json)

            assert not result["success"]
            assert result["status_code"] == 404
            assert not result["healthy"]

    def test_rollback_deployment(self):
        """Test deployment rollback"""
        agent = DeployAgent()

        result_json = agent.rollback_deployment(
            platform="vercel",
            deployment_id="dpl_12345",
            target_version="v1.0.0"
        )

        result = json.loads(result_json)

        assert result["success"]
        assert result["platform"] == "vercel"
        assert result["deployment_id"] == "dpl_12345"
        assert result["rolled_back_to"] == "v1.0.0"

    @pytest.mark.asyncio
    async def test_full_deployment_workflow_success(self):
        """Test complete deployment workflow"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'), \
             patch('requests.get') as mock_get, \
             patch.dict('os.environ', {'GITHUB_TOKEN': 'mock_token'}), \
             patch('subprocess.run'):

            # Mock HTTP verification
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_get.return_value = mock_response

            agent = DeployAgent(business_id="test", use_learning=False)
            await agent.initialize()

            config = DeploymentConfig(
                repo_name="test-app",
                platform="vercel",
                framework="nextjs"
            )

            business_data = {
                "code_files": {
                    "pages/index.js": "export default function Home() { return <div>Test</div> }"
                }
            }

            result = await agent.full_deployment_workflow(config, business_data)

            assert isinstance(result, DeploymentResult)
            assert result.success
            assert result.deployment_url
            assert result.platform == "vercel"
            assert result.duration_seconds > 0
            assert result.steps_taken == 5

            # Cleanup
            deploy_dir = Path(f"businesses/{config.repo_name}")
            if deploy_dir.exists():
                import shutil
                shutil.rmtree(deploy_dir)

    @pytest.mark.asyncio
    async def test_full_deployment_workflow_failure(self):
        """Test deployment workflow failure handling"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'), \
             patch.dict('os.environ', {'GITHUB_TOKEN': 'mock_token'}), \
             patch('subprocess.run'):

            agent = DeployAgent(business_id="test", use_learning=False)
            await agent.initialize()

            config = DeploymentConfig(
                repo_name="test-app",
                platform="unsupported-platform"  # Invalid platform
            )

            business_data = {
                "code_files": {
                    "pages/index.js": "content"
                }
            }

            result = await agent.full_deployment_workflow(config, business_data)

            assert isinstance(result, DeploymentResult)
            assert not result.success
            assert result.error
            assert "Unsupported platform" in result.error

    def test_get_statistics_no_deployments(self):
        """Test statistics with no deployments"""
        agent = DeployAgent(business_id="test")

        stats = agent.get_statistics()

        assert stats["agent_id"] == "deploy_agent_test"
        assert stats["deployments_attempted"] == 0
        assert stats["deployments_successful"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_statistics_with_deployments(self):
        """Test statistics with deployments"""
        agent = DeployAgent(business_id="test")
        agent.deployments_attempted = 10
        agent.deployments_successful = 8
        agent.total_cost = 0.20

        stats = agent.get_statistics()

        assert stats["deployments_attempted"] == 10
        assert stats["deployments_successful"] == 8
        assert stats["success_rate"] == 0.8
        assert stats["total_cost"] == 0.20

    @pytest.mark.asyncio
    async def test_load_deployment_strategies(self):
        """Test loading strategies from ReasoningBank"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'), \
             patch('agents.deploy_agent.get_reasoning_bank') as mock_rb:

            # Mock ReasoningBank
            mock_bank = Mock()
            mock_strategy = Mock()
            mock_strategy.description = "Successful deployment"
            mock_strategy.steps = ["step1", "step2"]
            mock_strategy.win_rate = 0.95
            mock_strategy.usage_count = 10
            mock_bank.search_strategies.return_value = [mock_strategy]
            mock_rb.return_value = mock_bank

            agent = DeployAgent(use_learning=True)
            await agent.initialize()

            strategies = await agent._load_deployment_strategies("vercel")

            assert len(strategies) == 1
            assert strategies[0]["description"] == "Successful deployment"
            assert strategies[0]["win_rate"] == 0.95

    @pytest.mark.asyncio
    async def test_load_anti_patterns(self):
        """Test loading anti-patterns from Replay Buffer"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'), \
             patch('agents.deploy_agent.get_replay_buffer') as mock_replay:

            # Mock ReplayBuffer
            mock_buffer = Mock()
            anti_pattern = {
                "failure_rationale": "Timeout during build",
                "error_category": "timeout",
                "fix_applied": "Increased timeout to 600s"
            }
            mock_buffer.query_anti_patterns.return_value = [anti_pattern]
            mock_replay.return_value = mock_buffer

            agent = DeployAgent(use_learning=True)
            await agent.initialize()

            anti_patterns = await agent._load_anti_patterns("vercel")

            assert len(anti_patterns) == 1
            assert anti_patterns[0]["error_category"] == "timeout"


class TestFactoryFunction:
    """Test factory function"""

    @pytest.mark.asyncio
    async def test_get_deploy_agent_default(self):
        """Test factory function with defaults"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'):

            agent = await get_deploy_agent()

            assert isinstance(agent, DeployAgent)
            assert agent.business_id == "default"

    @pytest.mark.asyncio
    async def test_get_deploy_agent_custom(self):
        """Test factory function with custom parameters"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'):

            agent = await get_deploy_agent(
                business_id="custom-business",
                use_learning=False,
                use_reflection=False
            )

            assert agent.business_id == "custom-business"


class TestThreadSafety:
    """Test thread safety of concurrent operations"""

    @pytest.mark.asyncio
    async def test_concurrent_deployments(self):
        """Test multiple concurrent deployments"""
        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'), \
             patch('requests.get') as mock_get, \
             patch.dict('os.environ', {'GITHUB_TOKEN': 'mock_token'}), \
             patch('subprocess.run'):

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_get.return_value = mock_response

            agent = DeployAgent(use_learning=False)
            await agent.initialize()

            # Run 3 deployments concurrently
            configs = [
                DeploymentConfig(repo_name=f"app-{i}", platform="vercel")
                for i in range(3)
            ]

            business_data = {
                "code_files": {
                    "pages/index.js": "export default () => <div>Test</div>"
                }
            }

            tasks = [
                agent.full_deployment_workflow(config, business_data)
                for config in configs
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(r.success for r in results)
            assert len(results) == 3

            # Cleanup
            import shutil
            for config in configs:
                deploy_dir = Path(f"businesses/{config.repo_name}")
                if deploy_dir.exists():
                    shutil.rmtree(deploy_dir)


class TestErrorHandling:
    """Test error handling edge cases"""

    def test_prepare_files_with_empty_code(self):
        """Test file preparation with empty code files"""
        agent = DeployAgent()

        result_json = agent.prepare_deployment_files(
            business_name="test-app",
            code_files={},
            framework="nextjs"
        )

        result = json.loads(result_json)
        assert result["success"]
        # Should at least create package.json
        assert result["files_written"] >= 1

        # Cleanup
        deploy_dir = Path(f"businesses/test-app")
        if deploy_dir.exists():
            import shutil
            shutil.rmtree(deploy_dir)

    def test_verify_deployment_network_error(self):
        """Test deployment verification with network error"""
        agent = DeployAgent()

        with patch('requests.get', side_effect=Exception("Network error")):
            result_json = agent.verify_deployment("https://test-app.vercel.app")
            result = json.loads(result_json)

            assert not result["success"]
            assert "error" in result
            assert "Network error" in result["error"]


# Performance benchmarks
class TestPerformance:
    """Performance benchmarks"""

    @pytest.mark.asyncio
    async def test_deployment_speed(self):
        """Benchmark deployment workflow speed"""
        import time

        with patch('agents.deploy_agent.AzureCliCredential'), \
             patch('agents.deploy_agent.AzureAIAgentClient'), \
             patch('agents.deploy_agent.ChatAgent'), \
             patch('requests.get') as mock_get, \
             patch.dict('os.environ', {'GITHUB_TOKEN': 'mock_token'}), \
             patch('subprocess.run'):

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.5
            mock_get.return_value = mock_response

            agent = DeployAgent(use_learning=False, use_reflection=False)
            await agent.initialize()

            config = DeploymentConfig(repo_name="benchmark-app")
            business_data = {
                "code_files": {
                    "pages/index.js": "export default () => <div>Benchmark</div>"
                }
            }

            start = time.time()
            result = await agent.full_deployment_workflow(config, business_data)
            duration = time.time() - start

            assert result.success
            # Should complete in reasonable time (< 30s for mock)
            assert duration < 30.0

            # Cleanup
            deploy_dir = Path(f"businesses/{config.repo_name}")
            if deploy_dir.exists():
                import shutil
                shutil.rmtree(deploy_dir)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
