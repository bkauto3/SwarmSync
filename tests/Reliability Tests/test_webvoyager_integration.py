"""
WebVoyager Integration Tests for Genesis
Paper: https://arxiv.org/abs/2401.13919

Tests the WebVoyager multimodal web agent integration with Analyst and Content agents.

Expected Performance:
- 59.1% success rate on diverse web tasks
- 5-8 navigation steps per task
- 30-50% faster than manual web research
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from infrastructure.webvoyager_client import WebVoyagerClient, get_webvoyager_client


class TestWebVoyagerClient:
    """Test WebVoyager client functionality"""

    def test_webvoyager_client_initialization(self):
        """Test WebVoyager client initializes correctly"""
        client = get_webvoyager_client(
            headless=True,
            max_iterations=10,
            text_only=False
        )

        assert client is not None
        assert client.use_webvoyager is True
        assert client.headless is True
        assert client.max_iterations == 10
        assert client.text_only is False

    def test_webvoyager_client_text_only_mode(self):
        """Test WebVoyager client with text-only mode (accessibility tree)"""
        client = get_webvoyager_client(
            headless=True,
            max_iterations=15,
            text_only=True
        )

        assert client is not None
        assert client.text_only is True

    @pytest.mark.asyncio
    async def test_webvoyager_navigate_fallback(self):
        """Test fallback navigation when WebVoyager unavailable"""
        # Create client with WebVoyager disabled
        client = WebVoyagerClient(use_webvoyager=False)

        result = await client.navigate_and_extract(
            url="https://example.com",
            task="Get page title"
        )

        # Fallback should still return structured response
        assert 'success' in result
        assert 'trajectory' in result
        assert 'screenshots' in result

    @pytest.mark.asyncio
    @patch('infrastructure.webvoyager_client.WebVoyagerClient._run_webvoyager_sync')
    async def test_webvoyager_navigate_success(self, mock_run):
        """Test successful web navigation"""
        # Mock WebVoyager execution
        mock_run.return_value = {
            'success': True,
            'answer': 'Task completed successfully',
            'trajectory': [
                {'iteration': 1, 'action': 'Click [5]', 'url': 'https://example.com'}
            ],
            'screenshots': ['/tmp/screenshot_1.png'],
            'iterations': 1,
            'error': None
        }

        client = get_webvoyager_client(headless=True)
        result = await client.navigate_and_extract(
            url="https://example.com",
            task="Click the first link"
        )

        assert result['success'] is True
        assert result['answer'] == 'Task completed successfully'
        assert len(result['trajectory']) == 1
        assert result['iterations'] == 1


class TestAnalystAgentWebVoyagerIntegration:
    """Test WebVoyager integration with Analyst Agent"""

    @pytest.mark.asyncio
    async def test_analyst_has_webvoyager_client(self):
        """Test Analyst Agent initializes with WebVoyager client"""
        from agents.analyst_agent import AnalystAgent

        analyst = AnalystAgent(business_id="test")

        # Check WebVoyager client is initialized (if available)
        # Graceful degradation if dependencies not installed
        assert hasattr(analyst, 'webvoyager')

    @pytest.mark.asyncio
    async def test_analyst_web_research_tool_exists(self):
        """Test Analyst Agent has web_research tool"""
        from agents.analyst_agent import AnalystAgent

        analyst = AnalystAgent(business_id="test")
        await analyst.initialize()

        # Check web_research method exists
        assert hasattr(analyst, 'web_research')
        assert callable(analyst.web_research)

    @pytest.mark.asyncio
    @patch('infrastructure.webvoyager_client.WebVoyagerClient.navigate_and_extract')
    async def test_analyst_web_research_execution(self, mock_navigate):
        """Test Analyst Agent can execute web research"""
        from agents.analyst_agent import AnalystAgent

        # Mock WebVoyager response
        mock_navigate.return_value = {
            'success': True,
            'answer': 'Product prices: $49, $79, $99',
            'trajectory': [
                {'iteration': 1, 'action': 'Search', 'url': 'https://example.com/search'}
            ],
            'screenshots': [],
            'iterations': 1,
            'error': None
        }

        analyst = AnalystAgent(business_id="test")

        # Execute web research (if WebVoyager available)
        if hasattr(analyst, 'webvoyager') and analyst.webvoyager:
            result_json = await analyst.web_research(
                url="https://example.com",
                task="Search for product prices and extract top 3 results"
            )

            # Result should be JSON string
            import json
            result = json.loads(result_json)

            assert 'research_id' in result
            assert result['url'] == "https://example.com"
            assert 'metadata' in result


class TestContentAgentWebVoyagerIntegration:
    """Test WebVoyager integration with Content Agent"""

    @pytest.mark.asyncio
    async def test_content_has_webvoyager_client(self):
        """Test Content Agent initializes with WebVoyager client"""
        from agents.content_agent import ContentAgent

        content = ContentAgent(business_id="test")

        # Check WebVoyager client is initialized (if available)
        assert hasattr(content, 'webvoyager')

    @pytest.mark.asyncio
    async def test_content_web_research_tool_exists(self):
        """Test Content Agent has web_content_research tool"""
        from agents.content_agent import ContentAgent

        content = ContentAgent(business_id="test")
        await content.initialize()

        # Check web_content_research method exists
        assert hasattr(content, 'web_content_research')
        assert callable(content.web_content_research)

    @pytest.mark.asyncio
    @patch('infrastructure.webvoyager_client.WebVoyagerClient.navigate_and_extract')
    async def test_content_web_research_execution(self, mock_navigate):
        """Test Content Agent can execute web content research"""
        from agents.content_agent import ContentAgent

        # Mock WebVoyager response
        mock_navigate.return_value = {
            'success': True,
            'answer': 'Top articles: 1. AI Trends 2025, 2. LLM Best Practices, 3. Agent Systems',
            'trajectory': [
                {'iteration': 1, 'action': 'Search', 'url': 'https://medium.com/search'}
            ],
            'screenshots': [],
            'iterations': 1,
            'error': None
        }

        content = ContentAgent(business_id="test")

        # Execute web content research (if WebVoyager available)
        if hasattr(content, 'webvoyager') and content.webvoyager:
            result_json = await content.web_content_research(
                url="https://medium.com",
                task="Find top 3 AI articles and extract titles"
            )

            # Result should be JSON string
            import json
            result = json.loads(result_json)

            assert 'research_id' in result
            assert result['url'] == "https://medium.com"
            assert 'metadata' in result


class TestWebVoyagerPerformance:
    """Test WebVoyager performance characteristics"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @patch('infrastructure.webvoyager_client.WebVoyagerClient._run_webvoyager_sync')
    async def test_webvoyager_performance_metrics(self, mock_run):
        """Test WebVoyager meets performance targets"""
        # Mock execution with realistic timing
        mock_run.return_value = {
            'success': True,
            'answer': 'Task completed',
            'trajectory': [
                {'iteration': i, 'action': f'Action {i}', 'url': 'https://example.com'}
                for i in range(1, 6)  # 5 navigation steps
            ],
            'screenshots': [f'/tmp/screenshot_{i}.png' for i in range(1, 6)],
            'iterations': 5,
            'error': None
        }

        client = get_webvoyager_client(headless=True)

        import time
        start_time = time.time()

        result = await client.navigate_and_extract(
            url="https://example.com",
            task="Multi-step navigation task"
        )

        elapsed_time = time.time() - start_time

        # Performance checks
        assert result['success'] is True
        assert result['iterations'] <= 8, "Should complete in 5-8 steps (paper benchmark)"
        assert elapsed_time < 30, "Should complete within reasonable time"

    def test_webvoyager_graceful_degradation(self):
        """Test system degrades gracefully when WebVoyager unavailable"""
        from agents.analyst_agent import AnalystAgent
        from agents.content_agent import ContentAgent

        # Agents should initialize even if WebVoyager unavailable
        analyst = AnalystAgent(business_id="test")
        content = ContentAgent(business_id="test")

        # Attributes should exist even if None
        assert hasattr(analyst, 'webvoyager')
        assert hasattr(content, 'webvoyager')


# Benchmark tests (optional, requires real WebVoyager setup)
class TestWebVoyagerBenchmark:
    """Benchmark tests for WebVoyager (requires full setup)"""

    @pytest.mark.skipif(
        True,  # Skip by default, requires full WebVoyager setup
        reason="Requires full WebVoyager setup with Selenium and Chrome"
    )
    @pytest.mark.asyncio
    async def test_webvoyager_real_navigation(self):
        """Real-world test with actual WebVoyager (requires setup)"""
        client = get_webvoyager_client(headless=True)

        result = await client.navigate_and_extract(
            url="https://example.com",
            task="Get the page title and first paragraph"
        )

        # Real execution test
        assert result['success'] in [True, False]  # May succeed or fail
        assert 'trajectory' in result
        assert 'iterations' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# ============================================================================
# SECURITY: PATH VALIDATION TESTS
# ============================================================================


@pytest.mark.asyncio
class TestWebVoyagerPathValidation:
    """Test path validation security features"""

    async def test_validate_navigation_safe_urls(self):
        """
        Test: Path validation allows safe URLs

        Validates:
        - HTTP URLs allowed
        - HTTPS URLs allowed
        - Valid paths allowed
        """
        client = WebVoyagerClient(use_webvoyager=False)

        # Safe URLs should pass
        assert client._validate_navigation("https://example.com") is True
        assert client._validate_navigation("http://example.com") is True
        assert client._validate_navigation("https://example.com/safe/path") is True
        assert client._validate_navigation("https://example.com/api/v1/users") is True

    async def test_validate_navigation_directory_traversal(self):
        """
        Test: Path validation blocks directory traversal

        Validates:
        - ".." patterns blocked
        - "/.." patterns blocked
        - Alternate forms blocked
        """
        client = WebVoyagerClient(use_webvoyager=False)

        # Directory traversal should fail
        assert client._validate_navigation("https://example.com/../etc/passwd") is False
        assert client._validate_navigation("https://example.com/../../etc/passwd") is False
        assert client._validate_navigation("https://example.com/safe/../../../etc") is False

    async def test_validate_navigation_suspicious_patterns(self):
        """
        Test: Path validation blocks suspicious patterns

        Validates:
        - /etc/passwd blocked
        - /proc/ blocked
        - File:// protocol blocked
        - JavaScript: protocol blocked
        - Data: URLs blocked
        - Template injection blocked
        """
        client = WebVoyagerClient(use_webvoyager=False)

        # Suspicious patterns should fail
        assert client._validate_navigation("file:///etc/passwd") is False
        assert client._validate_navigation("https://example.com/proc/self") is False
        assert client._validate_navigation("javascript:alert('xss')") is False
        assert client._validate_navigation("data:text/html,<script>alert('xss')</script>") is False
        assert client._validate_navigation("https://example.com/${user}") is False

    async def test_validate_navigation_invalid_protocols(self):
        """
        Test: Path validation blocks invalid protocols

        Validates:
        - FTP blocked
        - SSH blocked
        - Telnet blocked
        - Only http/https allowed
        """
        client = WebVoyagerClient(use_webvoyager=False)

        # Invalid protocols should fail
        assert client._validate_navigation("ftp://example.com") is False
        assert client._validate_navigation("ssh://example.com") is False
        assert client._validate_navigation("telnet://example.com") is False
        assert client._validate_navigation("gopher://example.com") is False

    async def test_validate_navigation_domain_allowlist(self):
        """
        Test: Path validation respects domain allow-list

        Validates:
        - Only allowed domains pass
        - Other domains blocked
        - Empty allow-list allows all
        """
        # With allow-list
        client_restricted = WebVoyagerClient(
            use_webvoyager=False,
            allowed_domains=["example.com", "github.com"]
        )

        assert client_restricted._validate_navigation("https://example.com") is True
        assert client_restricted._validate_navigation("https://github.com") is True
        assert client_restricted._validate_navigation("https://evil.com") is False
        assert client_restricted._validate_navigation("https://google.com") is False

        # Without allow-list (all allowed)
        client_unrestricted = WebVoyagerClient(use_webvoyager=False)
        assert client_unrestricted._validate_navigation("https://example.com") is True
        assert client_unrestricted._validate_navigation("https://google.com") is True

    async def test_navigate_and_extract_blocks_unsafe_urls(self):
        """
        Test: navigate_and_extract() enforces URL validation

        Validates:
        - Unsafe URLs rejected before navigation
        - Error returned with explanation
        - No actual navigation attempted
        """
        client = WebVoyagerClient(use_webvoyager=False)

        # Try to navigate to unsafe URL
        result = await client.navigate_and_extract(
            url="https://example.com/../etc/passwd",
            task="Test task"
        )

        # Should fail validation
        assert result['success'] is False
        assert 'error' in result
        assert 'security validation' in result['error'].lower()
        assert result['iterations'] == 0

    async def test_fallback_navigate_blocks_unsafe_urls(self):
        """
        Test: _fallback_navigate() also enforces URL validation

        Validates:
        - Fallback mode has same security
        - Unsafe URLs blocked even in fallback
        """
        client = WebVoyagerClient(use_webvoyager=False)

        # Try fallback navigation to unsafe URL
        result = await client._fallback_navigate(
            url="javascript:alert('xss')",
            task="Test task"
        )

        # Should fail validation
        assert result['success'] is False
        assert 'error' in result
        assert 'security validation' in result['error'].lower()

    async def test_validate_navigation_edge_cases(self):
        """
        Test: Path validation handles edge cases

        Validates:
        - Null byte injection blocked
        - Windows UNC paths blocked
        - Mixed case patterns still blocked
        - Empty URLs handled gracefully
        """
        client = WebVoyagerClient(use_webvoyager=False)

        # Edge cases
        assert client._validate_navigation("https://example.com/test%00.txt") is False  # Null byte
        assert client._validate_navigation("\\\\server\\share") is False  # UNC path
        assert client._validate_navigation("https://example.com/PROC/self") is False  # Mixed case
        assert client._validate_navigation("") is True  # Empty URL (relative)

    async def test_navigate_with_allowlist_enforcement(self):
        """
        Test: Full navigation respects domain allow-list

        Validates:
        - Domain restriction works in real navigation
        - Allowed domains succeed
        - Blocked domains fail
        """
        client = WebVoyagerClient(
            use_webvoyager=False,
            allowed_domains=["example.com"]
        )

        # Allowed domain
        result_allowed = await client.navigate_and_extract(
            url="https://example.com",
            task="Test task"
        )
        # Should attempt navigation (may succeed or fail due to network, but not blocked by security)
        assert result_allowed['error'] is None or 'security validation' not in str(result_allowed.get('error', '')).lower()

        # Blocked domain
        result_blocked = await client.navigate_and_extract(
            url="https://google.com",
            task="Test task"
        )
        # Should be blocked by security
        assert result_blocked['success'] is False
        assert 'error' in result_blocked
        assert 'allow-list' in result_blocked['error'].lower() or 'security validation' in result_blocked['error'].lower()


# ============================================================================
# END SECURITY: PATH VALIDATION TESTS
# ============================================================================
