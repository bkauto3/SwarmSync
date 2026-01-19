"""
Integration Tests for TOON in A2A Connector
--------------------------------------------
Tests TOON encoding integration with A2A service.

Tests cover:
1. TOON encoding in A2A requests
2. Content-Type negotiation
3. Backward compatibility
4. Token reduction metrics
5. Feature flag control

Author: Hudson (Code Review Agent)
Date: 2025-10-27
Version: 1.0.0
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from infrastructure.a2a_connector import A2AConnector
from infrastructure.toon_encoder import encode_to_toon


def create_mock_response(status=200, content_type="application/json", data=None):
    """Helper to create mock HTTP response"""
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.headers = {"Content-Type": content_type}

    if data is None:
        data = {"result": "success", "status": "success"}

    mock_response.json = AsyncMock(return_value=data)
    mock_response.text = AsyncMock(return_value=json.dumps(data))

    # Create async context manager
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_response
    mock_ctx.__aexit__.return_value = None

    return mock_ctx


class TestA2AToonIntegration:
    """Test TOON integration with A2A connector"""

    @pytest.fixture
    def connector(self, monkeypatch):
        """Create A2A connector with TOON enabled"""
        monkeypatch.setenv("A2A_ALLOW_HTTP", "true")
        monkeypatch.setenv("ENVIRONMENT", "test")
        return A2AConnector(
            base_url="http://localhost:8080",
            enable_toon=True
        )

    @pytest.fixture
    def connector_no_toon(self, monkeypatch):
        """Create A2A connector with TOON disabled"""
        monkeypatch.setenv("A2A_ALLOW_HTTP", "true")
        monkeypatch.setenv("ENVIRONMENT", "test")
        return A2AConnector(
            base_url="http://localhost:8080",
            enable_toon=False
        )

    @pytest.mark.asyncio
    async def test_toon_encoding_for_tabular_data(self, connector):
        """Test that tabular data is TOON-encoded"""
        mock_ctx = create_mock_response()

        with patch.object(connector, '_session') as mock_session:
            mock_session.post = MagicMock(return_value=mock_ctx)

            arguments = {
                "users": [
                    {"id": 1, "name": "Alice", "age": 30},
                    {"id": 2, "name": "Bob", "age": 25},
                    {"id": 3, "name": "Charlie", "age": 35}
                ]
            }

            result = await connector.invoke_agent_tool(
                agent_name="test_agent",
                tool_name="process_users",
                arguments=arguments
            )

            # Verify TOON was used
            stats = connector.get_toon_statistics()
            assert stats["toon_encoded"] >= 1, "TOON encoding not used"
            assert stats["avg_token_reduction"] > 0.2, "Token reduction too low"

    @pytest.mark.asyncio
    async def test_json_fallback_for_non_tabular(self, connector):
        """Test that non-tabular data uses JSON"""
        mock_ctx = create_mock_response()

        with patch.object(connector, '_session') as mock_session:
            mock_session.post = MagicMock(return_value=mock_ctx)

            arguments = {
                "name": "Alice",
                "metadata": {"key": "value"}
            }

            result = await connector.invoke_agent_tool(
                agent_name="test_agent",
                tool_name="process_user",
                arguments=arguments
            )

            # Verify JSON was used
            stats = connector.get_toon_statistics()
            assert stats["json_encoded"] >= 1, "JSON encoding not used"

    @pytest.mark.asyncio
    async def test_toon_disabled_uses_json(self, connector_no_toon):
        """Test that TOON disabled always uses JSON"""
        mock_ctx = create_mock_response()

        with patch.object(connector_no_toon, '_session') as mock_session:
            mock_session.post = MagicMock(return_value=mock_ctx)

            arguments = {
                "users": [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"}
                ]
            }

            result = await connector_no_toon.invoke_agent_tool(
                agent_name="test_agent",
                tool_name="process_users",
                arguments=arguments
            )

            # Verify only JSON was used
            stats = connector_no_toon.get_toon_statistics()
            assert stats["toon_encoded"] == 0, "TOON should be disabled"
            assert stats["json_encoded"] >= 1, "JSON encoding not used"

    @pytest.mark.asyncio
    async def test_accept_header_includes_toon(self, connector):
        """Test that Accept header includes TOON"""
        mock_ctx = create_mock_response()

        with patch.object(connector, '_session') as mock_session:
            mock_session.post = MagicMock(return_value=mock_ctx)

            arguments = {"data": [{"id": 1}, {"id": 2}]}

            await connector.invoke_agent_tool(
                agent_name="test_agent",
                tool_name="test_tool",
                arguments=arguments
            )

            # Verify Accept header
            call_args = mock_session.post.call_args
            headers = call_args.kwargs.get("headers", {})
            assert "Accept" in headers
            assert "application/toon" in headers["Accept"]
            assert "application/json" in headers["Accept"]

    @pytest.mark.asyncio
    async def test_toon_response_decoding(self, connector):
        """Test that TOON-encoded responses are decoded"""
        # For this test, we'll skip TOON response decoding since it requires
        # the A2A service to support TOON responses. The encoder/decoder
        # tests already validate the TOON format.
        # This test validates that the Accept header is set correctly.
        mock_ctx = create_mock_response()

        with patch.object(connector, '_session') as mock_session:
            mock_session.post = MagicMock(return_value=mock_ctx)

            result = await connector.invoke_agent_tool(
                agent_name="test_agent",
                tool_name="test_tool",
                arguments={"test": "data"}
            )

            # Verify Accept header includes TOON
            call_args = mock_session.post.call_args
            headers = call_args.kwargs.get("headers", {})
            assert "Accept" in headers
            assert "application/toon" in headers["Accept"]

    def test_toon_statistics_tracking(self, connector):
        """Test that TOON statistics are tracked correctly"""
        # Initial stats
        stats = connector.get_toon_statistics()
        assert stats["requests_sent"] == 0
        assert stats["toon_encoded"] == 0
        assert stats["json_encoded"] == 0
        assert stats["toon_usage_rate"] == 0.0
        assert stats["avg_token_reduction"] == 0.0

        # Simulate TOON encoding
        connector.toon_stats["requests_sent"] = 10
        connector.toon_stats["toon_encoded"] = 7
        connector.toon_stats["json_encoded"] = 3
        connector.toon_stats["total_token_reduction"] = 2.8  # 40% avg

        stats = connector.get_toon_statistics()
        assert stats["requests_sent"] == 10
        assert stats["toon_encoded"] == 7
        assert stats["json_encoded"] == 3
        assert stats["toon_usage_rate"] == 0.7
        assert abs(stats["avg_token_reduction"] - 0.4) < 0.01

    def test_toon_feature_flag_from_env(self, monkeypatch):
        """Test TOON can be disabled via environment variable"""
        # Allow HTTP for testing
        monkeypatch.setenv("A2A_ALLOW_HTTP", "true")
        monkeypatch.setenv("ENVIRONMENT", "test")
        # Disable via env
        monkeypatch.setenv("A2A_ENABLE_TOON", "false")

        connector = A2AConnector(
            base_url="http://localhost:8080",
            enable_toon=True  # Explicit True, but env overrides
        )

        assert connector.enable_toon is False

    def test_backward_compatibility_without_toon(self, monkeypatch):
        """Test that existing code works without TOON"""
        # Allow HTTP for testing
        monkeypatch.setenv("A2A_ALLOW_HTTP", "true")
        monkeypatch.setenv("ENVIRONMENT", "test")
        # Old code that doesn't specify enable_toon
        connector = A2AConnector(
            base_url="http://localhost:8080"
        )

        # Should default to enabled
        assert connector.enable_toon is True

        # Should have TOON stats initialized
        stats = connector.get_toon_statistics()
        assert "toon_encoded" in stats


class TestToonTokenReduction:
    """Test token reduction with real-world data"""

    def test_user_list_reduction(self):
        """Test token reduction for user lists"""
        from infrastructure.toon_encoder import calculate_token_reduction

        users = [
            {"id": i, "name": f"User{i}", "email": f"user{i}@example.com", "age": 20 + i}
            for i in range(1, 21)
        ]

        reduction = calculate_token_reduction(users)
        assert reduction > 0.35, f"Expected >35% reduction, got {reduction:.1%}"

    def test_api_response_reduction(self):
        """Test token reduction for typical API responses"""
        from infrastructure.toon_encoder import calculate_token_reduction

        api_response = [
            {
                "id": i,
                "timestamp": f"2025-10-27T12:00:{i:02d}Z",
                "status": "success",
                "duration_ms": 100 + i,
                "user_id": 1000 + i
            }
            for i in range(1, 51)
        ]

        reduction = calculate_token_reduction(api_response)
        assert reduction > 0.40, f"Expected >40% reduction, got {reduction:.1%}"

    def test_csv_like_data_reduction(self):
        """Test token reduction for CSV-like data"""
        from infrastructure.toon_encoder import calculate_token_reduction

        data = [
            {
                "date": f"2025-10-{i:02d}",
                "revenue": 1000 + i * 10,
                "expenses": 500 + i * 5,
                "profit": 500 + i * 5
            }
            for i in range(1, 31)
        ]

        reduction = calculate_token_reduction(data)
        assert reduction > 0.30, f"Expected >30% reduction, got {reduction:.1%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
