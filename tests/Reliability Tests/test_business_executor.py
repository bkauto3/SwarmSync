"""
Tests for Business Execution Engine

Comprehensive test suite for:
- Vercel API client
- GitHub API client
- Deployment validation
- Business executor core
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from infrastructure.execution import (
    BusinessExecutor,
    BusinessExecutionConfig,
    BusinessExecutionResult,
    VercelClient,
    VercelProject,
    VercelDeployment,
    VercelAPIError,
    GitHubClient,
    GitHubRepository,
    GitHubAPIError,
    DeploymentValidator,
    ValidationReport,
    ValidationResult
)


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def test_config():
    """Test configuration."""
    return BusinessExecutionConfig(
        vercel_token="test_vercel_token",
        vercel_team_id="test_team_id",
        github_token="test_github_token",
        mongodb_uri="mongodb://localhost:27017",
        github_org="test-org",
        temp_dir="/tmp"
    )


@pytest.fixture
def test_business_plan():
    """Test business plan."""
    return {
        "name": "Test AI Writing Assistant",
        "description": "AI-powered writing tool",
        "type": "saas_tool",
        "tech_stack": ["Next.js", "OpenAI", "Stripe"],
        "mvp_features": [
            "Text input",
            "AI suggestions",
            "Export to PDF"
        ]
    }


@pytest.fixture
def mock_vercel_project():
    """Mock Vercel project."""
    return VercelProject(
        id="prj_test123",
        name="test-app",
        framework="nextjs",
        created_at=datetime.now(),
        git_repository={"repo": "test-org/test-app"}
    )


@pytest.fixture
def mock_github_repo():
    """Mock GitHub repository."""
    return GitHubRepository(
        id=12345,
        name="test-app",
        full_name="test-org/test-app",
        html_url="https://github.com/test-org/test-app",
        clone_url="https://github.com/test-org/test-app.git",
        ssh_url="git@github.com:test-org/test-app.git",
        default_branch="main",
        private=False,
        created_at=datetime.now()
    )


# ============================================
# VERCEL CLIENT TESTS
# ============================================

class TestVercelClient:
    """Test suite for Vercel API client."""

    @pytest.mark.asyncio
    async def test_create_project_success(self, mock_vercel_project):
        """Test successful project creation."""
        client = VercelClient(token="test_token", team_id="test_team")

        with patch("httpx.AsyncClient") as mock_http:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "id": "prj_test123",
                "name": "test-app",
                "framework": "nextjs",
                "createdAt": int(datetime.now().timestamp() * 1000)
            }

            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            project = await client.create_project(
                name="test-app",
                framework="nextjs"
            )

            assert project.id == "prj_test123"
            assert project.name == "test-app"
            assert project.framework == "nextjs"

    @pytest.mark.asyncio
    async def test_create_project_error(self):
        """Test project creation error handling."""
        client = VercelClient(token="test_token")

        with patch("httpx.AsyncClient") as mock_http:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": {"message": "Invalid project name"}
            }

            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(VercelAPIError) as exc_info:
                await client.create_project(name="invalid name!")

            assert "Invalid project name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_deployment_status(self):
        """Test getting deployment status."""
        client = VercelClient(token="test_token")

        with patch("httpx.AsyncClient") as mock_http:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "dpl_test123",
                "url": "test-app.vercel.app",
                "readyState": "READY",
                "createdAt": int(datetime.now().timestamp() * 1000),
                "projectId": "prj_test123"
            }

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            deployment = await client.get_deployment_status("dpl_test123")

            assert deployment.id == "dpl_test123"
            assert deployment.state == "READY"
            assert deployment.ready_state == "READY"

    @pytest.mark.asyncio
    async def test_wait_for_deployment_success(self):
        """Test waiting for deployment to complete."""
        client = VercelClient(token="test_token")

        call_count = 0

        async def mock_get_status(deployment_id):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                return VercelDeployment(
                    id=deployment_id,
                    url="test-app.vercel.app",
                    state="READY",
                    created_at=datetime.now(),
                    project_id="prj_test",
                    ready_state="READY"
                )
            else:
                return VercelDeployment(
                    id=deployment_id,
                    url="test-app.vercel.app",
                    state="BUILDING",
                    created_at=datetime.now(),
                    project_id="prj_test",
                    ready_state="BUILDING"
                )

        with patch.object(client, "get_deployment_status", side_effect=mock_get_status):
            url = await client.wait_for_deployment(
                deployment_id="dpl_test",
                timeout_seconds=30,
                poll_interval=1
            )

            assert url == "https://test-app.vercel.app"
            assert call_count >= 2

    @pytest.mark.asyncio
    async def test_wait_for_deployment_timeout(self):
        """Test deployment timeout."""
        client = VercelClient(token="test_token")

        async def mock_get_status(deployment_id):
            return VercelDeployment(
                id=deployment_id,
                url="test-app.vercel.app",
                state="BUILDING",
                created_at=datetime.now(),
                project_id="prj_test",
                ready_state="BUILDING"
            )

        with patch.object(client, "get_deployment_status", side_effect=mock_get_status):
            with pytest.raises(VercelAPIError) as exc_info:
                await client.wait_for_deployment(
                    deployment_id="dpl_test",
                    timeout_seconds=2,
                    poll_interval=1
                )

            assert "timed out" in str(exc_info.value).lower()


# ============================================
# GITHUB CLIENT TESTS
# ============================================

class TestGitHubClient:
    """Test suite for GitHub API client."""

    @pytest.mark.asyncio
    async def test_create_repo_success(self):
        """Test successful repository creation."""
        client = GitHubClient(token="test_token", org="test-org")

        with patch("httpx.AsyncClient") as mock_http:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                "id": 12345,
                "name": "test-repo",
                "full_name": "test-org/test-repo",
                "html_url": "https://github.com/test-org/test-repo",
                "clone_url": "https://github.com/test-org/test-repo.git",
                "ssh_url": "git@github.com:test-org/test-repo.git",
                "default_branch": "main",
                "private": False,
                "created_at": "2025-11-03T00:00:00Z"
            }

            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            repo = await client.create_repo(
                name="test-repo",
                description="Test repository"
            )

            assert repo.id == 12345
            assert repo.name == "test-repo"
            assert repo.full_name == "test-org/test-repo"

    @pytest.mark.asyncio
    async def test_create_repo_error(self):
        """Test repository creation error handling."""
        client = GitHubClient(token="test_token")

        with patch("httpx.AsyncClient") as mock_http:
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.json.return_value = {
                "message": "Repository already exists"
            }

            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(GitHubAPIError) as exc_info:
                await client.create_repo(name="existing-repo", description="Test")

            assert "already exists" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_repo_success(self):
        """Test getting repository metadata."""
        client = GitHubClient(token="test_token")

        with patch("httpx.AsyncClient") as mock_http:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 12345,
                "name": "test-repo",
                "full_name": "test-org/test-repo",
                "html_url": "https://github.com/test-org/test-repo",
                "clone_url": "https://github.com/test-org/test-repo.git",
                "ssh_url": "git@github.com:test-org/test-repo.git",
                "default_branch": "main",
                "private": False,
                "created_at": "2025-11-03T00:00:00Z"
            }

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            repo = await client.get_repo("test-org", "test-repo")

            assert repo.name == "test-repo"
            assert repo.full_name == "test-org/test-repo"


# ============================================
# DEPLOYMENT VALIDATOR TESTS
# ============================================

class TestDeploymentValidator:
    """Test suite for deployment validation."""

    @pytest.mark.asyncio
    async def test_validate_deployment_success(self):
        """Test successful deployment validation."""
        validator = DeploymentValidator(timeout=5.0)

        with patch("httpx.AsyncClient") as mock_http:
            mock_response = Mock()
            mock_response.status_code = 200
            # Make content longer than 100 bytes to pass content check
            mock_response.text = "<html><head><title>Test</title></head><body>" + ("Content " * 50) + "</body></html>"
            mock_response.elapsed.total_seconds.return_value = 0.5

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            report = await validator.validate_full_deployment(
                deployment_url="https://test-app.vercel.app"
            )

            assert report.success
            assert report.passed_checks > 0

    @pytest.mark.asyncio
    async def test_validate_deployment_failure(self):
        """Test deployment validation failure."""
        validator = DeploymentValidator(timeout=5.0)

        with patch("httpx.AsyncClient") as mock_http:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.elapsed.total_seconds.return_value = 0.5

            mock_http.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            report = await validator.validate_full_deployment(
                deployment_url="https://test-app.vercel.app"
            )

            assert not report.success

    @pytest.mark.asyncio
    async def test_check_response_time(self):
        """Test response time validation."""
        validator = DeploymentValidator()

        result = await validator._check_response_time(
            url="https://httpbin.org/delay/1",
            max_time=3.0
        )

        # Should pass since 1s delay < 3s max
        assert result.check == "Response Time"

    def test_validation_report_metrics(self):
        """Test validation report metrics."""
        results = [
            ValidationResult(check="Test 1", passed=True, details="OK"),
            ValidationResult(check="Test 2", passed=True, details="OK"),
            ValidationResult(check="Test 3", passed=False, details="Failed")
        ]

        report = ValidationReport(
            success=False,
            deployment_url="https://test.com",
            results=results
        )

        assert report.passed_checks == 2
        assert report.total_checks == 3
        assert report.pass_rate == pytest.approx(66.67, rel=0.1)


# ============================================
# BUSINESS EXECUTOR TESTS
# ============================================

class TestBusinessExecutor:
    """Test suite for business executor."""

    @pytest.mark.asyncio
    async def test_generate_minimal_nextjs_app(self, test_config, test_business_plan):
        """Test minimal Next.js app generation."""
        executor = BusinessExecutor(test_config)

        code_files = executor._generate_minimal_nextjs_app(test_business_plan)

        assert "package.json" in code_files
        assert "src/app/page.tsx" in code_files
        assert "src/app/layout.tsx" in code_files
        assert "README.md" in code_files

        # Verify package.json is valid JSON
        import json
        package_data = json.loads(code_files["package.json"])
        assert "next" in package_data["dependencies"]
        assert package_data["name"] == "test-ai-writing-assistant"

    def test_sanitize_repo_name(self, test_config):
        """Test repository name sanitization."""
        executor = BusinessExecutor(test_config)

        assert executor._sanitize_repo_name("My Test App!") == "my-test-app"
        assert executor._sanitize_repo_name("Test@App#123") == "testapp123"
        assert executor._sanitize_repo_name("   spaces   ") == "spaces"

    def test_sanitize_project_name(self, test_config):
        """Test project name sanitization."""
        executor = BusinessExecutor(test_config)

        assert executor._sanitize_project_name("My Test App!") == "my-test-app"
        assert executor._sanitize_project_name("A" * 100) == "a" * 52  # Max 52 chars

    def test_extract_repo_path(self, test_config):
        """Test repo path extraction."""
        executor = BusinessExecutor(test_config)

        assert executor._extract_repo_path(
            "https://github.com/user/repo"
        ) == "user/repo"

        assert executor._extract_repo_path(
            "https://github.com/user/repo.git"
        ) == "user/repo"

        assert executor._extract_repo_path(
            "git@github.com:user/repo.git"
        ) == "user/repo"

    def test_prepare_env_vars(self, test_config, test_business_plan):
        """Test environment variable preparation."""
        executor = BusinessExecutor(test_config)

        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test123",
            "STRIPE_API_KEY": "sk_test_stripe"
        }):
            env_vars = executor._prepare_env_vars(test_business_plan)

            assert env_vars["GENESIS_CREATED"] == "true"
            assert env_vars["GENESIS_VERSION"] == "1.0"
            assert env_vars["BUSINESS_TYPE"] == "saas_tool"
            assert "OPENAI_API_KEY" in env_vars
            assert "STRIPE_API_KEY" in env_vars

    @pytest.mark.asyncio
    async def test_execute_business_minimal(self, test_config, test_business_plan):
        """Test minimal business execution (mocked)."""
        executor = BusinessExecutor(test_config)

        # Mock all external calls
        with patch.object(executor, "_create_github_repo", return_value=AsyncMock(
            return_value="https://github.com/test-org/test-app"
        )):
            with patch.object(executor, "_deploy_to_vercel", return_value=AsyncMock(
                return_value={
                    "url": "test-app.vercel.app",
                    "project_id": "prj_test",
                    "deployment_id": "dpl_test"
                }
            )):
                with patch.object(executor.validator, "validate_full_deployment", return_value=AsyncMock(
                    return_value=ValidationReport(
                        success=True,
                        deployment_url="https://test-app.vercel.app",
                        results=[
                            ValidationResult(check="Test", passed=True, details="OK")
                        ]
                    )
                )):
                    # Generate code files
                    code_files = executor._generate_minimal_nextjs_app(test_business_plan)

                    # Mock the actual async methods
                    executor._create_github_repo = AsyncMock(
                        return_value="https://github.com/test-org/test-app"
                    )
                    executor._deploy_to_vercel = AsyncMock(
                        return_value={
                            "url": "test-app.vercel.app",
                            "project_id": "prj_test",
                            "deployment_id": "dpl_test"
                        }
                    )
                    executor.validator.validate_full_deployment = AsyncMock(
                        return_value=ValidationReport(
                            success=True,
                            deployment_url="https://test-app.vercel.app",
                            results=[
                                ValidationResult(check="Test", passed=True, details="OK")
                            ]
                        )
                    )

                    result = await executor.execute_business(
                        business_plan=test_business_plan,
                        code_files=code_files
                    )

                    assert result.success
                    assert result.deployment_url is not None
                    assert result.repo_url is not None
                    assert result.execution_time_seconds > 0


# ============================================
# INTEGRATION TESTS
# ============================================

@pytest.mark.integration
class TestIntegration:
    """Integration tests (require real credentials)."""

    @pytest.mark.asyncio
    async def test_vercel_list_projects(self):
        """Test listing Vercel projects (requires VERCEL_TOKEN)."""
        token = os.getenv("VERCEL_TOKEN")
        if not token:
            pytest.skip("VERCEL_TOKEN not set")

        client = VercelClient(token=token)
        projects = await client.list_projects(limit=5)

        assert isinstance(projects, list)
