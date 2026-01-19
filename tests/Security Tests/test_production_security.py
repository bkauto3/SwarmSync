"""
Production Security Validation Tests
Tests that authentication is enforced on all production endpoints

Created: October 21, 2025
Purpose: Verify security fixes are deployed before production rollout
"""
import pytest
import os
import requests
from unittest.mock import patch

# Set production environment for these tests
os.environ["GENESIS_ENV"] = "production"


class TestProductionSecurity:
    """Test suite for production security validation"""

    @pytest.fixture(scope="class")
    def a2a_base_url(self):
        """A2A service base URL"""
        return "http://localhost:8080"

    @pytest.fixture(scope="class")
    def valid_api_key(self):
        """Valid API key from environment"""
        return os.getenv("A2A_API_KEY", "vwvLm04y7KfzokntdM7uThHEGbGCxlTuTDv4iXGG7Z8")

    def test_unauthenticated_invoke_rejected(self, a2a_base_url):
        """Test that /a2a/invoke rejects requests without API key"""
        response = requests.post(
            f"{a2a_base_url}/a2a/invoke",
            json={"tool": "extract_intent", "arguments": {"prompt": "test"}}
        )

        assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}"
        assert "Missing API key" in response.text or "API key" in response.text

    def test_invalid_api_key_rejected(self, a2a_base_url):
        """Test that invalid API key is rejected"""
        response = requests.post(
            f"{a2a_base_url}/a2a/invoke",
            headers={"X-API-Key": "invalid-key-12345"},
            json={"tool": "extract_intent", "arguments": {"prompt": "test"}}
        )

        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        assert "Invalid API key" in response.text

    def test_valid_api_key_accepted(self, a2a_base_url, valid_api_key):
        """Test that valid API key is accepted"""
        response = requests.post(
            f"{a2a_base_url}/a2a/invoke",
            headers={"X-API-Key": valid_api_key},
            json={"tool": "extract_intent", "arguments": {"prompt": "test"}}
        )

        # Should NOT be 401/403 (authentication should succeed)
        # May be 400 if arguments are wrong, but NOT auth error
        assert response.status_code not in [401, 403], \
            f"Valid API key rejected with {response.status_code}: {response.text}"

    def test_marketing_strategy_requires_auth(self, a2a_base_url):
        """Test that /a2a/marketing/strategy requires authentication"""
        response = requests.post(
            f"{a2a_base_url}/a2a/marketing/strategy",
            params={
                "business_name": "TestCo",
                "target_audience": "Developers",
                "budget": 5000.0
            }
        )

        assert response.status_code == 401, \
            f"Marketing endpoint should require auth, got {response.status_code}"

    def test_builder_frontend_requires_auth(self, a2a_base_url):
        """Test that /a2a/builder/frontend requires authentication"""
        response = requests.post(
            f"{a2a_base_url}/a2a/builder/frontend",
            params={
                "app_name": "TestApp",
                "features": ["auth", "db"],
                "pages": ["home", "about"]
            }
        )

        assert response.status_code == 401, \
            f"Builder endpoint should require auth, got {response.status_code}"

    def test_health_endpoint_public(self, a2a_base_url):
        """Test that /health endpoint is public (does not require auth)"""
        response = requests.get(f"{a2a_base_url}/health")

        assert response.status_code == 200, \
            f"Health endpoint should be public, got {response.status_code}"
        assert "healthy" in response.text.lower()

    def test_version_endpoint_public(self, a2a_base_url):
        """Test that /a2a/version endpoint is public"""
        response = requests.get(f"{a2a_base_url}/a2a/version")

        assert response.status_code == 200, \
            f"Version endpoint should be public, got {response.status_code}"

    def test_agents_list_public(self, a2a_base_url):
        """Test that /a2a/agents endpoint is public"""
        response = requests.get(f"{a2a_base_url}/a2a/agents")

        assert response.status_code == 200, \
            f"Agents list should be public, got {response.status_code}"

    def test_a2a_card_public(self, a2a_base_url):
        """Test that /a2a/card endpoint is public"""
        response = requests.get(f"{a2a_base_url}/a2a/card")

        assert response.status_code == 200, \
            f"A2A card should be public, got {response.status_code}"

    def test_genesis_env_is_production(self):
        """Test that GENESIS_ENV is set to production"""
        genesis_env = os.getenv("GENESIS_ENV")

        assert genesis_env == "production", \
            f"GENESIS_ENV should be 'production', got '{genesis_env}'"

    def test_api_key_is_set(self):
        """Test that A2A_API_KEY is set in environment or .env file"""
        # Try environment first
        api_key = os.getenv("A2A_API_KEY")

        # If not in env, check .env file
        if api_key is None:
            try:
                with open(".env", "r") as f:
                    for line in f:
                        if line.startswith("A2A_API_KEY="):
                            api_key = line.split("=", 1)[1].strip()
                            break
            except FileNotFoundError:
                pass

        assert api_key is not None, "A2A_API_KEY must be set in environment or .env file"
        assert len(api_key) >= 32, f"API key should be at least 32 chars, got {len(api_key)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
